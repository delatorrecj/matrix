<#
.SYNOPSIS
    Starts the complete MATRIX application stack locally on Windows PowerShell.
.DESCRIPTION
    1. Checks if ports 3000 and 8000 are already in use and frees them cleanly.
    2. Launches Backend API Server (FastAPI) on http://localhost:8000.
    3. Launches Frontend Web Application (Next.js) on http://localhost:3000.
#>

$root = $PSScriptRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "         MATRIX Urban Impact Simulator Launcher           " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

function Free-Port([int]$Port) {
    $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($connections) {
        foreach ($c in $connections) {
            $pidToKill = $c.OwningProcess
            if ($pidToKill -and $pidToKill -ne 0 -and $pidToKill -ne 4) {
                Write-Host "Freeing port $Port (stopping existing process PID $pidToKill)..." -ForegroundColor Yellow
                Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
            }
        }
        Start-Sleep -Seconds 1
    }
}

Write-Host "Checking and clearing ports 8000 and 3000..." -ForegroundColor Gray
Free-Port 8000
Free-Port 3000

Write-Host "[1/2] Launching Backend API Server (http://localhost:8000)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\app\apps\api'; uv run uvicorn matrix_api.main:app --host 0.0.0.0 --port 8000 --reload"

Write-Host "[2/2] Launching Frontend Web App (http://localhost:3000)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\app\apps\web'; npm run dev -- -p 3000"

Write-Host ""
Write-Host "Stack started successfully!" -ForegroundColor Cyan
Write-Host "  -> Web App UI:       http://localhost:3000" -ForegroundColor White
Write-Host "  -> API & WS Gateway: http://localhost:8000" -ForegroundColor White
Write-Host "  -> API Swagger Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
