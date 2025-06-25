import pypsa
import pandas as pd
import numpy as np
import sqlite3
import json

import threading
import logging
import sys
from io import StringIO
from queue import Queue, Empty

# Global stream for capturing logs
log_stream = StringIO()
interval_disabled = False

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

def load_data_for_diagram(DATABASE_PATH):
    conn = connect_to_db(DATABASE_PATH)
    power_plants_df = pd.read_sql_query("SELECT * FROM power_plants", conn)
    buses_df = pd.read_sql_query("SELECT * FROM buses", conn).set_index('id')
    lines_df = pd.read_sql_query("SELECT id, name, from_bus, to_bus, length_km, max_capacity_mw, r, x FROM lines", conn)
    storage_units_df = pd.read_sql_query("SELECT * FROM storage_units", conn)
    conn.close()
    return power_plants_df, buses_df, lines_df, storage_units_df

def load_data_table(DATABASE_PATH, table):
    conn = connect_to_db(DATABASE_PATH)
    df = pd.read_sql_query("SELECT * FROM " + str(table), conn)
    conn.close()
    return df 


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
                    longitude=row["longitude"], latitude=row["latitude"], carrier="AC")

    # Add power plants (generators) to the network
    for _, row in power_plants_df.iterrows():
        bus_name = buses_df.loc[buses_df['id'] == int(row['bus_id']), 'name']
        if not bus_name.empty:
            p_nom_max = row["capacity_mw"]

            # Determine the generation profile
            if row['type'] == 'Solar':
                filtered_df = solar_profile_df[solar_profile_df['profile_name'] == row['profile']]
            elif row['type'] == 'Wind':
                filtered_df = wind_profile_df[wind_profile_df['profile_name'] == row['profile']]
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
                type=row['type'],
                e_sum_max=1e10,  # Temporary set to very high number.  Default value of infinity would otherwise be overwritten by 1e6 which could be binding.
                overwrite=True
            )
        else:
            print(f"Warning: Bus ID {row['bus_id']} for generator {row['name']} not found in buses_df.")


    # Add storage units to the network
    for _, row in storage_units_df.iterrows():
        # Determine storage_name, handling potential KeyError if 'name' column is missing
        storage_name_val = None
        if 'name' in row.index and pd.notna(row['name']) and str(row['name']).strip():
            storage_name_val = row['name']
        else:
            storage_id_val = row.get('id', 'UnknownID') # .get() is safe for potentially missing 'id' column
            storage_name_val = f"StorageUnit_{storage_id_val}"
            if 'name' not in row.index:
                # This message is helpful if the entire column is missing.
                # To avoid printing for every row if column is missing, this could be outside loop.
                # For now, this provides context per problematic row.
                print(f"Info: 'name' key missing for storage unit row (ID: '{storage_id_val}'). Using default name '{storage_name_val}'.")
            elif pd.isna(row['name']) or not str(row['name']).strip():
                print(f"Info: Empty name for storage unit ID '{storage_id_val}'. Using default name '{storage_name_val}'.")

        bus_id_val = row.get('bus_id') # bus_id seems to exist based on traceback

        bus_name_series = pd.Series(dtype=str) # Default to empty series
        if bus_id_val is not None and pd.notna(bus_id_val):
            try:
                bus_id_lookup = int(bus_id_val)
                # Check if bus_id_lookup exists in the 'id' column of buses_df
                if bus_id_lookup in buses_df['id'].unique():
                    bus_name_series = buses_df.loc[buses_df['id'] == bus_id_lookup, 'name']
            except ValueError:
                 print(f"Warning: bus_id '{bus_id_val}' for storage unit '{storage_name_val}' is not a valid integer.")

        if not bus_name_series.empty:
            network.add(
                "StorageUnit",
                storage_name_val, # Use the determined/defaulted name
                bus=bus_name_series.values[0],
                p_nom=row.get("capacity_mw", 0), # Use .get for safety
                e_nom=row.get("max_energy_mwh", 0), # Use .get for safety
                efficiency_store=row.get("efficiency", 1.0), # Default efficiency
                efficiency_dispatch=row.get("efficiency", 1.0), # Default efficiency
                overwrite=True
            )
        else:
            # This is the original error location
            print(f"Warning: Bus ID {bus_id_val} for storage unit '{storage_name_val}' not found in buses_df.")

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
                carrier="AC",
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

def get_network_elements(network):
    nodes_data = []
    edges_data = []

    # Buses
    for bus_id, bus in network.buses.iterrows():
        nodes_data.append({
            'id': str(bus_id),
            'label': str(bus_id),
            'type': 'bus',
            'x': bus['longitude'],
            'y': bus['latitude']
        })

    # Generators
    for gen_id, gen in network.generators.iterrows():
        bus = network.buses.loc[gen['bus']]

        if gen['p_nom'] > 0:
            nodes_data.append({
                'id': str(gen_id),
                'label': f'{gen_id}({gen["p_nom"]:.0f}MW)',
                'type': 'generator',
                'fuel': gen['type'],  # To identify wind and solar plant
                'capacity': gen['p_nom'],
                'x': bus['longitude'],
                'y': bus['latitude']
            })
            # Add an edge connecting generator to its bus
            edges_data.append({
                'source': str(gen_id),
                'target': str(gen['bus']),
                'type': 'secondary'
            })
    
    # Storage Units
    for storage_id, storage in network.storage_units.iterrows():
        bus = network.buses.loc[storage['bus']]
        nodes_data.append({
            'id': str(storage_id),
            'label': str(storage_id),
            'type': 'storage',
            'capacity': storage['p_nom'],
            'x': bus['longitude'],
            'y': bus['latitude']
        })
        # Add an edge connecting storage to its bus
        edges_data.append({
            'source': str(storage_id),
            'target': str(storage['bus']),
            'type': 'secondary'
        })

    # Edges (Lines)
    for line_id, line in network.lines.iterrows():

        edges_data.append({
            'source': str(line['bus0']),
            'target': str(line['bus1']),
            'length': line['length'],
            'capacity': line['s_nom'],
            'label': f'{line["s_nom"]:.0f}MW',
            'type': 'primary'
        })
    
    # Clean output: Convert to JSON
    clean_data = {
        "nodes": nodes_data,
        "links": edges_data
    }

    return json.dumps(clean_data)


def get_network_elements_from_df(DATABASE_PATH, power_plants_df_override=None, buses_df_override=None, lines_df_override=None, storage_units_df_override=None):
    nodes_data = []
    edges_data = []

    # Load data: use override if provided, else load from DB
    if power_plants_df_override is not None:
        power_plants_df = power_plants_df_override
    else:
        power_plants_df = load_data_table(DATABASE_PATH, 'power_plants')

    if buses_df_override is not None:
        buses_df = buses_df_override.set_index('id' if 'id' in buses_df_override.columns else buses_df_override.index.name)
    else:
        buses_df = load_data_table(DATABASE_PATH, 'buses').set_index('id')

    if lines_df_override is not None:
        lines_df = lines_df_override
    else:
        lines_df = load_data_table(DATABASE_PATH, 'lines')

    if storage_units_df_override is not None:
        storage_units_df = storage_units_df_override
    else:
        storage_units_df = load_data_table(DATABASE_PATH, 'storage_units')


    # Buses
    # Ensure buses_df has 'id' in columns if it's not the index, for itertuples
    processed_buses_df = buses_df.reset_index() if buses_df.index.name == 'id' or 'id' in buses_df.columns else buses_df
    if 'id' not in processed_buses_df.columns and 'Index' not in processed_buses_df.columns: # if 'id' was index and reset
        processed_buses_df.rename(columns={'index':'id'}, inplace=True)


    for bus_row in processed_buses_df.itertuples():
        # bus_id = bus_row.id if hasattr(bus_row, 'id') else bus_row.Index # Access 'id' or 'Index'
        bus_id_attr = 'id' if 'id' in processed_buses_df.columns else 'Index'
        bus_id = getattr(bus_row, bus_id_attr)

        nodes_data.append({
            'id': str(bus_id),
            'name': bus_row.name,
            'label': bus_row.name,
            'type': 'bus',
            'x': bus_row.longitude,
            'y': bus_row.latitude
        })

    # Edges (Lines)
    for line_row in lines_df.itertuples():
        edges_data.append({
            'source': str(line_row.from_bus),
            'target': str(line_row.to_bus),
            'length': line_row.length_km,
            'capacity': line_row.max_capacity_mw,
            'label': f'{line_row.max_capacity_mw:.0f}MW',
            'type': 'primary'
        })
    
    # Generators
    for gen_row in power_plants_df.itertuples():
        # Ensure bus_id is correctly accessed (it might be int or string due to various sources)
        bus_id_val = int(gen_row.bus_id) if isinstance(gen_row.bus_id, (str, float)) and str(gen_row.bus_id).isdigit() else gen_row.bus_id
        
        # Check if bus_id_val exists in the index of buses_df
        if bus_id_val not in buses_df.index:
            print(f"Warning: Bus ID {bus_id_val} for generator {gen_row.name} not found in buses_df. Available bus IDs: {buses_df.index.tolist()}")
            continue # Skip this generator if its bus is not found
            
        bus = buses_df.loc[bus_id_val]

        if gen_row.capacity_mw > 0:
            nodes_data.append({
                'id': 'gen'+str(gen_row.id),
                'name': str(gen_row.name),
                'label': f'{gen_row.name}({gen_row.capacity_mw:.0f}MW)',
                'type': 'generator',
                'fuel': gen_row.type,  # To identify wind and solar plant
                'capacity': gen_row.capacity_mw,
                'x': bus['longitude'], # bus is a Series, access normally
                'y': bus['latitude']  # bus is a Series, access normally
            })
            # Add an edge connecting generator to its bus
            edges_data.append({
                'source': 'gen'+str(gen_row.id),
                'target': str(gen_row.bus_id),
                'type': 'secondary'
            })
    
    # Storage Units
    for storage_row in storage_units_df.itertuples():
        bus_id_val = int(storage_row.bus_id) if isinstance(storage_row.bus_id, (str, float)) and str(storage_row.bus_id).isdigit() else storage_row.bus_id
        
        if bus_id_val not in buses_df.index:
            print(f"Warning: Bus ID {bus_id_val} for storage unit {storage_row.name} not found in buses_df. Available bus IDs: {buses_df.index.tolist()}")
            continue # Skip this storage unit if its bus is not found

        bus = buses_df.loc[bus_id_val]
        nodes_data.append({
            'id': 'storage'+str(storage_row.id),
            'name': str(storage_row.name),
            'label': storage_row.name,
            'type': 'storage',
            'capacity': storage_row.capacity_mw,
            'x': bus['longitude'], # bus is a Series, access normally
            'y': bus['latitude']   # bus is a Series, access normally
        })
        # Add an edge connecting storage to its bus
        edges_data.append({
            'source': 'storage'+str(storage_row.id),
            'target': str(storage_row.bus_id),
            'type': 'secondary'
        })


    # Clean output: Convert to JSON
    clean_data = {
        "nodes": nodes_data,
        "links": edges_data
    }

    return json.dumps(clean_data)


def calc_aggregate_capacities(DATABASE_PATH, power_plants_df_override=None): # Allow override for consistency

    if power_plants_df_override is not None:
        power_plants_df_to_use = power_plants_df_override
    else:
        # Fallback to loading from DB if no override is provided
        # Note: This part of calc_aggregate_capacities might need its own set of overrides
        # if it's meant to reflect in-memory changes from various sources.
        # For now, just using power_plants.
        power_plants_df_to_use = load_data_table(DATABASE_PATH, 'power_plants')


    solar_capacity = power_plants_df_to_use.loc[power_plants_df_to_use['type'] == 'Solar', 'capacity_mw'].sum()
    wind_capacity = power_plants_df_to_use.loc[power_plants_df_to_use['type'] == 'Wind', 'capacity_mw'].sum()
    dsr_capacity = power_plants_df_to_use.loc[power_plants_df_to_use['type'] == 'DSR', 'capacity_mw'].sum()

    return solar_capacity, wind_capacity, dsr_capacity



# Function to Run Optimization and Capture Output
def run_optimization(network):

    # Load network data and create PyPSA network object
    # power_plants_df, storage_units_df, buses_df, lines_df, demand_df, snapshots_df, wind_profile_df, solar_profile_df  = load_data(DATABASE_PATH)
    # network = create_network(power_plants_df, storage_units_df, buses_df, lines_df, demand_df, snapshots_df, wind_profile_df, solar_profile_df)

    # Set up logging 
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    try:
        logger.info("Starting network optimization...")

        try:
            network.optimize(solver_name='cplex')
            logger.info("Optimization complete!")
            optimization_successful = True
        except Exception as opt_error:  # Catch solver errors
            logger.exception("Error during optimization: %s", opt_error)
            logger.debug("CPLEX log: %s", network.opt.get_log())  # Log CPLEX solver's internal log!
            optimization_successful = False  # Mark optimization as unsuccessful
            raise  # Re-raise the error for the main thread to handle

        # Process results if optimization was successful
        if optimization_successful:

            # Convert the snapshots to a list of strings for JSON serialization
            snapshots_list = [str(snapshot) for snapshot in network.snapshots]

            # Store the optimization results as a dictionary
            optimization_results_dict = {
                "snapshots": snapshots_list,
                "generators_t_p": {
                    "data": network.generators_t.p.rename(index=str).to_dict(),
                    "types": network.generators["type"].to_dict()  # Add generator types from the network object
                },
                "storage_units_t_p": network.storage_units_t.p.rename(index=str).to_dict(),
                "buses_t_marginal_price": network.buses_t.marginal_price.rename(index=str).to_dict()
            }

            return optimization_results_dict

    except Exception as e:
        logger.exception("An unexpected error occurred: %s", e)
        return None
