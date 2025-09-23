#!/usr/bin/env python3
"""
Kafka-MQTT Bridge v2 - Complete Rewrite
=====================================

A robust, production-ready bridge that consumes truck location data from Kafka CDC streams
and publishes structured messages to MQTT topics for real-time IoT applications.

Features:
- Resilient connection management with automatic reconnection
- Comprehensive error handling and logging
- Message validation and transformation
- Health checks and monitoring
- Clean shutdown handling
- Configuration validation
"""

import json
import logging
import os
import signal
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from threading import Event, Thread
from typing import Dict, List, Optional, Any

import paho.mqtt.client as mqtt
from kafka import KafkaConsumer
from kafka.errors import KafkaError


@dataclass
class Config:
    """Configuration container with validation"""
    
    # Kafka Configuration
    kafka_bootstrap_servers: str = "debezium-cluster-kafka-bootstrap:9092"
    kafka_topic: str = "realtime.trucks.location"
    kafka_group_id: str = "truck-mqtt-bridge-v2"
    kafka_auto_offset_reset: str = "latest"
    kafka_session_timeout: int = 30000
    kafka_heartbeat_interval: int = 3000
    
    # MQTT Configuration  
    mqtt_broker: str = "mosquitto.mqtt.svc"
    mqtt_port: int = 1883
    mqtt_topic_prefix: str = "trucks"
    mqtt_qos: int = 1
    mqtt_keepalive: int = 60
    mqtt_reconnect_min_delay: int = 1
    mqtt_reconnect_max_delay: int = 120
    
    # Application Configuration
    log_level: str = "INFO"
    health_check_interval: int = 30
    max_retries: int = 5
    retry_backoff: float = 2.0
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create configuration from environment variables"""
        return cls(
            # Kafka
            kafka_bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', cls.kafka_bootstrap_servers),
            kafka_topic=os.getenv('KAFKA_TOPIC', cls.kafka_topic),
            kafka_group_id=os.getenv('KAFKA_GROUP_ID', cls.kafka_group_id),
            kafka_auto_offset_reset=os.getenv('KAFKA_AUTO_OFFSET_RESET', cls.kafka_auto_offset_reset),
            
            # MQTT
            mqtt_broker=os.getenv('MQTT_BROKER', cls.mqtt_broker),
            mqtt_port=int(os.getenv('MQTT_PORT', str(cls.mqtt_port))),
            mqtt_topic_prefix=os.getenv('MQTT_TOPIC_PREFIX', cls.mqtt_topic_prefix),
            mqtt_qos=int(os.getenv('MQTT_QOS', str(cls.mqtt_qos))),
            
            # Application
            log_level=os.getenv('LOG_LEVEL', cls.log_level),
            health_check_interval=int(os.getenv('HEALTH_CHECK_INTERVAL', str(cls.health_check_interval))),
        )


class MQTTManager:
    """Manages MQTT connection with automatic reconnection and health monitoring"""
    
    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.client_id = f"kafka-mqtt-bridge-{uuid.uuid4().hex[:8]}"
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.connection_event = Event()
        
    def setup(self) -> bool:
        """Initialize MQTT client with callbacks"""
        try:
            self.client = mqtt.Client(client_id=self.client_id)
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_publish = self._on_publish
            self.client.on_log = self._on_log
            
            # Configure reconnection
            self.client.reconnect_delay_set(
                min_delay=self.config.mqtt_reconnect_min_delay,
                max_delay=self.config.mqtt_reconnect_max_delay
            )
            
            self.logger.info(f"MQTT client initialized with ID: {self.client_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MQTT client: {e}")
            return False
    
    def connect(self) -> bool:
        """Connect to MQTT broker with retry logic"""
        if not self.client:
            self.logger.error("MQTT client not initialized")
            return False
        
        try:
            self.logger.info(f"Connecting to MQTT broker: {self.config.mqtt_broker}:{self.config.mqtt_port}")
            self.client.connect(
                self.config.mqtt_broker,
                self.config.mqtt_port,
                self.config.mqtt_keepalive
            )
            self.client.loop_start()
            
            # Wait for connection with timeout
            if self.connection_event.wait(timeout=30):
                self.logger.info("MQTT connection established successfully")
                return True
            else:
                self.logger.error("MQTT connection timeout")
                return False
                
        except Exception as e:
            self.logger.error(f"MQTT connection failed: {e}")
            return False
    
    def disconnect(self):
        """Gracefully disconnect from MQTT broker"""
        if self.client and self.connected:
            self.logger.info("Disconnecting from MQTT broker")
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            self.connection_event.clear()
    
    def publish_message(self, topic: str, payload: str) -> bool:
        """Publish message to MQTT topic with error handling"""
        if not self.connected or not self.client:
            self.logger.warning(f"Cannot publish to {topic}: MQTT not connected")
            return False
        
        try:
            result = self.client.publish(topic, payload, qos=self.config.mqtt_qos)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.debug(f"Published message to {topic}")
                return True
            else:
                self.logger.error(f"Failed to publish to {topic}: error code {result.rc}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error publishing to {topic}: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.connected = True
            self.connection_event.set()
            self.logger.info(f"Connected to MQTT broker (client: {self.client_id})")
        else:
            self.logger.error(f"MQTT connection failed with code {rc}")
            self.connection_event.set()  # Unblock waiting threads
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        self.connected = False
        self.connection_event.clear()
        
        if rc == 0:
            self.logger.info("MQTT client disconnected gracefully")
        else:
            self.logger.warning(f"Unexpected MQTT disconnection (code: {rc})")
    
    def _on_publish(self, client, userdata, mid):
        """MQTT publish callback"""
        self.logger.debug(f"Message published successfully (mid: {mid})")
    
    def _on_log(self, client, userdata, level, buf):
        """MQTT logging callback"""
        if level == mqtt.MQTT_LOG_DEBUG:
            self.logger.debug(f"MQTT: {buf}")
        elif level in (mqtt.MQTT_LOG_INFO, mqtt.MQTT_LOG_NOTICE):
            self.logger.debug(f"MQTT: {buf}")
        elif level == mqtt.MQTT_LOG_WARNING:
            self.logger.warning(f"MQTT: {buf}")
        elif level == mqtt.MQTT_LOG_ERR:
            self.logger.error(f"MQTT: {buf}")


class KafkaManager:
    """Manages Kafka consumer with robust error handling"""
    
    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.consumer: Optional[KafkaConsumer] = None
    
    def setup(self) -> bool:
        """Initialize Kafka consumer"""
        try:
            self.consumer = KafkaConsumer(
                self.config.kafka_topic,
                bootstrap_servers=self.config.kafka_bootstrap_servers.split(','),
                group_id=self.config.kafka_group_id,
                auto_offset_reset=self.config.kafka_auto_offset_reset,
                session_timeout_ms=self.config.kafka_session_timeout,
                heartbeat_interval_ms=self.config.kafka_heartbeat_interval,
                value_deserializer=self._safe_deserialize_value,
                enable_auto_commit=True,
                auto_commit_interval_ms=5000,
                max_poll_records=10,  # Process messages in small batches
                consumer_timeout_ms=1000  # Poll timeout for graceful shutdown
            )
            
            self.logger.info(f"Kafka consumer initialized for topic: {self.config.kafka_topic}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Kafka consumer: {e}")
            return False
    
    def close(self):
        """Close Kafka consumer"""
        if self.consumer:
            self.logger.info("Closing Kafka consumer")
            self.consumer.close()
            self.consumer = None
    
    def consume_messages(self):
        """Generator that yields Kafka messages with error handling"""
        if not self.consumer:
            self.logger.error("Kafka consumer not initialized")
            return
        
        try:
            for message in self.consumer:
                if message.value is not None:
                    yield message
                else:
                    self.logger.debug("Skipped tombstone record (null message)")
                    
        except KafkaError as e:
            self.logger.error(f"Kafka consumer error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error consuming messages: {e}")
    
    def _safe_deserialize_value(self, raw_value: bytes) -> Optional[Dict]:
        """Safely deserialize Kafka message value"""
        if raw_value is None:
            return None
        
        try:
            return json.loads(raw_value.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self.logger.warning(f"Failed to deserialize message value: {e}")
            return None


class MessageProcessor:
    """Processes CDC messages and transforms them for MQTT publishing"""
    
    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.processed_count = 0
        self.error_count = 0
    
    def process_cdc_message(self, kafka_message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract and validate truck data from CDC message"""
        try:
            if not kafka_message:
                return None
            
            payload = kafka_message.get('payload', {})
            operation = payload.get('op', '')
            
            # Only process create, update, and read operations
            if operation not in ['c', 'u', 'r']:
                self.logger.debug(f"Skipping operation: {operation}")
                return None
            
            after_data = payload.get('after', {})
            if not after_data:
                self.logger.debug("No 'after' data in CDC message")
                return None
            
            # Extract and validate truck data
            truck_data = {
                'truck_id': after_data.get('id'),
                'latitude': self._extract_coordinate(after_data, 'latitude'),
                'longitude': self._extract_coordinate(after_data, 'longitude'),
                'created_at': after_data.get('created_at'),
                'updated_at': after_data.get('updated_at'),
                'operation': operation,
                'source_db': payload.get('source', {}).get('db', 'unknown'),
                'timestamp': datetime.now().isoformat(),
                'message_id': f"{after_data.get('id', 'unknown')}_{int(time.time()*1000)}"
            }
            
            # Validate required fields
            if not self._validate_truck_data(truck_data):
                return None
            
            self.processed_count += 1
            self.logger.info(f"Processed truck {truck_data['truck_id']} "
                          f"at ({truck_data['latitude']:.6f}, {truck_data['longitude']:.6f})")
            
            return truck_data
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error processing CDC message: {e}")
            return None
    
    def create_mqtt_messages(self, truck_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Create multiple MQTT messages from truck data"""
        truck_id = truck_data['truck_id']
        messages = []
        
        # Individual truck location topic
        location_payload = {
            'truck_id': truck_id,
            'latitude': truck_data['latitude'],
            'longitude': truck_data['longitude'],
            'timestamp': truck_data['timestamp'],
            'message_id': truck_data['message_id']
        }
        messages.append({
            'topic': f"{self.config.mqtt_topic_prefix}/{truck_id}/location",
            'payload': json.dumps(location_payload)
        })
        
        # Individual truck status topic
        status_payload = {
            'truck_id': truck_id,
            'operation': truck_data['operation'],
            'created_at': truck_data['created_at'],
            'updated_at': truck_data['updated_at'],
            'source_db': truck_data['source_db'],
            'timestamp': truck_data['timestamp']
        }
        messages.append({
            'topic': f"{self.config.mqtt_topic_prefix}/{truck_id}/status",
            'payload': json.dumps(status_payload)
        })
        
        # Aggregated topic for all trucks
        messages.append({
            'topic': f"{self.config.mqtt_topic_prefix}/all/locations",
            'payload': json.dumps(truck_data)
        })
        
        return messages
    
    def _extract_coordinate(self, data: Dict, field: str) -> Optional[float]:
        """Extract and validate coordinate value"""
        value = data.get(field)
        if value is None:
            return None
        
        try:
            if isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str):
                return float(value)
            else:
                self.logger.warning(f"Invalid {field} type: {type(value)}")
                return None
        except (ValueError, TypeError):
            self.logger.warning(f"Cannot convert {field} to float: {value}")
            return None
    
    def _validate_truck_data(self, truck_data: Dict[str, Any]) -> bool:
        """Validate truck data completeness"""
        required_fields = ['truck_id', 'latitude', 'longitude']
        
        for field in required_fields:
            if truck_data.get(field) is None:
                self.logger.warning(f"Missing required field '{field}' in truck data")
                return False
        
        # Validate coordinate ranges (rough global bounds)
        lat = truck_data['latitude']
        lon = truck_data['longitude']
        
        if not (-90 <= lat <= 90):
            self.logger.warning(f"Invalid latitude: {lat}")
            return False
        
        if not (-180 <= lon <= 180):
            self.logger.warning(f"Invalid longitude: {lon}")
            return False
        
        return True
    
    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics"""
        return {
            'processed_count': self.processed_count,
            'error_count': self.error_count
        }


class KafkaMQTTBridge:
    """Main bridge application coordinating Kafka consumption and MQTT publishing"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = self._setup_logging()
        
        # Components
        self.kafka_manager = KafkaManager(config, self.logger)
        self.mqtt_manager = MQTTManager(config, self.logger)
        self.processor = MessageProcessor(config, self.logger)
        
        # Control
        self.running = False
        self.shutdown_event = Event()
        self.health_thread = None
        
        # Statistics
        self.start_time = None
        self.published_count = 0
        self.publish_error_count = 0
    
    def _setup_logging(self) -> logging.Logger:
        """Configure logging with proper formatting"""
        logger = logging.getLogger('kafka_mqtt_bridge_v2')
        logger.setLevel(getattr(logging, self.config.log_level.upper()))
        
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def start(self) -> bool:
        """Start the bridge application"""
        self.logger.info("=" * 60)
        self.logger.info("Starting Kafka-MQTT Bridge v2")
        self.logger.info("=" * 60)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.start_time = datetime.now()
        
        # Initialize components
        if not self.kafka_manager.setup():
            self.logger.error("Failed to setup Kafka manager")
            return False
        
        if not self.mqtt_manager.setup():
            self.logger.error("Failed to setup MQTT manager")
            return False
        
        if not self.mqtt_manager.connect():
            self.logger.error("Failed to connect to MQTT broker")
            return False
        
        # Start health monitoring
        self.health_thread = Thread(target=self._health_monitor, daemon=True)
        self.health_thread.start()
        
        self.running = True
        self.logger.info("Bridge started successfully - entering main loop")
        
        return True
    
    def run(self):
        """Main bridge loop"""
        if not self.running:
            self.logger.error("Bridge not started")
            return
        
        try:
            for kafka_message in self.kafka_manager.consume_messages():
                if self.shutdown_event.is_set():
                    self.logger.info("Shutdown requested, stopping message processing")
                    break
                
                # Process CDC message
                truck_data = self.processor.process_cdc_message(kafka_message.value)
                
                if truck_data:
                    # Create and publish MQTT messages
                    mqtt_messages = self.processor.create_mqtt_messages(truck_data)
                    published_topics = []
                    
                    for msg in mqtt_messages:
                        if self.mqtt_manager.publish_message(msg['topic'], msg['payload']):
                            published_topics.append(msg['topic'])
                            self.published_count += 1
                        else:
                            self.publish_error_count += 1
                    
                    if published_topics:
                        self.logger.info(f"Published truck {truck_data['truck_id']} to "
                                       f"{len(published_topics)} MQTT topics")
                    else:
                        self.logger.warning(f"Failed to publish truck {truck_data['truck_id']} "
                                          f"to any MQTT topics")
        
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
        
        finally:
            self._cleanup()
    
    def stop(self):
        """Stop the bridge application"""
        self.logger.info("Stopping Kafka-MQTT Bridge v2...")
        self.running = False
        self.shutdown_event.set()
    
    def _cleanup(self):
        """Clean up resources"""
        self.logger.info("Cleaning up resources...")
        
        if self.mqtt_manager:
            self.mqtt_manager.disconnect()
        
        if self.kafka_manager:
            self.kafka_manager.close()
        
        self._log_final_stats()
        self.logger.info("Bridge stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self.stop()
    
    def _health_monitor(self):
        """Health monitoring thread"""
        while self.running and not self.shutdown_event.wait(self.config.health_check_interval):
            try:
                uptime = datetime.now() - self.start_time
                stats = self.processor.get_stats()
                
                self.logger.info(f"Health Check - Uptime: {uptime}, "
                               f"Processed: {stats['processed_count']}, "
                               f"Published: {self.published_count}, "
                               f"Errors: {stats['error_count'] + self.publish_error_count}, "
                               f"MQTT Connected: {self.mqtt_manager.connected}")
                
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
    
    def _log_final_stats(self):
        """Log final statistics"""
        if self.start_time:
            uptime = datetime.now() - self.start_time
            stats = self.processor.get_stats()
            
            self.logger.info("=" * 60)
            self.logger.info("FINAL STATISTICS")
            self.logger.info("=" * 60)
            self.logger.info(f"Total Uptime: {uptime}")
            self.logger.info(f"Messages Processed: {stats['processed_count']}")
            self.logger.info(f"MQTT Messages Published: {self.published_count}")
            self.logger.info(f"Processing Errors: {stats['error_count']}")
            self.logger.info(f"Publishing Errors: {self.publish_error_count}")
            
            if stats['processed_count'] > 0:
                success_rate = (self.published_count / (stats['processed_count'] * 3)) * 100
                self.logger.info(f"Publishing Success Rate: {success_rate:.1f}%")
            
            self.logger.info("=" * 60)


def main():
    """Entry point"""
    try:
        # Load configuration
        config = Config.from_env()
        
        # Create and start bridge
        bridge = KafkaMQTTBridge(config)
        
        if bridge.start():
            bridge.run()
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
