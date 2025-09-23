# Repository Structure

This repository contains a comprehensive real-time truck tracking system with organized components.

## 📁 Directory Structure

```
simon-cursor-test/
├── mqtt/                           # MQTT Components
│   ├── configs/                    # MQTT broker and bridge configurations
│   │   ├── mosquitto-mqtt-broker.yaml
│   │   └── kafka-mqtt-bridge-deployment.yaml
│   ├── bridge/                     # Kafka-to-MQTT bridge implementation
│   │   ├── kafka-mqtt-bridge.py
│   │   └── requirements-mqtt.txt
│   ├── tests/                      # MQTT testing utilities
│   │   └── mqtt_subscriber_test.py
│   └── build-mqtt/                 # MQTT bridge build artifacts
│
├── data/                           # Data and Scripts
│   ├── coordinates/                # Truck coordinate data
│   │   ├── truck-coordinates.md
│   │   └── convert_coordinates.py
│   └── sql-scripts/               # Database scripts
│       ├── add_western_australia_trucks.sql
│       ├── add_western_australia_trucks_batch2.sql
│       ├── add-10-more-trucks-demo.sql
│       └── add-20-more-trucks-test.sql
│
├── debezium-work/                 # Change Data Capture (CDC)
│   ├── configs/                   # Kafka and Debezium configurations
│   ├── scripts/                   # Database setup scripts
│   └── docs/                      # CDC documentation
│
├── kafka-components/              # Kafka Processing
│   ├── kafka-to-influx-consumer.py
│   ├── build-consumer/
│   └── requirements.txt
│
├── deployments/                   # Kubernetes Deployments
│   ├── kafka-consumer-deployment.yaml
│   ├── influxdb-deployment.yaml
│   └── grafana-deployment.yaml
│
├── docker/                        # Container Definitions
│   ├── Dockerfile.consumer
│   └── Dockerfile.mqtt-bridge
│
├── temperature-sensors/           # Temperature Sensor Simulators
│   ├── temperature_sensor_original.py
│   ├── temperature_sensor_v1.py
│   └── temperature_sensor_v2.py
│
├── README.md                      # Main documentation
└── demo-trucks-connector.yaml    # Legacy connector (to be removed)
```

## 🏗️ System Architecture

**Real-Time Data Pipeline:**
```
MySQL Database → Debezium CDC → Kafka Topics → MQTT Bridge → IoT Applications
                                              → InfluxDB → Grafana Dashboards
```

## 🚀 Quick Start

### MQTT System
```bash
# Deploy MQTT broker
kubectl apply -f mqtt/configs/mosquitto-mqtt-broker.yaml

# Deploy Kafka-MQTT bridge
kubectl apply -f mqtt/configs/kafka-mqtt-bridge-deployment.yaml

# Test MQTT messages
python3 mqtt/tests/mqtt_subscriber_test.py
```

### Data Management
```bash
# Load Western Australia truck coordinates
kubectl exec -i mysql-pod -- mysql -u root -p < data/sql-scripts/add_western_australia_trucks_batch2.sql

# Convert coordinate formats
python3 data/coordinates/convert_coordinates.py
```

### Monitoring
```bash
# Deploy monitoring stack
kubectl apply -f deployments/influxdb-deployment.yaml
kubectl apply -f deployments/grafana-deployment.yaml
```

## 📊 Data Flow

1. **Source**: MySQL `trucks.location` table with high-precision coordinates
2. **CDC**: Debezium captures changes with `decimal.handling.mode: "double"`
3. **Streaming**: Kafka `realtime.trucks.location` topic
4. **Distribution**: MQTT topics (`trucks/{id}/location`, `trucks/all/locations`)
5. **Visualization**: InfluxDB storage → Grafana dashboards

## 🌍 Sample Data

- **20 Western Australia locations** (Pilbara mining region)
- **Coordinates**: -22.77°S to -22.78°S, 117.76°E to 117.77°E
- **Precision**: 8 decimal places (~1mm accuracy)
- **Format**: Converted from DMS (Degrees/Minutes/Seconds) to decimal

## 🔧 Development

Each component is self-contained with its own:
- Configuration files
- Build scripts
- Requirements/dependencies
- Documentation

See individual folder READMEs for component-specific details.
