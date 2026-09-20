# RideCompare Local Startup Script - 100% Python Backend (PowerShell)

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "   Smart Taxi Fare Comparison - 100% Python Backend   " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($ScriptDir) {
    Set-Location $ScriptDir
}

# 1. Install / Verify Python dependencies
Write-Host "📦 Installing / Verifying Python dependencies..." -ForegroundColor Gray
pip install -r requirements.txt

# 2. Install / Verify Frontend dependencies
Set-Location frontend
Write-Host "🌐 Installing / Verifying Frontend dependencies..." -ForegroundColor Gray
npm install
Set-Location ..

# 3. Start FastAPI Python Backend
Write-Host "🚀 Starting FastAPI Python Backend on http://localhost:5000 ..." -ForegroundColor Green
Start-Process uvicorn -ArgumentList "backend.app.main:app --host 0.0.0.0 --port 5000 --reload"

# 4. Start Vite React Frontend
Write-Host "🎨 Starting Vite React Frontend on http://localhost:5173 ..." -ForegroundColor Magenta
Set-Location frontend
npm run dev
