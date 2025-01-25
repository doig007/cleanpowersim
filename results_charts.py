from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from external_functions import load_data_table
DATABASE_PATH = 'power_system.db'

def generate_result_charts(optimization_results):

    # If optimization results are not available, return an empty list
    if not optimization_results:
        return []   

    print("Generating result charts...")

    snapshots = pd.to_datetime(optimization_results["snapshots"])
    generation_data = pd.DataFrame(optimization_results["generators_t_p"]["data"])
    generator_types = optimization_results["generators_t_p"]["types"]
    shadow_prices = pd.DataFrame(optimization_results["buses_t_marginal_price"])
    storage_data = pd.DataFrame(optimization_results.get("storage_units_t_p", {}))

    graphs_list = []

    # Calculate Summary Statistics
    avg_price = shadow_prices.mean().mean()  # Time-averaged, node-averaged
    load_weighted_avg_price = (shadow_prices * generation_data.sum(axis=1)).sum().sum() / generation_data.sum().sum()
    renewable_generation = generation_data.loc[:, [col for col, type in optimization_results["generators_t_p"]["types"].items() if type in ['Wind', 'Solar', 'Nuclear', 'Biomass']]].sum().sum()
    total_generation = generation_data.sum().sum()
    renewable_percentage = (renewable_generation / total_generation) * 100 if total_generation > 0 else 0  # Avoid division by zero

    # Create Summary Table
    summary_table = dbc.Table([
        html.Thead(html.Tr([html.Th("Metric"), html.Th("Value")])),
        html.Tbody([
            html.Tr([html.Td("Time-Average Annual Price (£/MWh)"), html.Td(f"{avg_price:.2f}")]),
            html.Tr([html.Td("Load-Average Annual Price (£/MWh)"), html.Td(f"{load_weighted_avg_price:.2f}")]),
            html.Tr([html.Td("% Generation from Renewable Sources"), html.Td(f"{renewable_percentage:.2f}%")]),
            html.Tr([html.Td("Total Generation (MWh)"), html.Td(f"{total_generation:.2f}")]),
            html.Tr([html.Td("Grid carbon intensity (g/kWh)"), html.Td("")])
        ])
    ], bordered=True, hover=True)









    ###################################################
    # Chart 1: Pie Chart of Total Generation by Type
    ###################################################
    total_generation = generation_data.sum()
    total_generation_by_type = total_generation.groupby(generator_types).sum()

    # Sort and identify the top N generators
    top_n = 4  # Keep the top 4
    top_generators = total_generation_by_type.nlargest(top_n)
    other_generation = total_generation_by_type.drop(top_generators.index).sum()

    # Combine into a new series for the pie chart
    pie_chart_data = pd.concat([top_generators, pd.Series({'Other': other_generation})])


    pie_fig = go.Figure(
        data=[go.Pie(
            labels=pie_chart_data.index,
            values=pie_chart_data.values,
            textinfo='label+percent',
            hoverinfo='label+value',
            marker=dict(colors=['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A'])
        )]
    )

    pie_fig.update_layout(
        title=f"Total Generation by Type ({snapshots.min().strftime('%Y-%m-%d')} to {snapshots.max().strftime('%Y-%m-%d')})",
        template="plotly_white",
        autosize=True,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    graphs_list.append({
        'id': 'total-generation-pie',
        'figure': pie_fig,
        'title': f"Total Generation by Type ({snapshots.min().strftime('%Y-%m-%d')} to {snapshots.max().strftime('%Y-%m-%d')})",
        'raw_data': total_generation_by_type.to_dict()
    })

    ###################################################
    # Chart 2: Price-Duration Curve for Each Node
    ###################################################
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
        title="Price-Duration Curve By Node",
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

    ######################################################################################################
    # Chart 3: Stacked Area Chart of Typical Daily Generation Profile by Type (Including Storage)
    ######################################################################################################
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

    ######################################################################################################
    # Render Graphs
    ######################################################################################################

    print("Rendering graphs...")

    graph_1 = graphs_list[0]['figure'] # Generation by type pie Chart
    graph_2 = graphs_list[1]['figure'] # Price-Duration Curves
    graph_3 = graphs_list[2]['figure'] # Typical diurnal generation profile

    #graphs_html = html.Div([
    #    dcc.Graph(figure=graph_1, style={'flex': '1', 'margin': '5px'}),
    #    dcc.Graph(figure=graph_2, style={'flex': '2', 'margin': '5px'}),
    #    dcc.Graph(figure=graph_3, style={'flex': '3', 'margin': '5px'}),
    #], style={'display': 'flex', 'justifyContent': 'flex-start', 'width': '100%'})

    graphs_html = dbc.Container([
        dbc.Row([
            dbc.Col(dcc.Graph(figure=graph_1), width=6),
            dbc.Col(summary_table, width=6)
        ], style={'display': 'flex', 'justifyContent': 'flex-start', 'width': '100%'}),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=graph_2), width=6),
            dbc.Col(dcc.Graph(figure=graph_3), width=6)
        ], style={'display': 'flex', 'justifyContent': 'flex-start', 'width': '100%'})
    ])

    return graphs_html









    return 




def generate_dashboard_chart():
    
    # Load demand and generation data
    power_plants_df = load_data_table(DATABASE_PATH, 'power_plants')
    demand_df = load_data_table(DATABASE_PATH, 'demand_profile')
    solar_profile_df = load_data_table(DATABASE_PATH, 'solar_profile')
    wind_profile_df = load_data_table(DATABASE_PATH, 'wind_profile')

    # Ensure 'snapshot' is datetime and align profiles
    demand_df['snapshot'] = pd.to_datetime(demand_df['snapshot'], dayfirst=True)
    solar_profile_df['snapshot_time'] = pd.to_datetime(solar_profile_df['snapshot_time'], dayfirst=True)
    wind_profile_df['snapshot_time'] = pd.to_datetime(wind_profile_df['snapshot_time'], dayfirst=True)

    # Group demand by date and find the day with the highest demand
    demand_df['date'] = demand_df['snapshot'].dt.date
    daily_demand = demand_df.groupby('date')['demand_mw'].sum()
    max_demand_date = daily_demand.idxmax()

    # Filter data for the selected date
    max_day_data = demand_df[demand_df['date'] == max_demand_date]
    max_day_data['hour'] = max_day_data['snapshot'].dt.hour
    hourly_demand = max_day_data.groupby('hour')['demand_mw'].sum() / 1000  # Convert MW to GW

    # Align snapshots
    common_snapshots = max_day_data['snapshot'].unique()
    solar_profile_df = solar_profile_df[solar_profile_df['snapshot_time'].isin(common_snapshots)]
    wind_profile_df = wind_profile_df[wind_profile_df['snapshot_time'].isin(common_snapshots)]

    # Group plant types into desired categories
    type_mapping = {
        'Solar': 'Solar',
        'Wind': 'Wind',
        'DSR': 'DSR',
        'CC': 'CC',
    }
    power_plants_df['group'] = power_plants_df['type'].map(type_mapping).fillna('Other')

    # Prepare capacity data
    capacity_by_hour = pd.DataFrame(index=hourly_demand.index)

    for group in power_plants_df['group'].unique():
        if group in ['Solar', 'Wind']:
            # Handle solar and wind plants with profiles
            plants = power_plants_df[power_plants_df['group'] == group]
            profile_df = solar_profile_df if group == 'Solar' else wind_profile_df

            # Pre-filter profiles and merge with plants
            merged_df = plants.merge(
                profile_df,
                right_on='profile_name',
                left_on='profile',
                how='inner'
            )

            merged_df['adjusted_capacity'] = (merged_df['capacity_mw'] * merged_df['profile_y']) / 1000  # Convert MW to GW

            # Sum adjusted capacities per hour
            adjusted_capacity = merged_df.groupby('snapshot_time')['adjusted_capacity'].sum()
            adjusted_capacity.index = adjusted_capacity.index.hour

            capacity_by_hour[group] = adjusted_capacity
        else:
            # Aggregate other plant groups directly
            plants = power_plants_df[power_plants_df['group'] == group]
            total_capacity = plants['capacity_mw'].sum() / 1000  # Convert MW to GW
            capacity_by_hour[group] = total_capacity


    # Prepare the graph
    fig = go.Figure()

    # Add stacked bars for all plant groups
    for group in capacity_by_hour.columns:
        fig.add_trace(go.Bar(
            x=capacity_by_hour.index,
            y=capacity_by_hour[group],
            name=f'{group} Capacity',
            marker=dict(opacity=0.7)
        ))

    # Add line for hourly demand
    fig.add_trace(go.Scatter(
        x=hourly_demand.index,
        y=hourly_demand.values,
        mode='lines+markers',
        name='Hourly Demand',
        line=dict(color='red', width=3)
    ))

    # Update layout
    fig.update_layout(
        title=f"24-Hour Capacity vs Demand on {max_demand_date}",
        xaxis_title="Hour of Day",
        yaxis_title="Power (GW)",
        barmode='stack',  # Enable stacking for bars
        template="plotly_white",
        autosize=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Return the graph to the div
    return [dcc.Graph(figure=fig)]