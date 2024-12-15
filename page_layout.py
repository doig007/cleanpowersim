import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
import pandas as pd
import plotly.graph_objects as go
from external_functions import load_data, create_diagram_tab
from network_styles import cytoscape_styles  # Import the external stylesheet

DATABASE_PATH = 'power_system.db'

# Content Page Callback
def display_page(pathname):
    # Set a default tab content
    tab_content = html.Div([
            html.Iframe(
                src="/assets/welcome.html",
                style={
                    'width': '100%',
                    'height': '800px',
                    'border': 'none'
                }
            )
        ])

    # Determine content based on pathname
    if pathname == '/editor/power-plants':
        power_plants_df = load_data(DATABASE_PATH)[0]
        tab_content = html.Div([
            html.H2("System Editor: Power Plants", className='text-center my-4'),
            dash_table.DataTable(
                id={'type': 'data-table', 'index': 'power-plants'},
                columns=[{"name": i, "id": i, "editable": True} for i in power_plants_df.columns],
                data=power_plants_df.to_dict('records'),
                editable=True,
                row_deletable=True,
                style_table={'marginBottom': '20px', 'width': '90%', 'margin': 'auto'}
            ),
            html.Button("Save Changes", id={'type': 'save-changes-btn', 'index': 'power-plants'}, n_clicks=0, className='btn btn-primary my-4')
    ])
    elif pathname == '/editor/buses':
        buses_df = load_data(DATABASE_PATH)[1]
        tab_content = html.Div([
            html.H2("System Editor: Buses", className='text-center my-4'),
            dash_table.DataTable(
                id={'type': 'data-table', 'index': 'buses'},
                columns=[{"name": i, "id": i, "editable": True} for i in buses_df.columns],
                data=buses_df.to_dict('records'),
                editable=True,
                row_deletable=True,
                style_table={'marginBottom': '20px', 'width': '90%', 'margin': 'auto'}
            ),
            html.Button("Save Changes", id={'type': 'save-changes-btn', 'index': 'buses'}, n_clicks=0, className='btn btn-primary my-4')
        ])
    elif pathname == '/editor/lines':
        lines_df = load_data(DATABASE_PATH)[2]
        tab_content = html.Div([
            html.H2("System Editor: Lines", className='text-center my-4'),
            dash_table.DataTable(
                id={'type': 'data-table', 'index': 'lines'},
                columns=[{"name": i, "id": i, "editable": True} for i in lines_df.columns],
                data=lines_df.to_dict('records'),
                editable=True,
                row_deletable=True,
                style_table={'marginBottom': '20px', 'width': '90%', 'margin': 'auto'}
            ),
            html.Button("Save Changes", id={'type': 'save-changes-btn', 'index': 'lines'}, n_clicks=0, className='btn btn-primary my-4')
        ])
    elif pathname == '/editor/demand-profile':
        demand_df = load_data(DATABASE_PATH)[3]
        tab_content = html.Div([
            html.H2("System Editor: Demand Profile", className='text-center my-4'),
            dash_table.DataTable(
                id={'type': 'data-table', 'index': 'demand-profile'},
                columns=[{"name": i, "id": i, "editable": True} for i in demand_df.columns],
                data=demand_df.to_dict('records'),
                editable=True,
                row_deletable=True,
                style_table={'marginBottom': '20px', 'width': '90%', 'margin': 'auto'}
            ),
            html.Button("Save Changes", id={'type': 'save-changes-btn', 'index': 'demand-profile'}, n_clicks=0, className='btn btn-primary my-4')
        ])
    elif pathname == '/editor/storage-units':
        storage_units_df = load_data(DATABASE_PATH)[4]
        tab_content = html.Div([
            html.H2("System Editor: Storage Units", className='text-center my-4'),
            dash_table.DataTable(
                id={'type': 'data-table', 'index': 'storage-units'},
                columns=[{"name": i, "id": i, "editable": True} for i in storage_units_df.columns],
                data=storage_units_df.to_dict('records'),
                editable=True,
                row_deletable=True,
                style_table={'marginBottom': '20px', 'width': '90%', 'margin': 'auto'}
            ),
            html.Button("Save Changes", id={'type': 'save-changes-btn', 'index': 'storage-units'}, n_clicks=0, className='btn btn-primary my-4')
        ])
    elif pathname == '/editor/wind-profile':
        wind_profile_df = load_data(DATABASE_PATH)[6]
        tab_content = html.Div([
            html.H2("System Editor: Wind Profile", className='text-center my-4'),
            dash_table.DataTable(
                id={'type': 'data-table', 'index': 'wind-profile'},
                columns=[{"name": i, "id": i, "editable": True} for i in wind_profile_df.columns],
                data=wind_profile_df.to_dict('records'),
                editable=True,
                row_deletable=True,
                style_table={'marginBottom': '20px', 'width': '90%', 'margin': 'auto'}
            ),
            html.Button("Save Changes", id={'type': 'save-changes-btn', 'index': 'wind-profile'}, n_clicks=0, className='btn btn-primary my-4')
        ])
    elif pathname == '/editor/solar-profile':
        solar_profile_df = load_data(DATABASE_PATH)[7]
        tab_content = html.Div([
            html.H2("System Editor: Solar Profile", className='text-center my-4'),
            dash_table.DataTable(
                id={'type': 'data-table', 'index': 'solar-profile'},
                columns=[{"name": i, "id": i, "editable": True} for i in solar_profile_df.columns],
                data=solar_profile_df.to_dict('records'),
                editable=True,
                row_deletable=True,
                style_table={'marginBottom': '20px', 'width': '90%', 'margin': 'auto'}
            ),
            html.Button("Save Changes", id={'type': 'save-changes-btn', 'index': 'solar-profile'}, n_clicks=0, className='btn btn-primary my-4')
        ])
    elif pathname == '/diagram':
        tab_content = create_diagram_tab(DATABASE_PATH)
    
    elif pathname == '/settings':
        snapshots_df = load_data(DATABASE_PATH)[5]
        tab_content = html.Div([
            html.H2("Settings", className='text-center my-4'),
            dash_table.DataTable(
                id={'type': 'data-table', 'index': 'snapshots'},
                columns=[{"name": i, "id": i, "editable": True} for i in snapshots_df.columns],
                data=snapshots_df.to_dict('records'),
                editable=True,
                row_deletable=True,
                style_table={'marginBottom': '20px', 'width': '90%', 'margin': 'auto'}
            ),
            html.Button("Save Changes", id={'type': 'save-changes-btn', 'index': 'snapshots'}, n_clicks=0, className='btn btn-primary my-4')
        ])
    elif pathname == '/results':
        tab_content = html.Div([
            html.H2("Optimization Results", className='text-center my-4'),
            html.Div(id='page-ready', style={'display': 'none'}),  # Hidden div to signal page readiness
            html.Div(id={'type': 'run-output', 'index': 'results'}, style={'marginTop': '20px', 'textAlign': 'center'}),
            dcc.Store(id={'type': 'graphs-output', 'index': 'results'}, data=[]),  # Store to hold all graphs data dynamically
            html.Div(id={'type': 'dynamic-graphs-container', 'index': 'results'}, style={'marginTop': '20px'})
        ])

    # Return the content
    return html.Div([
        tab_content
    ])

# Active Links Callback
def set_active_links(pathname):
    # Default values for all active links
    active_links = {
        'editor-link': {'backgroundColor': "transparent"},
        'diagram-link': False,
        'settings-link': False,        
        'results-link': False
    }

    # Set the active link based on pathname
    if pathname.find('editor') > 0:
        active_links['editor-link'] = {'backgroundColor': "#0d6efd"}
    elif pathname == '/diagram':
        active_links['diagram-link'] = True
    elif pathname == '/settings':
        active_links['settings-link'] = True
    elif pathname == '/results':
        active_links['results-link'] = True

    # Return each link state
    return (
        active_links['editor-link'],
        active_links['diagram-link'],
        active_links['settings-link'],
        active_links['results-link']
    )

# Boostrap Sidebar
def get_menu_layout():
    return html.Div([
        dcc.Link(
                html.H2("Clean Power Sim", className="display-10 text-white my-6", style={'padding':'20px'}),
                href="/",  # Set the default route to link back to
                style={'textDecoration': 'none'}  # Remove underline from link
        ),
        html.Hr(),
        dbc.Nav(
            [
                dbc.DropdownMenu(
                    [
                        dbc.DropdownMenuItem("Power Plants", href="/editor/power-plants", id="power-plants-link", className="ms-4 text-white"),
                        dbc.DropdownMenuItem("Storage Units", href="/editor/storage-units", id="storage-units-link", className="ms-4 text-white"),
                        dbc.DropdownMenuItem("Buses", href="/editor/buses", id="buses-link", className="ms-4 text-white"),
                        dbc.DropdownMenuItem("Transmission Lines", href="/editor/lines", id="lines-link", className="ms-4 text-white"),
                        dbc.DropdownMenuItem("Demand Profile", href="/editor/demand-profile", id="demand-profile-link", className="ms-4 text-white"),
                        dbc.DropdownMenuItem("Wind Profile", href="/editor/wind-profile", id="wind-profile-link", className="ms-4 text-white"),
                        dbc.DropdownMenuItem("Solar Profile", href="/editor/solar-profile", id="solar-profile-link", className="ms-4 text-white")
                    ],
                    label=html.Span([
                        html.I(className="bi bi-pencil-square me-2 text-white"),
                        html.Span("Editor", className="text-white")
                    ]),
                    id="editor-link",
                    nav=True,
                    menu_variant="dark",
                    className="nav-item text-white",
                    toggle_style={
                        "background": "transparent"
                    }
                ),
                dbc.NavLink(
                    [html.I(className="bi bi-diagram-3-fill me-2"), "Network Diagram"],
                    href="/diagram",
                    id="diagram-link",
                    active=False,
                    className="nav-item text-white"
                ),
                dbc.NavLink(
                    [html.I(className="bi bi-gear-fill me-2"), "Settings"],
                    href="/settings",
                    id="settings-link",
                    active=False,
                    className="nav-item text-white"
                ),
                dbc.NavLink(
                    [html.I(className="bi bi-bar-chart-line-fill me-2"), "Results"],
                    href="/results",
                    id="results-link",
                    active=False,
                    className="nav-item text-white"
                )
            ],
            vertical=True,
            pills=True,
            className="nav flex-column"
        ),
        html.Hr(),
        dbc.Button(
            [html.I(className="bi bi-play-circle me-2"), "Run Optimization"],
            id="run-model-btn",
            color="success",
            className="w-100 mt-4"
        ),
        html.Hr(),
        dbc.Button(
            [html.I(className="bi bi-download me-2"), "Download Network Data"],
            id="download-network-btn",
            color="secondary",
            className="w-100 mt-2"
        ),
        dcc.Download(id="download-network-excel"),  # Download component for network data
        dbc.Button(
            [html.I(className="bi bi-upload me-2"), "Upload Network Data"],
            id="upload-network-btn",
            color="secondary",
            className="w-100 mt-2"
        ),
        dcc.Upload(
            id="upload-network-file",
            children=html.Div(['Drag and Drop or ', html.A('Select Files')]),
            style={
                'width': '100%', 'height': '60px', 'lineHeight': '60px',
                'borderWidth': '1px', 'borderStyle': 'dashed',
                'borderRadius': '5px', 'textAlign': 'center',
                'marginTop': '10px', 'color': 'white'
            },
            multiple=False
        )
    ], className="sidebar bg-dark", style={"height": "100vh", "padding": "0"})

def generate_result_charts(optimization_results):
    # Extract stored data
    snapshots = pd.to_datetime(optimization_results["snapshots"])
    generation_data = pd.DataFrame(optimization_results["generators_t_p"])
    shadow_prices = pd.DataFrame(optimization_results["buses_t_marginal_price"])
    storage_data = pd.DataFrame(optimization_results["storage_units_t_p"])

    graphs_list = []

    # Example chart 1: Stacked Generation Chart (including storage)
    stacked_fig = go.Figure()

    # Add generators to the chart
    for generator in generation_data.columns:
        stacked_fig.add_trace(go.Scatter(
            x=snapshots,
            y=generation_data[generator],
            mode='lines',
            stackgroup='one',
            name=generator
        ))

    # Add storage units to the chart, with separate treatment for charging and discharging
    for storage_unit in storage_data.columns:
        # Storage output (discharging) - positive values
        discharging = storage_data[storage_unit].clip(lower=0)
        stacked_fig.add_trace(go.Scatter(
            x=snapshots,
            y=discharging,
            mode='lines',
            stackgroup='one',
            name=f"{storage_unit} (discharging)"
        ))

        # Storage input (charging) - negative values
        charging = storage_data[storage_unit].clip(upper=0)
        stacked_fig.add_trace(go.Scatter(
            x=snapshots,
            y=charging,
            mode='lines',
            stackgroup='one',
            name=f"{storage_unit} (charging)",
            fill='tonexty'  # Ensures it's visually distinct
        ))

    # Update layout
    stacked_fig.update_layout(
        title='Stacked Generation by Snapshot (Including Storage)',
        xaxis_title='Snapshot',
        yaxis_title='Generation (MW)',
        template='plotly_dark'
    )

    # Store raw data for this graph
    # Convert snapshots to a Series to concatenate
    snapshots_series = pd.Series(snapshots, name="snapshot")
    raw_data_stacked = pd.concat([snapshots_series, generation_data,storage_data], axis=1).to_dict('records')

    graphs_list.append({
        'id': 'stacked-generation',
        'figure': stacked_fig,
        'title': 'Stacked Generation (Including Storage)',
        'raw_data': raw_data_stacked  # Add raw data to the list
    })

    # Example chart 2: Shadow Price Chart
    shadow_fig = go.Figure()
    for bus in shadow_prices.columns:
        shadow_fig.add_trace(go.Scatter(
            x=snapshots,
            y=shadow_prices[bus],
            mode='lines',
            name=f'Shadow Price - {bus}'
        ))
    shadow_fig.update_layout(
        title='Shadow Price by Snapshot',
        xaxis_title='Snapshot',
        yaxis_title='Shadow Price (EUR/MWh)',
        template='plotly_dark'
    )

    # Store raw data for this graph
    raw_data_shadow = pd.concat([snapshots_series, shadow_prices], axis=1).to_dict('records')

    graphs_list.append({
        'id': 'shadow-price',
        'figure': shadow_fig,
        'title': 'Shadow Price',
        'raw_data': raw_data_shadow  # Add raw data to the list
    })

    return graphs_list
