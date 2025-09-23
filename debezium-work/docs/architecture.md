# Architecture Overview

This document provides an architectural overview of the Debezium MySQL CDC setup on OpenShift.

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenShift Cluster                        │
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │     MySQL       │    │   Kafka Cluster │                │
│  │   Database      │    │                 │                │
│  │                 │    │ ┌─────────────┐ │                │
│  │ ┌─────────────┐ │    │ │   Broker 0  │ │                │
│  │ │  test DB    │ │    │ └─────────────┘ │                │
│  │ │ customers   │ │    │ ┌─────────────┐ │                │
│  │ └─────────────┘ │    │ │   Broker 1  │ │                │
│  │                 │    │ └─────────────┘ │                │
│  │ ┌─────────────┐ │    │ ┌─────────────┐ │                │
│  │ │ trucks DB   │ │────│▶│   Broker 2  │ │                │
│  │ │ location    │ │    │ └─────────────┘ │                │
│  │ └─────────────┘ │    │                 │                │
│  │                 │    │ ┌─────────────┐ │                │
│  │ Binary Logs     │    │ │ ZooKeeper   │ │                │
│  │ GTID Enabled    │    │ │ Cluster     │ │                │
│  └─────────────────┘    │ └─────────────┘ │                │
│           │              └─────────────────┘                │
│           │                       │                         │
│           │              ┌─────────────────┐                │
│           │              │  Kafka Topics   │                │
│           │              │                 │                │
│           │              │ trucks.trucks.  │                │
│           │              │    location     │                │
│           │              │                 │                │
│           │              │ trucks-schema-  │                │
│           │              │    history      │                │
│           │              │                 │                │
│           │              │ __debezium-     │                │
│           │              │  heartbeat.     │                │
│           │              │   trucks        │                │
│           │              └─────────────────┘                │
│           │                       ▲                         │
│           │                       │                         │
│           │              ┌─────────────────┐                │
│           └──────────────▶│ KafkaConnect    │                │
│                          │   Cluster       │                │
│                          │                 │                │
│                          │ ┌─────────────┐ │                │
│                          │ │  Debezium   │ │                │
│                          │ │   MySQL     │ │                │
│                          │ │ Connector   │ │                │
│                          │ └─────────────┘ │                │
│                          └─────────────────┘                │
│                                   │                         │
│           ┌───────────────────────────────────────┐         │
│           │         Data Flow                     │         │
│           │                                       │         │
│           │  1. MySQL writes to binary log        │         │
│           │  2. Debezium reads binary log         │         │
│           │  3. Converts to CDC events            │         │
│           │  4. Publishes to Kafka topics         │         │
│           │  5. Consumers process events          │         │
│           └───────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Components

### MySQL Database
- **Purpose**: Source database for change data capture
- **Configuration**: 
  - Binary logging enabled (`log-bin`, `binlog-format=ROW`)
  - GTID enabled for consistent replication
  - Dedicated `debezium` user with CDC permissions
- **Databases**:
  - `test`: Customer data for initial testing
  - `trucks`: Location tracking for real-time CDC demo

### Kafka Cluster (Strimzi)
- **Purpose**: Distributed streaming platform for CDC events
- **Configuration**:
  - 3 Kafka brokers for high availability
  - 3 ZooKeeper nodes for coordination
  - Replication factor of 3 for fault tolerance
- **Topics**:
  - Data topics: `{prefix}.{database}.{table}`
  - Schema history: `{connector-name}-schema-history`
  - Heartbeat: `__debezium-heartbeat.{prefix}`

### KafkaConnect Cluster
- **Purpose**: Runs Debezium connectors
- **Configuration**:
  - Custom image built with Debezium MySQL connector
  - JSON converters for message serialization
  - Internal topics for offset/config storage
- **Build Process**:
  - Downloads Debezium connector plugin
  - Creates custom image with connector included
  - Uses OpenShift ImageStream for image management

### Debezium MySQL Connector
- **Purpose**: Captures changes from MySQL binary log
- **Configuration**:
  - Connects to MySQL using `debezium` user
  - Monitors specific databases/tables
  - Handles initial snapshots and ongoing changes
  - Tracks schema evolution

## 📊 Data Flow

### Initial Snapshot Process

1. **Connector Startup**: Debezium connector starts and connects to MySQL
2. **Schema Reading**: Reads table schemas and stores in schema history topic
3. **Consistent Snapshot**: 
   - Locks tables briefly to get consistent point-in-time snapshot
   - Reads all existing data from monitored tables
   - Publishes snapshot events with `op: "r"` (READ)
4. **Binlog Position**: Records current binlog position for future streaming

### Streaming Changes

1. **Binlog Reading**: Connector continuously reads MySQL binary log
2. **Event Processing**: Converts binlog events to Debezium change events
3. **Schema Handling**: Tracks schema changes and updates history
4. **Message Publishing**: Publishes events to appropriate Kafka topics
5. **Offset Management**: Tracks processing progress for fault tolerance

### Message Format

Each CDC event contains:

```json
{
  "schema": { /* Schema definition */ },
  "payload": {
    "op": "c|u|d|r",  // create, update, delete, read
    "ts_ms": 1234567890123,
    "before": { /* Previous state (null for create) */ },
    "after": { /* New state (null for delete) */ },
    "source": {
      "version": "3.2.1.Final",
      "connector": "mysql",
      "name": "trucks",
      "ts_ms": 1234567890123,
      "snapshot": "false",
      "db": "trucks",
      "table": "location",
      "server_id": 1,
      "gtid": "...",
      "file": "binlog.000005",
      "pos": 1234,
      "row": 0
    }
  }
}
```

## 🔄 High Availability

### Kafka Cluster HA
- **3 Broker Setup**: Tolerates 1 broker failure
- **Replication Factor 3**: Each topic partition has 3 replicas
- **Min In-Sync Replicas**: Ensures at least 2 replicas are synchronized

### MySQL HA Considerations
- **Current Setup**: Single instance (suitable for development)
- **Production**: Consider MySQL replication or MySQL Group Replication
- **Backup Strategy**: Regular backups with point-in-time recovery

### KafkaConnect HA
- **Current Setup**: Single replica (suitable for development)  
- **Production**: Multiple replicas with distributed task execution
- **Fault Tolerance**: Automatic task redistribution on failure

## 🔒 Security Model

### Authentication
- **MySQL**: Username/password authentication for `debezium` user
- **Kafka**: Internal cluster communication (can add TLS/SASL)
- **OpenShift**: RBAC controls for resource access

### Network Security
- **Internal Traffic**: All communication within OpenShift cluster network
- **Service Mesh**: Can integrate with Istio for advanced traffic management
- **Network Policies**: Control pod-to-pod communication

### Data Security
- **In-Transit**: Can enable TLS for Kafka communication
- **At-Rest**: Encryption depends on underlying storage
- **Secrets**: Sensitive data stored in OpenShift secrets

## 📈 Scalability

### Horizontal Scaling
- **Kafka**: Add more brokers to increase throughput
- **KafkaConnect**: Scale connector replicas for load distribution
- **Consumers**: Multiple consumer instances for parallel processing

### Vertical Scaling
- **Resource Limits**: Increase CPU/memory as needed
- **MySQL**: Scale up database server resources
- **Partition Strategy**: Increase topic partitions for parallelism

## 🔍 Monitoring Points

### Key Metrics
- **MySQL**: Binary log position, GTID execution
- **Connector**: Lag metrics, error rates, throughput
- **Kafka**: Topic partition offsets, consumer lag
- **System**: CPU, memory, disk usage

### Health Checks
- **Connectivity**: Database connection status
- **Schema Evolution**: Schema history topic consistency  
- **Data Consistency**: Compare source and target record counts
- **Performance**: End-to-end latency measurements

## 🎯 Use Cases

### Real-time Analytics
- Stream database changes to analytics platforms
- Build real-time dashboards and reports
- Trigger alerts based on data changes

### Microservices Integration
- Propagate data changes between services
- Maintain eventually consistent data replicas
- Implement event-driven architectures

### Data Pipeline
- ETL processes with real-time updates
- Data lake ingestion with change streams
- Audit and compliance logging

This architecture provides a robust foundation for change data capture with MySQL and Kafka, suitable for both development and production environments with appropriate scaling and security enhancements.

