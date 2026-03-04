<# Reset ClickHouse data and reinitialize #>

Write-Host "WARNING: This will delete all ClickHouse data!" -ForegroundColor Red
Write-Host "Waiting 10 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "Stopping..." -ForegroundColor Cyan
docker-compose down

Write-Host "Removing volume..." -ForegroundColor Cyan
docker volume rm clickhouse_data -f

Write-Host "Starting..." -ForegroundColor Cyan
docker-compose up -d

Start-Sleep -Seconds 15

& .\init-clickhouse.ps1Write-Host "Reset complete" -ForegroundColor Green
