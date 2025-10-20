# West Angelas Mining Site - Real-Time Truck Tracking

## 🏭 Site Overview

**Location**: West Angelas Mine, Pilbara Region, Western Australia  
**Coordinates**: -23.17°S, 118.77°E  
**Operator**: Mining Operations  
**Purpose**: Real-time tracking of mining truck fleet operations

## 🚛 Fleet Information

### Active Trucks
- **Truck #1**: 17-point route with bidirectional traversal
- **Truck #2**: 10-point route with bidirectional traversal

### Route Coverage
- **Coordinate Range**: -23.166°S to -23.176°S, 118.771°E to 118.790°E
- **Precision**: 8 decimal places (~1mm accuracy)
- **Total Route Points**: 27 unique waypoints across both trucks

## 📊 Real-Time Monitoring System

### Data Pipeline Architecture
```
MySQL Database → Debezium CDC → Kafka Topics → MQTT Bridge → Real-time Applications
                                              → InfluxDB → Grafana Dashboards
```

### Key Components
- **CDC Topic**: `realtime.trucks.location`
- **MQTT Topics**:
  - `trucks/{truck_id}/location` - Individual truck updates
  - `trucks/{truck_id}/status` - Truck operational status
  - `trucks/all/locations` - Aggregated location stream

### Performance Metrics
- **Update Frequency**: Every 5 seconds per truck
- **End-to-End Latency**: ~1-2 seconds from MySQL → MQTT
- **Data Retention**: Historical data stored in InfluxDB
- **Monitoring**: Real-time Grafana dashboards

## 🗂️ Site Structure

```
West Angelas Mining Site/
├── README.md                    # This file
├── configs/                     # Site-specific configurations
├── data/                        # Site coordinate data and routes
├── monitoring/                  # Grafana dashboards and alerts
├── docs/                        # Site documentation
└── scripts/                     # Site-specific operations scripts
```

## 🚀 Getting Started

### Prerequisites
- Kubernetes cluster with Strimzi Kafka operator
- MySQL database with CDC configuration
- MQTT broker (Mosquitto)
- Grafana/InfluxDB for monitoring

### Quick Start
1. Deploy Kafka and MySQL infrastructure
2. Configure Debezium CDC connector
3. Deploy MQTT bridge
4. Start truck location injection
5. Monitor via Grafana dashboards

## 📍 Coordinate System

All coordinates use **WGS84 decimal degrees**:
- **Latitude**: Negative values (Southern Hemisphere)
- **Longitude**: Positive values (Eastern Hemisphere)
- **Format**: -XX.XXXXXXXX, XXX.XXXXXXXX

## 🔧 Operations

### Truck Injection Script
Use `continuous_truck_injection.sh` to simulate real-time truck movements:
```bash
./continuous_truck_injection.sh
```

### Monitoring Commands
```bash
# Check MySQL records
kubectl exec -n debezium-example mysql-pod -- mysql -u root -p -D trucks

# Monitor Kafka topics
kubectl exec kafka-pod -- bin/kafka-console-consumer.sh --topic realtime.trucks.location

# Check MQTT messages
kubectl logs -n mqtt mqtt-listener-pod
```

## 📈 Analytics & Insights

- **Fleet Utilization**: Real-time tracking of active trucks
- **Route Optimization**: Analysis of movement patterns
- **Operational Efficiency**: Monitoring of cycle times and distances
- **Predictive Maintenance**: Based on usage patterns

---

*Last Updated: October 2025*  
*System Status: ✅ Operational*
