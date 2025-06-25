import dash
from dash import dcc, html, Input, Output, State, MATCH, ALL, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash.dependencies import ClientsideFunction

import pandas as pd
import io
import base64
import os
import tempfile

from functools import lru_cache

from page_layout import display_page, get_menu_layout, set_active_links, generate_result_charts
from external_functions import load_data, save_data, load_data_table, get_network_elements_from_df, create_network, run_optimization
from results_charts import generate_dashboard_chart

from external_functions import log_stream, interval_disabled  # Import global variables


# Set up the SQLite database connection function
DATABASE_PATH = 'power_system.db'

# Load data into Pandas DataFrame from SQLite
power_plants_df, buses_df, lines_df, demand_df, storage_units_df, snapshots_df, wind_profile_df, solar_profile_df = load_data(DATABASE_PATH)

# Initialize Dash app with Bootstrap stylesheet
app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdnjs.cloudflare.com/ajax/libs/bootstrap-icons/1.8.1/font/bootstrap-icons.min.css"
    ]
)

app.title = 'Clean Power Sim'
app._favicon = ("assets/favicon.ico")


# Define layout with an enhanced sidebar for navigation
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(get_menu_layout(), width=3, style={'padding': '0', 'margin': '0'}),  # Enhanced Sidebar column from separate module
        dbc.Col([
            dcc.Location(id='url', refresh=False),
            html.Div(id='page-content'),  # Main content area
            html.Div(id='upload-feedback'), # For upload status messages
            
            # Modal to display progress and solver output
            dbc.Modal(
                [
                    dbc.ModalHeader("Running Optimization"),
                    dbc.ModalBody([
                        dbc.Progress(id="optimization-progress", value=0, striped=True, animated=True),
                        html.H3("Solver Command Line Output:", className="text-primary mb-4 fs-6"),
                        html.Div(id="solver-output", style={"marginTop": "20px", "whiteSpace": "pre-wrap", "minHeight":"200px", "maxHeight": "300px", "overflowY": "scroll"})
                    ]),
                    dbc.ModalFooter(
                        dbc.Button("Close", id="close-modal-btn", className="ms-auto", n_clicks=0)
                    ),
                ],
                id="optimization-modal",
                is_open=False,
                size="lg"
            ),
        ], width=9)  # Main content column
    ]),
    dcc.Store(id='optimization-intent', data=False, storage_type='memory'),  # Track user intent to run optimization
    dcc.Interval(id="optimization-interval", interval=1000, n_intervals=0, disabled=True),  # Interval for updates
    dcc.Store(id='optimization-progress-store', data=0, storage_type='memory'),  # Store for progress updates
    dcc.Store(id='optimization-results', data=None, storage_type='memory'),  # Store to keep optimization results
    dcc.Store(id={'type': 'save-status', 'index': 'global'}, data=0, storage_type='memory'),
    # Stores for edited table data
    dcc.Store(id={'type': 'edited-table-store', 'index': 'power-plants'}, storage_type='memory'),
    dcc.Store(id={'type': 'edited-table-store', 'index': 'buses'}, storage_type='memory'),
    dcc.Store(id={'type': 'edited-table-store', 'index': 'lines'}, storage_type='memory'),
    dcc.Store(id={'type': 'edited-table-store', 'index': 'demand-profile'}, storage_type='memory'),
    dcc.Store(id={'type': 'edited-table-store', 'index': 'storage-units'}, storage_type='memory'),
    dcc.Store(id={'type': 'edited-table-store', 'index': 'snapshots'}, storage_type='memory'),
    dcc.Store(id={'type': 'edited-table-store', 'index': 'wind-profile'}, storage_type='memory'),
    dcc.Store(id={'type': 'edited-table-store', 'index': 'solar-profile'}, storage_type='memory')
], fluid=True)

############################
### Callback definitions ###
############################

# Main callback to display pages based on navigation and handle active link highlighting
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')],
    [State('optimization-intent', 'data'),
     State('optimization-results', 'data')]
)
def update_page_content(pathname, optimization_intent, optimization_results):
    return display_page(pathname, optimization_intent, optimization_results)

@app.callback(
    [
        Output('dashboard-link', 'active'),
        Output('editor-link', 'toggle_style'), # using dropdown menu (no active prop) so manually changing background color
        Output('diagram-link', 'active'),
        Output('settings-link', 'active'),
        Output('results-link', 'active')
    ],
    [Input('url', 'pathname')]
)
def update_active_links(pathname):
    active_links = set_active_links(pathname)
    return active_links


# Callback for saving changes in the Editor pages
@app.callback(
    [Output({'type': 'save-status', 'index': MATCH}, 'data', allow_duplicate=True),
     Output({'type': 'edited-table-store', 'index': MATCH}, 'data', allow_duplicate=True)],
    [Input({'type': 'save-changes-btn', 'index': ALL}, 'n_clicks')],
    [State({'type': 'data-table', 'index': ALL}, 'data')],
    prevent_initial_call=True
)
def save_changes(n_clicks_list, tables_data_list):

    if (not ctx.triggered) or (not any(n_clicks_list)):
        raise PreventUpdate

    # Determine which button was triggered and get its corresponding index
    triggered_button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    triggered_index = dash.callback_context.inputs_list[0][0]['id']['index']


    # Find the corresponding table data
    table_data = None
    for i, state_input in enumerate(dash.callback_context.states_list[0]):
        if state_input['id']['index'] == triggered_index:
            table_data = tables_data_list[i]
            break
    
    if table_data is None:
        raise PreventUpdate

    df = pd.DataFrame(table_data)
    # Instead of saving to DB, store in dcc.Store
    # save_data(DATABASE_PATH, triggered_index.replace('-', '_'), df)
    print(f"Storing data for {triggered_index} in dcc.Store")

    return 1, df.to_dict('records')


# Callback to run optimization (via setting intent) and navigate to results page when the run optimization button is clicked
@app.callback(
    [
        Output('url', 'pathname'), 
        Output('optimization-intent', 'data', allow_duplicate=True),
        Output('optimization-modal', 'is_open', allow_duplicate=True)
    ],
    [
        Input('run-model-btn', 'n_clicks')
    ],
    [        
        State('optimization-modal', 'is_open')
    ],
    prevent_initial_call=True
)
def navigate_to_results_and_set_intent(n_clicks, optimization_modal):
    if n_clicks:
        # Navigate to results page and set optimization intent to True and modal to True
        return '/results', True, True
    raise PreventUpdate  # Prevent unnecessary updates if not clicked

# Callback to run optimization when the intent is set
@app.callback(
    [
        Output('optimization-intent', 'data', allow_duplicate=True),  # Reset the intent after running
        Output('optimization-results', 'data', allow_duplicate=True),  # Store the results
        Output('optimization-interval', 'disabled', allow_duplicate=True), # Set the interval for async running of optimization
        Output({'type': 'run-output', 'index': 'results'}, 'children', allow_duplicate=True), # Output to display the result of the optimization
        Output({'type': 'dynamic-graphs-container', 'index': 'results'}, 'children', allow_duplicate=True), # Output to display the charts of the optimization result
        Output("optimization-modal", "is_open", allow_duplicate=True), # Close the modal after optimization
    ],
    [Input('optimization-intent', 'data')],
    [
        State('url', 'pathname'), # Add pathname to check if on results page
        State({'type': 'edited-table-store', 'index': 'power-plants'}, 'data'),
        State({'type': 'edited-table-store', 'index': 'buses'}, 'data'),
        State({'type': 'edited-table-store', 'index': 'lines'}, 'data'),
        State({'type': 'edited-table-store', 'index': 'demand-profile'}, 'data'),
        State({'type': 'edited-table-store', 'index': 'storage-units'}, 'data'),
        State({'type': 'edited-table-store', 'index': 'snapshots'}, 'data'),
        State({'type': 'edited-table-store', 'index': 'wind-profile'}, 'data'),
        State({'type': 'edited-table-store', 'index': 'solar-profile'}, 'data')
    ],
    prevent_initial_call=True
)
def run_optimization_callback(optimization_intent, pathname,
                               edited_power_plants, edited_buses, edited_lines, 
                               edited_demand, edited_storage_units, edited_snapshots, 
                               edited_wind_profile, edited_solar_profile):
    global interval_disabled
    # Access global DataFrames (loaded at app start)
    global power_plants_df, buses_df, lines_df, demand_df, storage_units_df, snapshots_df, wind_profile_df, solar_profile_df


    if optimization_intent:     
        print("Running optimization...")

        # Function to get DataFrame, preferring edited data from store, else global copy
        def get_df_from_store_or_global(edited_data, global_df_ref):
            if edited_data:
                print(f"Using edited data for {global_df_ref.attrs.get('name', 'unknown table')}")
                return pd.DataFrame(edited_data)
            else:
                print(f"Using global data for {global_df_ref.attrs.get('name', 'unknown table')}")
                # Add a name attribute to global dfs for easier logging if not already present
                if 'name' not in global_df_ref.attrs:
                    # This is a bit of a hack for logging; ideally, names are known
                    for name, df_val in globals().items():
                        if df_val is global_df_ref:
                            global_df_ref.attrs['name'] = name
                            break
                return global_df_ref.copy() # Use a copy of the global DataFrame

        # Prepare DataFrames for network creation
        current_power_plants_df = get_df_from_store_or_global(edited_power_plants, power_plants_df)
        current_buses_df = get_df_from_store_or_global(edited_buses, buses_df)
        current_lines_df = get_df_from_store_or_global(edited_lines, lines_df)
        current_demand_df = get_df_from_store_or_global(edited_demand, demand_df)
        current_storage_units_df = get_df_from_store_or_global(edited_storage_units, storage_units_df)
        current_snapshots_df = get_df_from_store_or_global(edited_snapshots, snapshots_df)
        current_wind_profile_df = get_df_from_store_or_global(edited_wind_profile, wind_profile_df)
        current_solar_profile_df = get_df_from_store_or_global(edited_solar_profile, solar_profile_df)
        
        network = create_network(current_power_plants_df, current_storage_units_df, current_buses_df, current_lines_df, 
                                 current_demand_df, current_snapshots_df, current_wind_profile_df, current_solar_profile_df)

        # Run optimization directly (no threading)
        optimization_results = run_optimization(network)  # Get the results directly

        if optimization_results is not None:  # Check result from optimization
            print("Optimization complete! storing results.") # Check to see if it completes
            interval_disabled = True # disable interval as soon as result or exception occurs.

            charts_html = generate_result_charts(optimization_results)
            run_output = "Optimization complete!"
            # Only update page content if on the /results page
            if pathname == '/results':
                return False, optimization_results, interval_disabled, run_output, charts_html, False
            else:
                return False, optimization_results, interval_disabled, dash.no_update, dash.no_update, False
        else:
            print("Optimization Failed.  Returning None")
            interval_disabled = True # disable interval as soon as result or exception occurs.

            charts_html = "Charts will appear here once the model has finished optimization"
            run_output = "Optimization model has failed."
            # Only update page content if on the /results page
            if pathname == '/results':
                return False, None, interval_disabled, run_output, charts_html, True
            else:
                return False, None, interval_disabled, dash.no_update, dash.no_update, True

    else:
        # If optimization_intent is False, none of these outputs should update.
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update


# Callback to Update Logs and Fetch Results
@app.callback(
    [
        Output('optimization-progress', 'value'),
        Output('solver-output', 'children'),
        Output('optimization-results', 'data', allow_duplicate=True),
        Output('optimization-interval', 'disabled', allow_duplicate=True),
    ],
    Input("optimization-interval", "n_intervals"),
    [State("solver-output", "children"),
     State("optimization-results", "data")],
     State('optimization-interval','disabled'),
    prevent_initial_call=True,
)
def update_logs_and_fetch_results(n_intervals, current_output, current_results, interval_disabled_state):
    global log_stream
    global interval_disabled

    if interval_disabled: # Prevent updates and further checks if already disabled
        raise PreventUpdate

    # Initialize progress
    progress = min(n_intervals*0.1, 100)  # Simulate progress

    # Fetch new logs from the log stream
    log_stream.seek(0)
    new_logs = log_stream.read()
    log_stream.truncate(0)
    log_stream.seek(0)

    # Append new logs to the current output
    updated_output = current_output or ""
    updated_output += "\n" + new_logs

    progress = 100

    return progress, updated_output, current_results, interval_disabled



# Callback to close solver modal on button click
@app.callback(
    Output("optimization-modal", "is_open", allow_duplicate=True),
    Input("close-modal-btn", "n_clicks"),
    State("optimization-modal", "is_open"),
    prevent_initial_call=True
)
def close_modal(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open


# Callback to handle downloading entire network file as Excel
@app.callback(
    Output('download-network-excel', 'data'),
    Input('download-network-btn', 'n_clicks'),
    [
        State({'type': 'edited-table-store', 'index': 'power-plants'}, 'data'),
        State({'type': 'edited-table-store', 'index': 'buses'}, 'data'),
        State({'type': 'edited-table-store', 'index': 'lines'}, 'data'),
        State({'type': 'edited-table-store', 'index': 'demand-profile'}, 'data'),
        State({'type': 'edited-table-store', 'index': 'storage-units'}, 'data'),
        State({'type': 'edited-table-store', 'index': 'snapshots'}, 'data'),
        State({'type': 'edited-table-store', 'index': 'wind-profile'}, 'data'),
        State({'type': 'edited-table-store', 'index': 'solar-profile'}, 'data')
    ],
    prevent_initial_call=True
)
def download_network_data(n_clicks,
                           edited_power_plants, edited_buses, edited_lines,
                           edited_demand, edited_storage_units, edited_snapshots,
                           edited_wind_profile, edited_solar_profile):
    if not n_clicks:
        raise PreventUpdate

    # Access global DataFrames (loaded at app start)
    global power_plants_df, buses_df, lines_df, demand_df, storage_units_df, snapshots_df, wind_profile_df, solar_profile_df

    # Helper function (similar to run_optimization_callback)
    def get_df_for_download(edited_data, global_df_ref):
        if edited_data:
            df = pd.DataFrame(edited_data)
            # Attempt to convert known date columns back to datetime if they were stringified
            # This is important for Excel to recognize them as dates.
            if global_df_ref.attrs.get('name') == 'demand_df' and 'snapshot' in df.columns:
                df['snapshot'] = pd.to_datetime(df['snapshot'])
            elif global_df_ref.attrs.get('name') == 'snapshots_df' and 'snapshot_time' in df.columns:
                 df['snapshot_time'] = pd.to_datetime(df['snapshot_time'])
            return df
        else:
            return global_df_ref.copy()

    # Prepare DataFrames for Excel export
    # Assigning names to global_df_ref.attrs for the helper if not already done (as in run_optimization)
    # This should ideally be done once at app startup.
    if 'name' not in power_plants_df.attrs: power_plants_df.attrs['name'] = 'power_plants_df'
    if 'name' not in buses_df.attrs: buses_df.attrs['name'] = 'buses_df'
    if 'name' not in lines_df.attrs: lines_df.attrs['name'] = 'lines_df'
    if 'name' not in demand_df.attrs: demand_df.attrs['name'] = 'demand_df'
    if 'name' not in storage_units_df.attrs: storage_units_df.attrs['name'] = 'storage_units_df'
    if 'name' not in snapshots_df.attrs: snapshots_df.attrs['name'] = 'snapshots_df'
    if 'name' not in wind_profile_df.attrs: wind_profile_df.attrs['name'] = 'wind_profile_df'
    if 'name' not in solar_profile_df.attrs: solar_profile_df.attrs['name'] = 'solar_profile_df'
    
    current_power_plants_df = get_df_for_download(edited_power_plants, power_plants_df)
    current_buses_df = get_df_for_download(edited_buses, buses_df)
    current_lines_df = get_df_for_download(edited_lines, lines_df)
    current_demand_df = get_df_for_download(edited_demand, demand_df)
    current_storage_units_df = get_df_for_download(edited_storage_units, storage_units_df)
    current_snapshots_df = get_df_for_download(edited_snapshots, snapshots_df)
    current_wind_profile_df = get_df_for_download(edited_wind_profile, wind_profile_df)
    current_solar_profile_df = get_df_for_download(edited_solar_profile, solar_profile_df)

    # Create an Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        current_power_plants_df.to_excel(writer, sheet_name='Power Plants', index=False)
        current_buses_df.to_excel(writer, sheet_name='Buses', index=False)
        current_lines_df.to_excel(writer, sheet_name='Transmission Lines', index=False)
        current_demand_df.to_excel(writer, sheet_name='Demand Profile', index=False)
        current_storage_units_df.to_excel(writer, sheet_name='Storage Units', index=False)
        current_snapshots_df.to_excel(writer, sheet_name='Snapshots', index=False)
        current_wind_profile_df.to_excel(writer, sheet_name='Wind Profile', index=False)
        current_solar_profile_df.to_excel(writer, sheet_name='Solar Profile', index=False)
    output.seek(0)

    return dcc.send_bytes(output.getvalue(), "network_data.xlsx")


# Callback to handle uploading replacement network file
@app.callback(
    [
        Output('upload-feedback', 'children'),
        Output({'type': 'edited-table-store', 'index': 'power-plants'}, 'data', allow_duplicate=True),
        Output({'type': 'edited-table-store', 'index': 'buses'}, 'data', allow_duplicate=True),
        Output({'type': 'edited-table-store', 'index': 'lines'}, 'data', allow_duplicate=True),
        Output({'type': 'edited-table-store', 'index': 'demand-profile'}, 'data', allow_duplicate=True),
        Output({'type': 'edited-table-store', 'index': 'storage-units'}, 'data', allow_duplicate=True),
        Output({'type': 'edited-table-store', 'index': 'snapshots'}, 'data', allow_duplicate=True),
        Output({'type': 'edited-table-store', 'index': 'wind-profile'}, 'data', allow_duplicate=True),
        Output({'type': 'edited-table-store', 'index': 'solar-profile'}, 'data', allow_duplicate=True)
    ],
    Input('upload-network-btn', 'n_clicks'),
    [State('upload-network-file', 'contents'),
     State('upload-network-file', 'filename')],
    prevent_initial_call=True
)
def upload_network_data(n_clicks, contents, filename):
    if not contents or n_clicks is None:
        raise PreventUpdate
    
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    temp_file_path = None  # Initialize to ensure it's defined in finally
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            temp_file.write(decoded)
            temp_file_path = temp_file.name

        # Load the uploaded Excel file into Pandas DataFrames
        xls = pd.ExcelFile(temp_file_path)
        
        # Define expected sheets and their corresponding global DataFrame names for fallback
        sheet_map = {
            'Power Plants': 'power-plants',
            'Buses': 'buses',
            'Transmission Lines': 'lines',
            'Demand Profile': 'demand-profile',
            'Storage Units': 'storage-units',
            'Snapshots': 'snapshots',
            'Wind Profile': 'wind-profile',
            'Solar Profile': 'solar-profile'
        }
        
        store_outputs = {}
        parse_errors = []

        for sheet_name, store_id in sheet_map.items():
            try:
                df = pd.read_excel(xls, sheet_name)
                # Special handling for date columns if necessary
                if sheet_name == 'Demand Profile' and 'snapshot' in df.columns:
                    df['snapshot'] = pd.to_datetime(df['snapshot']).dt.strftime('%Y-%m-%d %H:%M:%S')
                if sheet_name == 'Snapshots' and 'snapshot_time' in df.columns:
                    df['snapshot_time'] = pd.to_datetime(df['snapshot_time']).dt.strftime('%Y-%m-%d %H:%M:%S')
                store_outputs[store_id] = df.to_dict('records')
            except Exception as sheet_error:
                parse_errors.append(f"Error parsing sheet '{sheet_name}': {sheet_error}")
                store_outputs[store_id] = dash.no_update # Don't update store if sheet is bad
        
        if parse_errors:
            feedback_message = dbc.Alert(f"File uploaded with errors: {'; '.join(parse_errors)}", color="warning")
        else:
            feedback_message = dbc.Alert(f"File '{filename}' uploaded and processed successfully.", color="success")

        # Order of return values must match the order of Outputs
        return [
            feedback_message,
            store_outputs.get('power-plants', dash.no_update),
            store_outputs.get('buses', dash.no_update),
            store_outputs.get('lines', dash.no_update),
            store_outputs.get('demand-profile', dash.no_update),
            store_outputs.get('storage-units', dash.no_update),
            store_outputs.get('snapshots', dash.no_update),
            store_outputs.get('wind-profile', dash.no_update),
            store_outputs.get('solar-profile', dash.no_update)
        ]

    except Exception as e:
        print(f"Error processing uploaded network data: {e}")
        return [dbc.Alert(f"Error processing file: {e}", color="danger")] + [dash.no_update] * 8

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
             os.remove(temp_file_path)


# Callbacks to update capacities and display feedback in Dashboard
@app.callback(
    [
        Output('network-data', 'data'),
        Output({'type': 'edited-table-store', 'index': 'power-plants'}, 'data', allow_duplicate=True)
    ],
    [
        Input('solar-slider', 'value'),
        Input('wind-slider', 'value'),
        Input('dsr-slider', 'value')
    ],
    [
        State({'type': 'edited-table-store', 'index': 'power-plants'}, 'data'),
        State({'type': 'edited-table-store', 'index': 'buses'}, 'data'),
        State({'type': 'edited-table-store', 'index': 'lines'}, 'data'),
        State({'type': 'edited-table-store', 'index': 'storage-units'}, 'data')
    ],
    prevent_initial_call=True
)
def update_generator_capacities(new_solar_capacity, new_wind_capacity, new_dsr_capacity,
                                edited_power_plants_data, edited_buses_data,
                                edited_lines_data, edited_storage_units_data):
    # Check if the callback context has triggered the callback
    if not ctx.triggered:
        raise PreventUpdate

    # Determine current power_plants_df (from store or global)
    if edited_power_plants_data:
        current_power_plants_df = pd.DataFrame(edited_power_plants_data)
    else:
        current_power_plants_df = power_plants_df.copy() # Use global df

    # Determine other DataFrames for network diagram (from store or global)
    current_buses_df = pd.DataFrame(edited_buses_data) if edited_buses_data else buses_df.copy()
    current_lines_df = pd.DataFrame(edited_lines_data) if edited_lines_data else lines_df.copy()
    current_storage_units_df = pd.DataFrame(edited_storage_units_data) if edited_storage_units_data else storage_units_df.copy()


    # Calculate original capacities from the current_power_plants_df
    solar_capacity = current_power_plants_df.loc[current_power_plants_df['type'] == 'Solar', 'capacity_mw'].sum()
    wind_capacity = current_power_plants_df.loc[current_power_plants_df['type'] == 'Wind', 'capacity_mw'].sum()
    dsr_capacity = current_power_plants_df.loc[current_power_plants_df['type'] == 'DSR', 'capacity_mw'].sum()

    # Handle cases where original capacity might be zero to avoid division by zero
    if solar_capacity == 0 and new_solar_capacity > 0 :
        print("Warning: Trying to scale solar capacity from 0. This is not yet fully supported by sliders.")
        # Potentially raise PreventUpdate or handle by adding new generator assets
    if wind_capacity == 0 and new_wind_capacity > 0:
        print("Warning: Trying to scale wind capacity from 0. This is not yet fully supported by sliders.")
    if dsr_capacity == 0 and new_dsr_capacity > 0:
        print("Warning: Trying to scale DSR capacity from 0. This is not yet fully supported by sliders.")

    # Adjust solar capacities
    if solar_capacity > 0:
        solar_generators_idx = current_power_plants_df[current_power_plants_df['type'] == 'Solar'].index
        current_power_plants_df.loc[solar_generators_idx, 'capacity_mw'] = \
            current_power_plants_df.loc[solar_generators_idx, 'capacity_mw'] * (new_solar_capacity * 1000 / solar_capacity)
    elif new_solar_capacity == 0: # If original is 0 and new is 0, or new is set to 0
        solar_generators_idx = current_power_plants_df[current_power_plants_df['type'] == 'Solar'].index
        current_power_plants_df.loc[solar_generators_idx, 'capacity_mw'] = 0


    # Adjust wind capacities
    if wind_capacity > 0:
        wind_generators_idx = current_power_plants_df[current_power_plants_df['type'] == 'Wind'].index
        current_power_plants_df.loc[wind_generators_idx, 'capacity_mw'] = \
            current_power_plants_df.loc[wind_generators_idx, 'capacity_mw'] * (new_wind_capacity * 1000 / wind_capacity)
    elif new_wind_capacity == 0:
        wind_generators_idx = current_power_plants_df[current_power_plants_df['type'] == 'Wind'].index
        current_power_plants_df.loc[wind_generators_idx, 'capacity_mw'] = 0

    # Adjust dsr capacities
    if dsr_capacity > 0:
        dsr_generators_idx = current_power_plants_df[current_power_plants_df['type'] == 'DSR'].index
        current_power_plants_df.loc[dsr_generators_idx, 'capacity_mw'] = \
            current_power_plants_df.loc[dsr_generators_idx, 'capacity_mw'] * (new_dsr_capacity * 1000 / dsr_capacity)
    elif new_dsr_capacity == 0:
        dsr_generators_idx = current_power_plants_df[current_power_plants_df['type'] == 'DSR'].index
        current_power_plants_df.loc[dsr_generators_idx, 'capacity_mw'] = 0
        
    # Generate network data for diagram using potentially modified DataFrames
    network_data_elements = get_network_elements_from_df(
        DATABASE_PATH, # Still needed for fallback if a store is empty and global var not loaded
        power_plants_df_override=current_power_plants_df,
        buses_df_override=current_buses_df,
        lines_df_override=current_lines_df,
        storage_units_df_override=current_storage_units_df
    )

    return network_data_elements, current_power_plants_df.to_dict('records')


# Callbacks to draw graph on Dashboard
@app.callback(
    [
        Output({'type': 'dynamic-graphs-container', 'index': 'indicative_inputs'}, 'children'),
    ],
    [
        Input('network-data', 'data')
    ]
)
def plot_indicative_day(network_data):
    print('Plotting indicative inputs...')

    return generate_dashboard_chart()


########################
# Clientside callbacks #
########################

# Clientside callback to handle drawing network diagram
app.clientside_callback(
    ClientsideFunction(
        namespace='clientside',
        function_name='createMap'
    ),
    Output('d3-container', 'children'),
    Input('network-data', 'data')
)


###################
# Run Dash server #
###################

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
