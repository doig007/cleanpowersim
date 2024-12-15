from dash import html, Input, Output, MATCH, clientside_callback
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto

import pypsa
import pandas as pd
import numpy as np
import sqlite3
import json

from network_styles import cytoscape_styles  # Import the external stylesheet

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
    # Saves the provided dataframe 'df' into the table 'table_name' in the database located at DATABASE_PATH
    conn = connect_to_db(DATABASE_PATH)
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    conn.commit()
    conn.close()

def create_network(power_plants_df, buses_df, lines_df, demand_df, storage_units_df, snapshots_df, wind_profile_df, solar_profile_df):
    network = pypsa.Network()  # Create a PyPSA Network

    # Add snapshots to the network
    network.set_snapshots(pd.to_datetime(snapshots_df['snapshot_time'], dayfirst=True))

    solar_profile_df.index = pd.to_datetime(solar_profile_df.index, dayfirst=True)
    wind_profile_df.index = pd.to_datetime(wind_profile_df.index, dayfirst=True)

    solar_profile_df['snapshot_time'] = pd.to_datetime(solar_profile_df['snapshot_time'], errors='coerce', dayfirst=True)
    wind_profile_df['snapshot_time'] = pd.to_datetime(wind_profile_df['snapshot_time'], errors='coerce', dayfirst=True)

    # Add buses to the network
    for _, row in buses_df.iterrows():
        network.add("Bus", row["name"], v_nom=row["voltage_kv"],
                    longitude=row["longitude"], latitude=row["latitude"])

    # Add power plants (generators) to the network
    for _, row in power_plants_df.iterrows():
        bus_name = buses_df.loc[buses_df['id'] == int(row['bus_id']), 'name']
        if not bus_name.empty:
            p_nom_max = row["capacity_mw"]

            # Determine the generation profile
            if row['type'] == 'Solar':
                filtered_df = solar_profile_df[solar_profile_df['profile'] == row['profile']]
            elif row['type'] == 'Wind':
                filtered_df = wind_profile_df[wind_profile_df['profile'] == row['profile']]
            else:
                filtered_df = pd.DataFrame()

            # Validate and set the profile
            if not filtered_df.empty and 'snapshot_time' in filtered_df.columns:
                profile = filtered_df.set_index('snapshot_time')['profile']
                profile = profile.reindex(network.snapshots).fillna(1)  # Align with network snapshots
            else:
                profile = pd.Series(1.0, index=network.snapshots)

            # Add generator to the network
            network.add(
                "Generator",
                row["name"],
                bus=bus_name.values[0],
                p_nom=p_nom_max,
                p_max_pu=profile,
                marginal_cost=row["srmc"],
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

    # Ensure snapshot alignment
    demand_timeseries.index = pd.to_datetime(demand_timeseries.index, dayfirst=True)
    network.snapshots = pd.to_datetime(network.snapshots, dayfirst=True)

    # Reindex demand data to match network snapshots
    demand_timeseries = demand_timeseries.reindex(network.snapshots).fillna(0)

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

    # Buses
    for bus_id, bus in network.buses.iterrows():
        nodes_data.append({
            'data': {
                'id': bus_id,
                'label': bus_id,
                'type': 'bus'
            },
            'position': {
                'x': bus['longitude'],
                'y': bus['latitude']
            }
        })

    # Generators
    for gen_id, gen in network.generators.iterrows():
        bus = network.buses.loc[gen['bus']]
        size = max(1, min(50, gen['p_nom'] / 100))  # Scale capacity between 1 and 50
        nodes_data.append({
            'data': {
                'id': gen_id,
                'label': f'{gen_id}({gen["p_nom"]:.0f}MW)',   # Tooltip content
                'type': 'generator',
                'capacity': gen['p_nom'],
                'size': size
            },
            'position': {
                'x': (bus['longitude']),
                'y': (bus['latitude'])
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

    # Storage Units
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
                'x': (bus['longitude']),
                'y': (bus['latitude'])
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

def create_diagram_tab(DATABASE_PATH):

    power_plants_df, buses_df, lines_df, demand_df, storage_units_df, snapshots_df, wind_profile_df, solar_profile_df = load_data(DATABASE_PATH)    # Reload the data from the database
    network = create_network(power_plants_df, buses_df, lines_df, demand_df, storage_units_df, snapshots_df, wind_profile_df, solar_profile_df)
    elements = get_network_elements(network)

    graph_id = 'network-graph-diagram'

    tab_content = html.Div([
            html.H2("Network Diagram", className='text-center my-4'),
            dbc.ButtonGroup(
                [
                    dbc.Button(html.I(className="bi bi-zoom-in"), id={'type': 'zoom-button', 'index': 'zoom-in'}, color="primary"),
                    dbc.Button(html.I(className="bi bi-zoom-out"), id={'type': 'zoom-button', 'index': 'zoom-out'}, color="primary"),
                    dbc.Button(html.I(className="bi bi-arrows-fullscreen"), id={'type': 'zoom-button', 'index': 'fit'}, color="primary")
                ],
                className="d-flex justify-content-center my-2"
            ),
            html.Div(
                cyto.Cytoscape(
                    id=graph_id,
                    elements=elements,
                    style={'width': '100%', 'height': '600px'},
                    layout={'name': 'cose'},
                    zoom=1,
                    minZoom=0.5,
                    maxZoom=3,
                    userZoomingEnabled=True,
                    userPanningEnabled=True,
                    stylesheet=cytoscape_styles,
                    autoungrabify=True
                ),
                # Add data attributes for javascript access
                **{'data-elements': json.dumps(elements), 'data-stylesheet': json.dumps(cytoscape_styles)}
            ),
            html.Div(id='tooltip', style={'display': 'none', 'position': 'absolute', 'z-index': '1000'})
    ])

    return tab_content

    