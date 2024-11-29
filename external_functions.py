import pypsa
import pandas as pd
import numpy as np
import sqlite3

def connect_to_db(DATABASE_PATH):
    return sqlite3.connect(DATABASE_PATH)

def load_data(DATABASE_PATH):
    conn = connect_to_db(DATABASE_PATH)
    power_plants_df = pd.read_sql_query("SELECT * FROM power_plants", conn)
    buses_df = pd.read_sql_query("SELECT * FROM buses", conn)
    lines_df = pd.read_sql_query("SELECT id, name, from_bus, to_bus, length_km, max_capacity_mw, r, x FROM lines", conn)
    demand_df = pd.read_sql_query("SELECT * FROM demand_profile", conn)
    storage_units_df = pd.read_sql_query("SELECT * FROM storage_units", conn)
    snapshots_df = pd.read_sql_query("SELECT * FROM snapshots", conn)
    wind_profile_df = pd.read_sql_query("SELECT * FROM wind_profile", conn)
    solar_profile_df = pd.read_sql_query("SELECT * FROM solar_profile", conn)
    conn.close()
    return power_plants_df, buses_df, lines_df, demand_df, storage_units_df, snapshots_df, wind_profile_df, solar_profile_df 

def save_data(DATABASE_PATH, table_name, df):
    conn = connect_to_db(DATABASE_PATH)
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    conn.commit()
    conn.close()

def create_network(power_plants_df, buses_df, lines_df, demand_df, storage_units_df, snapshots_df, wind_profile_df, solar_profile_df):
    network = pypsa.Network()  # Create a PyPSA Network

    # Add snapshots to the network
    network.set_snapshots(snapshots_df.loc[:,'snapshot_time'])

    # Add buses to the network
    for _, row in buses_df.iterrows():
        network.add("Bus", row["name"], v_nom=row["voltage_kv"],
                    longitude=row["longitude"], latitude=row["latitude"])

    # Add power plants (generators) to the network
    for _, row in power_plants_df.iterrows():
        bus_name = buses_df.loc[buses_df['id'] == int(row['bus_id']), 'name']
        if not bus_name.empty:
            network.add(
                "Generator",
                row["name"],
                bus=bus_name.values[0],
                p_nom=1e6 if pd.isna(row["capacity_mw"]) else row["capacity_mw"],
                marginal_cost=1e6 if pd.isna(row["srmc"]) else row["srmc"],
                overwrite=True
            )
        else:
            print(f"Warning: Bus ID {row['bus_id']} for generator {row['name']} not found in buses_df.")

    # Add storage units to the network
    for _, row in storage_units_df.iterrows():
        bus_name = buses_df.loc[buses_df['id'] == int(row['bus_id']), 'name']
        if not bus_name.empty:
            network.add(
                "StorageUnit",
                row["name"],
                bus=bus_name.values[0],
                p_nom=row["capacity_mw"],
                e_nom=row["max_energy_mwh"],
                efficiency_store=row["efficiency"],
                efficiency_dispatch=row["efficiency"],
                overwrite=True
            )
        else:
            print(f"Warning: Bus ID {row['bus_id']} for storage unit {row['name']} not found in buses_df.")

    # Add transmission lines to the network
    for _, row in lines_df.iterrows():
        bus0_name = buses_df.loc[buses_df['id'] == int(row['from_bus']), 'name']
        bus1_name = buses_df.loc[buses_df['id'] == int(row['to_bus']), 'name']
        if not bus0_name.empty and not bus1_name.empty:
            network.add(
                "Line",
                row["name"],
                bus0=bus0_name.values[0],
                bus1=bus1_name.values[0],
                length=row["length_km"],
                s_nom=1e6 if pd.isna(row["max_capacity_mw"]) else row["max_capacity_mw"],
                r=row["r"],
                x=row["x"],
                overwrite=True
            )
        else:
            print(f"Warning: Buses for line {row['name']} not found in buses_df (from_bus: {row['from_bus']}, to_bus: {row['to_bus']}).")

    # Add demand as loads to the network (now including snapshot timestamp)
    demand_timeseries = demand_df.pivot(index='snapshot', columns='bus_id', values='demand_mw')

    # Iterate over each bus to add the time series demand data as loads to the network
    for bus_id in demand_timeseries.columns:
        bus_name = buses_df.loc[buses_df['id'] == bus_id, 'name'].values[0]
        if pd.notna(bus_name):
            network.add(
                "Load",
                f"Load_{bus_id}",
                bus=bus_name,
                p_set=demand_timeseries[bus_id]  # Provide entire time series directly
            )
        else:
            print(f"Warning: Bus ID {bus_id} not found in buses_df.")


    # Replace infinities with large finite values (since some solvers cannot handle 'inf')
    network.generators.replace([np.inf], 1e6, inplace=True)
    network.generators.replace([-np.inf], -1e6, inplace=True)
    network.lines.replace([np.inf], 1e6, inplace=True)
    network.lines.replace([-np.inf], -1e6, inplace=True)
    network.loads.replace([np.inf], 1e6, inplace=True)
    network.buses.replace([np.inf], 1e6, inplace=True)
    network.buses.replace([-np.inf], -1e6, inplace=True)

    return network

# This function will generate elements using the provided bus, generator, and line data for cytoscape
def get_network_elements(network):

    nodes_data = []
    edges_data = []

    # Scaling factor for better visualization
    scaling_factor = 100  # Adjust this to scale latitude/longitude appropriately for visualization

    # Buses
    for bus_id, bus in network.buses.iterrows():
        nodes_data.append({
            'data': {
                'id': bus_id,
                'label': bus_id,
                'type': 'bus'
            },
            'position': {
                'x': bus['longitude'] * scaling_factor,
                'y': bus['latitude'] * scaling_factor
            }
        })

    # Generators
    offset_distance = 20  # Distance from bus for placing generators and storage
    for gen_id, gen in network.generators.iterrows():
        bus = network.buses.loc[gen['bus']]
        nodes_data.append({
            'data': {
                'id': gen_id,
                'label': f'{gen_id}({gen["p_nom"]:.0f}MW)',
                'type': 'generator',
                'capacity': gen['p_nom']
            },
            'position': {
                'x': (bus['longitude'] * scaling_factor) + offset_distance,
                'y': (bus['latitude'] * scaling_factor) + offset_distance
            }
        })
        # Add an edge connecting generator to its bus
        edges_data.append({
            'data': {
                'id': f'{gen_id}_to_{gen["bus"]}',
                'source': gen_id,
                'target': gen['bus'],
                'edgeType': 'secondary'
            }
        })
        offset_distance *= -1  # Alternate the direction of the offset

    # Storage Units
    offset_distance = 30
    for storage_id, storage in network.storage_units.iterrows():
        bus = network.buses.loc[storage['bus']]
        nodes_data.append({
            'data': {
                'id': storage_id,
                'label': storage_id,
                'type': 'storage',
                'capacity': storage['p_nom']
            },
            'position': {
                'x': (bus['longitude'] * scaling_factor) + offset_distance,
                'y': (bus['latitude'] * scaling_factor) - offset_distance
            }
        })
        # Add an edge connecting storage to its bus
        edges_data.append({
            'data': {
                'id': f'{storage_id}_to_{storage["bus"]}',
                'source': storage_id,
                'target': storage['bus'],
                'edgeType': 'secondary'
            }
        })
        offset_distance *= -1  # Alternate the direction of the offset

    # Edges (Lines)
    for line_id, line in network.lines.iterrows():
        edges_data.append({
            'data': {
                'id': line_id,
                'source': line['bus0'],
                'target': line['bus1'],
                'length': line['length'],
                'capacity': line['s_nom'],
                'label': f'{line["s_nom"]:.0f}MW'
            }
        })

    return nodes_data + edges_data
