import pandas as pd

def check_capacity_vs_demand(network):
    # Calculate effective capacities directly from p_max_pu
    generator_capacities = network.generators_t.p_max_pu * network.generators.p_nom
    total_capacity_per_snapshot = generator_capacities.sum(axis=1)
    total_demand_per_snapshot = network.loads_t.p_set.sum(axis=1)

    # Compare capacity vs demand for each snapshot
    passed_snapshots = (total_capacity_per_snapshot >= total_demand_per_snapshot).sum()
    failed_snapshots = len(network.snapshots) - passed_snapshots

    # Return summary as a single dictionary
    return {
        "Check Name": "Total Capacity vs Total Demand",
        "Snapshots Passed": passed_snapshots,
        "Snapshots Failed": failed_snapshots
    }

def check_nodal_capacity_vs_demand(network):
    results = {"Snapshots Passed": 0, "Snapshots Failed": 0}

    # Calculate nodal generation capacity
    generator_capacities = network.generators_t.p_max_pu * network.generators.p_nom
    nodal_generation_capacity = generator_capacities.groupby(network.generators.bus, axis=1).sum()

    # Calculate transmission capacity into each node
    transmission_capacity = pd.DataFrame(0, index=network.snapshots, columns=network.buses.index)
    for line_name, line in network.lines.iterrows():
        bus0 = line.bus0
        bus1 = line.bus1
        line_capacity = line.s_nom  # Nominal capacity of the line

        # Distribute line capacity to both connected buses (i.e., double counting)
        transmission_capacity[bus0] += line_capacity
        transmission_capacity[bus1] += line_capacity

    # Total nodal capacity (generation + transmission)
    total_nodal_capacity = nodal_generation_capacity.add(transmission_capacity, fill_value=0)

    # Compare total capacity vs nodal demand
    for snapshot in network.snapshots:
        for bus in network.buses.index:
            nodal_demand = network.loads_t.p_set.get(bus, pd.Series(0, index=network.snapshots))[snapshot]
            if total_nodal_capacity.at[snapshot, bus] >= nodal_demand:
                results["Snapshots Passed"] += 1
            else:
                results["Snapshots Failed"] += 1

    # Return summary as a dictionary
    return {
        "Check Name": "Nodal Capacity vs Demand",
        **results
    }



def export_network_to_excel(network, file_path):
    """
    Exports the PyPSA network object to an Excel file.

    Args:
    - network (pypsa.Network): The PyPSA network object to export.
    - file_path (str): Path to save the Excel file.
    """
    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        # Export network components to DataFrames
        network.buses.to_excel(writer, sheet_name='Buses')
        network.generators.to_excel(writer, sheet_name='Generators')
        network.generators_t.p_max_pu.to_excel(writer, sheet_name='Generator Profiles')
        network.loads.to_excel(writer, sheet_name='Loads')
        network.loads_t.p_set.to_excel(writer, sheet_name='Load Profiles')
        network.storage_units.to_excel(writer, sheet_name='Storage Units')
        network.storage_units_t.p.to_excel(writer, sheet_name='Storage Power')
        network.storage_units_t.state_of_charge.to_excel(writer, sheet_name='Storage State')
        network.lines.to_excel(writer, sheet_name='Lines')
        network.snapshots.to_series().to_frame(name='Snapshots').to_excel(writer, sheet_name='Snapshots')

    print(f"Network successfully exported to {file_path}")

# Example usage
# file_path = "network_export.xlsx"
# export_network_to_excel(network, file_path)