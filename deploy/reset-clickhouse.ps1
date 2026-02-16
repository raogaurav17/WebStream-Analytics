# PowerShell script to reset ClickHouse data and reinitialize tables
# Use this if ClickHouse is in an inconsistent state

Write-Host "WARNING: This script will delete all ClickHouse data!" -ForegroundColor Red
Write-Host "Press Ctrl+C to cancel, or wait 10 seconds to continue..." -ForegroundColor Yellow

Start-Sleep -Seconds 10

Write-Host "Stopping Docker containers..." -ForegroundColor Cyan
docker-compose down

Write-Host "Removing ClickHouse data volume..." -ForegroundColor Cyan
docker volume rm clickhouse_data -f

Write-Host "Starting Docker containers..." -ForegroundColor Cyan
docker-compose up -d

Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host "Running ClickHouse initialization..." -ForegroundColor Cyan
& .\init-clickhouse.ps1

Write-Host "ClickHouse reset complete!" -ForegroundColor Green
