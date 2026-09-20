@echo off
title Smart Taxi Fare Comparison - Local Runner
echo ====================================================
echo    Smart Taxi Fare Comparison - 100%% Python Backend
echo ====================================================

cd "%~dp0"

echo 📦 1. Verifying Python dependencies...
python -m pip install -r requirements.txt

echo 🌐 2. Verifying Frontend dependencies...
cd frontend
call npm install
cd ..

echo 🚀 3. Starting FastAPI Python Backend on http://127.0.0.1:5000 ...
start "FastAPI Backend (Port 5000)" cmd /k "python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 5000 --reload"

echo 🎨 4. Starting Vite React Frontend on http://localhost:5173 ...
cd frontend
call npm run dev
