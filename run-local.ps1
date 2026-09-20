# RideCompare Local Startup Script with ML Engine (Windows PowerShell)

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "   Starting RideCompare & ML Intelligence Engine    " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($ScriptDir) {
    Set-Location $ScriptDir
}

# 1. Start Python ML Microservice
Write-Host "🧠 Starting Python ML Intelligence Microservice (Port 5001)..." -ForegroundColor Yellow
Start-Process python -ArgumentList "ml/server.py" -NoNewWindow

# 2. Setup and run backend
Set-Location backend

Write-Host "📦 Checking and installing dependencies..." -ForegroundColor Gray
npm install

Write-Host "🗄️ Setting up database and running migrations..." -ForegroundColor Gray
npm run db:setup

# 3. Launch Express server
Write-Host "🚀 Starting local backend server in development mode..." -ForegroundColor Green
npm run dev
