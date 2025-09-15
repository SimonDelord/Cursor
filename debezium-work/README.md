# Debezium MySQL Connector on OpenShift

This repository contains a complete, working setup for Debezium MySQL Change Data Capture (CDC) on OpenShift using Strimzi/AMQ Streams.

## 🎯 Overview

This setup demonstrates real-time data streaming from MySQL to Kafka using Debezium. It captures changes from MySQL database tables and publishes them to Kafka topics for downstream processing.

## 📋 Components

### Infrastructure
- **Kafka Cluster**: 3-node Kafka cluster with ZooKeeper
- **MySQL Database**: Configured with binary logging and GTID for CDC
- **KafkaConnect Cluster**: Custom-built with Debezium MySQL connector
- **Debezium Connector**: Change data capture connector for MySQL

### Test Data
- **Trucks Database**: Location tracking system with real-time updates
- **Test Database**: Customer data for initial testing

## 🚀 Quick Start

### Prerequisites
- OpenShift cluster with admin access
- Strimzi/AMQ Streams Operator installed
- Namespace `debezium-example` created

### 1. Deploy Kafka Cluster

```bash
oc apply -f configs/kafka-cluster.yaml
```

Wait for the cluster to be ready:
```bash
oc get kafka debezium-cluster -n debezium-example
```

### 2. Deploy MySQL Database

```bash
# Deploy MySQL with Debezium configuration
oc apply -f configs/mysql-init-script.yaml
oc apply -f configs/mysql-deployment.yaml
```

Wait for MySQL to be ready:
```bash
oc get pods -n debezium-example | grep mysql
```

### 3. Deploy KafkaConnect Cluster

```bash
oc apply -f configs/kafkaconnect-cluster.yaml
```

Monitor the build process:
```bash
oc get pods -n debezium-example | grep build
```

Wait for the connect cluster to be ready:
```bash
oc get kafkaconnect debezium-connect-cluster -n debezium-example
```

### 4. Create Test Data

```bash
# Connect to MySQL and create test databases
oc exec -it deployment/mysql -n debezium-example -- mysql -u root -pdebezium123

# Run the scripts
mysql> source /docker-entrypoint-initdb.d/02-create-sample-data.sql;
```

Or execute the scripts manually:
```bash
oc exec -it deployment/mysql -n debezium-example -- mysql -u root -pdebezium123 < scripts/create-trucks-database.sql
```

### 5. Deploy Debezium Connector

```bash
oc apply -f configs/trucks-debezium-connector.yaml
```

Check connector status:
```bash
oc get kafkaconnector trucks-debezium-connector -n debezium-example
```

### 6. Monitor Real-time Changes

```bash
# Monitor truck location changes
oc exec -n debezium-example debezium-cluster-kafka-0 -- \
  bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic trucks.trucks.location
```

### 7. Test Real-time Data Capture

In another terminal, add more truck locations:
```bash
oc exec -it deployment/mysql -n debezium-example -- mysql -u root -pdebezium123 trucks < scripts/add-10-more-trucks.sql
```

You should see the changes appear immediately in the Kafka consumer!

## 📁 File Structure

```
debezium-work/
├── configs/                    # Kubernetes configurations
│   ├── kafka-cluster.yaml      # Kafka cluster with ZooKeeper
│   ├── mysql-deployment.yaml   # MySQL with CDC configuration
│   ├── mysql-init-script.yaml  # MySQL user setup and sample data
│   ├── kafkaconnect-cluster.yaml # KafkaConnect with Debezium plugin
│   └── trucks-debezium-connector.yaml # Working CDC connector
├── scripts/                    # Database scripts
│   ├── create-trucks-database.sql # Truck location table setup
│   └── add-10-more-trucks.sql  # Additional test data
├── docs/                       # Additional documentation
└── README.md                   # This file
```

## 🔧 Configuration Details

### MySQL Configuration

The MySQL deployment includes Debezium-optimized settings:

```yaml
# Binary logging for CDC
server-id = 1
log-bin = mysql-bin
binlog-format = ROW
binlog-row-image = FULL

# GTID for consistent replication
gtid-mode = ON
enforce-gtid-consistency = ON
```

### KafkaConnect Build

The KafkaConnect cluster is built with the Debezium MySQL connector:

```yaml
build:
  output:
    type: imagestream
    image: debezium-connect:latest
  plugins:
    - name: debezium-mysql-connector
      artifacts:
        - type: zip
          url: https://repo1.maven.org/maven2/io/debezium/debezium-connector-mysql/3.2.1.Final/debezium-connector-mysql-3.2.1.Final-plugin.zip
```

### Connector Configuration

Key connector settings:

```yaml
config:
  database.hostname: mysql
  database.include.list: trucks
  table.include.list: trucks.location
  topic.prefix: trucks
  snapshot.mode: initial
  schema.history.internal.kafka.topic: trucks-schema-history
```

## 🔍 Monitoring and Troubleshooting

### Check Connector Status
```bash
oc describe kafkaconnector trucks-debezium-connector -n debezium-example
```

### View Connector Logs
```bash
oc logs deployment/debezium-connect-cluster-connect -n debezium-example
```

### List Kafka Topics
```bash
oc exec -n debezium-example debezium-cluster-kafka-0 -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```

### Monitor Schema History
```bash
oc exec -n debezium-example debezium-cluster-kafka-0 -- \
  bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic trucks-schema-history
```

## ✅ Success Indicators

When everything is working correctly, you should see:

1. **Kafka Cluster**: `READY: True`
2. **MySQL Pod**: `Running` with 1/1 ready
3. **KafkaConnect**: `READY: True` with custom image built
4. **Connector**: `READY: True` with tasks in `RUNNING` state
5. **Topics Created**:
   - `trucks.trucks.location` (data changes)
   - `trucks-schema-history` (schema tracking)
   - `__debezium-heartbeat.trucks` (heartbeat monitoring)

## 🎉 Real-time Data Flow

When you insert new truck locations:

```sql
INSERT INTO location (id, latitude, longitude) VALUES 
(21, 40.7128, -74.0060);  -- New York City
```

You'll immediately see a CDC event:

```json
{
  "op": "c",
  "ts_ms": 1694735123456,
  "before": null,
  "after": {
    "id": 21,
    "latitude": 40.7128,
    "longitude": -74.0060,
    "created_at": "2024-09-15T10:30:00Z",
    "updated_at": "2024-09-15T10:30:00Z"
  }
}
```

## 📚 Additional Resources

- [Debezium Documentation](https://debezium.io/documentation/)
- [Strimzi Documentation](https://strimzi.io/docs/)
- [AMQ Streams Documentation](https://access.redhat.com/documentation/en-us/red_hat_amq_streams)

## 🤝 Contributing

This configuration was developed and tested successfully. Feel free to adapt it for your specific use cases!

## 📄 License

MIT License - Feel free to use and modify as needed.
