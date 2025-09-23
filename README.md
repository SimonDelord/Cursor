# Simon Cursor Test

This is a test repository for exploring Cursor AI capabilities.

## Projects

### Temperature Sensor Simulator

A Python application that simulates a temperature sensor by generating random temperature readings at regular intervals. Available in two versions:

#### Version 1 - Basic Sensor (`temperature_sensor_v1.py`)

The original standalone version with console output only.

**Features:**
- Configurable temperature range and reading intervals
- Realistic temperature changes with gradual variance
- Clean output with timestamps and reading counters
- Command-line interface with customizable parameters
- Graceful shutdown with Ctrl+C
- No external dependencies (Python standard library only)

**Usage:**
```bash
# Basic usage (default settings)
python temperature_sensor_v1.py

# Custom temperature range and interval
python temperature_sensor_v1.py --min-temp 20 --max-temp 30 --interval 1.5

# Run for a specific duration (60 seconds)
python temperature_sensor_v1.py --duration 60
```

#### Version 2 - MQTT Enabled (`temperature_sensor_v2.py`)

Enhanced version with MQTT broker integration for IoT applications.

**Additional Features:**
- 📡 **MQTT Publishing**: Sends readings to any MQTT broker
- 🔐 **Authentication**: Supports username/password authentication
- 📊 **JSON Payloads**: Structured data with timestamps and metadata
- 🏷️ **Sensor IDs**: Configurable sensor identification
- 🔄 **Auto-reconnection**: Handles connection drops gracefully
- 📴 **Fallback Mode**: Works without MQTT if broker unavailable

**Prerequisites:**
```bash
# Install MQTT client library
pip install paho-mqtt
```

**Usage Examples:**
```bash
# Basic usage with local MQTT broker
python temperature_sensor_v2.py --mqtt-broker localhost

# Full configuration with authentication
python temperature_sensor_v2.py \
  --mqtt-broker mqtt.example.com \
  --mqtt-port 8883 \
  --mqtt-topic "home/sensors/temperature" \
  --mqtt-username "sensor_user" \
  --mqtt-password "secret123" \
  --sensor-id "living_room_temp"

# Custom sensor settings with MQTT
python temperature_sensor_v2.py \
  --min-temp 20 --max-temp 30 \
  --interval 5 \
  --mqtt-broker localhost \
  --mqtt-topic "sensors/temp"

# Without MQTT (acts like v1)
python temperature_sensor_v2.py
```

**MQTT Payload Format:**
```json
{
  "sensor_id": "temp_001",
  "temperature": 23.45,
  "timestamp": "2024-01-15T14:30:15.123456",
  "reading_count": 1,
  "unit": "celsius"
}
```

**Supported MQTT Brokers:**
- Local Mosquitto
- AWS IoT Core
- Azure IoT Hub
- Google Cloud IoT
- HiveMQ Cloud
- Any standard MQTT v3.1.1 broker

### Real-Time Truck Tracking System

A comprehensive real-time data pipeline for tracking truck locations using CDC (Change Data Capture), Kafka, and MQTT technologies.

#### Architecture Overview

The system demonstrates a modern data streaming architecture:

**MySQL** → **Debezium CDC** → **Kafka** → **MQTT Bridge** → **Real-time Applications**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   MySQL     │───▶│  Debezium   │───▶│    Kafka    │───▶│MQTT Broker  │
│ (trucks.    │    │   CDC       │    │   Topics    │    │ (Mosquitto) │
│  location)  │    │ Connector   │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                           │                      │
                                           ▼                      ▼
                                   ┌─────────────┐    ┌─────────────┐
                                   │  InfluxDB   │    │    Web      │
                                   │ (Grafana)   │    │ Clients     │
                                   └─────────────┘    └─────────────┘
```

#### Key Components

**1. Database Layer (`debezium-work/configs/`)**
- MySQL database with `trucks.location` table
- Optimized for CDC with binary logging and GTID support
- Stores truck coordinates with high precision (8 decimal places)

**2. Change Data Capture**
- **Connector**: `trucks-debezium-connector.yaml` 
- **Topic**: `realtime.trucks.location` 
- **Decimal Handling**: Configured with `decimal.handling.mode: "double"` for numeric coordinate values
- **Features**: Real-time change streaming, supports insert/update/delete operations

**3. Message Streaming**
- **Kafka Topics**:
  - `realtime.trucks.location` - Main CDC stream
  - Schema and heartbeat topics for connector management
- **Message Format**: JSON with proper numeric lat/long values (no base64 encoding)

**4. MQTT Bridge (`kafka-mqtt-bridge.py`)**
- Consumes from Kafka and publishes to MQTT topics:
  - `trucks/{truck_id}/location` - Individual truck location updates
  - `trucks/{truck_id}/status` - Truck operational status  
  - `trucks/all/locations` - Aggregated location stream for all trucks
- **QoS 1**: At-least-once delivery guarantee

**5. Data Visualization & Monitoring**
- **Grafana**: Real-time dashboards and alerts
- **InfluxDB**: Time-series data storage for historical analysis

#### Sample Data - Western Australia Trucks

The system includes 20 truck locations from the Pilbara mining region:

- **Coordinate Range**: -22.77°S to -22.78°S, 117.76°E to 117.77°E
- **IDs**: 420-439
- **Source**: Converted from DMS (Degrees/Minutes/Seconds) to decimal degrees
- **Precision**: 8 decimal places (~1mm accuracy)

See [`truck-coordinates.md`](truck-coordinates.md) for complete coordinate data and conversion details.

#### Key Files

**Configuration:**
- `debezium-work/configs/trucks-debezium-connector.yaml` - CDC connector setup
- `mosquitto-mqtt-broker.yaml` - MQTT broker deployment
- `kafka-mqtt-bridge-deployment.yaml` - Bridge service deployment

**Data Processing:**
- `kafka-mqtt-bridge.py` - Kafka to MQTT message bridge
- `kafka-to-influx-consumer.py` - Kafka to InfluxDB consumer
- `convert_coordinates.py` - DMS to decimal coordinate converter

**Sample Data:**
- `add_western_australia_trucks_batch2.sql` - 20 Pilbara truck locations
- `truck-coordinates.md` - Complete coordinate reference

#### Running the System

**Prerequisites:**
```bash
# Kubernetes cluster with Strimzi Kafka operator
# Debezium connector images
kubectl apply -f debezium-work/configs/
```

**Deploy Components:**
```bash
# Deploy Kafka cluster
kubectl apply -f debezium-work/configs/kafka-cluster.yaml

# Deploy MySQL with CDC configuration  
kubectl apply -f debezium-work/configs/mysql-deployment.yaml

# Deploy MQTT broker
kubectl apply -f mosquitto-mqtt-broker.yaml

# Deploy CDC connector
kubectl apply -f debezium-work/configs/trucks-debezium-connector.yaml

# Deploy message bridge
kubectl apply -f kafka-mqtt-bridge-deployment.yaml
```

**Add Sample Data:**
```bash
# Load Western Australia truck coordinates
kubectl exec -i mysql-pod -- mysql -u root -p < add_western_australia_trucks_batch2.sql
```

#### Monitoring & Testing

**Check CDC Messages:**
```bash
kubectl exec kafka-pod -- bin/kafka-console-consumer.sh \
  --topic realtime.trucks.location --from-beginning
```

**Monitor MQTT Topics:**
```bash
# Install paho-mqtt: pip install paho-mqtt
python3 mqtt_subscriber_test.py
```

**View Metrics:**
- Kafka: Connect to Kafka bootstrap service
- Grafana: Access via port-forward to grafana service
- MQTT: mosquitto service on port 1883

#### Technical Highlights

✅ **Numeric Coordinates**: Longitude/latitude as proper numbers (not strings/base64)  
✅ **Real-time CDC**: Sub-second change detection from MySQL  
✅ **High Availability**: Kafka replication and MQTT persistence  
✅ **Scalable Architecture**: Kubernetes-native deployment  
✅ **Monitoring Ready**: Built-in metrics and observability  

## Getting Started

This repository was created to test various development workflows and AI-assisted coding features.
