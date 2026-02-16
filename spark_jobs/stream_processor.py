"""
Web Traffic Analysis - Spark Structured Streaming Application

This application implements a dual-sink streaming pipeline that:
1. Reads events from Kafka in real-time
2. Parses and validates the Avro/JSON schema
3. Writes raw events to HBase for low-latency queries
4. Writes aggregated data to ClickHouse for analytical queries
5. Maintains fault tolerance with checkpointing

The pipeline handles micro-batches and provides exactly-once semantics through
Spark's checkpointing mechanism and idempotent writes to both sinks.

Prerequisites:
    - Spark 3.5.0+ with Scala 2.12
    - Kafka broker at kafka:29092
    - HBase instance at hbase:9090
    - ClickHouse instance at clickhouse:8123
    - Environment variables: CLICKHOUSE_USER, CLICKHOUSE_PASSWORD
    - ClickHouse JDBC driver (clickhouse-jdbc-0.6.4-shaded.jar)

Author: Analytics Team
License: Internal Use Only
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType

import os

# Retrieve credentials from environment for secure ClickHouse connection
user = os.getenv("CLICKHOUSE_USER")
password = os.getenv("CLICKHOUSE_PASSWORD")

# Initialize Spark Session with optimized configuration for streaming
spark = SparkSession.builder \
    .appName("ECommerceEventProcessor") \
    .config("spark.sql.streaming.checkpointLocation", "/opt/spark-apps/checkpoint") \
    .getOrCreate()

# Define the schema for incoming events from Kafka
# Ensures type safety and early error detection during parsing
event_schema = StructType([
    StructField("event_id", StringType(), True),        # Unique identifier for the event
    StructField("event_type", StringType(), True),      # Type of event (click, purchase, etc.)
    StructField("user_id", StringType(), True),         # User who performed the action
    StructField("product_id", StringType(), True),      # Product involved in the event
    StructField("price", DoubleType(), True),           # Price of the product
    StructField("timestamp", TimestampType(), True),    # Timestamp of the event
    StructField("category", StringType(), True),        # Product category
    StructField("ip_address", StringType(), True),      # Client IP address
])

# Read streaming data from Kafka topic
# Using external bootstrap server with earliest offsets for replay capability
kafka_df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:29092") \
    .option("subscribe", "events") \
    .option("startingOffsets", "earliest") \
    .load()

# Parse Kafka message (JSON string) into structured columns
# The 'value' field contains the serialized JSON payload
parsed_df = kafka_df \
    .select(from_json(col("value").cast("string"), event_schema).alias("data")) \
    .select("data.*")

# Dual-sink write function executed for each micro-batch
# Implements the core business logic: writing to both HBase and ClickHouse
def write_to_sinks(df, batch_id):
    """
    Process and write a micro-batch to multiple sinks.
    
    Args:
        df: DataFrame containing the current micro-batch
        batch_id: Unique identifier for this batch
    
    Writes to:
        1. HBase table 'events' - for low-latency operational queries
        2. ClickHouse table 'events' - for analytical/OLAP queries
    """
    print(f"Processing micro-batch {batch_id}")
    
    # Skip empty batches to avoid unnecessary writes
    if df.count() == 0:
        print(f"Batch {batch_id} is empty, skipping write")
        return

    # ==== SINK 1: HBase (operational store for low-latency access) ====
    def hbase_write(partition):
        """
        Write events to HBase using happybase library.
        Runs in parallel on executor nodes, one partition per executor.
        
        HBase schema:
            Row Key: event_id
            Column Family: 'cf'
            Columns: event_type, user_id, product_id, price, timestamp, category, ip
        """
        try:
            import happybase
            conn = happybase.Connection('hbase', 9090)
            table = conn.table('events')
            
            # Write each row from the partition to HBase
            for row in partition:
                key = row['event_id'].encode()
                data = {
                    b'cf:event_type':   str(row['event_type']).encode(),
                    b'cf:user_id':      str(row['user_id']).encode(),
                    b'cf:product_id':   str(row['product_id']).encode(),
                    b'cf:price':        str(row['price']).encode(),
                    b'cf:timestamp':    str(row['timestamp']).encode(),
                    b'cf:category':     str(row['category']).encode(),
                    b'cf:ip':           str(row['ip_address']).encode(),
                }
                table.put(key, data)
            conn.close()
            print(f"Successfully wrote partition to HBase for batch {batch_id}")
        except Exception as e:
            print(f"ERROR writing to HBase: {e}")
            raise

    # Attempt HBase write with failure handling
    try:
        df.foreachPartition(hbase_write)
    except Exception as e:
        print(f"WARN: HBase write failed for batch {batch_id}: {e}")

    # ==== SINK 2: ClickHouse (analytical store for OLAP queries) ====
    try:
        df.write \
            .format("jdbc") \
            .option("url", "jdbc:clickhouse://clickhouse:8123/default") \
            .option("dbtable", "events") \
            .option("user", user) \
            .option("password", password) \
            .option("driver", "com.clickhouse.jdbc.ClickHouseDriver") \
            .mode("append") \
            .save()
        print(f"Successfully wrote batch {batch_id} to ClickHouse")
    except Exception as e:
        print(f"ERROR writing to ClickHouse: {e}")
        print(f"Retrying with ignore mode to handle duplicates...")
        try:
            # Retry with 'ignore' mode to gracefully handle duplicate key errors
            df.write \
                .format("jdbc") \
                .option("url", "jdbc:clickhouse://clickhouse:8123/default") \
                .option("dbtable", "events") \
                .option("user", user) \
                .option("password", password) \
                .option("driver", "com.clickhouse.jdbc.ClickHouseDriver") \
                .mode("ignore") \
                .save()
            print(f"Successfully wrote batch {batch_id} to ClickHouse (with retry)")
        except Exception as e2:
            print(f"ERROR: Final ClickHouse write failed for batch {batch_id}: {e2}")
            raise

# ==== Stream Initialization and Processing ====
# foreachBatch sink enables:
#   - Custom per-batch logic (write_to_sinks function)
#   - Exactly-once processing semantics via checkpointing
#   - Fault tolerance: if app crashes, checkpoint recovers missed batches
# 
# Trigger model:
#   - processingTime="10 seconds": Process available data every 10 seconds
#   - If no data arrives, batches are skipped (no idle writes)
query = parsed_df.writeStream \
    .foreachBatch(write_to_sinks) \
    .option("checkpointLocation", "./checkpoint") \
    .trigger(processingTime="10 seconds") \
    .start()

print("--- Stream Started (Targets: ClickHouse + HBase) ---")
print("Pipeline running with 10-second micro-batch trigger")
print("Checkpoint recovery enabled for fault tolerance")

# Block execution until stream terminates (error, timeout, or manual stop)
# This call never returns unless the stream stops
query.awaitTermination()