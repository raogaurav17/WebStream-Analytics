<# Web Traffic Analysis - Spark streaming pipeline orchestration #>

Write-Host "Web Traffic Analysis Pipeline" -ForegroundColor Cyan
Push-Location $PSScriptRoot\deploy

Write-Host "Loading .env..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*([^#=]\S*?)\s*=(.*)$') {
            $name = $matches[1]
            $value = $matches[2].Trim('"')
            [System.Environment]::SetEnvironmentVariable($name, $value)
        }
    }
}

Write-Host "Initializing ClickHouse..." -ForegroundColor Cyan
if (Test-Path "init-clickhouse.ps1") {
    & .\init-clickhouse.ps1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: ClickHouse initialization failed" -ForegroundColor Red
        Pop-Location
        exit 1
    }
}

Pop-Location

Write-Host "Starting Event Producer..." -ForegroundColor Cyan
docker exec -d spark-master python3 /opt/spark-apps/log_producer.py --rate 5 --users 100

Write-Host "Stopping any previous Spark jobs..." -ForegroundColor Yellow
docker exec spark-master bash -c "pkill -f stream_processor.py; sleep 2" 2>$null
Write-Host "Done" -ForegroundColor Green

Write-Host "Submitting Spark Job..." -ForegroundColor Cyan

$ivyFix = "-Divy.home=/opt/spark/.ivy -Divy.cache.dir=/opt/spark/.ivy/cache"
$javaOpts = "spark.driver.extraJavaOptions=$ivyFix"
$packages = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0"

docker exec spark-master /opt/spark/bin/spark-submit `
    --master "local[*]" `
    --deploy-mode client `
    --conf $javaOpts `
    --packages $packages `
    --jars /opt/spark-apps/clickhouse-jdbc-0.6.4-shaded.jar `
    /opt/spark-apps/stream_processor.py 2>&1 | Tee-Object -FilePath spark_job.log

if ($LASTEXITCODE -eq 0) {
    Write-Host "Spark job completed successfully" -ForegroundColor Green
}
else {
    Write-Host "ERROR: Spark job failed with exit code $LASTEXITCODE" -ForegroundColor Red
}

exit $LASTEXITCODE