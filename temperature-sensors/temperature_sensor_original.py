#!/usr/bin/env python3
"""
Temperature Sensor Simulator

A simple Python application that simulates a temperature sensor by generating
random temperature readings at regular intervals.
"""

import random
import time
from datetime import datetime
import argparse


class TemperatureSensor:
    """Simulates a temperature sensor with configurable parameters."""
    
    def __init__(self, min_temp=18.0, max_temp=35.0, interval=2.0, variance=1.0):
        """
        Initialize the temperature sensor.
        
        Args:
            min_temp (float): Minimum temperature in Celsius
            max_temp (float): Maximum temperature in Celsius
            interval (float): Time interval between readings in seconds
            variance (float): Maximum temperature change between readings
        """
        self.min_temp = min_temp
        self.max_temp = max_temp
        self.interval = interval
        self.variance = variance
        self.current_temp = random.uniform(min_temp, max_temp)
        self.reading_count = 0
    
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
        return f"[{timestamp}] Reading #{self.reading_count:04d}: {temperature:6.2f}°C"
    
    def run(self, duration=None):
        """
        Run the temperature sensor simulation.
        
        Args:
            duration (float, optional): Duration to run in seconds. If None, runs indefinitely.
        """
        print("🌡️  Temperature Sensor Simulator Starting...")
        print(f"   Temperature range: {self.min_temp}°C to {self.max_temp}°C")
        print(f"   Reading interval: {self.interval} seconds")
        print(f"   Press Ctrl+C to stop\n")
        
        start_time = time.time()
        
        try:
            while True:
                # Check duration limit
                if duration and (time.time() - start_time) >= duration:
                    break
                
                # Get and display temperature reading
                temperature = self.get_temperature_reading()
                print(self.format_reading(temperature))
                
                # Wait for next reading
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            print(f"\n\n🛑 Sensor simulation stopped after {self.reading_count} readings.")
            print("Thank you for using the Temperature Sensor Simulator!")


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description="Temperature Sensor Simulator - Generate random temperature readings"
    )
    
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
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.min_temp >= args.max_temp:
        print("Error: min-temp must be less than max-temp")
        return 1
    
    if args.interval <= 0:
        print("Error: interval must be positive")
        return 1
    
    # Create and run sensor
    sensor = TemperatureSensor(
        min_temp=args.min_temp,
        max_temp=args.max_temp,
        interval=args.interval,
        variance=args.variance
    )
    
    sensor.run(duration=args.duration)
    return 0


if __name__ == "__main__":
    exit(main())
