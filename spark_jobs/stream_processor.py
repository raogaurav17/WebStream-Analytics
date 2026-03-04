"""E-Commerce Streaming Analytics - Kafka to ClickHouse via Spark."""

from pyspark import SparkConf
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType

import os
import urllib.request
import urllib.parse
import json

CLICKHOUSE_USER     = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "clickhouse")
CLICKHOUSE_HOST     = "clickhouse"
CLICKHOUSE_PORT     = "8123"
CLICKHOUSE_DB       = "default"
CLICKHOUSE_TABLE    = "events"

conf = SparkConf()
conf.set("spark.sql.streaming.checkpointLocation", "/opt/spark-apps/checkpoint_v2")

spark = SparkSession.builder \
    .appName("ECommerceEventProcessor") \
    .config(conf=conf) \
    .getOrCreate()

spark.sparkContext.setLogLevel("INFO")

event_schema = StructType([
    StructField("event_id",   StringType(),    True),
    StructField("event_type", StringType(),    True),
    StructField("user_id",    StringType(),    True),
    StructField("product_id", StringType(),    True),
    StructField("price",      DoubleType(),    True),
    StructField("timestamp",  TimestampType(), True),
    StructField("category",   StringType(),    True),
    StructField("ip_address", StringType(),    True),
])

print("Connecting to Kafka at kafka:29092...")
kafka_df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:29092") \
    .option("subscribe", "events") \
    .option("startingOffsets", "earliest") \
    .option("failOnDataLoss", "false") \
    .option("maxOffsetsFetchPerPartition", 10000) \
    .load()

print("Parsing event schema...")

enriched_df = kafka_df \
    .select(from_json(col("value").cast("string"), event_schema).alias("data")) \
    .select("data.*")

def write_partition_to_clickhouse(rows):
    """Write rows to ClickHouse via HTTP API."""
    rows = list(rows)
    if not rows:
        return

    lines = []
    for row in rows:
        record = {
            "event_id":   row.event_id   or "",
            "event_type": row.event_type or "",
            "user_id":    row.user_id    or "",
            "product_id": row.product_id or "",
            "price":      row.price      if row.price is not None else 0.0,
            "timestamp":  row.timestamp.strftime("%Y-%m-%d %H:%M:%S") if row.timestamp else "1970-01-01 00:00:00",
            "category":   row.category   or "",
            "ip_address": row.ip_address or "",
        }
        lines.append(json.dumps(record))

    payload = "\n".join(lines).encode("utf-8")

    query = f"INSERT INTO {CLICKHOUSE_DB}.{CLICKHOUSE_TABLE} FORMAT JSONEachRow"
    params = urllib.parse.urlencode({"query": query})
    url = f"http://{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/?{params}"

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-ClickHouse-User", CLICKHOUSE_USER)
    req.add_header("X-ClickHouse-Key", CLICKHOUSE_PASSWORD)

    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()

def write_to_sinks(batch_df, batch_id):
    """Process micro-batch and write to ClickHouse."""

    if batch_df.count() == 0:
        return

    row_count = batch_df.count()
    try:
        batch_df.foreachPartition(write_partition_to_clickhouse)
        print(f"Batch {batch_id}: {row_count} rows written")
    except Exception as e:
        print(f"Write failed: {str(e)[:500]}")

print("\nStarting streaming pipeline...")
print(f"Kafka topic: events") 
print(f"ClickHouse: http://{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}")

query = enriched_df.writeStream \
    .foreachBatch(write_to_sinks) \
    .option("checkpointLocation", "/opt/spark-apps/checkpoint_v2") \
    .trigger(processingTime="10 seconds") \
    .start()

print("Streaming pipeline started")

query.awaitTermination()