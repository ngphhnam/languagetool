# Script to start LanguageTool Java server
# This script will automatically start the Java server if it's not already running

$LANGTOOL_JAR_PATH = $env:LANGTOOL_JAR_PATH
$LANGTOOL_JAVA_PORT = 8011

# Try to find LanguageTool jar file if not specified
if (-not $LANGTOOL_JAR_PATH) {
    # Common locations (check most common first)
    $possiblePaths = @(
        "D:\LanguageTool\LanguageTool-6.0\languagetool-server.jar",  # User's current location
        "$env:USERPROFILE\LanguageTool\LanguageTool-6.0\languagetool-server.jar",
        "$env:USERPROFILE\Downloads\LanguageTool-6.0\languagetool-server.jar",
        "$PSScriptRoot\..\..\LanguageTool\LanguageTool-6.0\languagetool-server.jar",
        "$PSScriptRoot\languagetool-server.jar",
        "C:\LanguageTool\LanguageTool-6.0\languagetool-server.jar"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $LANGTOOL_JAR_PATH = $path
            Write-Host "Found LanguageTool at: $LANGTOOL_JAR_PATH" -ForegroundColor Green
            break
        }
    }
}

# If still not found, ask user or use environment variable
if (-not $LANGTOOL_JAR_PATH) {
    Write-Host "LanguageTool jar file not found automatically." -ForegroundColor Yellow
    Write-Host "Please set LANGTOOL_JAR_PATH environment variable:" -ForegroundColor Yellow
    Write-Host "  `$env:LANGTOOL_JAR_PATH='D:\LanguageTool\LanguageTool-6.0\languagetool-server.jar'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Or download LanguageTool from: https://languagetool.org/download/" -ForegroundColor Yellow
    Write-Host "Then extract and set the path to languagetool-server.jar" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Skipping Java server auto-start. Please start manually:" -ForegroundColor Yellow
    Write-Host "  java -cp languagetool-server.jar org.languagetool.server.HTTPServer --port 8011 --public" -ForegroundColor Gray
    exit 0  # Exit with 0 so script doesn't fail, just skip
}

# Check if Java is installed
try {
    $javaVersion = java -version 2>&1
    Write-Host "Java found" -ForegroundColor Green
} catch {
    Write-Host "Java not found! Please install Java 8+" -ForegroundColor Red
    Write-Host "Download from: https://adoptium.net/" -ForegroundColor Yellow
    exit 1
}

# Check if port is already in use
$portInUse = Test-NetConnection -ComputerName localhost -Port $LANGTOOL_JAVA_PORT -InformationLevel Quiet -WarningAction SilentlyContinue
if ($portInUse) {
    Write-Host "Port $LANGTOOL_JAVA_PORT is already in use. Java server might already be running." -ForegroundColor Yellow
    Write-Host "Skipping Java server startup..." -ForegroundColor Gray
    exit 0
}

# Start Java server
Write-Host "Starting LanguageTool Java server on port $LANGTOOL_JAVA_PORT..." -ForegroundColor Yellow
Write-Host "  JAR: $LANGTOOL_JAR_PATH" -ForegroundColor Gray
Write-Host "  Port: $LANGTOOL_JAVA_PORT" -ForegroundColor Gray
Write-Host ""

# Change to the directory containing the jar file for better compatibility
$jarDirectory = Split-Path -Parent $LANGTOOL_JAR_PATH
$jarFileName = Split-Path -Leaf $LANGTOOL_JAR_PATH

# Start Java server from the jar directory
Start-Process java -ArgumentList "-cp", "`"$jarFileName`"", "org.languagetool.server.HTTPServer", "--port", "$LANGTOOL_JAVA_PORT", "--public" -WorkingDirectory $jarDirectory -WindowStyle Normal

Write-Host "Java server starting in new window..." -ForegroundColor Green
Write-Host "Waiting for server to initialize (this may take 10-15 seconds)..." -ForegroundColor Gray

# Wait and retry connection with multiple attempts
$maxRetries = 6
$retryDelay = 3
$serverReady = $false

for ($i = 1; $i -le $maxRetries; $i++) {
    Start-Sleep -Seconds $retryDelay
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$LANGTOOL_JAVA_PORT/v2/languages" -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "LanguageTool Java server is running successfully!" -ForegroundColor Green
            $serverReady = $true
            break
        }
    } catch {
        Write-Host "  Attempt ${i}/${maxRetries}: Server not ready yet, waiting..." -ForegroundColor Gray
    }
}

if (-not $serverReady) {
    Write-Host "Server might still be starting up. Check the Java server window for status." -ForegroundColor Yellow
    Write-Host "  The Python service will retry connection on startup." -ForegroundColor Gray
}

