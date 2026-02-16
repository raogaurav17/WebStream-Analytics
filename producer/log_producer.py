#!/usr/bin/env python3
"""
Web Traffic Log Producer for Kafka

Purpose:
    Generates synthetic web server events and publishes them to Kafka.
    Serves as the event source for the Spark streaming pipeline.

Usage:
    python log_producer.py

Output Topic:
    Topic Name: 'weblogs'
    Message Format: JSON object containing IP, URL path, HTTP status, timestamp
    
Prerequisites:
    - Kafka broker running at localhost:9092
    - 'weblogs' topic must exist or auto-create enabled
    - kafka-python library installed

Event Schema:
    {
        "ip": "192.168.x.x" (simulated client IP),
        "url": one of ["/", "/login", "/api", "/products", "/cart"],
        "status": one of [200, 200, 200, 404, 500] (weighted to 200),
        "ts": float (Unix timestamp)
    }
"""

from kafka import KafkaProducer
import time
import json
import random

# Initialize Kafka producer - this will create the connection to the broker
# Note: In production, consider adding retries, timeouts, and error handling
producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# Simulated pool of website URLs (realistic web application endpoints)
urls = ["/", "/login", "/api", "/products", "/cart"]

# HTTP status codes with weighted distribution (200 is most common)
# In reality, 200 appears 3/5 times, 404 and 500 each appear 1/5 times
statuses = [200, 200, 200, 404, 500]

print("Sending logs to Kafka...")
print("Connecting to broker at localhost:9092, topic: 'weblogs'")

# Infinite event generation loop - runs continuously until manually stopped
while True:
    # Create a simulated web server event
    event = {
        # Simulated client IP (192.168.1.1 - 192.168.1.255)
        "ip": f"192.168.1.{random.randint(1, 255)}",
        
        # Random endpoint hit by the client
        "url": random.choice(urls),
        
        # Random HTTP response status (weighted towards success)
        "status": random.choice(statuses),
        
        # Current timestamp in Unix epoch format
        "ts": time.time()
    }
    
    # Send event to Kafka broker
    # Kafka assigns partition based on message key (None here = round-robin)
    producer.send("weblogs", event)
    
    # Print to stdout for visibility
    print(event)
    
    # Generate one event every 200ms (5 events/second)
    # Adjust this to simulate higher/lower traffic rates
    time.sleep(0.2)
