import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, Input, Output, State
import pandas as pd
import json
import plotly.graph_objects as go

from external_functions import load_data, create_network, get_network_elements
from model_checks import check_capacity_vs_demand, check_nodal_capacity_vs_demand, export_network_to_excel

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
        power_plants_df, buses_df, lines_df, demand_df, storage_units_df, snapshots_df, wind_profile_df, solar_profile_df = load_data(DATABASE_PATH)    # Reload the data from the database
        network = create_network(power_plants_df, buses_df, lines_df, demand_df, storage_units_df, snapshots_df, wind_profile_df, solar_profile_df)
        network_data = get_network_elements(network)

        # Create a network graph using D3
        tab_content = html.Div([
            html.H2("Network Diagram", className='text-center my-4'),
            dcc.Store(id="network-data", storage_type='memory', data=network_data),
            html.Script(src='/assets/network_diagram.js'),
            dbc.ButtonGroup([
                dbc.Button(html.I(className="fas fa-search-plus fa-lg"), id="zoom-in", color="secondary"),
                dbc.Button(html.I(className="fas fa-search-minus fa-lg"), id="zoom-out", color="primary"),
                dbc.Button(html.I(className="fas fa-compress-arrows-alt fa-lg"), id="fit", color="primary")
            ],
            className="d-flex justify-content-center my-2"
            ),
            html.Div(
                id="d3-container",
                style={"width": "100%", "height": "600px"},
            )
        ])
    
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
            html.H2("Optimisation Results", className='text-center my-4'),
            html.Div(id='page-ready', style={'display': 'none'}),  # Hidden div to signal page readiness
            html.Div(id={'type': 'run-output', 'index': 'results'}, style={'marginTop': '20px', 'textAlign': 'center'}),
            html.Div(id={'type': 'dynamic-graphs-container', 'index': 'results'}, style={'marginTop': '20px'})
        ])

    elif pathname == '/debug':
        
        # Load network data and create a network instance
        power_plants_df, buses_df, lines_df, demand_df, storage_units_df, snapshots_df, wind_profile_df, solar_profile_df = load_data(DATABASE_PATH)
        network = create_network(power_plants_df, buses_df, lines_df, demand_df, storage_units_df, snapshots_df, wind_profile_df, solar_profile_df)

        # Perform the capacity vs demand summary
        capacity_check_summary = check_capacity_vs_demand(network)
        nodal_capacity_check_summary = check_nodal_capacity_vs_demand(network)

        # Create a single-row DataTable to display the summary
        debug_table = dash_table.DataTable(
            id="debug-summary-table",
            columns=[
                {"name": "Check Name", "id": "Check Name"},
                {"name": "Snapshots Passed", "id": "Snapshots Passed"},
                {"name": "Snapshots Failed", "id": "Snapshots Failed"}
            ],
            data=[capacity_check_summary, nodal_capacity_check_summary],
            style_table={'margin': '20px auto', 'width': '90%'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_cell={'textAlign': 'center'},
        )

        tab_content = html.Div([
            html.H2("Model Debug", className='text-center my-4'),
            html.Div(debug_table)
        ])

    elif pathname == '/dashboard':
        
        power_plants_df, buses_df, lines_df, demand_df, storage_units_df, snapshots_df, wind_profile_df, solar_profile_df = load_data(DATABASE_PATH)    # Reload the data from the database
        network = create_network(power_plants_df, buses_df, lines_df, demand_df, storage_units_df, snapshots_df, wind_profile_df, solar_profile_df)
        network_data = get_network_elements(network)

        # Calculate total capacities for Solar and Wind plants
        solar_capacity = power_plants_df.loc[power_plants_df['type'] == 'Solar', 'capacity_mw'].sum()
        wind_capacity = power_plants_df.loc[power_plants_df['type'] == 'Wind', 'capacity_mw'].sum()
        dsr_capacity = power_plants_df.loc[power_plants_df['type'] == 'DSR', 'capacity_mw'].sum()

        tab_content = dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H2("Welcome to the Power System Optimization Dashboard"),
                    html.P(" This dashboard provides tools to optimize and analyze power system operations, allowing users to adjust, simulate, and evaluate various components of a power grid. Whether you're managing power plants, assessing grid stability, or planning future expansions, this platform helps you make data-driven decisions with intuitive visualizations and modeling features.",className="ms-2 text-secondary")
                ])
            ]),
            dbc.Row([
                # Left-hand side: Sliders
                dbc.Col([
                    html.H3("Adjust the Renewable Energy Capacities Below:", className="text-primary mb-4 fs-6"),
                    html.Div([
                        # Solar Adjustment Section
                        html.Div([
                            html.Div([
                                html.I(className="bi bi-sun text-warning", style={"fontSize": "2rem"}),
                                html.Span(" Solar PV Capacity (GW)", className="ms-2 fw-bold text-secondary")
                            ], className="d-flex align-items-center mb-2"),
                            dcc.Slider(
                                id='solar-slider',
                                min=0,
                                max=max(5000,solar_capacity*1.5)/1000,
                                step=10,
                                value=solar_capacity/1000,
                                marks=None,
                                tooltip={"placement": "bottom", "always_visible": True},
                                className="yellow-slider"
                            ),
                            html.Div(id='solar-output', className="text-center mt-2 text-info")
                        ], className="mb-4"),

                        # Wind Adjustment Section
                        html.Div([
                            html.Div([
                                html.I(className="bi bi-wind text-info", style={"fontSize": "2rem"}),
                                html.Span(" Wind Capacity (GW)", className="ms-2 fw-bold text-secondary")
                            ], className="d-flex align-items-center mb-2"),
                            dcc.Slider(
                                id='wind-slider',
                                min=0,
                                max=max(5000,wind_capacity*1.5)/1000,
                                step=10,
                                value=wind_capacity/1000,
                                marks=None,
                                tooltip={"placement": "bottom", "always_visible": True}
                            ),
                            html.Div(id='wind-output', className="text-center mt-2 text-info")
                        ], className="mb-4"),

                        # DSR Adjustment Section
                        html.Div([
                            html.Div([
                                html.I(className="bi bi-lightning text-success", style={"fontSize": "2rem"}),
                                html.Span(" DSR Capacity (GW)", className="ms-2 fw-bold text-secondary")
                            ], className="d-flex align-items-center mb-2"),
                            dcc.Slider(
                                id='dsr-slider',
                                min=0,
                                max=max(15000,dsr_capacity*1.5)/1000,
                                step=10,
                                value=dsr_capacity/1000,
                                marks=None,
                                tooltip={"placement": "bottom", "always_visible": True},
                                className="green-slider"
                            ),
                            html.Div(id='dsr-output', className="text-center mt-2 text-info")
                        ], className="mb-4"),




                    ])
                ], width=3),  # Left column width: 3/12

                # Right-hand side: Network Diagram
                dbc.Col([
                    html.H3("Network Diagram", className="text-primary mb-4 fs-6"),
                    dcc.Store(id="network-data", storage_type='memory', data=network_data),
                    html.Script(src='/assets/network_diagram.js'),
                    html.Div(
                        id="d3-container",
                        style={"width": "100%"}
                    )
                ], width=9)  # Right column width: 9/12
            ])
        ], fluid=True)

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

    print("Generating result charts...")

    snapshots = pd.to_datetime(optimization_results["snapshots"])
    generation_data = pd.DataFrame(optimization_results["generators_t_p"]["data"])
    generator_types = optimization_results["generators_t_p"]["types"]
    shadow_prices = pd.DataFrame(optimization_results["buses_t_marginal_price"])
    storage_data = pd.DataFrame(optimization_results.get("storage_units_t_p", {}))

    graphs_list = []

# Chart 1: Pie Chart of Total Generation by Type
    total_generation = generation_data.sum()
    total_generation_by_type = total_generation.groupby(generator_types).sum()
    total_generation_by_type = total_generation_by_type[total_generation_by_type > 0]  # Exclude zero values from graph

    pie_fig = go.Figure(
        data=[go.Pie(
            labels=total_generation_by_type.index,
            values=total_generation_by_type.values,
            textinfo='label+percent',
            hoverinfo='label+value',
            marker=dict(colors=['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A'])
        )]
    )

    pie_fig.update_layout(
        title=f"Total Generation by Type ({snapshots.min().strftime('%Y-%m-%d')} to {snapshots.max().strftime('%Y-%m-%d')})",
        template="plotly_white",
        autosize=True,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    graphs_list.append({
        'id': 'total-generation-pie',
        'figure': pie_fig,
        'title': f"Total Generation by Type ({snapshots.min().strftime('%Y-%m-%d')} to {snapshots.max().strftime('%Y-%m-%d')})",
        'raw_data': total_generation_by_type.to_dict()
    })

    # Chart 2: Price-Duration Curve for Each Node
    price_duration_fig = go.Figure()
    for node in shadow_prices.columns:
        sorted_prices = shadow_prices[node].sort_values(ascending=False).reset_index(drop=True)
        price_duration_fig.add_trace(go.Scatter(
            x=sorted_prices.index,
            y=sorted_prices.values,
            mode='lines',
            name=node
        ))
    price_duration_fig.update_layout(
        title="Price-Duration Curve",
        xaxis_title="Hours",
        yaxis_title="Price (GBP/MWh)",
        template="plotly_white",
        autosize=True,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    graphs_list.append({
        'id': 'price-duration-curve',
        'figure': price_duration_fig,
        'title': 'Price-Duration Curve',
        'raw_data': shadow_prices.to_dict()
    })

    # Chart 3: Stacked Area Chart of Typical Daily Generation Profile by Type (Including Storage)
    generation_data.index = pd.to_datetime(generation_data.index)
    aligned_generator_types = pd.Series(generator_types).reindex(generation_data.columns)

    # Transpose for grouping on columns and aggregate hourly
    hourly_generation_by_type = generation_data.T.groupby(aligned_generator_types).sum().T.groupby(generation_data.index.hour).mean()

    # Remove types with all zero values
    hourly_generation_by_type = hourly_generation_by_type.loc[:, (hourly_generation_by_type != 0).any(axis=0)]

    # Aggregate storage data for charging and discharging
    storage_data.index = pd.to_datetime(storage_data.index)
    hourly_storage = storage_data.groupby(storage_data.index.hour).sum()

    stacked_area_fig = go.Figure()

    # Add generation types
    for generation_type in hourly_generation_by_type.columns:
        stacked_area_fig.add_trace(go.Scatter(
            x=hourly_generation_by_type.index,
            y=hourly_generation_by_type[generation_type],
            mode='lines',
            stackgroup='one',
            name=generation_type
        ))

    # Add storage charging (negative values) and discharging (positive values)
    stacked_area_fig.add_trace(go.Scatter(
        x=hourly_storage.index,
        y=hourly_storage.clip(upper=0).sum(axis=1),  # Charging as negative
        mode='lines',
        stackgroup='one',
        name="Storage (Charging)",
        line=dict(dash='dot', color='blue')
    ))
    stacked_area_fig.add_trace(go.Scatter(
        x=hourly_storage.index,
        y=hourly_storage.clip(lower=0).sum(axis=1),  # Discharging as positive
        mode='lines',
        stackgroup='one',
        name="Storage (Discharging)",
        line=dict(dash='dot', color='orange')
    ))

    stacked_area_fig.update_layout(
        title="Typical Daily Generation Profile by Type (Including Storage)",
        xaxis_title="Hour of Day",
        yaxis_title="Average Generation (MW)",
        template="plotly_white",
        autosize=True,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    graphs_list.append({
        'id': 'daily-generation-profile',
        'figure': stacked_area_fig,
        'title': 'Typical Daily Generation Profile by Type (Including Storage)',
        'raw_data': {
            "generation": hourly_generation_by_type.to_dict(),
            "storage": hourly_storage.to_dict()
        }
    })


    return graphs_list

def render_graphs(graphs_list):
    if not graphs_list:
        return html.Div("No graphs to display")

    print("Rendering graphs...")

    graph_1 = graphs_list[0]['figure'] # Generation by type pie Chart
    graph_2 = graphs_list[1]['figure'] # Price-Duration Curves
    graph_3 = graphs_list[2]['figure'] # Typical diurnal generation profile

    graphs_html = html.Div([
        dcc.Graph(figure=graph_1, style={'flex': '1', 'margin': '5px'}),
        dcc.Graph(figure=graph_2, style={'flex': '2', 'margin': '5px'}),
        dcc.Graph(figure=graph_3, style={'flex': '3', 'margin': '5px'}),
    ], style={'display': 'flex', 'justifyContent': 'flex-start', 'width': '100%'})

    return graphs_html