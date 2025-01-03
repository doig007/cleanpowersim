import dash
from dash import dcc, html, Input, Output, State, MATCH, ALL, ctx
from dash import dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash.dependencies import ClientsideFunction

import pandas as pd
import pypsa
import numpy as np
import matplotlib.pyplot as plt
import io
import json
import base64
import os
import tempfile
import xlsxwriter

from functools import lru_cache  #TO DO: Investigate adding back in


from page_layout import display_page, get_menu_layout, set_active_links, generate_result_charts, render_graphs
from external_functions import load_data, create_network, save_data

plt.switch_backend('Agg') # Set matplotlib to use a non-interactive backend

# Step 1: Set up the SQLite database connection function
DATABASE_PATH = 'power_system.db'

# Step 2: Load data into Pandas DataFrame from SQLite
power_plants_df, buses_df, lines_df, demand_df, storage_units_df, snapshots_df, wind_profile_df, solar_profile_df = load_data(DATABASE_PATH)

# Step 3: Initialize Dash app with Bootstrap stylesheet
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdnjs.cloudflare.com/ajax/libs/bootstrap-icons/1.8.1/font/bootstrap-icons.min.css"
    ]
)

app.title = 'Clean Power Sim'
app._favicon = ("assets/favicon.ico")


# Step 4: Define layout with an enhanced sidebar for navigation
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(get_menu_layout(), width=3, style={'padding': '0', 'margin': '0'}),  # Enhanced Sidebar column from separate module
        dbc.Col([
            dcc.Location(id='url', refresh=False),
            dcc.Store(id='optimization-intent', data=False, storage_type='memory'),  # Track user intent to run optimization
            dcc.Store(id='optimization-results', data=None, storage_type='memory'),  # Store to keep optimization results
            dcc.Store(id={'type': 'save-status', 'index': 'global'}, data=0, storage_type='memory'),
            html.Div(id='page-content'),  # Main content area
        ], width=9)  # Main content column
    ])
], fluid=True)

# Step 6: Define callback to display pages based on navigation and handle active link highlighting
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def update_page_content(pathname):
    return display_page(pathname)

@app.callback(
    [
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

# Step 7: Single Callback for saving changes
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

# Step 8: Define the callback to run optimization when the button is clicked
@app.callback(
    [Output('url', 'pathname'), Output('optimization-intent', 'data', allow_duplicate=True)],
    Input('run-model-btn', 'n_clicks'),
    prevent_initial_call=True
)
def navigate_to_results_and_set_intent(n_clicks):
    if n_clicks:
        # Navigate to results page and set intent to True for optimization
        return '/results', True
    raise PreventUpdate  # Prevent unnecessary updates if not clicked

@app.callback(
    [
        Output({'type': 'run-output', 'index': 'results'}, 'children'),
        Output({'type': 'dynamic-graphs-container', 'index': 'results'}, 'children'),
        Output('optimization-intent', 'data', allow_duplicate=True),  # Reset the intent after running
        Output('optimization-results', 'data')  # Store the results in memory
    ],
    [Input('page-ready', 'id')],
    [State('optimization-intent', 'data'), State('optimization-results', 'data'), State('url', 'pathname')],
    prevent_initial_call=True
)
def handle_results_page(page_ready, optimization_intent, optimization_results, pathname):
    if pathname == '/results':
        # If optimization intent is set, run the model and store the results
        if optimization_intent:
            try:
                power_plants_df, storage_units_df, buses_df, lines_df, demand_df, snapshots_df, wind_profile_df, solar_profile_df  = load_data(DATABASE_PATH)
                network = create_network(power_plants_df, storage_units_df, buses_df, lines_df, demand_df, snapshots_df, wind_profile_df, solar_profile_df)

                #model = network.optimize.create_model()
                #model.to_file('c:/Temp/model.lp','lp')
            
                # Run optimization using PyPSA's optimize method
                network.optimize(solver_name='cplex')

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

                # Generate charts using the new function
                graphs_list = generate_result_charts(optimization_results_dict)
                charts_html = render_graphs(graphs_list)

                # Convert results dictionary to JSON for storage
                optimization_results_json = json.dumps(optimization_results_dict)

                current_datetime = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                run_output = "Economic Dispatch Run Successfully " + "".join(current_datetime)

                return run_output, charts_html, False, optimization_results_json

            except Exception as e:
                print(f"Error running optimization: {str(e)}")
                return f"Error running economic dispatch: {str(e)}", [], False, None

        # If there are already stored results, return them
        elif optimization_results:
            # Load stored results from JSON
            optimization_results_dict = json.loads(optimization_results)

            # Generate charts from stored results
            graphs_list = generate_result_charts(optimization_results_dict)
            charts_html = render_graphs(graphs_list)

            run_output = "Loaded previous results"
            return run_output, charts_html, False, optimization_results

    # If none of the conditions are met, do nothing
    raise PreventUpdate


# Callback to handle downloading entire network file as Excel
@app.callback(
    Output("download-network-excel", "data"),
    Input("download-network-btn", "n_clicks"),
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


# Clientside callback to handle drawing network diagram
app.clientside_callback(
    ClientsideFunction(
        namespace='clientside',
        function_name='createMap'
    ),
    Output('d3-container', 'children'),
    Input('network-data', 'data')
)



#@app.callback(
#    Output('network-graph', 'zoom'),
#    [Input('zoom-in', 'n_clicks'),
#     Input('zoom-out', 'n_clicks'),
#     Input('fit', 'n_clicks')],
#    State('network-graph', 'zoom')
#)
#def adjust_zoom(zoom_in, zoom_out, fit, current_zoom):
#    ctx = dash.callback_context
#
#    if not ctx.triggered:
#        raise PreventUpdate
#
#    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
#    if triggered_id == 'zoom-in':
#        return min(current_zoom + 0.2, 3)  # Increase zoom, cap at maxZoom
#    elif triggered_id == 'zoom-out':
#        return max(current_zoom - 0.2, 0.5)  # Decrease zoom, cap at minZoom
#    elif triggered_id == 'fit':
#        # Use a specific fit function if desired
#        return 1  # Reset zoom to default
#    return current_zoom


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
