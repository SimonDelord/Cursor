# Troubleshooting Guide

This guide covers common issues encountered during the Debezium setup and their solutions.

## 🚨 Common Issues and Solutions

### 1. GTID NullPointerException

**Error**: `Cannot invoke "com.github.shyiko.mysql.binlog.GtidSet.getUUIDSets()" because "this.gtidSet" is null`

**Solution**: 
- Ensure MySQL GTID is properly enabled
- Check connector configuration has proper GTID settings
- Reset the connector if necessary

```bash
# Check MySQL GTID status
oc exec -it deployment/mysql -n debezium-example -- mysql -u root -pdebezium123 -e "SHOW VARIABLES LIKE 'gtid_mode';"

# Reset connector
oc delete kafkaconnector trucks-debezium-connector -n debezium-example
oc apply -f configs/trucks-debezium-connector.yaml
```

### 2. Schema History Topic Missing

**Error**: `The db history topic is missing`

**Solution**:
- Ensure Kafka cluster is running
- Create the schema history topic manually if needed
- Use `initial` snapshot mode

```bash
# Create schema history topic manually
oc exec -n debezium-example debezium-cluster-kafka-0 -- \
  bin/kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic trucks-schema-history \
  --partitions 1 \
  --replication-factor 1
```

### 3. Connector Plugin Not Found

**Error**: `Failed to find any class that implements Connector and which name matches io.debezium.connector.mysql.MySqlConnector`

**Solution**:
- Check if the KafkaConnect build completed successfully
- Verify Debezium plugin is included in the build
- Check build logs for any failures

```bash
# Check build status
oc get pods -n debezium-example | grep build

# Check build logs
oc logs -f <build-pod-name> -n debezium-example

# Check available connectors
oc exec debezium-connect-cluster-connect-0 -n debezium-example -- \
  curl -s http://localhost:8083/connector-plugins | grep -i mysql
```

### 4. MySQL Connection Issues

**Error**: Connection refused or authentication failed

**Solution**:
- Verify MySQL service is running
- Check credentials and network connectivity
- Ensure debezium user has proper permissions

```bash
# Check MySQL pod status
oc get pods -n debezium-example | grep mysql

# Test MySQL connection
oc exec -it deployment/mysql -n debezium-example -- \
  mysql -u debezium -pdebezium -e "SHOW DATABASES;"

# Check user permissions
oc exec -it deployment/mysql -n debezium-example -- \
  mysql -u root -pdebezium123 -e "SHOW GRANTS FOR 'debezium'@'%';"
```

### 5. KafkaConnect Build Failures

**Error**: Build pod in `Error` or `Failed` state

**Solution**:
- Check build pod logs for specific errors
- Verify network connectivity for downloading plugins
- Check OpenShift registry permissions

```bash
# Check build logs
oc get pods -n debezium-example | grep build
oc logs <build-pod-name> -n debezium-example

# Check registry permissions
oc describe kafkaconnect debezium-connect-cluster -n debezium-example
```

## 🔍 Diagnostic Commands

### Check Overall Cluster Health

```bash
# Check all resources
oc get kafka,kafkaconnect,kafkaconnector -n debezium-example

# Check pod status
oc get pods -n debezium-example

# Check services
oc get svc -n debezium-example
```

### Verify Kafka Topics

```bash
# List all topics
oc exec -n debezium-example debezium-cluster-kafka-0 -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --list

# Check topic details
oc exec -n debezium-example debezium-cluster-kafka-0 -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 \
  --describe --topic trucks.trucks.location
```

### Monitor Connector Status

```bash
# Get connector status
oc get kafkaconnector trucks-debezium-connector -n debezium-example -o yaml

# Check connector details
oc describe kafkaconnector trucks-debezium-connector -n debezium-example
```

### Check Logs

```bash
# KafkaConnect logs
oc logs deployment/debezium-connect-cluster-connect -n debezium-example -f

# MySQL logs
oc logs deployment/mysql -n debezium-example -f

# Kafka broker logs
oc logs debezium-cluster-kafka-0 -n debezium-example -f
```

## 🔄 Reset Procedures

### Complete Connector Reset

```bash
# 1. Delete connector
oc delete kafkaconnector trucks-debezium-connector -n debezium-example

# 2. Delete related topics (optional - will lose data!)
oc exec -n debezium-example debezium-cluster-kafka-0 -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --delete \
  --topic trucks.trucks.location

oc exec -n debezium-example debezium-cluster-kafka-0 -- \
  bin/kafka-topics.sh --bootstrap-server localhost:9092 --delete \
  --topic trucks-schema-history

# 3. Restart KafkaConnect
oc rollout restart deployment/debezium-connect-cluster-connect -n debezium-example

# 4. Wait for restart
oc rollout status deployment/debezium-connect-cluster-connect -n debezium-example

# 5. Recreate connector
oc apply -f configs/trucks-debezium-connector.yaml
```

### MySQL Database Reset

```bash
# Connect to MySQL and reset data
oc exec -it deployment/mysql -n debezium-example -- mysql -u root -pdebezium123

# Drop and recreate database
mysql> DROP DATABASE IF EXISTS trucks;
mysql> CREATE DATABASE trucks;
mysql> exit

# Rerun setup script
oc exec -it deployment/mysql -n debezium-example -- \
  mysql -u root -pdebezium123 trucks < /path/to/create-trucks-database.sql
```

## 📊 Performance Monitoring

### Check Resource Usage

```bash
# Pod resource usage
oc top pods -n debezium-example

# Node resource usage
oc top nodes
```

### Monitor Topic Lag

```bash
# Check consumer group lag (if applicable)
oc exec -n debezium-example debezium-cluster-kafka-0 -- \
  bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --list

oc exec -n debezium-example debezium-cluster-kafka-0 -- \
  bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --describe --group <group-name>
```

## 📞 Getting Help

If you encounter issues not covered here:

1. Check the Debezium logs for specific error messages
2. Verify all prerequisites are met
3. Consult the [Debezium documentation](https://debezium.io/documentation/)
4. Check the [Strimzi documentation](https://strimzi.io/docs/)
5. Search existing GitHub issues in the Debezium project

## 🎯 Success Validation

After troubleshooting, verify everything works:

```bash
# 1. Check connector status
oc get kafkaconnector trucks-debezium-connector -n debezium-example

# 2. Insert test data
oc exec -it deployment/mysql -n debezium-example -- \
  mysql -u root -pdebezium123 -e "INSERT INTO trucks.location (id, latitude, longitude) VALUES (999, 37.7749, -122.4194);"

# 3. Verify data appears in Kafka
oc exec -n debezium-example debezium-cluster-kafka-0 -- \
  bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic trucks.trucks.location --max-messages 1
```

If you see the new record in Kafka, your setup is working correctly! 🎉
