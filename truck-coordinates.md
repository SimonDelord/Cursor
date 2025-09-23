# Truck Location Coordinates

This document contains the geographical coordinates for truck locations used in the real-time tracking demonstration.

## Western Australia - Pilbara Region Coordinates

### Original DMS (Degrees, Minutes, Seconds) Format
The following 20 coordinates were provided in DMS format and converted to decimal degrees:

| ID Range | Original DMS Coordinates | Decimal Degrees |
|----------|-------------------------|-----------------|
| 420-439 | 22°46'25"S 117°45'43"E | -22.77361111, 117.76194444 |
| | 22°46'30"S 117°45'51"E | -22.77500000, 117.76416667 |
| | 22°46'28"S 117°45'56"E | -22.77444444, 117.76555556 |
| | 22°46'27"S 117°45'59"E | -22.77416667, 117.76638889 |
| | 22°46'29"S 117°46'03"E | -22.77472222, 117.76750000 |
| | 22°46'23"S 117°46'07"E | -22.77305556, 117.76861111 |
| | 22°46'27"S 117°46'09"E | -22.77416667, 117.76916667 |
| | 22°46'29"S 117°46'20"E | -22.77472222, 117.77222222 |
| | 22°46'27"S 117°46'23"E | -22.77416667, 117.77305556 |
| | 22°46'20"S 117°46'17"E | -22.77222222, 117.77138889 |
| | 22°46'18"S 117°46'21"E | -22.77166667, 117.77250000 |
| | 22°46'25"S 117°46'28"E | -22.77361111, 117.77444444 |
| | 22°46'32"S 117°46'29"E | -22.77555556, 117.77472222 |
| | 22°46'36"S 117°46'18"E | -22.77666667, 117.77166667 |
| | 22°46'39"S 117°46'10"E | -22.77750000, 117.76944444 |
| | 22°46'40"S 117°45'59"E | -22.77777778, 117.76638889 |
| | 22°46'43"S 117°45'48"E | -22.77861111, 117.76333333 |
| | 22°46'46"S 117°45'38"E | -22.77944444, 117.76055556 |
| | 22°46'46"S 117°45'36"E | -22.77944444, 117.76000000 |
| | 22°46'49"S 117°45'33"E | -22.78027778, 117.75916667 |

### Location Information
- **Region**: Western Australia, Pilbara region
- **Area**: Mining/industrial region known for iron ore operations
- **Coordinate System**: WGS84 (World Geodetic System 1984)
- **Precision**: 8 decimal places (approximately 1mm precision)

### Usage in System
These coordinates are stored in the MySQL `trucks.location` table and streamed through:
1. **MySQL Database** → Debezium CDC → **Kafka Topic** (`realtime.trucks.location`) → **MQTT Topics** (`trucks/{id}/location`, `trucks/all/locations`)

### Data Processing Notes
- Originally stored as DECIMAL(10,8) for latitude and DECIMAL(11,8) for longitude in MySQL
- Debezium connector configured with `decimal.handling.mode: "double"` to ensure numeric values in Kafka messages
- Converted from string representation to proper numeric values to avoid base64 encoding issues

### Files Related to These Coordinates
- `add_western_australia_trucks.sql` - First batch (IDs 400-419)
- `add_western_australia_trucks_batch2.sql` - Second batch (IDs 420-439)  
- `convert_coordinates.py` - Python script for DMS to decimal conversion

## Map Visualization
The coordinates form a cluster in the Pilbara region of Western Australia, suitable for demonstrating real-time truck tracking in a mining operations context.

```
Approximate bounding box:
- North: -22.771667°S
- South: -22.780278°S  
- West: 117.759167°E
- East: 117.774722°E
```
