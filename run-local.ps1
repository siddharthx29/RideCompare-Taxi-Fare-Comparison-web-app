# Smart Taxi Fare Comparison - Local Runner (PowerShell)

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "   Smart Taxi Fare Comparison - 100% Python Backend " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($ScriptDir) {
    Set-Location $ScriptDir
}

# 1. Install / Verify Python dependencies
Write-Host "📦 1. Verifying Python dependencies..." -ForegroundColor Gray
python -m pip install -r requirements.txt

# 2. Install / Verify Frontend dependencies
Set-Location frontend
Write-Host "🌐 2. Verifying Frontend dependencies..." -ForegroundColor Gray
npm install
Set-Location ..

# 3. Start FastAPI Python Backend in separate process window
Write-Host "🚀 3. Starting FastAPI Backend on http://127.0.0.1:5000 ..." -ForegroundColor Green
Start-Process cmd -ArgumentList "/k python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 5000 --reload"

# 4. Start Vite React Frontend
Write-Host "🎨 4. Starting Vite React Frontend on http://localhost:5173 ..." -ForegroundColor Magenta
Set-Location frontend
npm run dev
