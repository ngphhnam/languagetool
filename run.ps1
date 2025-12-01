# Script to run LanguageTool service with self-hosted server configuration
# This script will automatically start the Java server if needed

Write-Host "Starting LanguageTool Service..." -ForegroundColor Green
Write-Host "  Service will run on port 8010" -ForegroundColor Yellow
Write-Host "  Connecting to self-hosted Java server on port 8011" -ForegroundColor Yellow
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Python not found! Please install Python 3.9+" -ForegroundColor Red
    exit 1
}

# Try to start Java server automatically
Write-Host "Checking Java server..." -ForegroundColor Cyan
& "$PSScriptRoot\start-java-server.ps1"
$javaServerStarted = $LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq $null

if (-not $javaServerStarted) {
    Write-Host "Could not start Java server automatically." -ForegroundColor Yellow
    Write-Host "  Please start it manually from D:\LanguageTool\LanguageTool-6.0:" -ForegroundColor Yellow
    Write-Host "    java -cp languagetool-server.jar org.languagetool.server.HTTPServer --port 8011 --public" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Or set LANGTOOL_JAR_PATH environment variable:" -ForegroundColor Yellow
    Write-Host "    `$env:LANGTOOL_JAR_PATH='D:\LanguageTool\LanguageTool-6.0\languagetool-server.jar'" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "Java server check completed" -ForegroundColor Green
    Write-Host ""
}

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Install dependencies if needed
if (-not (Test-Path "venv\Lib\site-packages\fastapi")) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -q -r requirements.txt
}

# Set environment variable for LanguageTool server
$env:LANGTOOL_SERVER = "http://localhost:8011"

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  LANGTOOL_SERVER = $env:LANGTOOL_SERVER" -ForegroundColor White
Write-Host ""
Write-Host "Starting service on http://localhost:8010..." -ForegroundColor Green
Write-Host "  Make sure Java server is running on port 8011" -ForegroundColor Gray
Write-Host ""

# Run the service
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
