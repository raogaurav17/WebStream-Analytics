#!/bin/bash
# Web Traffic Analysis - Spark streaming pipeline orchestration

set -e

echo -e "\033[36mWeb Traffic Analysis Pipeline\033[0m"

cd "$(dirname "$0")/deploy"

# Load .env file
echo -e "\033[33mLoading .env...\033[0m"
if [ -f ".env" ]; then
    export $(cat .env | sed 's/#.*//' | grep '^\s*[^=]\+=' | xargs)
fi

# Initialize ClickHouse
echo -e "\033[36mInitializing ClickHouse...\033[0m"
if [ -f "init-clickhouse.sh" ]; then
    bash ./init-clickhouse.sh
    if [ $? -ne 0 ]; then
        echo -e "\033[31mERROR: ClickHouse initialization failed\033[0m"
        exit 1
    fi
fi

cd ..

# Start Event Producer
echo -e "\033[36mStarting Event Producer...\033[0m"
docker exec -d spark-master python3 /opt/spark-apps/log_producer.py --rate 5 --users 100 || true

# Stop any previous Spark jobs
echo -e "\033[33mStopping any previous Spark jobs...\033[0m"
docker exec spark-master bash -c "pkill -f stream_processor.py; sleep 2" 2>/dev/null || true
echo -e "\033[32mDone\033[0m"

# Submit Spark Job
echo -e "\033[36mSubmitting Spark Job...\033[0m"

IVY_FIX="-Divy.home=/opt/spark/.ivy -Divy.cache.dir=/opt/spark/.ivy/cache"
JAVA_OPTS="spark.driver.extraJavaOptions=$IVY_FIX"
PACKAGES="org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0"

docker exec spark-master /opt/spark/bin/spark-submit \
    --master "local[*]" \
    --deploy-mode client \
    --conf "$JAVA_OPTS" \
    --packages "$PACKAGES" \
    --jars /opt/spark-apps/clickhouse-jdbc-0.6.4-shaded.jar \
    /opt/spark-apps/stream_processor.py 2>&1 | tee spark_job.log

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\033[32mSpark job completed successfully\033[0m"
else
    echo -e "\033[31mERROR: Spark job failed with exit code $EXIT_CODE\033[0m"
fi

exit $EXIT_CODE
