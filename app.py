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
    dcc.Store(id={'type': 'save-status', 'index': 'global'}, data=0, storage_type='memory')
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
    Output({'type': 'save-status', 'index': MATCH}, 'data', allow_duplicate=True),
    [Input({'type': 'save-changes-btn', 'index': ALL}, 'n_clicks')],
    [State({'type': 'data-table', 'index': ALL}, 'data')],
    prevent_initial_call=True
)
def save_changes(n_clicks_list, tables_data_list):

    if (not ctx.triggered) or (not any(n_clicks_list)):
        return 0

    # Determine which button was triggered and get its corresponding index
    triggered = ctx.triggered[0]['prop_id']
    triggered_index = triggered.split('"index":"')[1].split('"')[0].strip()

    if n_clicks_list[0] > 0 and tables_data_list[0] is not None:
        print("saving: "+ triggered_index)
        df = pd.DataFrame(tables_data_list[0])
        save_data(DATABASE_PATH, triggered_index.replace('-', '_'), df)

    return 1


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
    [
        Input('optimization-intent', 'data')
    ],
    prevent_initial_call=True
)
def run_optimization_callback(optimization_intent):
    global interval_disabled

    if optimization_intent:     
        print("Running optimization...")
        # Load network data and create network object HERE, in the main thread
        power_plants_df, storage_units_df, buses_df, lines_df, demand_df, snapshots_df, wind_profile_df, solar_profile_df  = load_data(DATABASE_PATH)
        network = create_network(power_plants_df, storage_units_df, buses_df, lines_df, demand_df, snapshots_df, wind_profile_df, solar_profile_df)

        # Run optimization directly (no threading)
        optimization_results = run_optimization(network)  # Get the results directly

        if optimization_results is not None:  # Check result from optimization
            print("Optimization complete! storing results.") # Check to see if it completes
            interval_disabled = True # disable interval as soon as result or exception occurs.

            charts_html = generate_result_charts(optimization_results)
            run_output = "Optimization complete!"

            return False, optimization_results, interval_disabled, run_output, charts_html, False  # Return the actual result
        else:
            print("Optimization Failed.  Returning None")
            interval_disabled = True # disable interval as soon as result or exception occurs.

            charts_html = "Charts will appear here once the model has finished optimization"
            run_output = "Optimization model has failed."

            return False, None, interval_disabled, run_output, charts_html, True  # Return None which indicates error to callback

    else:
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
    prevent_initial_call=True
)
def download_network_data(n_clicks):
    # Load data from the database
    power_plants_df, buses_df, lines_df, demand_df, storage_units_df, snapshots_df, wind_profile_df, solar_profile_df = load_data(DATABASE_PATH)

    # Create an Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        power_plants_df.to_excel(writer, sheet_name='Power Plants', index=False)
        buses_df.to_excel(writer, sheet_name='Buses', index=False)
        lines_df.to_excel(writer, sheet_name='Transmission Lines', index=False)
        demand_df.to_excel(writer, sheet_name='Demand Profile', index=False)
        storage_units_df.to_excel(writer, sheet_name='Storage Units', index=False)
        snapshots_df.to_excel(writer, sheet_name='Snapshots', index=False)
        wind_profile_df.to_excel(writer, sheet_name='Wind Profile', index=False)
        solar_profile_df.to_excel(writer, sheet_name='Solar Profile', index=False)
    output.seek(0)

    return dcc.send_bytes(output.getvalue(), "network_data.xlsx")


# Callback to handle uploading replacement network file
@app.callback(
    Output({'type': 'save-status', 'index': MATCH}, 'data', allow_duplicate=True),
    Input('upload-network-btn', 'n_clicks'),
    State('upload-network-file', 'contents'),
    State('upload-network-file', 'filename'),
    prevent_initial_call=True
)
def upload_network_data(n_clicks, contents, filename):
    if not contents or n_clicks is None:
        raise PreventUpdate

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
        temp_file.write(decoded)
        temp_file_path = temp_file.name

    # Load the uploaded Excel file into Pandas DataFrames
    try:
        with pd.ExcelFile(temp_file_path) as xls:
            power_plants_df = pd.read_excel(xls, 'Power Plants')
            buses_df = pd.read_excel(xls, 'Buses')
            lines_df = pd.read_excel(xls, 'Transmission Lines')
            demand_df = pd.read_excel(xls, 'Demand Profile', parse_dates=['snapshot'])
            storage_units_df = pd.read_excel(xls, 'Storage Units')
            snapshots_df = pd.read_excel(xls, 'Snapshots', parse_dates=['snapshot_time'])
            wind_profile_df = pd.read_excel(xls, 'Wind Profile')
            solar_profile_df = pd.read_excel(xls, 'Solar Profile')

            # Save to the SQLite database
            save_data(DATABASE_PATH, 'power_plants', power_plants_df)
            save_data(DATABASE_PATH, 'buses', buses_df)
            save_data(DATABASE_PATH, 'lines', lines_df)
            save_data(DATABASE_PATH, 'demand_profile', demand_df)
            save_data(DATABASE_PATH, 'storage_units', storage_units_df)
            save_data(DATABASE_PATH, 'snapshots', snapshots_df)
            save_data(DATABASE_PATH, 'wind_profile', wind_profile_df)
            save_data(DATABASE_PATH, 'solar_profile', solar_profile_df)

    except Exception as e:
        print(f"Error loading uploaded network data: {e}")
        raise PreventUpdate

    finally:
        # Clean up the temporary file
        os.remove(temp_file_path)

    return 1  # Signal that the save was successful


# Callbacks to update capacities and display feedback in Dashboard
@app.callback(
    [
        Output('network-data', 'data')
    ],
    [
        Input('solar-slider', 'value'),
        Input('wind-slider', 'value'),
        Input('dsr-slider', 'value')
    ],
    prevent_initial_call=True
)
def update_generator_capacities(new_solar_capacity, new_wind_capacity, new_dsr_capacity):
    # Check if the callback context has triggered the callback
    if not ctx.triggered:
        raise PreventUpdate

    power_plants_df = load_data_table(DATABASE_PATH, 'power_plants')

    # Calculate original capacities
    solar_capacity = power_plants_df.loc[power_plants_df['type'] == 'Solar', 'capacity_mw'].sum()
    wind_capacity = power_plants_df.loc[power_plants_df['type'] == 'Wind', 'capacity_mw'].sum()
    dsr_capacity = power_plants_df.loc[power_plants_df['type'] == 'DSR', 'capacity_mw'].sum()

    # TO ADD: code that handles the possibility that all solar/wind/DSR capacity has been set to zero

    # Adjust solar capacities
    solar_generators = power_plants_df[power_plants_df['type'] == 'Solar']
    power_plants_df.loc[solar_generators.index, 'capacity_mw'] = \
        solar_generators['capacity_mw'] * (new_solar_capacity * 1000 / solar_capacity)

    # Adjust wind capacities
    wind_generators = power_plants_df[power_plants_df['type'] == 'Wind']
    power_plants_df.loc[wind_generators.index, 'capacity_mw'] = \
        wind_generators['capacity_mw'] * (new_wind_capacity * 1000 / wind_capacity)

    # Adjust dsr capacities
    dsr_generators = power_plants_df[power_plants_df['type'] == 'DSR']
    power_plants_df.loc[dsr_generators.index, 'capacity_mw'] = \
        dsr_generators['capacity_mw'] * (new_dsr_capacity * 1000 / dsr_capacity)

    # Save back to database
    save_data(DATABASE_PATH, 'power_plants', power_plants_df)


    network_data = get_network_elements_from_df(DATABASE_PATH)

    return [network_data]


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
