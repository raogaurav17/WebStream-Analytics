<# Initialize ClickHouse tables for the streaming pipeline #>

Write-Host "Initializing ClickHouse..." -ForegroundColor Cyan
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
else {
    Write-Host "WARNING: .env not found" -ForegroundColor Yellow
}

$CLICKHOUSE_USER = [System.Environment]::GetEnvironmentVariable("CLICKHOUSE_USER")
$CLICKHOUSE_PASSWORD = [System.Environment]::GetEnvironmentVariable("CLICKHOUSE_PASSWORD")

if (-not $CLICKHOUSE_USER -or -not $CLICKHOUSE_PASSWORD) {
    Write-Host "ERROR: Credentials not found in .env" -ForegroundColor Red
    exit 1
}

Write-Host "Finding ClickHouse container..." -ForegroundColor Yellow

$CH_CONTAINER = docker ps --filter "name=^clickhouse$" --format "{{.Names}}" | Select-Object -First 1

if (-not $CH_CONTAINER) {
    $CH_CONTAINER = docker ps --filter "ancestor=clickhouse/clickhouse-server" --format "{{.Names}}" | Select-Object -First 1
}

if (-not $CH_CONTAINER) {
    Write-Host "ERROR: ClickHouse container not found" -ForegroundColor Red
    exit 1
}

Write-Host "Waiting for ClickHouse..." -ForegroundColor Yellow
$ready = $false
for ($i = 1; $i -le 30; $i++) {
    $ping = docker exec $CH_CONTAINER wget --spider -q http://localhost:8123/ping 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "ClickHouse ready" -ForegroundColor Green
        $ready = $true
        break
    }
    Start-Sleep -Seconds 2
}

if (-not $ready) {
    Write-Host "ERROR: ClickHouse timeout" -ForegroundColor Red
    exit 1
}

Write-Host "Creating events table..." -ForegroundColor Yellow

$sqlCreateTable = @"
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
ORDER BY (timestamp, event_id)
SETTINGS index_granularity = 8192;
"@

docker exec $CH_CONTAINER clickhouse-client `
    --user=$CLICKHOUSE_USER `
    --password=$CLICKHOUSE_PASSWORD `
    --query=$sqlCreateTable

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create table" -ForegroundColor Red
    exit 1
}

Write-Host "Verifying tables..." -ForegroundColor Yellow
docker exec $CH_CONTAINER clickhouse-client `
    --user=$CLICKHOUSE_USER `
    --password=$CLICKHOUSE_PASSWORD `
    --query="SHOW TABLES FROM default;"

Write-Host "Done" -ForegroundColor Green