"""
Smart Taxi Fare Comparison - Root Server Launcher
Runs the FastAPI Backend cleanly regardless of current working directory.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Change working directory to project root
os.chdir(str(ROOT_DIR))

import uvicorn
from backend.app.config import settings

if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.PORT))
    print(f"Starting Smart Taxi Fare Comparison Backend on http://127.0.0.1:{port} ...")
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, reload=True)
