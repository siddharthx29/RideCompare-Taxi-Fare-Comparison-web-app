"""
Smart Taxi Fare Comparison - Root Server Launcher
Runs the FastAPI Backend cleanly with configuration, CLI arguments, and environment support.
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure stdout/stderr supports UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure working directory is always the project root
os.chdir(str(ROOT_DIR))

import uvicorn
from backend.app.config import settings

def main():
    parser = argparse.ArgumentParser(
        description="Smart Taxi Fare Comparison & Route Aggregator Backend Launcher",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("HOST", "0.0.0.0"),
        help="Host interface to bind the server to.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", settings.PORT)),
        help="Port number to run the server on.",
    )
    parser.add_argument(
        "--reload",
        dest="reload",
        action="store_true",
        default=os.environ.get("ENV", "development").lower() != "production",
        help="Enable auto-reload on code changes.",
    )
    parser.add_argument(
        "--no-reload",
        dest="reload",
        action="store_false",
        help="Disable auto-reload (recommended for production).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("WORKERS", 1)),
        help="Number of worker processes (used when reload is disabled).",
    )

    args = parser.parse_args()

    display_host = "127.0.0.1" if args.host in ("0.0.0.0", "::") else args.host
    print("=" * 70)
    print("  🚀 SMART CAB FARE COMPARISON PLATFORM - BACKEND LAUNCHER")
    print("=" * 70)
    print(f"  • API Base URL:       http://{display_host}:{args.port}/api/v1")
    print(f"  • Interactive Docs:   http://{display_host}:{args.port}/docs")
    print(f"  • Health Check:       http://{display_host}:{args.port}/health")
    print(f"  • Active Environment: {settings.ENVIRONMENT}")
    print(f"  • Auto Reload:        {'Enabled' if args.reload else 'Disabled'}")
    print("=" * 70)
    print("Starting Uvicorn ASGI server...")

    if args.reload:
        uvicorn.run(
            "backend.app.main:app",
            host=args.host,
            port=args.port,
            reload=True,
            reload_dirs=[str(ROOT_DIR / "backend")],
        )
    else:
        uvicorn.run(
            "backend.app.main:app",
            host=args.host,
            port=args.port,
            reload=False,
            workers=args.workers,
        )

if __name__ == "__main__":
    main()
