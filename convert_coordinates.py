#!/usr/bin/env python3
"""
Convert DMS (Degrees, Minutes, Seconds) coordinates to decimal degrees
and generate SQL INSERT statements for the MySQL location table
"""

def dms_to_decimal(degrees, minutes, seconds, direction):
    """Convert DMS to decimal degrees"""
    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if direction in ['S', 'W']:
        decimal = -decimal
    return decimal

def parse_coordinate(coord_str):
    """Parse coordinate string like "22°46'25\"S" """
    # Remove quotes and split
    coord_str = coord_str.replace('"', '').strip()
    direction = coord_str[-1]  # Last character (N/S/E/W)
    coord_str = coord_str[:-1]  # Remove direction
    
    # Split by degree, minute symbols
    parts = coord_str.replace('°', ' ').replace("'", ' ').split()
    degrees = int(parts[0])
    minutes = int(parts[1])
    seconds = int(parts[2]) if len(parts) > 2 else 0
    
    return dms_to_decimal(degrees, minutes, seconds, direction)

# The 20 coordinate pairs provided
coordinates = [
    ('22°46\'25"S', '117°45\'43"E'),
    ('22°46\'30"S', '117°45\'51"E'),
    ('22°46\'28"S', '117°45\'56"E'),
    ('22°46\'27"S', '117°45\'59"E'),
    ('22°46\'29"S', '117°46\'03"E'),
    ('22°46\'23"S', '117°46\'07"E'),
    ('22°46\'27"S', '117°46\'09"E'),
    ('22°46\'29"S', '117°46\'20"E'),
    ('22°46\'27"S', '117°46\'23"E'),
    ('22°46\'20"S', '117°46\'17"E'),
    ('22°46\'18"S', '117°46\'21"E'),
    ('22°46\'25"S', '117°46\'28"E'),
    ('22°46\'32"S', '117°46\'29"E'),
    ('22°46\'36"S', '117°46\'18"E'),
    ('22°46\'39"S', '117°46\'10"E'),
    ('22°46\'40"S', '117°45\'59"E'),
    ('22°46\'43"S', '117°45\'48"E'),
    ('22°46\'46"S', '117°45\'38"E'),
    ('22°46\'46"S', '117°45\'36"E'),
    ('22°46\'49"S', '117°45\'33"E')
]

print("Converting coordinates to decimal degrees...")
print("=" * 60)

# Convert coordinates and prepare SQL
sql_values = []
start_id = 400  # Start from ID 400 to avoid conflicts

for i, (lat_dms, lon_dms) in enumerate(coordinates):
    lat_decimal = parse_coordinate(lat_dms)
    lon_decimal = parse_coordinate(lon_dms)
    truck_id = start_id + i
    
    print(f"Truck {truck_id}: {lat_dms} {lon_dms} → {lat_decimal:.6f}, {lon_decimal:.6f}")
    
    sql_values.append(f"({truck_id}, {lat_decimal:.8f}, {lon_decimal:.8f})")

# Generate SQL file content
sql_insert_values = ',\n'.join(sql_values)
sql_content = f"""-- Insert 20 new truck locations from DMS coordinates
-- These locations appear to be in Western Australia (Pilbara region)

USE trucks;

INSERT INTO location (id, latitude, longitude) VALUES
{sql_insert_values};
"""

# Write SQL file
with open('add_western_australia_trucks.sql', 'w') as f:
    f.write(sql_content)

print("\n" + "=" * 60)
print("SQL file 'add_western_australia_trucks.sql' created successfully!")
print(f"Contains {len(coordinates)} truck locations with IDs {start_id}-{start_id + len(coordinates) - 1}")
