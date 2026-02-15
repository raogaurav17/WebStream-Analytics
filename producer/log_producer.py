from kafka import KafkaProducer
import time, json, random

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

urls = ["/", "/login", "/api", "/products", "/cart"]
statuses = [200, 200, 200, 404, 500]

print("Sending logs to Kafka...")

while True:
    event = {
        "ip": f"192.168.1.{random.randint(1,255)}",
        "url": random.choice(urls),
        "status": random.choice(statuses),
        "ts": time.time()
    }
    producer.send("weblogs", event)
    print(event)
    time.sleep(0.2)
