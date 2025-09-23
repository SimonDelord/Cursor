#!/usr/bin/env python3
"""
Kafka to MQTT Bridge for Truck Location Data
Consumes from demo.trucks.location Kafka topic and publishes to MQTT
"""

import json
import logging
import time
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from kafka import KafkaConsumer
import paho.mqtt.client as mqtt

# Configuration from environment variables
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'debezium-cluster-kafka-bootstrap:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'demo.trucks.location')
KAFKA_GROUP_ID = os.getenv('KAFKA_GROUP_ID', 'truck-mqtt-bridge')

MQTT_BROKER = os.getenv('MQTT_BROKER', 'mosquitto.mqtt.svc')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_TOPIC_PREFIX = os.getenv('MQTT_TOPIC_PREFIX', 'trucks')

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KafkaToMQTTBridge:
    def __init__(self):
        """Initialize Kafka consumer and MQTT client"""
        self.kafka_consumer = None
        self.mqtt_client = None
        self.connected = False
        self._setup_kafka()
        self._setup_mqtt()

    def _setup_kafka(self):
        """Setup Kafka consumer"""
        try:
            self.kafka_consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(','),
                group_id=KAFKA_GROUP_ID,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')) if x is not None else None,
                auto_offset_reset='latest',  # Only consume new messages
                enable_auto_commit=True,
                auto_commit_interval_ms=1000
            )
            logger.info(f"Connected to Kafka topic: {KAFKA_TOPIC}")
        except Exception as e:
            logger.error(f"Failed to setup Kafka consumer: {e}")
            raise

    def _setup_mqtt(self):
        """Setup MQTT client"""
        try:
            # Generate unique client ID to avoid conflicts
            client_id = f"kafka-mqtt-bridge-{str(uuid.uuid4())[:8]}"
            
            self.mqtt_client = mqtt.Client(client_id=client_id)
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
            self.mqtt_client.on_publish = self._on_mqtt_publish
            
            # Set reconnect delay and max attempts
            self.mqtt_client.reconnect_delay_set(min_delay=1, max_delay=120)
            
            logger.info(f"Connecting to MQTT broker: {MQTT_BROKER}:{MQTT_PORT} with client ID: {client_id}")
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            
            # Wait for connection
            time.sleep(3)
            
        except Exception as e:
            logger.error(f"Failed to setup MQTT client: {e}")
            raise

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.connected = True
            logger.info(f"Connected to MQTT broker with result code {rc}")
        else:
            logger.error(f"Failed to connect to MQTT broker with result code {rc}")

    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker with result code {rc}")
            logger.info("MQTT client will attempt to reconnect automatically")
        else:
            logger.info("MQTT client disconnected gracefully")

    def _on_mqtt_publish(self, client, userdata, mid):
        """MQTT publish callback"""
        logger.debug(f"Message published with mid: {mid}")

    def _extract_truck_data(self, kafka_message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract truck location data from Kafka CDC message"""
        try:
            # Handle tombstone records (None values)
            if kafka_message is None:
                logger.debug("Skipping tombstone record (None message)")
                return None
                
            payload = kafka_message.get('payload', {})
            operation = payload.get('op', '')
            
            # Process create (c), update (u), and read (r) operations
            if operation not in ['c', 'u', 'r']:
                return None
            
            after_data = payload.get('after', {})
            if not after_data:
                return None
            
            # Extract truck location data
            truck_data = {
                'truck_id': after_data.get('id'),
                'latitude': float(after_data.get('latitude', '0')),
                'longitude': float(after_data.get('longitude', '0')),
                'created_at': after_data.get('created_at'),
                'updated_at': after_data.get('updated_at'),
                'operation': operation,
                'source': payload.get('source', {}).get('db', 'unknown'),
                'timestamp': datetime.now().isoformat()
            }
            
            # Validate required fields
            if not all([truck_data['truck_id'], truck_data['latitude'], truck_data['longitude']]):
                logger.warning(f"Missing required fields in message: {truck_data}")
                return None
                
            return truck_data
            
        except Exception as e:
            logger.error(f"Error extracting truck data: {e}")
            return None

    def _publish_to_mqtt(self, truck_data: Dict[str, Any]):
        """Publish truck location data to MQTT topics"""
        try:
            # Check if MQTT client is connected before publishing
            if not self.connected:
                logger.warning(f"MQTT not connected, skipping truck {truck_data.get('truck_id', 'unknown')}")
                return
            
            truck_id = truck_data['truck_id']
            
            # Create different MQTT topics for different data aspects
            topics = {
                f"{MQTT_TOPIC_PREFIX}/{truck_id}/location": {
                    'truck_id': truck_id,
                    'latitude': truck_data['latitude'],
                    'longitude': truck_data['longitude'],
                    'timestamp': truck_data['timestamp']
                },
                f"{MQTT_TOPIC_PREFIX}/{truck_id}/status": {
                    'truck_id': truck_id,
                    'operation': truck_data['operation'],
                    'created_at': truck_data['created_at'],
                    'updated_at': truck_data['updated_at']
                },
                f"{MQTT_TOPIC_PREFIX}/all/locations": truck_data
            }
            
            # Publish to each topic
            published_count = 0
            for topic, data in topics.items():
                payload = json.dumps(data)
                result = self.mqtt_client.publish(topic, payload, qos=1)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(f"Published truck {truck_id} data to {topic}")
                    published_count += 1
                else:
                    logger.error(f"Failed to publish to {topic}: error code {result.rc}")
            
            if published_count > 0:
                logger.info(f"Successfully published truck {truck_id} to {published_count} MQTT topics")
            
        except Exception as e:
            logger.error(f"Error publishing to MQTT: {e}")

    def run_bridge(self):
        """Main bridge loop"""
        logger.info("Starting Kafka → MQTT bridge...")
        
        # Wait for MQTT connection
        retry_count = 0
        while not self.connected and retry_count < 30:
            time.sleep(1)
            retry_count += 1
        
        if not self.connected:
            logger.error("Failed to connect to MQTT broker after 30 seconds")
            return
        
        logger.info("Bridge is running - consuming Kafka messages and publishing to MQTT...")
        
        try:
            for kafka_message in self.kafka_consumer:
                try:
                    # Extract truck data from Kafka CDC message
                    truck_data = self._extract_truck_data(kafka_message.value)
                    
                    if truck_data:
                        # Publish to MQTT
                        self._publish_to_mqtt(truck_data)
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    continue
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"Bridge error: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup resources"""
        if self.kafka_consumer:
            self.kafka_consumer.close()
            logger.info("Kafka consumer closed")
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("MQTT client disconnected")


if __name__ == "__main__":
    bridge = KafkaToMQTTBridge()
    bridge.run_bridge()

