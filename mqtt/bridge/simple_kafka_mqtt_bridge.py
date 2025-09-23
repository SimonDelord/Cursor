#!/usr/bin/env python3
"""
Simple Kafka-MQTT Bridge - Working Version
==========================================

A straightforward, reliable bridge that consumes truck location data from Kafka 
and publishes to MQTT topics. Focus on simplicity and reliability.
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime

from kafka import KafkaConsumer
import paho.mqtt.client as mqtt

# Configuration from environment variables
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "realtime.trucks.location")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "truck-mqtt-bridge-simple")
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "trucks")
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()

# Setup logging
logging.basicConfig(level=LOG_LEVEL,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleKafkaMQTTBridge:
    def __init__(self):
        self.mqtt_client = None
        self.kafka_consumer = None
        self.connected_to_mqtt = False
        self.client_id = f"simple-kafka-mqtt-bridge-{str(uuid.uuid4())[:8]}"

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected_to_mqtt = True
            logger.info(f"✅ Connected to MQTT broker with client ID: {self.client_id}")
        else:
            logger.error(f"❌ Failed to connect to MQTT broker, return code {rc}")
            self.connected_to_mqtt = False

    def _on_mqtt_disconnect(self, client, userdata, rc):
        self.connected_to_mqtt = False
        logger.warning(f"⚠️ Disconnected from MQTT broker with result code {rc}")

    def _setup_mqtt(self):
        logger.info(f"🔗 Connecting to MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
        self.mqtt_client = mqtt.Client(client_id=self.client_id)
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.mqtt_client.loop_start()
        
        # Wait for connection to be established
        timeout = 30
        while not self.connected_to_mqtt and timeout > 0:
            logger.info("⏳ Waiting for MQTT connection...")
            time.sleep(1)
            timeout -= 1
        
        if not self.connected_to_mqtt:
            raise Exception("Failed to connect to MQTT broker within timeout")
            
        logger.info("✅ MQTT client setup complete")

    def _setup_kafka(self):
        logger.info(f"🔗 Setting up Kafka consumer for topic: {KAFKA_TOPIC}")
        self.kafka_consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=KAFKA_GROUP_ID,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')) if x is not None else None,
            auto_offset_reset='earliest',  # Start from the beginning of the topic
            enable_auto_commit=True,
            auto_commit_interval_ms=5000  # Commit offsets every 5 seconds
        )
        logger.info("✅ Kafka consumer created successfully")

    def _process_message(self, message):
        logger.info(f"🔍 ===== PROCESSING NEW MESSAGE =====")
        logger.info(f"🔍 Message key: {message.key}")
        logger.info(f"🔍 Message partition: {message.partition}")
        logger.info(f"🔍 Message offset: {message.offset}")
        logger.info(f"🔍 RAW MESSAGE CONTENT:")
        logger.info(f"🔍 {message.value}")
        logger.info(f"🔍 Message type: {type(message.value)}")
        
        if message.value is None:
            logger.info(f"❌ Received tombstone message for key {message.key}, skipping.")
            return

        try:
            # Check if message.value is a dict
            if not isinstance(message.value, dict):
                logger.error(f"❌ Expected dict, got {type(message.value)}: {message.value}")
                return
            
            logger.info(f"🔍 Message value keys: {list(message.value.keys())}")
            
            # The message IS the payload - no nested 'payload' key needed
            payload = message.value
            logger.info(f"🔍 Payload type: {type(payload)}")
            logger.info(f"🔍 Payload content: {payload}")
            
            if payload:
                logger.info(f"🔍 Payload keys: {list(payload.keys())}")
            
            op = payload.get('op')
            logger.info(f"📊 Operation extracted: '{op}' (type: {type(op)})")

            if op == 'c' or op == 'u':  # Create or Update operation
                logger.info(f"✅ Processing {op} operation")
                
                after = payload.get('after', {})
                logger.info(f"🔍 'after' section type: {type(after)}")
                logger.info(f"🔍 'after' section content: {after}")
                
                if after:
                    logger.info(f"🔍 'after' keys: {list(after.keys())}")
                
                # Extract individual fields with detailed logging
                truck_id = after.get('id')
                latitude = after.get('latitude') 
                longitude = after.get('longitude')
                created_at = after.get('created_at')
                updated_at = after.get('updated_at')

                logger.info(f"🚛 EXTRACTED VARIABLES:")
                logger.info(f"🚛 truck_id = '{truck_id}' (type: {type(truck_id)})")
                logger.info(f"🚛 latitude = '{latitude}' (type: {type(latitude)})")
                logger.info(f"🚛 longitude = '{longitude}' (type: {type(longitude)})")
                logger.info(f"🚛 created_at = '{created_at}' (type: {type(created_at)})")
                logger.info(f"🚛 updated_at = '{updated_at}' (type: {type(updated_at)})")

                # Check each field individually
                missing_fields = []
                if truck_id is None: missing_fields.append('id')
                if latitude is None: missing_fields.append('latitude')  
                if longitude is None: missing_fields.append('longitude')
                if created_at is None: missing_fields.append('created_at')
                if updated_at is None: missing_fields.append('updated_at')
                
                if missing_fields:
                    logger.warning(f"❌ Missing fields: {missing_fields}")
                    logger.warning(f"❌ Will skip this message")
                    return

                logger.info(f"✅ All required fields present!")
                
                truck_data = {
                    'truck_id': truck_id,
                    'latitude': latitude,
                    'longitude': longitude,
                    'timestamp': updated_at,  # Use updated_at as the primary timestamp
                    'operation': op,
                    'created_at': created_at,
                    'updated_at': updated_at
                }
                logger.info(f"✅ Created truck_data: {truck_data}")
                logger.info(f"🚀 CALLING _publish_to_mqtt...")
                self._publish_to_mqtt(truck_data)
                logger.info(f"✅ MQTT publish completed")
                
            elif op == 'd':  # Delete operation
                logger.info(f"🗑️ Processing delete operation")
                before = payload.get('before', {})
                truck_id = before.get('id')
                if truck_id:
                    logger.info(f"🗑️ Truck {truck_id} deleted. Publishing delete status.")
                    delete_payload = {
                        'truck_id': truck_id,
                        'status': 'deleted',
                        'timestamp': message.value.get('ts_ms')  # Debezium timestamp
                    }
                    self.mqtt_client.publish(f"{MQTT_TOPIC_PREFIX}/{truck_id}/status", json.dumps(delete_payload), qos=1)
                    self.mqtt_client.publish(f"{MQTT_TOPIC_PREFIX}/all/locations", json.dumps(delete_payload), qos=1)
                else:
                    logger.warning(f"⚠️ Skipping delete message due to missing truck_id: {before}")
            else:
                logger.info(f"❓ Skipping unknown operation type: '{op}'")

        except Exception as e:
            logger.error(f"❌ Error processing Kafka message: {e}")
            logger.error(f"❌ Message content: {message.value}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        
        logger.info(f"🔍 ===== MESSAGE PROCESSING COMPLETE =====\n")

    def _publish_to_mqtt(self, truck_data):
        if not self.connected_to_mqtt:
            logger.warning(f"⚠️ MQTT not connected, skipping publish for truck {truck_data.get('truck_id', 'unknown')}")
            return

        truck_id = truck_data['truck_id']
        logger.info(f"📤 Publishing truck {truck_id} to MQTT topics...")
        
        # Publish to individual truck location topic
        location_payload = {
            'truck_id': truck_id,
            'latitude': truck_data['latitude'],
            'longitude': truck_data['longitude'],
            'timestamp': truck_data['timestamp']
        }
        self.mqtt_client.publish(f"{MQTT_TOPIC_PREFIX}/{truck_id}/location", json.dumps(location_payload), qos=1)
        logger.info(f"✅ Published location for truck {truck_id} to {MQTT_TOPIC_PREFIX}/{truck_id}/location")

        # Publish to individual truck status topic
        status_payload = {
            'truck_id': truck_id,
            'operation': truck_data['operation'],
            'created_at': truck_data['created_at'],
            'updated_at': truck_data['updated_at']
        }
        self.mqtt_client.publish(f"{MQTT_TOPIC_PREFIX}/{truck_id}/status", json.dumps(status_payload), qos=1)
        logger.info(f"✅ Published status for truck {truck_id} to {MQTT_TOPIC_PREFIX}/{truck_id}/status")

        # Publish to all locations topic
        self.mqtt_client.publish(f"{MQTT_TOPIC_PREFIX}/all/locations", json.dumps(truck_data), qos=1)
        logger.info(f"✅ Published all data for truck {truck_id} to {MQTT_TOPIC_PREFIX}/all/locations")
        logger.info(f"🎉 Successfully published data for truck {truck_id} to MQTT topics.")

    def _publish_test_message(self, test_count):
        """Publish a test message to verify MQTT is working"""
        test_truck_data = {
            'truck_id': f'TEST-{test_count}',
            'latitude': -25.123 + (test_count * 0.001),  # Vary location slightly
            'longitude': 120.456 + (test_count * 0.001),
            'timestamp': datetime.now().isoformat(),
            'operation': 'c',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'test': True
        }
        logger.info(f"🧪 Publishing TEST message #{test_count} for truck TEST-{test_count}")
        self._publish_to_mqtt(test_truck_data)

    def run(self):
        logger.info("=" * 50)
        logger.info("Simple Kafka-MQTT Bridge Starting")
        logger.info("=" * 50)
        self._setup_mqtt()
        self._setup_kafka()
        logger.info("🚀 Bridge started - consuming messages...")
        
        processed_count = 0
        published_count = 0
        error_count = 0
        test_count = 0
        last_test_time = time.time()
        
        try:
            while True:
                current_time = time.time()
                
# Test functionality temporarily disabled - focusing on Kafka processing
                # if current_time - last_test_time >= 5:
                #     test_count += 1
                #     self._publish_test_message(test_count)
                #     last_test_time = current_time
                
                # Poll for messages with timeout
                message_batch = self.kafka_consumer.poll(timeout_ms=1000)
                
                if not message_batch:
                    logger.debug("🔄 Polling for messages...")
                    continue
                
                logger.info(f"📨 Received {sum(len(msgs) for msgs in message_batch.values())} messages")
                
                for topic_partition, messages in message_batch.items():
                    logger.debug(f"Processing {len(messages)} messages from {topic_partition}")
                    
                    for message in messages:
                        try:
                            logger.debug(f"📨 Processing message from partition {message.partition}, offset {message.offset}")
                            self._process_message(message)
                            processed_count += 1
                            published_count += 1  # Assume successful if no exception
                        except Exception as e:
                            error_count += 1
                            logger.error(f"❌ Error processing message: {e}")
                
                # Commit offsets
                self.kafka_consumer.commit()
                
        except KeyboardInterrupt:
            logger.info("⌨️ Shutting down bridge due to KeyboardInterrupt.")
        except Exception as e:
            logger.error(f"❌ An unexpected error occurred in the main loop: {e}")
        finally:
            logger.info("=" * 50)
            logger.info("📊 FINAL STATISTICS")
            logger.info("=" * 50)
            logger.info(f"Messages Processed: {processed_count}")
            logger.info(f"MQTT Messages Published: {published_count}")
            logger.info(f"Errors: {error_count}")
            logger.info("=" * 50)
            self.shutdown()

    def shutdown(self):
        logger.info("🧹 Cleaning up resources...")
        if self.mqtt_client:
            logger.info("🔌 Disconnecting from MQTT broker")
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        if self.kafka_consumer:
            logger.info("🔌 Closing Kafka consumer")
            self.kafka_consumer.close()
        logger.info("=" * 50)
        logger.info("✅ Bridge stopped")
        logger.info("=" * 50)


if __name__ == "__main__":
    bridge = SimpleKafkaMQTTBridge()
    bridge.run()