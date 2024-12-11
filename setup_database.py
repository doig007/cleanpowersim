import sqlite3

# Step 1: Connect to (or create) the SQLite database
conn = sqlite3.connect('power_system.db')
cursor = conn.cursor()

# Step 2: Create the Power Plants table
cursor.execute('''
CREATE TABLE IF NOT EXISTS power_plants (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    capacity_mw REAL NOT NULL,
    bus_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    srmc REAL NOT NULL,
    profile TEXT
)
''')


# Step 3: Create the Buses table (now with longitude and latitude)
cursor.execute('''
CREATE TABLE IF NOT EXISTS buses (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    voltage_kv REAL NOT NULL,
    longitude REAL,
    latitude REAL
)
''')

# Step 4: Create the Transmission Lines table
cursor.execute('''
CREATE TABLE IF NOT EXISTS lines (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    from_bus INTEGER NOT NULL,
    to_bus INTEGER NOT NULL,
    length_km REAL NOT NULL,
    max_capacity_mw REAL NOT NULL,
    r REAL NOT NULL,
    x REAL NOT NULL
)
''')

# Step 5: Create the Demand Profile table
cursor.execute('''
CREATE TABLE IF NOT EXISTS demand_profile (
    id INTEGER PRIMARY KEY,
    bus_id INTEGER NOT NULL,
    demand_mw REAL NOT NULL,
    snapshot TEXT NOT NULL
)
''')

# Step 6: Create the Storage Units table
cursor.execute('''
CREATE TABLE IF NOT EXISTS storage_units (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    capacity_mw REAL NOT NULL,
    max_energy_mwh REAL NOT NULL,
    bus_id INTEGER NOT NULL,
    efficiency REAL NOT NULL,
    type TEXT NOT NULL
)
''')

# Step 7: Create the Snapshots table
cursor.execute('''
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY,
    snapshot_time TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0
)
''')

# Step 8: Create the Wind and Solar profile tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS wind_profile (
    id INTEGER PRIMARY KEY,
    profile_name TEXT NOT NULL,
    snapshot_time TEXT NOT NULL,
    profile REAL NOT NULL DEFAULT 1.0
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS solar_profile (
    id INTEGER PRIMARY KEY,
    profile_name TEXT NOT NULL,
    snapshot_time TEXT NOT NULL,
    profile REAL NOT NULL DEFAULT 1.0
)
''')

# Step 9: Insert initial data into the Buses table (with longitude and latitude)
buses_data = [
    (1, "Bus A", 110, -79.3832, 43.6532),
    (2, "Bus B", 220, -80.2453, 42.3151),
    (3, "Bus C", 110, -81.0457, 44.2311)
]
cursor.executemany('''
INSERT OR IGNORE INTO buses (id, name, voltage_kv, longitude, latitude)
VALUES (?, ?, ?, ?, ?)
''', buses_data)

# Step 10: Insert initial data into the Power Plants table
power_plants_data = [
    (1, "Plant 1", 100, 1, "Solar", 15, "Solar A"),
    (2, "Plant 2", 200, 2, "Wind", 10, "Wind A"),
    (3, "Plant 3", 150, 3, "Hydro", 20, None)
]
cursor.executemany('''
INSERT OR IGNORE INTO power_plants (id, name, capacity_mw, bus_id, type, srmc, profile)
VALUES (?, ?, ?, ?, ?, ?, ?)
''', power_plants_data)

# Step 11: Insert initial data into the Transmission Lines table
lines_data = [
    (1, "Line 1", 1, 2, 50, 100, 0.01, 0.02),
    (2, "Line 2", 2, 3, 75, 150, 0.015, 0.025)
]
cursor.executemany('''
INSERT OR IGNORE INTO lines (id, name, from_bus, to_bus, length_km, max_capacity_mw, r, x)
VALUES (?, ?, ?, ?, ?, ?, ?, ?) 
''', lines_data)

# Step 11: Insert initial data into the Demand Profile table
demand_data = [
    (1, 1, 50, "2024-01-01 00:00:00"),
    (2, 2, 60, "2024-01-01 00:00:00"),
    (3, 3, 40, "2024-01-01 00:00:00"),
    (4, 1, 60, "2024-01-01 01:00:00"),
    (5, 2, 80, "2024-01-01 01:00:00"),
    (6, 3, 40, "2024-01-01 01:00:00"),
    (7, 1, 65, "2024-01-01 02:00:00"),
    (8, 2, 100, "2024-01-01 02:00:00"),
    (9, 3, 40, "2024-01-01 02:00:00"),  
]
cursor.executemany('''
INSERT OR IGNORE INTO demand_profile (id, bus_id, demand_mw, snapshot)
VALUES (?, ?, ?, ?)
''', demand_data)

# Step 13: Insert initial data into the Storage Units table
storage_units_data = [
    (1, "Storage 1", 50, 200, 1, 0.9, "Battery"),
    (2, "Storage 2", 100, 400, 2, 0.85, "Pumped Hydro"),
    (3, "Storage 3", 75, 300, 3, 0.88, "Battery")
]
cursor.executemany('''
INSERT OR IGNORE INTO storage_units (id, name, capacity_mw, max_energy_mwh, bus_id, efficiency, type)
VALUES (?, ?, ?, ?, ?, ?, ?)
''', storage_units_data)

# Step 14: Insert initial data into the Snapshots table
snapshots_data = [
    (1, "2024-01-01 00:00:00", 1.0),
    (2, "2024-01-01 01:00:00", 1.0),
    (3, "2024-01-01 02:00:00", 1.0)
]
cursor.executemany('''
INSERT OR IGNORE INTO snapshots (id, snapshot_time, weight)
VALUES (?, ?, ?)
''', snapshots_data)

# Step 15: Insert dummy data into the Wind and Solar profile tables
wind_profiles_data = [
    (1, "Wind A", "2024-01-01 00:00:00", 0.8),
    (2, "Wind A", "2024-01-01 01:00:00", 0.85),
    (3, "Wind A", "2024-01-01 02:00:00", 0.9),
    (4, "Wind B", "2024-01-01 00:00:00", 0.7),
    (5, "Wind B", "2024-01-01 01:00:00", 0.75),
    (6, "Wind B", "2024-01-01 02:00:00", 0.8)
]
cursor.executemany('''
INSERT OR IGNORE INTO wind_profile (id, profile_name, snapshot_time, profile)
VALUES (?, ?, ?, ?)
''', wind_profiles_data)

solar_profiles_data = [
    (1, "Solar A", "2024-01-01 00:00:00", 0.9),
    (2, "Solar A", "2024-01-01 01:00:00", 0.95),
    (3, "Solar A", "2024-01-01 02:00:00", 1.0),
    (4, "Solar B", "2024-01-01 00:00:00", 0.85),
    (5, "Solar B", "2024-01-01 01:00:00", 0.9),
    (6, "Solar B", "2024-01-01 02:00:00", 0.95)
]
cursor.executemany('''
INSERT OR IGNORE INTO solar_profile (id, profile_name, snapshot_time, profile)
VALUES (?, ?, ?, ?)
''', solar_profiles_data)

# Step 16: Commit changes and close the connection
conn.commit()
conn.close()

print("Database setup complete. The power_system.db file has been updated with initial data.")
