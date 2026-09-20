@echo off
title Smart Taxi Fare Comparison - Local Runner
echo ====================================================
echo    Smart Taxi Fare Comparison - 100%% Python Backend
echo ====================================================

cd "%~dp0"

echo 📦 Installing / Verifying Python dependencies...
call pip install -r requirements.txt

echo 🌐 Installing / Verifying Frontend dependencies...
cd frontend
call npm install
cd ..

echo 🚀 Starting FastAPI Python Backend on http://localhost:5000 ...
start "FastAPI Backend" cmd /k "uvicorn backend.app.main:app --host 0.0.0.0 --port 5000 --reload"

echo 🎨 Starting Vite React Frontend on http://localhost:5173 ...
cd frontend
call npm run dev
