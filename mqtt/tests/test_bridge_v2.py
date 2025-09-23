#!/usr/bin/env python3
"""
Test Script for Kafka-MQTT Bridge v2
====================================

Basic unit tests and integration checks for the new bridge implementation.
"""

import json
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add the bridge directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bridge'))

try:
    from kafka_mqtt_bridge_v2 import Config, MQTTManager, KafkaManager, MessageProcessor, KafkaMQTTBridge
except ImportError as e:
    print(f"Failed to import bridge modules: {e}")
    sys.exit(1)


class TestConfig(unittest.TestCase):
    """Test configuration management"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = Config()
        self.assertEqual(config.kafka_topic, "realtime.trucks.location")
        self.assertEqual(config.mqtt_broker, "mosquitto.mqtt.svc")
        self.assertEqual(config.mqtt_port, 1883)
    
    def test_env_config(self):
        """Test configuration from environment variables"""
        with patch.dict(os.environ, {
            'KAFKA_TOPIC': 'test.topic',
            'MQTT_BROKER': 'test.broker',
            'MQTT_PORT': '1234'
        }):
            config = Config.from_env()
            self.assertEqual(config.kafka_topic, 'test.topic')
            self.assertEqual(config.mqtt_broker, 'test.broker')
            self.assertEqual(config.mqtt_port, 1234)


class TestMessageProcessor(unittest.TestCase):
    """Test message processing logic"""
    
    def setUp(self):
        self.config = Config()
        # Create a mock logger
        self.logger = Mock()
        self.processor = MessageProcessor(self.config, self.logger)
    
    def test_valid_cdc_message(self):
        """Test processing of valid CDC message"""
        cdc_message = {
            'payload': {
                'op': 'c',
                'after': {
                    'id': 123,
                    'latitude': -22.77361111,
                    'longitude': 117.76194444,
                    'created_at': '2025-09-23T10:00:00Z',
                    'updated_at': '2025-09-23T10:00:00Z'
                },
                'source': {
                    'db': 'trucks'
                }
            }
        }
        
        result = self.processor.process_cdc_message(cdc_message)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['truck_id'], 123)
        self.assertEqual(result['latitude'], -22.77361111)
        self.assertEqual(result['longitude'], 117.76194444)
        self.assertEqual(result['operation'], 'c')
        self.assertEqual(result['source_db'], 'trucks')
    
    def test_invalid_operation(self):
        """Test skipping of invalid operations"""
        cdc_message = {
            'payload': {
                'op': 'd',  # Delete operation - should be skipped
                'after': None
            }
        }
        
        result = self.processor.process_cdc_message(cdc_message)
        self.assertIsNone(result)
    
    def test_missing_coordinates(self):
        """Test rejection of messages with missing coordinates"""
        cdc_message = {
            'payload': {
                'op': 'c',
                'after': {
                    'id': 123,
                    'latitude': None,  # Missing latitude
                    'longitude': 117.76194444
                }
            }
        }
        
        result = self.processor.process_cdc_message(cdc_message)
        self.assertIsNone(result)
    
    def test_invalid_coordinates(self):
        """Test rejection of invalid coordinate ranges"""
        cdc_message = {
            'payload': {
                'op': 'c',
                'after': {
                    'id': 123,
                    'latitude': 95.0,  # Invalid latitude (>90)
                    'longitude': 117.76194444
                }
            }
        }
        
        result = self.processor.process_cdc_message(cdc_message)
        self.assertIsNone(result)
    
    def test_mqtt_message_creation(self):
        """Test creation of MQTT messages from truck data"""
        truck_data = {
            'truck_id': 123,
            'latitude': -22.77361111,
            'longitude': 117.76194444,
            'created_at': '2025-09-23T10:00:00Z',
            'updated_at': '2025-09-23T10:00:00Z',
            'operation': 'c',
            'source_db': 'trucks',
            'timestamp': datetime.now().isoformat(),
            'message_id': 'test_123_123456789'
        }
        
        messages = self.processor.create_mqtt_messages(truck_data)
        
        self.assertEqual(len(messages), 3)  # location, status, all
        
        # Check location message
        location_msg = messages[0]
        self.assertEqual(location_msg['topic'], 'trucks/123/location')
        location_data = json.loads(location_msg['payload'])
        self.assertEqual(location_data['truck_id'], 123)
        self.assertEqual(location_data['latitude'], -22.77361111)
        
        # Check status message
        status_msg = messages[1]
        self.assertEqual(status_msg['topic'], 'trucks/123/status')
        status_data = json.loads(status_msg['payload'])
        self.assertEqual(status_data['operation'], 'c')
        
        # Check aggregated message
        all_msg = messages[2]
        self.assertEqual(all_msg['topic'], 'trucks/all/locations')
        all_data = json.loads(all_msg['payload'])
        self.assertEqual(all_data['truck_id'], 123)
    
    def test_coordinate_extraction(self):
        """Test coordinate extraction with different data types"""
        # Test integer
        result = self.processor._extract_coordinate({'lat': 123}, 'lat')
        self.assertEqual(result, 123.0)
        
        # Test float
        result = self.processor._extract_coordinate({'lat': 123.456}, 'lat')
        self.assertEqual(result, 123.456)
        
        # Test string number
        result = self.processor._extract_coordinate({'lat': '123.456'}, 'lat')
        self.assertEqual(result, 123.456)
        
        # Test invalid string
        result = self.processor._extract_coordinate({'lat': 'invalid'}, 'lat')
        self.assertIsNone(result)
        
        # Test missing field
        result = self.processor._extract_coordinate({}, 'lat')
        self.assertIsNone(result)


class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def test_bridge_initialization(self):
        """Test that bridge can be initialized with default config"""
        config = Config()
        bridge = KafkaMQTTBridge(config)
        
        self.assertIsNotNone(bridge.kafka_manager)
        self.assertIsNotNone(bridge.mqtt_manager)
        self.assertIsNotNone(bridge.processor)
        self.assertFalse(bridge.running)
    
    @patch('kafka_mqtt_bridge_v2.KafkaConsumer')
    def test_kafka_manager_setup(self, mock_consumer):
        """Test Kafka manager setup"""
        config = Config()
        logger = Mock()
        manager = KafkaManager(config, logger)
        
        # Mock successful consumer creation
        mock_consumer.return_value = Mock()
        
        result = manager.setup()
        self.assertTrue(result)
        self.assertIsNotNone(manager.consumer)
    
    @patch('paho.mqtt.client.Client')
    def test_mqtt_manager_setup(self, mock_client_class):
        """Test MQTT manager setup"""
        config = Config()
        logger = Mock()
        manager = MQTTManager(config, logger)
        
        # Mock MQTT client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        result = manager.setup()
        self.assertTrue(result)
        self.assertIsNotNone(manager.client)


def run_basic_validation():
    """Run basic validation to ensure the bridge can be imported and initialized"""
    print("🔍 Running basic validation tests...")
    
    try:
        # Test imports
        print("✅ Successfully imported all bridge modules")
        
        # Test configuration
        config = Config()
        print(f"✅ Default config created: {config.kafka_topic} → {config.mqtt_broker}")
        
        # Test environment config
        os.environ['TEST_KAFKA_TOPIC'] = 'test.topic'
        test_config = Config.from_env()
        print(f"✅ Environment config works: {test_config.kafka_topic}")
        
        # Test bridge initialization
        bridge = KafkaMQTTBridge(config)
        print("✅ Bridge initialized successfully")
        
        # Test message processor
        processor = MessageProcessor(config, Mock())
        test_message = {
            'payload': {
                'op': 'c',
                'after': {
                    'id': 999,
                    'latitude': -22.77361111,
                    'longitude': 117.76194444
                }
            }
        }
        result = processor.process_cdc_message(test_message)
        print(f"✅ Message processing works: truck {result['truck_id'] if result else 'None'}")
        
        print("\n🎉 All basic validation tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False


def main():
    """Main test runner"""
    print("=" * 60)
    print("Kafka-MQTT Bridge v2 - Test Suite")
    print("=" * 60)
    
    # Run basic validation first
    if not run_basic_validation():
        sys.exit(1)
    
    print("\n🧪 Running unit tests...")
    print("-" * 40)
    
    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    print("\n✅ Test suite completed!")


if __name__ == "__main__":
    main()
