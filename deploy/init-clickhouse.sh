#!/bin/bash
# Initialize ClickHouse tables for the streaming pipeline

set -e

echo -e "\033[36mInitializing ClickHouse...\033[0m"
echo -e "\033[33mLoading .env...\033[0m"

# Load .env file
if [ -f ".env" ]; then
    export $(cat .env | sed 's/#.*//' | grep '^\s*[^=]\+=' | xargs)
else
    echo -e "\033[33mWARNING: .env not found\033[0m"
fi

# Get credentials
CLICKHOUSE_USER=${CLICKHOUSE_USER:-}
CLICKHOUSE_PASSWORD=${CLICKHOUSE_PASSWORD:-}

if [ -z "$CLICKHOUSE_USER" ] || [ -z "$CLICKHOUSE_PASSWORD" ]; then
    echo -e "\033[31mERROR: Credentials not found in .env\033[0m"
    exit 1
fi

echo -e "\033[33mFinding ClickHouse container...\033[0m"

# Find ClickHouse container
CH_CONTAINER=$(docker ps --filter "name=^clickhouse$" --format "{{.Names}}" 2>/dev/null | head -n 1)

if [ -z "$CH_CONTAINER" ]; then
    CH_CONTAINER=$(docker ps --filter "ancestor=clickhouse/clickhouse-server" --format "{{.Names}}" 2>/dev/null | head -n 1)
fi

if [ -z "$CH_CONTAINER" ]; then
    echo -e "\033[31mERROR: ClickHouse container not found\033[0m"
    exit 1
fi

echo -e "\033[33mWaiting for ClickHouse...\033[0m"
READY=false
for i in {1..30}; do
    if docker exec "$CH_CONTAINER" wget --spider -q http://localhost:8123/ping 2>/dev/null; then
        echo -e "\033[32mClickHouse ready\033[0m"
        READY=true
        break
    fi
    sleep 2
done

if [ "$READY" != true ]; then
    echo -e "\033[31mERROR: ClickHouse timeout\033[0m"
    exit 1
fi

echo -e "\033[33mCreating events table...\033[0m"

SQL_CREATE_TABLE="
CREATE TABLE IF NOT EXISTS default.events
(
    event_id    String,
    event_type  String,
    user_id     String,
    product_id  String,
    price       Float64,
    timestamp   DateTime,
    category    String,
    ip_address  String
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, user_id)
SETTINGS index_granularity = 8192;
"

docker exec "$CH_CONTAINER" clickhouse-client \
    --user="$CLICKHOUSE_USER" \
    --password="$CLICKHOUSE_PASSWORD" \
    --query="$SQL_CREATE_TABLE"

if [ $? -ne 0 ]; then
    echo -e "\033[31mERROR: Failed to create table\033[0m"
    exit 1
fi

echo -e "\033[33mVerifying tables...\033[0m"
docker exec "$CH_CONTAINER" clickhouse-client \
    --user="$CLICKHOUSE_USER" \
    --password="$CLICKHOUSE_PASSWORD" \
    --query="SHOW TABLES FROM default;"

echo -e "\033[32mDone\033[0m"
