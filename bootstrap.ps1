# PLC MCP Server Bootstrap Script
# Run this in PowerShell to create the project

$ProjectDir = "$env:USERPROFILE\projects\plc-mcp-server"

Write-Host "Creating PLC MCP Server at $ProjectDir" -ForegroundColor Cyan

# Create directories
$dirs = @(
    "$ProjectDir\plc_mcp_server\plc",
    "$ProjectDir\plc_mcp_server\tools",
    "$ProjectDir\plc_mcp_server\safety",
    "$ProjectDir\tests"
)

foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

Write-Host "Directories created" -ForegroundColor Green

# Now cd into project and create venv
Set-Location $ProjectDir

Write-Host "Creating virtual environment..." -ForegroundColor Cyan
python -m venv venv
.\venv\Scripts\Activate.ps1

Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install mcp pycomm3 pyyaml pydantic

Write-Host ""
Write-Host "=== DONE ===" -ForegroundColor Green
Write-Host "Project created at: $ProjectDir"
Write-Host ""
Write-Host "Next: Clone the code from GitHub or copy files manually"
Write-Host "Then run: python -m plc_mcp_server --demo"
