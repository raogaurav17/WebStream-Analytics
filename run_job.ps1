<#
.SYNOPSIS
    Orchestrates the entire Web Traffic Analysis pipeline.

.DESCRIPTION
    This script is the main entry point for the Web Traffic Analysis system. It:
    - Loads configuration from .env file
    - Initializes ClickHouse database and tables
    - Submits the Spark Streaming job to the cluster
    - Monitors the job execution

.PREREQUISITES
    - Docker and Docker Compose running with all services up
    - .env file in deploy/ directory with credentials
    - Spark cluster accessible at spark-master:7077
    - ClickHouse, Kafka, and other services initialized

.EXAMPLE
    .\run_job.ps1

.NOTES
    The script requires administrative privileges for Docker access.
#>

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Web Traffic Analysis - Spark Job" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to deploy directory for accessing infrastructure scripts and .env file
Push-Location $PSScriptRoot\deploy

# Load configuration from .env file into environment variables
Write-Host "Loading environment variables from .env..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*([^#=]\S*?)\s*=(.*)$') {
            $name = $matches[1]
            $value = $matches[2].Trim('"')
            [System.Environment]::SetEnvironmentVariable($name, $value)
        }
    }
} else {
    Write-Host "WARNING: .env file not found in deploy directory" -ForegroundColor Yellow
}

# Initialize ClickHouse database schema and tables before starting Spark job
Write-Host ""
Write-Host "Initializing ClickHouse..." -ForegroundColor Cyan
if (Test-Path "init-clickhouse.ps1") {
    & .\init-clickhouse.ps1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: ClickHouse initialization failed" -ForegroundColor Red
        Pop-Location
        exit 1
    }
} else {
    Write-Host "WARNING: init-clickhouse.ps1 not found, skipping ClickHouse initialization" -ForegroundColor Yellow
}

Pop-Location

Write-Host ""
Write-Host "Submitting Hybrid Spark Job to Cluster..." -ForegroundColor Cyan

# Configure Spark with ClickHouse JDBC driver and fix Ivy cache settings
$jar = "clickhouse-jdbc-0.6.4-shaded.jar"
$ivyFix = "-Divy.home=/opt/spark/.ivy -Divy.cache.dir=/opt/spark/.ivy/cache"

# Submit the Spark Streaming job to the standalone cluster
docker exec spark-master `
    /opt/spark/bin/spark-submit `
    --master spark://spark-master:7077 `
    --deploy-mode client `
    --conf "spark.driver.extraJavaOptions=$ivyFix" `
    --conf "spark.executor.extraJavaOptions=$ivyFix" `
    --jars /opt/spark-apps/$jar `
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 `
    /opt/spark-apps/stream_processor.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Spark job completed successfully" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "ERROR: Spark job failed with exit code $LASTEXITCODE" -ForegroundColor Red
}

exit $LASTEXITCODE