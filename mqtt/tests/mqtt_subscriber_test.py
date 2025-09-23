#!/usr/bin/env python3
"""
Simple MQTT subscriber to check messages in trucks/all/locations topic
"""
import paho.mqtt.client as mqtt
import json
import time
import signal
import sys

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe("trucks/all/locations", qos=1)
        client.subscribe("trucks/+/location", qos=1)  # Subscribe to all truck location topics
        print("Subscribed to trucks/all/locations and trucks/+/location")
    else:
        print(f"Failed to connect with result code {rc}")

def on_message(client, userdata, msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    topic = msg.topic
    try:
        payload = json.loads(msg.payload.decode())
        print(f"\n[{timestamp}] Received message on topic: {topic}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
    except json.JSONDecodeError:
        print(f"\n[{timestamp}] Received non-JSON message on topic: {topic}")
        print(f"Raw payload: {msg.payload.decode()}")

def signal_handler(sig, frame):
    print('\nDisconnecting from MQTT broker...')
    client.loop_stop()
    client.disconnect()
    sys.exit(0)

if __name__ == "__main__":
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    print("Connecting to MQTT broker at localhost:1883...")
    try:
        client.connect("localhost", 1883, 60)
        client.loop_start()
        
        print("Listening for MQTT messages... (Press Ctrl+C to exit)")
        print("Waiting for messages on trucks/all/locations and trucks/+/location topics...")
        
        # Keep the script running
        while True:
            time.sleep(1)
            
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you have port forwarding active: kubectl port-forward -n mqtt svc/mosquitto 1883:1883")
