#!/bin/bash

# Continuous Truck Route Injection Script
# Injects truck_number=1 and truck_number=2 entries every 5 seconds
# Reverses direction when reaching end of routes
# Runs forever until stopped with Ctrl+C

echo "🚛 Starting Continuous Truck Route Injection"
echo "📊 truck_number=1: 17 route points"
echo "📊 truck_number=2: 10 route points" 
echo "⏱️  Injection interval: 5 seconds per truck"
echo "🔄 Auto-reverse at end of routes"
echo "🛑 Press Ctrl+C to stop"
echo "==============================================="

# Get MySQL pod name
MYSQL_POD=$(kubectl get pods -n debezium-example -l app=mysql -o jsonpath='{.items[0].metadata.name}')

if [ -z "$MYSQL_POD" ]; then
    echo "❌ Error: Could not find MySQL pod"
    exit 1
fi

echo "📡 Using MySQL pod: $MYSQL_POD"
echo "🚀 Starting injection loop..."
echo ""

# Truck 1 coordinates (17 points)
TRUCK1_COORDS=(
    "-23.173195,118.775248"
    "-23.171972,118.776257"
    "-23.169328,118.776407"
    "-23.169407,118.778467"
    "-23.168666,118.780200"
    "-23.169979,118.780498"
    "-23.171201,118.778673"
    "-23.173445,118.777502"
    "-23.175506,118.778732"
    "-23.175926,118.780518"
    "-23.175771,118.783375"
    "-23.175734,118.787561"
    "-23.174640,118.790002"
    "-23.172597,118.789923"
    "-23.171520,118.789744"
    "-23.173195,118.775248"
    "-23.174019,118.773752"
)

# Truck 2 coordinates (10 points)
TRUCK2_COORDS=(
    "-23.173195,118.775248"
    "-23.174019,118.773752"
    "-23.174822,118.773097"
    "-23.174859,118.771232"
    "-23.173600,118.770974"
    "-23.172177,118.771728"
    "-23.170919,118.772601"
    "-23.169149,118.773018"
    "-23.167672,118.773355"
    "-23.166449,118.773692"
)

# Initialize counters and directions
TRUCK1_INDEX=0
TRUCK2_INDEX=0
TRUCK1_DIRECTION=1  # 1 = forward, -1 = reverse
TRUCK2_DIRECTION=1  # 1 = forward, -1 = reverse
TRUCK1_MAX=$((${#TRUCK1_COORDS[@]} - 1))
TRUCK2_MAX=$((${#TRUCK2_COORDS[@]} - 1))

INJECTION_COUNT=0

# Function to inject truck entry
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
    else
        echo "❌ Failed to inject Truck $truck_number"
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
    elif [ $new_index -lt 0 ]; then
        new_index=0
        new_direction=1
    fi
    
    echo "$new_index $new_direction"
}

# Trap Ctrl+C for clean exit
trap 'echo -e "\n🛑 Stopping continuous injection..."; echo "📊 Total injections: $INJECTION_COUNT"; exit 0' INT

# Main injection loop
while true; do
    INJECTION_COUNT=$((INJECTION_COUNT + 1))
    echo "🔄 Injection cycle #$INJECTION_COUNT - $(date '+%H:%M:%S')"
    
    # Process Truck 1
    COORD1=${TRUCK1_COORDS[$TRUCK1_INDEX]}
    LAT1=$(echo $COORD1 | cut -d',' -f1)
    LON1=$(echo $COORD1 | cut -d',' -f2)
    inject_truck 1 $LAT1 $LON1 $TRUCK1_INDEX $TRUCK1_DIRECTION
    
    # Process Truck 2  
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


