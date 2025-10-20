#!/bin/bash

# West Angelas Mining Site - Truck Route Injection Script
# Site-specific version of the continuous truck injection for West Angelas
# Includes additional logging and monitoring features

echo "🏭 West Angelas Mining Site - Truck Route Injection"
echo "📍 Location: Pilbara Region, Western Australia"
echo "🚛 Fleet: 2 active trucks (Truck #1: 17 waypoints, Truck #2: 10 waypoints)"
echo "⏱️  Update Interval: 5 seconds per truck"
echo "🔄 Route Type: Bidirectional with auto-reverse"
echo "🛑 Press Ctrl+C to stop"
echo "==============================================="

# Site-specific configuration
SITE_NAME="West Angelas Mining Site"
SITE_TIMEZONE="Australia/Perth"
LOG_FILE="/tmp/west-angelas-truck-injection.log"

# Get MySQL pod name
MYSQL_POD=$(kubectl get pods -n debezium-example -l app=mysql -o jsonpath='{.items[0].metadata.name}')

if [ -z "$MYSQL_POD" ]; then
    echo "❌ Error: Could not find MySQL pod in debezium-example namespace"
    exit 1
fi

echo "📡 Connected to MySQL pod: $MYSQL_POD"
echo "🏭 Site: $SITE_NAME"
echo "🌏 Timezone: $SITE_TIMEZONE"
echo "📝 Logging to: $LOG_FILE"
echo "🚀 Starting injection loop..."
echo ""

# Initialize logging
echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') - INFO - Starting West Angelas truck injection" >> $LOG_FILE

# Truck 1 coordinates (17 points) - Primary mining circuit
TRUCK1_COORDS=(
    "-23.173195,118.775248"  # Main depot
    "-23.171972,118.776257"  # North access road
    "-23.169328,118.776407"  # Mining area entrance
    "-23.169407,118.778467"  # Pit access point
    "-23.168666,118.780200"  # Loading zone A
    "-23.169979,118.780498"  # Loading zone B
    "-23.171201,118.778673"  # Haul road junction
    "-23.173445,118.777502"  # Checkpoint Alpha
    "-23.175506,118.778732"  # Processing area
    "-23.175926,118.780518"  # Stockpile zone
    "-23.175771,118.783375"  # Conveyor loading
    "-23.175734,118.787561"  # Rail loading facility
    "-23.174640,118.790002"  # Eastern boundary
    "-23.172597,118.789923"  # Return route point
    "-23.171520,118.789744"  # Maintenance checkpoint
    "-23.173195,118.775248"  # Return to depot
    "-23.174019,118.773752"  # Final approach
)

# Truck 2 coordinates (10 points) - Secondary mining circuit
TRUCK2_COORDS=(
    "-23.173195,118.775248"  # Shared depot
    "-23.174019,118.773752"  # South access road
    "-23.174822,118.773097"  # Secondary pit entrance
    "-23.174859,118.771232"  # Overburden area
    "-23.173600,118.770974"  # Waste dump access
    "-23.172177,118.771728"  # Service road junction
    "-23.170919,118.772601"  # Equipment staging
    "-23.169149,118.773018"  # Fuel station
    "-23.167672,118.773355"  # West boundary
    "-23.166449,118.773692"  # Turnaround point
)

# Initialize counters and directions
TRUCK1_INDEX=0
TRUCK2_INDEX=0
TRUCK1_DIRECTION=1  # 1 = forward, -1 = reverse
TRUCK2_DIRECTION=1  # 1 = forward, -1 = reverse
TRUCK1_MAX=$((${#TRUCK1_COORDS[@]} - 1))
TRUCK2_MAX=$((${#TRUCK2_COORDS[@]} - 1))

INJECTION_COUNT=0
START_TIME=$(date +%s)

# Function to inject truck entry with enhanced logging
inject_truck() {
    local truck_number=$1
    local lat=$2
    local lon=$3
    local index=$4
    local direction=$5
    
    # Insert into database
    kubectl exec -n debezium-example $MYSQL_POD -- mysql -u root -pdebezium123 -D trucks -e \
        "INSERT INTO location (truck_number, latitude, longitude, created_at, updated_at) VALUES ($truck_number, $lat, $lon, NOW(), NOW());" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        local dir_arrow="→"
        if [ $direction -eq -1 ]; then
            dir_arrow="←"
        fi
        echo "✅ Truck $truck_number [$index] $dir_arrow ($lat, $lon)"
        
        # Enhanced logging with timestamp and coordinates
        echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') - INFO - Truck $truck_number injected at ($lat, $lon) - Index: $index, Direction: $direction" >> $LOG_FILE
    else
        echo "❌ Failed to inject Truck $truck_number"
        echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') - ERROR - Failed to inject Truck $truck_number at ($lat, $lon)" >> $LOG_FILE
    fi
}

# Function to update index and direction
update_index() {
    local current_index=$1
    local current_direction=$2
    local max_index=$3
    
    local new_index=$((current_index + current_direction))
    local new_direction=$current_direction
    
    # Check bounds and reverse if needed
    if [ $new_index -gt $max_index ]; then
        new_index=$max_index
        new_direction=-1
        echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') - INFO - Route reversed at max index $max_index" >> $LOG_FILE
    elif [ $new_index -lt 0 ]; then
        new_index=0
        new_direction=1
        echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') - INFO - Route reversed at min index 0" >> $LOG_FILE
    fi
    
    echo "$new_index $new_direction"
}

# Enhanced cleanup function
cleanup() {
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    echo -e "\n🛑 Stopping West Angelas truck injection..."
    echo "📊 Total injections: $INJECTION_COUNT"
    echo "⏱️  Runtime: ${duration} seconds"
    echo "🏭 Site: $SITE_NAME"
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') - INFO - Stopping injection after $INJECTION_COUNT cycles, runtime: ${duration}s" >> $LOG_FILE
    exit 0
}

# Trap Ctrl+C for clean exit
trap cleanup INT

# Main injection loop
while true; do
    INJECTION_COUNT=$((INJECTION_COUNT + 1))
    CURRENT_TIME=$(date '+%H:%M:%S')
    echo "🔄 Injection cycle #$INJECTION_COUNT - $CURRENT_TIME"
    
    # Process Truck 1 (Primary mining circuit)
    COORD1=${TRUCK1_COORDS[$TRUCK1_INDEX]}
    LAT1=$(echo $COORD1 | cut -d',' -f1)
    LON1=$(echo $COORD1 | cut -d',' -f2)
    inject_truck 1 $LAT1 $LON1 $TRUCK1_INDEX $TRUCK1_DIRECTION
    
    # Process Truck 2 (Secondary mining circuit)
    COORD2=${TRUCK2_COORDS[$TRUCK2_INDEX]}
    LAT2=$(echo $COORD2 | cut -d',' -f1)
    LON2=$(echo $COORD2 | cut -d',' -f2)
    inject_truck 2 $LAT2 $LON2 $TRUCK2_INDEX $TRUCK2_DIRECTION
    
    # Update indices for next iteration
    RESULT1=($(update_index $TRUCK1_INDEX $TRUCK1_DIRECTION $TRUCK1_MAX))
    TRUCK1_INDEX=${RESULT1[0]}
    TRUCK1_DIRECTION=${RESULT1[1]}
    
    RESULT2=($(update_index $TRUCK2_INDEX $TRUCK2_DIRECTION $TRUCK2_MAX))
    TRUCK2_INDEX=${RESULT2[0]}
    TRUCK2_DIRECTION=${RESULT2[1]}
    
    echo ""
    
    # Wait 5 seconds before next injection
    sleep 5
done
