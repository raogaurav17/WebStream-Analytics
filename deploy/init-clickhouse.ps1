<#
.SYNOPSIS
    Initializes ClickHouse database and tables for the Web Traffic Analysis system.

.DESCRIPTION
    This script automates the initialization of ClickHouse by:
    - Loading credentials from .env file
    - Discovering the ClickHouse container
    - Waiting for ClickHouse to be ready
    - Creating the required tables for event storage
    - Verifying table creation

.NOTES
    Prerequisites:
    - Docker containers must be running (docker-compose up -d)
    - .env file must be in the deploy directory with CLICKHOUSE_USER and CLICKHOUSE_PASSWORD

.EXAMPLE
    .\init-clickhouse.ps1
#>

Write-Host "Initializing ClickHouse tables..." -ForegroundColor Cyan

# Load environment variables from .env file in the deploy directory
Write-Host "Loading environment variables from .env..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*([^#=]\S*?)\s*=(.*)$') {
            $name = $matches[1]
            $value = $matches[2].Trim('"')
            [System.Environment]::SetEnvironmentVariable($name, $value)
        }
    }
    Write-Host ".env loaded successfully" -ForegroundColor Green
}
else {
    Write-Host "WARNING: .env file not found in current directory" -ForegroundColor Yellow
}

# Retrieve credentials from environment variables
$CLICKHOUSE_USER = [System.Environment]::GetEnvironmentVariable("CLICKHOUSE_USER")
$CLICKHOUSE_PASSWORD = [System.Environment]::GetEnvironmentVariable("CLICKHOUSE_PASSWORD")

# Validate that credentials are available
if (-not $CLICKHOUSE_USER -or -not $CLICKHOUSE_PASSWORD) {
    Write-Host "ERROR: CLICKHOUSE_USER and CLICKHOUSE_PASSWORD not found in .env file or environment" -ForegroundColor Red
    Write-Host "Please ensure .env file exists with:" -ForegroundColor Yellow
    Write-Host "  CLICKHOUSE_USER=default" -ForegroundColor Yellow
    Write-Host "  CLICKHOUSE_PASSWORD=your_password" -ForegroundColor Yellow
    exit 1
}

# Discover ClickHouse container using Docker image filter
Write-Host "Finding ClickHouse container..." -ForegroundColor Yellow
$CH_CONTAINER = docker ps --filter "ancestor=clickhouse/clickhouse-server" --format "{{.Names}}" | Select-Object -First 1

if (-not $CH_CONTAINER) {
    Write-Host "ERROR: ClickHouse container not found. Make sure docker-compose is running." -ForegroundColor Red
    Write-Host "Run: docker-compose up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host "Found container: $CH_CONTAINER" -ForegroundColor Green

# Wait for ClickHouse server to become ready before attempting table creation
Write-Host "Waiting for ClickHouse to be ready..." -ForegroundColor Yellow
$ready = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $result = docker exec $CH_CONTAINER clickhouse-client `
            --user=$CLICKHOUSE_USER `
            --password=$CLICKHOUSE_PASSWORD `
            -q "SELECT 1;" 2>$null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "ClickHouse is ready!" -ForegroundColor Green
            $ready = $true
            break
        }
    }
    catch {
        # Continue to next attempt
    }
    
    Write-Host "Attempt $i/30: Waiting for ClickHouse..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
}

if (-not $ready) {
    Write-Host "ERROR: ClickHouse did not become ready in time" -ForegroundColor Red
    exit 1
}

# Create the events table with MergeTree engine for efficient OLAP queries
# The table is created in the default database for compatibility with Spark JDBC connector
Write-Host "Creating tables in default database..." -ForegroundColor Yellow

$sqlCreateTable = @"
CREATE TABLE IF NOT EXISTS default.events (
    event_id String,
    event_type String,
    user_id String,
    product_id String,
    price Float64,
    timestamp DateTime,
    category String,
    ip_address String
) ENGINE = MergeTree()
ORDER BY (timestamp, event_id)
PARTITION BY toYYYYMM(timestamp)
SETTINGS index_granularity = 8192;
"@

docker exec $CH_CONTAINER clickhouse-client `
    --user=$CLICKHOUSE_USER `
    --password=$CLICKHOUSE_PASSWORD `
    -q $sqlCreateTable

if ($LASTEXITCODE -eq 0) {
    Write-Host "Table created successfully" -ForegroundColor Green
}
else {
    Write-Host "ERROR: Failed to create table" -ForegroundColor Red
    exit 1
}

# Verify the table was created by listing tables in the default database
Write-Host "Verifying tables..." -ForegroundColor Yellow
docker exec $CH_CONTAINER clickhouse-client `
    --user=$CLICKHOUSE_USER `
    --password=$CLICKHOUSE_PASSWORD `
    -q "SHOW TABLES FROM default;"

Write-Host "ClickHouse initialization complete!" -ForegroundColor Green
