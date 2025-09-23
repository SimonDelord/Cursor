#!/usr/bin/env python3
"""
MQTT Truck Location Listener
============================

A simple MQTT subscriber that listens to truck location updates
and displays them in real-time with formatted output.
"""

import json
import logging
import os
import time
from datetime import datetime

import paho.mqtt.client as mqtt

# Configuration from environment variables
MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto.mqtt.svc")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "trucks/all/locations")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Setup logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TruckLocationListener:
    def __init__(self):
        self.client = None
        self.connected = False
        self.message_count = 0
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logger.info(f"🔗 Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
            logger.info(f"📡 Subscribing to topic: {MQTT_TOPIC}")
            client.subscribe(MQTT_TOPIC, qos=1)
        else:
            logger.error(f"❌ Failed to connect to MQTT broker, return code {rc}")
            self.connected = False

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        logger.warning(f"⚡ Disconnected from MQTT broker with result code {rc}")

    def on_message(self, client, userdata, msg):
        self.message_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        try:
            # Parse the JSON message
            data = json.loads(msg.payload.decode('utf-8'))
            
            # Extract key fields
            truck_id = data.get('truck_id', 'Unknown')
            latitude = data.get('latitude', 'N/A')
            longitude = data.get('longitude', 'N/A')
            operation = data.get('operation', 'N/A')
            msg_timestamp = data.get('timestamp', 'N/A')
            
            # Check if it's a test message
            is_test = data.get('test', False)
            test_indicator = "🧪 [TEST]" if is_test else "🚛"
            
            print(f"\n{test_indicator} === TRUCK LOCATION UPDATE #{self.message_count} ===")
            print(f"📅 Received at: {timestamp}")
            print(f"🚛 Truck ID: {truck_id}")
            print(f"📍 Location: ({latitude}, {longitude})")
            print(f"🔄 Operation: {operation}")
            print(f"⏰ Message Timestamp: {msg_timestamp}")
            
            if is_test:
                print(f"🧪 Test Message Details:")
                print(f"   Created: {data.get('created_at', 'N/A')}")
                print(f"   Updated: {data.get('updated_at', 'N/A')}")
            
            print(f"📦 Raw Message: {json.dumps(data, indent=2)}")
            print("=" * 60)
            
            logger.info(f"Processed truck location update for truck {truck_id}")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse JSON message: {e}")
            print(f"\n❌ Invalid JSON received at {timestamp}")
            print(f"Raw payload: {msg.payload.decode('utf-8', errors='replace')}")
            
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        logger.info(f"✅ Successfully subscribed to {MQTT_TOPIC} with QoS {granted_qos[0]}")
        print(f"\n🎯 === MQTT TRUCK LOCATION LISTENER ===")
        print(f"📡 Listening to: {MQTT_TOPIC}")
        print(f"🔗 Broker: {MQTT_BROKER}:{MQTT_PORT}")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("🚛 Waiting for truck location updates...")
        print("=" * 60)

    def run(self):
        logger.info("🚀 Starting MQTT Truck Location Listener")
        
        # Create MQTT client
        self.client = mqtt.Client(client_id=f"truck-listener-{int(time.time())}")
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
        
        try:
            # Connect to broker
            logger.info(f"🔗 Connecting to MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            
            # Start the loop
            logger.info("🔄 Starting MQTT client loop...")
            self.client.loop_forever()
            
        except KeyboardInterrupt:
            logger.info("⌨️ Received keyboard interrupt, shutting down...")
        except Exception as e:
            logger.error(f"❌ Error in main loop: {e}")
        finally:
            self.shutdown()

    def shutdown(self):
        logger.info("🛑 Shutting down MQTT listener...")
        if self.client:
            self.client.disconnect()
        logger.info(f"📊 Total messages processed: {self.message_count}")
        logger.info("👋 MQTT Truck Location Listener stopped")

if __name__ == "__main__":
    listener = TruckLocationListener()
    listener.run()
