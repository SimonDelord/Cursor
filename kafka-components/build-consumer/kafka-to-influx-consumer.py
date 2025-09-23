#!/usr/bin/env python3
"""
Kafka to InfluxDB Consumer for Truck Location Data
Consumes truck location changes from Debezium and stores them in InfluxDB for Grafana visualization
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional

from kafka import KafkaConsumer
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Configuration
KAFKA_BOOTSTRAP_SERVERS = ['debezium-cluster-kafka-bootstrap:9092']
KAFKA_TOPIC = 'trucks.trucks.location'
KAFKA_GROUP_ID = 'truck-location-consumer'

INFLUXDB_URL = 'http://influxdb:8086'
INFLUXDB_TOKEN = 'trucks-admin-token-12345'
INFLUXDB_ORG = 'trucks'
INFLUXDB_BUCKET = 'locations'

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TruckLocationConsumer:
    def __init__(self):
        """Initialize Kafka consumer and InfluxDB client"""
        self.consumer = None
        self.influx_client = None
        self.write_api = None
        self._setup_kafka()
        self._setup_influxdb()

    def _setup_kafka(self):
        """Setup Kafka consumer"""
        try:
            self.consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id=KAFKA_GROUP_ID,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                auto_commit_interval_ms=1000
            )
            logger.info(f"Connected to Kafka topic: {KAFKA_TOPIC}")
        except Exception as e:
            logger.error(f"Failed to setup Kafka consumer: {e}")
            raise

    def _setup_influxdb(self):
        """Setup InfluxDB client"""
        try:
            self.influx_client = InfluxDBClient(
                url=INFLUXDB_URL,
                token=INFLUXDB_TOKEN,
                org=INFLUXDB_ORG
            )
            self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
            logger.info(f"Connected to InfluxDB: {INFLUXDB_URL}")
        except Exception as e:
            logger.error(f"Failed to setup InfluxDB client: {e}")
            raise

    def _extract_truck_data(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract truck location data from Debezium CDC message"""
        try:
            payload = message.get('payload', {})
            operation = payload.get('op', '')
            
            # We're interested in create (c) and update (u) operations
            if operation not in ['c', 'u', 'r']:  # create, update, read (snapshot)
                return None
            
            after_data = payload.get('after', {})
            if not after_data:
                return None
            
            # Extract truck location data
            truck_data = {
                'truck_id': after_data.get('id'),
                'latitude': after_data.get('latitude'),
                'longitude': after_data.get('longitude'),
                'operation': operation,
                'timestamp': payload.get('ts_ms', int(time.time() * 1000))
            }
            
            # Validate required fields
            if not all([truck_data['truck_id'], truck_data['latitude'], truck_data['longitude']]):
                logger.warning(f"Missing required fields in message: {truck_data}")
                return None
                
            return truck_data
            
        except Exception as e:
            logger.error(f"Error extracting truck data: {e}")
            return None

    def _write_to_influxdb(self, truck_data: Dict[str, Any]):
        """Write truck location data to InfluxDB"""
        try:
            # Convert timestamp from milliseconds to datetime
            timestamp = datetime.fromtimestamp(truck_data['timestamp'] / 1000)
            
            # Create InfluxDB Point
            point = Point("truck_location") \
                .tag("truck_id", str(truck_data['truck_id'])) \
                .tag("operation", truck_data['operation']) \
                .field("latitude", float(truck_data['latitude'])) \
                .field("longitude", float(truck_data['longitude'])) \
                .time(timestamp)
            
            # Write to InfluxDB
            self.write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
            
            logger.info(f"Written truck {truck_data['truck_id']} location: "
                       f"({truck_data['latitude']}, {truck_data['longitude']}) "
                       f"operation: {truck_data['operation']}")
            
        except Exception as e:
            logger.error(f"Error writing to InfluxDB: {e}")

    def consume_messages(self):
        """Main consumer loop"""
        logger.info("Starting to consume truck location messages...")
        
        try:
            for message in self.consumer:
                try:
                    # Extract truck data from Debezium message
                    truck_data = self._extract_truck_data(message.value)
                    
                    if truck_data:
                        # Write to InfluxDB
                        self._write_to_influxdb(truck_data)
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    continue
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"Consumer error: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup resources"""
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")
        
        if self.influx_client:
            self.influx_client.close()
            logger.info("InfluxDB client closed")


if __name__ == "__main__":
    consumer = TruckLocationConsumer()
    consumer.consume_messages()
