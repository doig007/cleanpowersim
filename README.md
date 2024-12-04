# cleanpowersim Clean Power System Simulation Web Application

## Overview
This project is an interactive web application designed to simulate power systems, specifically focused on renewable energy sources such as wind and solar. The application allows users to modify system parameters, view a network diagram, run optimization models, and view the results of these simulations. The app is built using Python, Dash, and PyPSA (Python for Power System Analysis).

## Features
- **Power System Editor**: Edit and configure power plants, transmission lines, storage units, demand profiles, and renewable generation profiles.
- **Network Diagram**: Visualize the power system network, including generators, storage units, and buses.
- **Optimization**: Run an optimization to determine the optimal dispatch of power generation, including economic dispatch using PyPSA.
- **Interactive Charts**: View the optimization results with dynamically generated charts.

## Requirements
- Python 3.7 or higher
- SQLite for the database backend
- Dash and related libraries for the web interface
- PyPSA for power system modeling
- Pandas, NumPy, Matplotlib, Plotly for data handling and visualization

## Installation
1. Clone the repository to your local machine:
   ```sh
   git clone https://github.com/yourusername/power-system-simulation.git
   cd power-system-simulation
   ```

2. Create a virtual environment and activate it:
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required Python packages:
   ```sh
   pip install -r requirements.txt
   ```

4. Set up the database by running the setup script:
   ```sh
   python setup_database.py
   ```
   This will create the `power_system.db` SQLite database and populate it with initial data for power plants, buses, transmission lines, demand profiles, storage units, and renewable generation profiles.

## Running the Application
To run the web application:
```sh
python app.py
```
The application will start a local server at `http://127.0.0.1:8050/`. You can navigate to this URL in your web browser to access the dashboard.

## Project Structure
- **app.py**: Main entry point of the Dash application, defining the layout and callbacks.
- **setup_database.py**: Script for creating and populating the SQLite database with initial data.
- **external_functions.py**: Contains utility functions for loading data, creating the PyPSA network, and managing the database.
- **page_layout.py**: Handles the different pages and layouts for the Dash application, including the power system editor and network diagram.
- **network_styles.py**: Defines the styles used for visualizing the power system network using Cytoscape.

## Key Features Explained
### Database Setup
The database (`power_system.db`) is set up using the `setup_database.py` script, which defines tables such as:
- **Power Plants**: Stores information about power plants, including type (solar, wind, hydro) and capacity.
- **Wind and Solar Profiles**: Stores the generation profiles (from 0 to 1) for different renewable energy plants, which act as constraints for maximum possible generation.
- **Demand Profiles**: Records the demand values for different buses at various snapshot times.

### Running Simulations
The `create_network` function in `external_functions.py` uses PyPSA to create a power system model, including buses, generators, transmission lines, and storage units. The model can be optimized using PyPSA's optimization engine to determine the optimal dispatch of the generators while respecting system constraints.

## Usage
1. **Edit System Data**: Navigate to the editor page to update the system data for power plants, transmission lines, demand, and storage units.
2. **Add Generation Profiles**: Edit or add wind and solar profiles to model different weather scenarios and generation patterns.
3. **Run Optimization**: Click on "Run Optimization" to determine optimal power dispatch, and view the results in the "Results" tab.
4. **Network Diagram**: Explore the interactive network diagram to see the layout of the power system and its components.

## Future Enhancements
- **Integration with Real-Time Data**: Connect to live weather or market data for dynamic simulations.
- **Advanced Optimization**: Implement more complex optimization algorithms considering carbon emissions and operational constraints.
- **User Management**: Add authentication and user management to allow multiple users to save their own configurations.

## Contributing
Contributions are welcome! Feel free to submit a pull request or open an issue for any feature requests or bug reports.

## License
This project is licensed under the MIT License. See the LICENSE file for more information.

## Contact
For any questions or suggestions, please contact james@doig.uk


