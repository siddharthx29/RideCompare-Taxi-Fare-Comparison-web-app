@echo off
title RideCompare Local Startup with ML Engine
echo ====================================================
echo    Starting RideCompare & ML Intelligence Engine    
echo ====================================================

cd "%~dp0"

echo 🧠 Starting Python ML Intelligence Microservice (Port 5001)...
start "RideCompare ML Engine" cmd /k "python ml/server.py"

cd backend

echo 📦 Checking backend dependencies...
call npm install

echo 🗄️ Setting up database and running migrations...
call npm run db:setup
if %ERRORLEVEL% neq 0 (
    echo.
    echo ⚠️ Database setup warning! Please verify PostgreSQL is running if database persistence is needed.
    echo Backend will proceed with in-memory or fallback handling.
    echo.
)

echo 🚀 Starting local backend server in development mode...
call npm run dev
