#!/bin/bash
set -e

echo "===================================================="
echo "        Starting RideCompare (Local Environment)     "
echo "===================================================="

# Ensure script runs in correct location
cd "$(dirname "$0")"
cd backend

echo "📦 Checking and installing dependencies..."
npm install

echo "🗄️ Setting up database and running migrations..."
npm run db:setup

echo "🚀 Starting local backend server in development mode..."
npm run dev
