#!/usr/bin/env python3
"""E-Commerce Event Producer - generates synthetic events to Kafka."""

from kafka import KafkaProducer
from kafka.errors import KafkaError
import time
import json
import random
import uuid
from datetime import datetime
import argparse
import os
import sys

EVENT_WEIGHTS = {
    "view": 0.60,
    "click": 0.20,
    "add_to_cart": 0.15,
    "purchase": 0.05
}

CATEGORIES = ["electronics", "clothing", "furniture", "food", "books", "sports"]

PRICE_RANGES = {
    "electronics": (50.0, 1500.0),
    "clothing": (15.0, 200.0),
    "furniture": (100.0, 2500.0),
    "food": (5.0, 50.0),
    "books": (8.0, 35.0),
    "sports": (20.0, 500.0)
}

def generate_event(user_id, event_type=None):
    """Generate a single e-commerce event."""
    category = random.choice(CATEGORIES)
    product_id = f"p_{random.randint(1, 500)}"
    
    if event_type is None:
        event_type = random.choices(
            list(EVENT_WEIGHTS.keys()),
            weights=list(EVENT_WEIGHTS.values())
        )[0]
    
    min_price, max_price = PRICE_RANGES[category]
    price = round(random.uniform(min_price, max_price), 2)
    
    ip_address = f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"
    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "user_id": user_id,
        "product_id": product_id,
        "price": price,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "category": category,
        "ip_address": ip_address
    }
    
    return event

def main():
    parser = argparse.ArgumentParser(description="E-Commerce Event Producer")
    parser.add_argument("--broker", default=None, help="Kafka broker address (auto-detected if in Docker)")
    parser.add_argument("--rate", type=int, default=5, help="Events per second")
    parser.add_argument("--users", type=int, default=100, help="Number of concurrent users")
    args = parser.parse_args()
    
    # Auto-detect Docker environment
    if args.broker is None:
        in_docker = os.path.exists("/.dockerenv")
        args.broker = "kafka:29092" if in_docker else "localhost:9092"
    
    try:
        producer = KafkaProducer(
            bootstrap_servers=args.broker,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks='all',
            retries=5,
            max_in_flight_requests_per_connection=1
        )
    except Exception as e:
        print(f"❌ Failed to connect to Kafka at {args.broker}")
        print(f"   Error: {str(e)}")
        print(f"   Make sure Kafka is running and accessible")
        sys.exit(1)
    
    print(f"---E-Commerce Event Producer Started---")
    print(f"   Broker: {args.broker}")
    print(f"   Rate: {args.rate} events/sec")
    print(f"   Active Users: {args.users}")
    print(f"   Topic: 'events'")
    print("")
    
    event_count = 0
    interval = 1.0 / args.rate
    
    try:
        while True:
            user_id = f"u_{random.randint(1, args.users)}"
            event = generate_event(user_id)
            future = producer.send("events", event)
            
            try:
                future.get(timeout=5)
            except KafkaError as e:
                print(f"⚠️  Failed to send event: {str(e)[:80]}")
            
            event_count += 1
            
            if event_count % 100 == 0:
                print(f"✓ {event_count} events sent | Latest: {event['event_type']} by {event['user_id']}")
            
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print(f"\n---Producer stopped---")
        print(f"Total events sent: {event_count}")
        producer.flush(timeout=10)
        producer.close()

if __name__ == "__main__":
    main()
