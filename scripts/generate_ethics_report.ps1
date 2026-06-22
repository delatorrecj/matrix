param(
    [string]$InputFile = "d:\PROJECTS\matrix\docs\aaih-ai-use-ethics-report.md",
    [string]$OutputDir = "d:\PROJECTS\matrix\docs",
    [string]$OutputDocx = "SmartCities_PUP_ATLAN_AI_Report.docx"
)

# Ensure the output directory exists
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$DocxPath = Join-Path $OutputDir $OutputDocx

Write-Host "Converting $InputFile to $DocxPath using Pandoc..."

try {
    pandoc $InputFile -o $DocxPath
    Write-Host "Successfully generated $DocxPath" -ForegroundColor Green
}
catch {
    Write-Error "Failed to convert file. Is pandoc installed? $_"
}
