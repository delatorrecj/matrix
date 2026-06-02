<#
  MATRIX - fetch direct, open, contact-free data for the Iloilo pilot (Windows-native mirror of fetch_open.py).
  Idempotent: skips files already present.  Run:  pwsh data/fetch/fetch_open.ps1
#>
$ErrorActionPreference = 'Continue'
$Raw  = Join-Path (Split-Path $PSScriptRoot -Parent) 'raw'
$UA   = 'Mozilla/5.0 (MATRIX/data-fetch; +https://github.com/delatorrecj/matrix)'
$Bbox = '10.65,122.50,10.78,122.61'   # Iloilo City Proper: S,W,N,E

function Grab($key, $url, $relpath) {
    $dest = Join-Path $Raw $relpath
    if ((Test-Path $dest) -and (Get-Item $dest).Length -gt 0) {
        Write-Host "  skip  $key (exists)"; return
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
    try {
        Invoke-WebRequest -Uri $url -OutFile $dest -UserAgent $UA -TimeoutSec 180
        Write-Host "  OK    $key -> raw/$relpath ($((Get-Item $dest).Length) B)"
    } catch {
        Write-Host "  FAIL  $key : $($_.Exception.Message)"
    }
}

$direct = @(
  @('LIT-CALDERON','https://ncts.upd.edu.ph/tssp/wp-content/uploads/2018/08/Calderon14.pdf','literature/Calderon2014_Iloilo_BRT.pdf'),
  @('LIT-BIKE19','https://ncts.upd.edu.ph/tssp/wp-content/uploads/2019/09/TSSP2019-04_Factors-Influencing-Bicycle-Use-in-a-Medium-Sized-City-the-Case-of-Iloilo-1-City-Philippines.pdf','literature/TSSP2019_Iloilo_bicycle_use.pdf'),
  @('LIT-POPGIS','https://isprs-archives.copernicus.org/articles/XLVI-4-W6-2021/185/2021/isprs-archives-XLVI-4-W6-2021-185-2021.pdf','literature/ISPRS2021_Iloilo_pop_forecast.pdf'),
  @('LIT-CDP','https://iloilocity.gov.ph/main/wp-content/uploads/2023/05/CDP2023-2028_4-13_Final-Document.pdf','literature/Iloilo_CDP_2023-2028.pdf'),
  @('CENSUS20','https://psa.gov.ph/system/files/phcd/2022-12/%281%29%20Region%206_final.xlsx','psa/PSA_2020_Census_RegionVI.xlsx')
)
Write-Host '== direct HTTP =='
foreach ($d in $direct) { Grab $d[0] $d[1] $d[2] }

Write-Host '== OpenStreetMap (Overpass) =='
$osm = Join-Path $Raw 'osm/iloilo_osm.json'
if ((Test-Path $osm) -and (Get-Item $osm).Length -gt 0) {
    Write-Host '  skip  OSM-ILO (exists)'
} else {
    New-Item -ItemType Directory -Force -Path (Split-Path $osm) | Out-Null
    $q = @"
[out:json][timeout:240];
(
  way["highway"]($Bbox);
  relation["route"~"bus|jeepney|share_taxi|minibus|tram"]($Bbox);
  node["public_transport"]($Bbox);
  node["amenity"~"school|hospital|clinic|marketplace|university|ferry_terminal"]($Bbox);
  node["historic"]($Bbox);
  way["landuse"]($Bbox);
);
out body geom;
"@
    try {
        Invoke-WebRequest -Uri 'https://overpass-api.de/api/interpreter' -Method Post -Body @{ data = $q } -OutFile $osm -UserAgent $UA -TimeoutSec 300
        Write-Host "  OK    OSM-ILO -> raw/osm/iloilo_osm.json ($((Get-Item $osm).Length) B)"
    } catch { Write-Host "  FAIL  OSM-ILO : $($_.Exception.Message)" }
}

Write-Host '== HDX / CKAN (Project CCHAIN) =='
try {
    $pkg = Invoke-RestMethod -Uri 'https://data.humdata.org/api/3/action/package_show?id=project-cchain' -UserAgent $UA -TimeoutSec 120
    foreach ($r in $pkg.result.resources) {
        if (-not $r.url) { continue }
        $fname = if ($r.name -and $r.name.Contains('.')) { $r.name } else { Split-Path $r.url -Leaf }
        Grab "CCHAIN:$fname" $r.url "hdx/$fname"
    }
} catch { Write-Host "  FAIL  CCHAIN : $($_.Exception.Message)" }
