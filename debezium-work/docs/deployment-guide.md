# Deployment Guide

This guide provides detailed step-by-step instructions for deploying the Debezium MySQL connector setup on OpenShift.

## 📋 Prerequisites

### Environment Requirements

- OpenShift 4.x cluster with cluster-admin privileges
- Minimum 8GB RAM and 4 CPUs available for the workload
- Persistent storage available (optional, using ephemeral in this setup)

### Operator Installation

1. **Install AMQ Streams/Strimzi Operator**

```bash
# Create subscription for AMQ Streams operator
oc apply -f - <<EOF
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: amq-streams
  namespace: openshift-operators
spec:
  channel: stable
  name: amq-streams
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF
```

2. **Verify Operator Installation**

```bash
oc get pods -n openshift-operators | grep amq-streams
```

### Namespace Setup

```bash
# Create namespace
oc new-project debezium-example

# Verify current context
oc project
```

## 🚀 Step-by-Step Deployment

### Step 1: Deploy Kafka Cluster

```bash
# Apply Kafka cluster configuration
oc apply -f configs/kafka-cluster.yaml

# Monitor deployment
watch oc get kafka debezium-cluster -n debezium-example

# Wait for READY status (this can take 5-10 minutes)
```

**Expected Output:**
```
NAME               READY   METADATA STATE   WARNINGS
debezium-cluster   True    ZooKeeper        True
```

**Verify Kafka Pods:**
```bash
oc get pods -n debezium-example
```

Expected pods:
- `debezium-cluster-kafka-0`
- `debezium-cluster-kafka-1` 
- `debezium-cluster-kafka-2`
- `debezium-cluster-zookeeper-0`
- `debezium-cluster-zookeeper-1`
- `debezium-cluster-zookeeper-2`
- `debezium-cluster-entity-operator-*`

### Step 2: Deploy MySQL Database

```bash
# Deploy MySQL initialization script
oc apply -f configs/mysql-init-script.yaml

# Deploy MySQL database
oc apply -f configs/mysql-deployment.yaml

# Monitor MySQL deployment
watch oc get pods -n debezium-example | grep mysql

# Wait for MySQL pod to be Running (1/1 Ready)
```

**Test MySQL Connection:**
```bash
# Connect to MySQL
oc exec -it deployment/mysql -n debezium-example -- mysql -u root -pdebezium123

# Verify databases
mysql> SHOW DATABASES;
mysql> USE test;
mysql> SHOW TABLES;
mysql> SELECT COUNT(*) FROM customers;
mysql> exit
```

**Verify Debezium User:**
```bash
oc exec -it deployment/mysql -n debezium-example -- \
  mysql -u debezium -pdebezium -e "SHOW DATABASES;"
```

### Step 3: Deploy KafkaConnect Cluster

```bash
# Deploy KafkaConnect with Debezium build
oc apply -f configs/kafkaconnect-cluster.yaml

# Monitor build process
watch oc get pods -n debezium-example | grep build

# Watch build logs
oc logs -f $(oc get pods -n debezium-example | grep build | awk '{print $1}')
```

**Build Process:**
1. Build pod starts: `debezium-connect-cluster-connect-build-*`
2. Downloads Debezium MySQL connector
3. Creates custom image with connector
4. Build completes and pod terminates

**Monitor KafkaConnect:**
```bash
watch oc get kafkaconnect debezium-connect-cluster -n debezium-example
```

**Expected Output:**
```
NAME                      READY   DESIRED REPLICAS   READY REPLICAS   UNAVAILABLE REPLICAS
debezium-connect-cluster  True    1                  1                
```

**Verify Connector Plugin:**
```bash
oc exec debezium-connect-cluster-connect-0 -n debezium-example -- \
  curl -s http://localhost:8083/connector-plugins | grep -i mysql
```

**Expected Output:**
```json
{
  "class": "io.debezium.connector.mysql.MySqlConnector",
  "type": "source",
  "version": "3.2.1.Final"
}
```

### Step 4: Create Test Data

```bash
# Create trucks database and sample data
oc exec -it deployment/mysql -n debezium-example -- \
  mysql -u root -pdebezium123 < scripts/create-trucks-database.sql

# Verify data creation
oc exec -it deployment/mysql -n debezium-example -- \
  mysql -u root -pdebezium123 -e "SELECT COUNT(*) FROM trucks.location;"
```

**Expected Output:**
```
+----------+
| COUNT(*) |
+----------+
|       10 |
+----------+
```

### Step 5: Deploy Debezium Connector

```bash
# Deploy the connector
oc apply -f configs/trucks-debezium-connector.yaml

# Monitor connector status
watch oc get kafkaconnector trucks-debezium-connector -n debezium-example
```

**Expected Output:**
```
NAME                      READY   MAXCONNECTORSREADY   CONNECTORSSTATUS
trucks-debezium-connector True    1                    1
```

**Check Detailed Status:**
```bash
oc describe kafkaconnector trucks-debezium-connector -n debezium-example
```

Look for:
- Connector Status: `RUNNING`
- Tasks Status: `RUNNING`
- No error messages in conditions

### Step 6: Verify Data Capture

**Check Created Topics:**
```bash
oc exec -n debezium-example debezium-cluster-kafka-0 -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --list | grep trucks
```

**Expected Topics:**
```
trucks.trucks.location
trucks-schema-history
__debezium-heartbeat.trucks
```

**Monitor Initial Snapshot:**
```bash
oc exec -n debezium-example debezium-cluster-kafka-0 -- \
  bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic trucks.trucks.location --from-beginning --max-messages 10
```

You should see 10 messages representing the initial truck locations.

### Step 7: Test Real-time Changes

**Start Consumer (in one terminal):**
```bash
oc exec -n debezium-example debezium-cluster-kafka-0 -- \
  bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic trucks.trucks.location
```

**Insert New Data (in another terminal):**
```bash
oc exec -it deployment/mysql -n debezium-example -- \
  mysql -u root -pdebezium123 trucks < scripts/add-10-more-trucks.sql
```

**Expected Result:** You should immediately see 10 new CDC events in the consumer terminal with `"op":"c"` (create operations).

## ✅ Deployment Validation

Run this complete validation script:

```bash
#!/bin/bash
echo "🔍 DEBEZIUM DEPLOYMENT VALIDATION"
echo "================================="

echo "1. Checking Kafka cluster..."
oc get kafka debezium-cluster -n debezium-example --no-headers | grep True && echo "✅ Kafka OK" || echo "❌ Kafka FAILED"

echo "2. Checking MySQL pod..."
oc get pods -n debezium-example | grep mysql | grep Running && echo "✅ MySQL OK" || echo "❌ MySQL FAILED"

echo "3. Checking KafkaConnect..."
oc get kafkaconnect debezium-connect-cluster -n debezium-example --no-headers | grep True && echo "✅ KafkaConnect OK" || echo "❌ KafkaConnect FAILED"

echo "4. Checking Connector..."
oc get kafkaconnector trucks-debezium-connector -n debezium-example --no-headers | grep True && echo "✅ Connector OK" || echo "❌ Connector FAILED"

echo "5. Checking Debezium plugin..."
oc exec debezium-connect-cluster-connect-0 -n debezium-example -- curl -s http://localhost:8083/connector-plugins | grep -q MySqlConnector && echo "✅ Plugin OK" || echo "❌ Plugin FAILED"

echo "6. Checking topics..."
TOPICS=$(oc exec -n debezium-example debezium-cluster-kafka-0 -- bin/kafka-topics.sh --bootstrap-server localhost:9092 --list | grep trucks | wc -l)
[ "$TOPICS" -ge 3 ] && echo "✅ Topics OK ($TOPICS found)" || echo "❌ Topics FAILED ($TOPICS found)"

echo "7. Testing data insertion..."
oc exec -it deployment/mysql -n debezium-example -- mysql -u root -pdebezium123 -e "INSERT INTO trucks.location (id, latitude, longitude) VALUES (9999, 51.5074, -0.1278);" > /dev/null 2>&1 && echo "✅ Data Insert OK" || echo "❌ Data Insert FAILED"

echo ""
echo "🎉 VALIDATION COMPLETE!"
echo "If all checks show ✅, your Debezium setup is working correctly!"
```

## 📊 Resource Requirements

### Minimum Resources

| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| Kafka (3 replicas) | 750m | 3Gi | Ephemeral |
| ZooKeeper (3 replicas) | 375m | 1.5Gi | Ephemeral |
| MySQL | 250m | 512Mi | Ephemeral |
| KafkaConnect | 250m | 1Gi | - |
| **Total** | **1.625 CPU** | **6Gi RAM** | **Ephemeral** |

### Production Recommendations

- Use persistent storage for Kafka and ZooKeeper
- Increase resource limits based on throughput requirements
- Configure monitoring and alerting
- Set up backup strategies for MySQL
- Consider multiple availability zones

## 🔒 Security Considerations

### Network Policies

```yaml
# Example NetworkPolicy for MySQL access
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mysql-access
  namespace: debezium-example
spec:
  podSelector:
    matchLabels:
      app: mysql
  ingress:
  - from:
    - podSelector:
        matchLabels:
          strimzi.io/cluster: debezium-connect-cluster
```

### Secret Management

```bash
# Update MySQL passwords
oc create secret generic mysql-secret \
  --from-literal=mysql-root-password=<new-root-password> \
  --from-literal=mysql-debezium-password=<new-debezium-password> \
  -n debezium-example --dry-run=client -o yaml | oc apply -f -
```

## 🎯 Next Steps

After successful deployment:

1. **Monitor Performance**: Set up monitoring with Prometheus/Grafana
2. **Scale Components**: Adjust replicas and resources based on load
3. **Add More Connectors**: Deploy additional Debezium connectors
4. **Implement Consumers**: Create applications to process CDC events
5. **Setup Alerting**: Configure alerts for failures and performance issues

## 📞 Support

For deployment issues:
1. Check the troubleshooting guide
2. Review logs from all components
3. Verify all prerequisites are met
4. Consult official documentation

🎉 **Congratulations!** You now have a fully functional Debezium MySQL CDC setup!

