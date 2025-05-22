# Clean Power System Simulation Web Application (cleanpowersim)

## Overview
This project is an interactive web application designed to simulate power systems, specifically focused on renewable energy sources such as wind and solar. The application allows users to modify system parameters, view a network diagram, run optimization models, and view the results of these simulations. The app is built using Python, Dash, and PyPSA (Python for Power System Analysis).

![image](https://github.com/user-attachments/assets/83a9704d-f620-4280-91a0-18cc42f9a93f)

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

## Data Handling and User Sessions
This application is designed to provide each user with a fresh, default dataset upon visiting the webpage. User-specific modifications to the data (e.g., through the Editor, Dashboard sliders, or file uploads) are maintained in-memory for the duration of their session and do not affect other users or the underlying default data.

**Key Characteristics:**

*   **Default Data Source:** The `power_system.db` SQLite database file serves as the master template for the default network data. It should be treated as read-only by the running web application. The script `setup_database.py` can be used to initialize or reset this database to its default state.
*   **In-Memory Session Data:**
    *   When the application starts, it loads the default data from `power_system.db` into global pandas DataFrames in memory.
    *   User interactions that modify data (e.g., editing tables, adjusting sliders on the dashboard, uploading a new network data file) operate on copies of this data, stored within Dash `dcc.Store` components in the user's browser session.
    *   These changes are isolated to the current user's session. Refreshing the page or starting a new session will revert to the clean, default dataset.
*   **No Persistent User Changes:** Changes made by a user are not saved back to `power_system.db`. This ensures that every user visit starts with the same baseline data.
*   **Data Download:** The "Download Network Data" feature allows users to download an Excel file representing the current state of their in-session data, including any modifications they've made.

**Implications for Developers:**

*   When adding new features that involve data modification, ensure that changes are made to the in-memory DataFrames (sourced from `dcc.Store`s or copies of the global defaults) and stored back into the appropriate `dcc.Store` for the session.
*   Avoid any direct calls to `save_data(DATABASE_PATH, ...)` or other database write operations targeting `power_system.db` within the regular user interaction callbacks in `app.py`.
*   The global DataFrames loaded at app startup (e.g., `app.power_plants_df`) should be treated as read-only defaults after initial load; always use `.copy()` if you need a mutable version based on these globals before storing it in a session store. Helper functions like `get_df_from_store_or_global` in `run_optimization_callback` demonstrate this pattern.


