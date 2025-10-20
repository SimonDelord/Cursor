# West Angelas Mining Site - Deployment Instructions

## 🚀 Quick Start Guide

### Prerequisites
- Kubernetes cluster with kubectl configured
- Strimzi Kafka operator installed
- MySQL database with CDC configuration
- MQTT broker (Mosquitto)

### 1. Deploy Site Configuration
```bash
kubectl apply -f configs/site-specific-config.yaml
```

### 2. Start Truck Tracking
```bash
# Use the site-specific injection script
./scripts/west-angelas-truck-injection.sh

# Or use the main project script
cd ../../../
./continuous_truck_injection.sh
```

### 3. Monitor Operations
```bash
# Check recent truck locations
kubectl exec -n debezium-example mysql-pod -- mysql -u root -p -D trucks \
  -e "SELECT truck_number, latitude, longitude, created_at FROM location ORDER BY created_at DESC LIMIT 10;"

# Monitor Kafka CDC topic
kubectl exec -n debezium-example kafka-pod -- bin/kafka-console-consumer.sh \
  --topic realtime.trucks.location --from-beginning

# Check MQTT bridge logs
kubectl logs -n mqtt kafka-mqtt-bridge-pod --tail=20
```

## 📊 Site-Specific Features

### Enhanced Logging
- Site-specific log file: `/tmp/west-angelas-truck-injection.log`
- Includes coordinate validation and route reversals
- UTC timestamps with site identification

### Route Descriptions
- Each waypoint includes descriptive labels (e.g., "Main depot", "Loading zone A")
- Two distinct circuits: Primary (17 points) and Secondary (10 points)
- Bidirectional routing with auto-reverse at boundaries

### Monitoring Integration
- ConfigMap with site-specific settings
- Real-time monitoring via MQTT topics
- Alert configuration for offline trucks and coordinate deviations

## 🗺️ Route Information

### Truck #1 - Primary Mining Circuit (17 waypoints)
- **Main depot** → **North access road** → **Mining area entrance** → **Pit access point**
- **Loading zones** → **Haul road junction** → **Processing area** → **Rail loading facility**
- **Return circuit** → **Maintenance checkpoint** → **Back to depot**

### Truck #2 - Secondary Mining Circuit (10 waypoints)  
- **Shared depot** → **South access road** → **Secondary pit entrance** → **Overburden area**
- **Waste dump access** → **Equipment staging** → **Fuel station** → **West boundary**

## 🔧 Configuration Files

### Site Configuration (`configs/site-specific-config.yaml`)
- Kubernetes ConfigMap with site settings
- Fleet configuration (2 active trucks)
- Monitoring and alerting parameters
- CDC and MQTT connection settings

### Route Data (`data/truck-routes.json`)
- Complete coordinate data with descriptions
- Operational metadata
- Route type and precision information

## 🚛 Fleet Management Commands

### View Active Trucks
```bash
kubectl exec -n debezium-example mysql-pod -- mysql -u root -p -D trucks \
  -e "SELECT truck_number, COUNT(*) as total_records FROM location GROUP BY truck_number ORDER BY truck_number;"
```

### Check Latest Positions
```bash
kubectl exec -n debezium-example mysql-pod -- mysql -u root -p -D trucks \
  -e "SELECT truck_number, latitude, longitude, created_at FROM location WHERE created_at >= (NOW() - INTERVAL 1 MINUTE) ORDER BY created_at DESC;"
```

### Monitor Route Progress
```bash
# Follow the injection script output
tail -f /tmp/west-angelas-truck-injection.log
```

## 📈 Performance Metrics

- **Update Frequency**: 5 seconds per truck
- **Coordinate Precision**: 8 decimal places (~1mm accuracy)
- **End-to-End Latency**: ~1-2 seconds (MySQL → MQTT)
- **Route Coverage**: 27 unique waypoints across site

## 🛠️ Troubleshooting

### Common Issues
1. **MySQL Pod Not Found**: Check namespace and pod labels
2. **Permission Denied**: Ensure script is executable (`chmod +x`)
3. **Database Connection**: Verify credentials and network connectivity
4. **MQTT Messages Missing**: Check bridge logs and broker status

### Debugging Commands
```bash
# Check pod status
kubectl get pods -n debezium-example
kubectl get pods -n mqtt

# View recent logs
kubectl logs -n debezium-example mysql-pod --tail=50
kubectl logs -n mqtt kafka-mqtt-bridge-pod --tail=50

# Test database connectivity
kubectl exec -n debezium-example mysql-pod -- mysql -u root -p -e "SHOW DATABASES;"
```

---

*West Angelas Mining Site - Real-Time Truck Tracking System*  
*Deployment Guide v1.0 - October 2025*
