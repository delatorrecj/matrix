# MATRIX simulate-up: Docker + SUMO baseline + warmed API + Web.
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")).Path
$AppRoot = Join-Path $RepoRoot "app"
$ApiDir = Join-Path $AppRoot "apps\api"
$WebDir = Join-Path $AppRoot "apps\web"
$KernelDir = Join-Path $AppRoot "packages\kernel"
$ApiLog = Join-Path $env:TEMP "matrix-simulate-api.log"
$WebLog = Join-Path $env:TEMP "matrix-simulate-web.log"
$BaselineLog = Join-Path $env:TEMP "matrix-simulate-baseline.log"
$TimeoutSec = 60
$WarmTimeoutSec = 180
$BaselineKey = if ($env:MATRIX_CITY_SLUG) { "baseline:$($env:MATRIX_CITY_SLUG):latest" } else { "baseline:iloilo:latest" }

function Test-Port([int]$port) {
    try {
        $c = [System.Net.Sockets.TcpClient]::new()
        $ar = $c.BeginConnect("127.0.0.1", $port, $null, $null)
        $ok = $ar.AsyncWaitHandle.WaitOne(800, $false) -and $c.Connected
        $c.Close()
        return $ok
    } catch { return $false }
}

function Test-DockerUp { return (Test-Port 5432) -and (Test-Port 6379) }

function Test-ApiUp {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 2
        return ($null -ne $r.StatusCode)
    } catch { return $false }
}

function Test-WebUp {
    try {
        $null = Invoke-WebRequest -Uri "http://127.0.0.1:3000" -UseBasicParsing -TimeoutSec 2
        return $true
    } catch {
        if ($_.Exception.Response) { return $true }
        return $false
    }
}

function Test-Baseline {
    try {
        $out = (docker exec matrix-redis redis-cli EXISTS $BaselineKey 2>$null | Out-String).Trim()
        return ($out -eq "1")
    } catch { return $false }
}

function Start-Logged([string]$workdir, [string]$cmdline, [string]$log) {
    if (Test-Path $log) { Remove-Item $log -Force }
    $inner = "cd /d `"$workdir`" && $cmdline > `"$log`" 2>&1"
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $inner -WindowStyle Hidden | Out-Null
}

function Start-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "docker not on PATH" }
    Push-Location $AppRoot
    try {
        docker compose up -d
        if ($LASTEXITCODE -ne 0) { throw "docker compose up -d failed (exit $LASTEXITCODE)" }
    } finally { Pop-Location }
}

function Ensure-Baseline {
    if (Test-Baseline) { return "up" }
    Write-Host "BASELINE  seeding SUMO -> Redis ($BaselineKey) ..."
    if (Test-Path $BaselineLog) { Remove-Item $BaselineLog -Force }
    $py = if (Get-Command uv -ErrorAction SilentlyContinue) {
        "uv run python -c `"from matrix_kernel.baseline import run_nightly_baseline; print(run_nightly_baseline())`""
    } else {
        "python -c `"from matrix_kernel.baseline import run_nightly_baseline; print(run_nightly_baseline())`""
    }
    Push-Location $KernelDir
    try {
        cmd /c "$py > `"$BaselineLog`" 2>&1"
        if ($LASTEXITCODE -ne 0) { throw "run_nightly_baseline failed (exit $LASTEXITCODE)" }
    } finally { Pop-Location }
    if (-not (Test-Baseline)) { throw "baseline key missing after seed: $BaselineKey" }
    return "started"
}

function Start-Api {
    # Full warm: personas + GraphRAG + validation reports (needs Redis/Chroma).
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        $cmd = "uv run python -m uvicorn matrix_api.main:app --reload --host 127.0.0.1 --port 8000"
    } else {
        $cmd = "python -m uvicorn matrix_api.main:app --reload --host 127.0.0.1 --port 8000"
    }
    Start-Logged $ApiDir $cmd $ApiLog
}

function Stop-Port([int]$port) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_.OwningProcess -gt 0) {
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}

function Stop-WebDev {
    Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object {
        $_.CommandLine -and ($_.CommandLine -match 'next') -and ($_.CommandLine -match 'apps\\web')
    } | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Stop-Port 3000
    Stop-Port 3001
}

function Start-Web {
    if (-not (Test-Path (Join-Path $WebDir "node_modules"))) {
        Write-Host "WEB  installing node_modules..."
        & npm.cmd install --prefix $WebDir
        if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
    }
    # One Next per .next dir. A leftover :3000 makes `next dev` hop to :3001 and tear chunks.
    Stop-WebDev
    Start-Sleep -Milliseconds 400
    Start-Logged $WebDir "npm.cmd run dev" $WebLog
}

function Show-Tail([string]$path, [string]$label) {
    if (-not (Test-Path $path)) { Write-Host "$label  (no log at $path)"; return }
    Write-Host "--- $label log (tail) ---"
    Get-Content $path -Tail 40 -ErrorAction SilentlyContinue
}

$dockerWasUp = Test-DockerUp
if (-not $dockerWasUp) { Start-Docker }

$t = (Get-Date).AddSeconds($TimeoutSec)
while ((Get-Date) -lt $t) { if (Test-DockerUp) { break }; Start-Sleep -Milliseconds 500 }
$dockerOk = Test-DockerUp
$dockerStatus = if (-not $dockerOk) { "failed" } elseif ($dockerWasUp) { "up" } else { "started" }

$baselineStatus = "failed"
if ($dockerOk) {
    try {
        $baselineStatus = Ensure-Baseline
    } catch {
        Write-Host "BASELINE error: $_"
        Show-Tail $BaselineLog "BASELINE"
        $baselineStatus = "failed"
    }
}

$apiWasUp = Test-ApiUp
$webWasUp = Test-WebUp
if ($dockerOk -and $baselineStatus -ne "failed") {
    if (-not $apiWasUp) { Start-Api }
    if (-not $webWasUp) { Start-Web }
}

$t = (Get-Date).AddSeconds($WarmTimeoutSec)
while ((Get-Date) -lt $t) {
    if ($baselineStatus -eq "failed") { break }
    if ((Test-ApiUp) -and (Test-WebUp)) { break }
    Start-Sleep -Milliseconds 500
}

$apiOk = Test-ApiUp
$webOk = Test-WebUp
$apiStatus = if (-not $apiOk) { "failed" } elseif ($apiWasUp) { "up" } else { "started" }
$webStatus = if (-not $webOk) { "failed" } elseif ($webWasUp) { "up" } else { "started" }

Write-Host "DOCKER    postgres:5432 redis:6379 chroma:8001  ($dockerStatus)"
Write-Host "BASELINE  $BaselineKey                          ($baselineStatus)"
Write-Host "API       http://localhost:8000/health           ($apiStatus)"
Write-Host "WEB       http://localhost:3000                  ($webStatus)"

if (-not $dockerOk -or $baselineStatus -eq "failed" -or -not $apiOk -or -not $webOk) {
    if (-not $apiOk) { Show-Tail $ApiLog "API" }
    if (-not $webOk) { Show-Tail $WebLog "WEB" }
    if ($baselineStatus -eq "failed") { Show-Tail $BaselineLog "BASELINE" }
    Write-Host "Hint: Docker Desktop, eclipse-sumo via uv, kernel data net/rou, .env, or ports."
    exit 1
}
exit 0
