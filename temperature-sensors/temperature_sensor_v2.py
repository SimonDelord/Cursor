#!/usr/bin/env python3
"""
Temperature Sensor Simulator v2 - with MQTT Support

A Python application that simulates a temperature sensor by generating
random temperature readings at regular intervals and publishes them to an MQTT broker.
"""

import random
import time
import json
from datetime import datetime
import argparse
import sys

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("Warning: paho-mqtt not installed. Install with: pip install paho-mqtt")


class TemperatureSensor:
    """Simulates a temperature sensor with configurable parameters and MQTT publishing."""
    
    def __init__(self, min_temp=18.0, max_temp=35.0, interval=2.0, variance=1.0,
                 mqtt_broker=None, mqtt_port=1883, mqtt_topic="sensors/temperature",
                 mqtt_username=None, mqtt_password=None, sensor_id="temp_001"):
        """
        Initialize the temperature sensor.
        
        Args:
            min_temp (float): Minimum temperature in Celsius
            max_temp (float): Maximum temperature in Celsius
            interval (float): Time interval between readings in seconds
            variance (float): Maximum temperature change between readings
            mqtt_broker (str): MQTT broker hostname/IP
            mqtt_port (int): MQTT broker port
            mqtt_topic (str): MQTT topic to publish to
            mqtt_username (str): MQTT username (optional)
            mqtt_password (str): MQTT password (optional)
            sensor_id (str): Unique sensor identifier
        """
        self.min_temp = min_temp
        self.max_temp = max_temp
        self.interval = interval
        self.variance = variance
        self.current_temp = random.uniform(min_temp, max_temp)
        self.reading_count = 0
        self.sensor_id = sensor_id
        
        # MQTT configuration
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_topic = mqtt_topic
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password
        self.mqtt_client = None
        self.mqtt_connected = False
        
        # Initialize MQTT if broker is specified
        if self.mqtt_broker and MQTT_AVAILABLE:
            self._setup_mqtt()
    
    def _setup_mqtt(self):
        """Set up MQTT client connection."""
        try:
            self.mqtt_client = mqtt.Client()
            
            # Set username and password if provided
            if self.mqtt_username and self.mqtt_password:
                self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)
            
            # Set callback functions
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
            self.mqtt_client.on_publish = self._on_mqtt_publish
            
            # Connect to broker
            print(f"🔌 Connecting to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}...")
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()  # Start the loop in a separate thread
            
            # Wait a moment for connection
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Failed to connect to MQTT broker: {e}")
            self.mqtt_client = None
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection."""
        if rc == 0:
            self.mqtt_connected = True
            print(f"✅ Connected to MQTT broker successfully!")
            print(f"📡 Publishing to topic: {self.mqtt_topic}")
        else:
            print(f"❌ Failed to connect to MQTT broker. Return code: {rc}")
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection."""
        self.mqtt_connected = False
        if rc != 0:
            print("🔌 Unexpected MQTT disconnection. Will attempt to reconnect...")
    
    def _on_mqtt_publish(self, client, userdata, mid):
        """Callback for successful MQTT publish."""
        pass  # Could add debug logging here if needed
    
    def get_temperature_reading(self):
        """
        Generate a realistic temperature reading with gradual changes.
        
        Returns:
            float: Temperature reading in Celsius
        """
        # Add some variance to simulate realistic sensor behavior
        change = random.uniform(-self.variance, self.variance)
        self.current_temp += change
        
        # Keep temperature within bounds
        self.current_temp = max(self.min_temp, min(self.max_temp, self.current_temp))
        
        # Add small random noise to simulate sensor precision
        noise = random.uniform(-0.1, 0.1)
        return round(self.current_temp + noise, 2)
    
    def format_reading(self, temperature):
        """
        Format temperature reading with timestamp.
        
        Args:
            temperature (float): Temperature value
            
        Returns:
            str: Formatted reading string
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.reading_count += 1
        mqtt_status = "📡" if self.mqtt_connected else "📴"
        return f"[{timestamp}] {mqtt_status} Reading #{self.reading_count:04d}: {temperature:6.2f}°C"
    
    def create_mqtt_payload(self, temperature):
        """
        Create JSON payload for MQTT publishing.
        
        Args:
            temperature (float): Temperature value
            
        Returns:
            str: JSON payload string
        """
        payload = {
            "sensor_id": self.sensor_id,
            "temperature": temperature,
            "timestamp": datetime.now().isoformat(),
            "reading_count": self.reading_count,
            "unit": "celsius"
        }
        return json.dumps(payload)
    
    def publish_to_mqtt(self, temperature):
        """
        Publish temperature reading to MQTT broker.
        
        Args:
            temperature (float): Temperature value
        """
        if not self.mqtt_client or not self.mqtt_connected:
            return False
        
        try:
            payload = self.create_mqtt_payload(temperature)
            result = self.mqtt_client.publish(self.mqtt_topic, payload, qos=1)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"❌ Failed to publish to MQTT: {e}")
            return False
    
    def run(self, duration=None):
        """
        Run the temperature sensor simulation.
        
        Args:
            duration (float, optional): Duration to run in seconds. If None, runs indefinitely.
        """
        print("🌡️  Temperature Sensor Simulator v2 (with MQTT) Starting...")
        print(f"   Temperature range: {self.min_temp}°C to {self.max_temp}°C")
        print(f"   Reading interval: {self.interval} seconds")
        print(f"   Sensor ID: {self.sensor_id}")
        
        if self.mqtt_broker:
            if MQTT_AVAILABLE:
                print(f"   MQTT Broker: {self.mqtt_broker}:{self.mqtt_port}")
                print(f"   MQTT Topic: {self.mqtt_topic}")
            else:
                print("   ⚠️  MQTT disabled: paho-mqtt not installed")
        else:
            print("   📴 MQTT disabled: no broker specified")
        
        print("   Press Ctrl+C to stop\n")
        
        start_time = time.time()
        
        try:
            while True:
                # Check duration limit
                if duration and (time.time() - start_time) >= duration:
                    break
                
                # Get temperature reading
                temperature = self.get_temperature_reading()
                
                # Display reading
                print(self.format_reading(temperature))
                
                # Publish to MQTT if enabled
                if self.mqtt_broker and MQTT_AVAILABLE:
                    success = self.publish_to_mqtt(temperature)
                    if not success and self.mqtt_connected:
                        print("   ⚠️  Failed to publish to MQTT")
                
                # Wait for next reading
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            print(f"\n\n🛑 Sensor simulation stopped after {self.reading_count} readings.")
            if self.mqtt_client:
                print("🔌 Disconnecting from MQTT broker...")
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            print("Thank you for using the Temperature Sensor Simulator v2!")
    
    def __del__(self):
        """Cleanup MQTT connection on object deletion."""
        if hasattr(self, 'mqtt_client') and self.mqtt_client:
            try:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            except:
                pass  # Ignore cleanup errors


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description="Temperature Sensor Simulator v2 - Generate random temperature readings with MQTT support"
    )
    
    # Temperature sensor parameters
    parser.add_argument(
        "--min-temp", 
        type=float, 
        default=18.0,
        help="Minimum temperature in Celsius (default: 18.0)"
    )
    
    parser.add_argument(
        "--max-temp", 
        type=float, 
        default=35.0,
        help="Maximum temperature in Celsius (default: 35.0)"
    )
    
    parser.add_argument(
        "--interval", 
        type=float, 
        default=2.0,
        help="Time interval between readings in seconds (default: 2.0)"
    )
    
    parser.add_argument(
        "--variance", 
        type=float, 
        default=1.0,
        help="Maximum temperature change between readings (default: 1.0)"
    )
    
    parser.add_argument(
        "--duration", 
        type=float, 
        help="Duration to run in seconds (default: runs indefinitely)"
    )
    
    parser.add_argument(
        "--sensor-id", 
        type=str, 
        default="temp_001",
        help="Unique sensor identifier (default: temp_001)"
    )
    
    # MQTT parameters
    parser.add_argument(
        "--mqtt-broker", 
        type=str,
        help="MQTT broker hostname or IP address"
    )
    
    parser.add_argument(
        "--mqtt-port", 
        type=int, 
        default=1883,
        help="MQTT broker port (default: 1883)"
    )
    
    parser.add_argument(
        "--mqtt-topic", 
        type=str, 
        default="sensors/temperature",
        help="MQTT topic to publish to (default: sensors/temperature)"
    )
    
    parser.add_argument(
        "--mqtt-username", 
        type=str,
        help="MQTT username (optional)"
    )
    
    parser.add_argument(
        "--mqtt-password", 
        type=str,
        help="MQTT password (optional)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.min_temp >= args.max_temp:
        print("Error: min-temp must be less than max-temp")
        return 1
    
    if args.interval <= 0:
        print("Error: interval must be positive")
        return 1
    
    if args.mqtt_broker and not MQTT_AVAILABLE:
        print("Error: paho-mqtt library is required for MQTT functionality")
        print("Install with: pip install paho-mqtt")
        return 1
    
    # Create and run sensor
    sensor = TemperatureSensor(
        min_temp=args.min_temp,
        max_temp=args.max_temp,
        interval=args.interval,
        variance=args.variance,
        mqtt_broker=args.mqtt_broker,
        mqtt_port=args.mqtt_port,
        mqtt_topic=args.mqtt_topic,
        mqtt_username=args.mqtt_username,
        mqtt_password=args.mqtt_password,
        sensor_id=args.sensor_id
    )
    
    sensor.run(duration=args.duration)
    return 0


if __name__ == "__main__":
    exit(main())

