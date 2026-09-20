#!/usr/bin/env bash
set -e

echo "===================================================="
echo "   Smart Taxi Fare Comparison - 100% Python Backend "
echo "===================================================="

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "🌐 Installing Frontend dependencies..."
cd frontend
npm install
cd ..

echo "🚀 Starting FastAPI Python Backend on http://localhost:5000 ..."
uvicorn backend.app.main:app --host 0.0.0.0 --port 5000 --reload &
BACKEND_PID=$!

echo "🎨 Starting Vite React Frontend on http://localhost:5173 ..."
cd frontend
npm run dev

kill $BACKEND_PID
