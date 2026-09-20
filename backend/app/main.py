"""
FastAPI Main Application Entrypoint for Smart Taxi Fare Comparison & Intelligence Platform.
"""

import os
import sys
import logging
from pathlib import Path
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Path configuration
APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
ROOT_DIR = BACKEND_DIR.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.app.config import settings
from backend.app.database import init_db, check_db_health
from backend.app.routers import geocode, route, analytics, ml_endpoints

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("smart-fare-backend")

# Initialize FastAPI App
app = FastAPI(
    title="Smart Taxi Fare Comparison & ML Intelligence API",
    description="Intelligent real-time multi-provider taxi fare comparison, clustering, regression, and anomaly detection.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# ---------------------------------------------------------
# Security & Headers Middleware
# ---------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# ---------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
]
if settings.CORS_ORIGINS:
    for o in settings.CORS_ORIGINS.split(","):
        o_clean = o.strip()
        if o_clean and o_clean not in origins:
            origins.append(o_clean)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if "*" not in origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Startup & Database Initialization
# ---------------------------------------------------------

@app.on_event("startup")
async def on_startup():
    logger.info("Initializing database schema and initial seed data...")
    init_db()
    logger.info(f"Smart Taxi Fare Comparison backend running in {settings.ENVIRONMENT} mode.")


# ---------------------------------------------------------
# Health Check Endpoint
# ---------------------------------------------------------

@app.get("/health", tags=["system"])
async def health_check():
    db_healthy = check_db_health()
    
    # Check ML models availability
    models_dir = ROOT_DIR / "ml" / "models" / "saved"
    has_models = (
        (models_dir / "fare_regressor.joblib").exists() and
        (models_dir / "kmeans_cluster.joblib").exists() and
        (models_dir / "anomaly_detector.joblib").exists()
    )

    return {
        "status": "healthy" if db_healthy else "degraded",
        "service": "Smart Taxi Fare Comparison API",
        "version": "2.0.0",
        "database": "connected" if db_healthy else "unavailable",
        "ml_engine": "ready" if has_models else "fallback_mode",
        "environment": settings.ENVIRONMENT
    }


# ---------------------------------------------------------
# Include API Routers (Both /api prefix and root for compatibility)
# ---------------------------------------------------------

app.include_router(geocode.router, prefix="/api")
app.include_router(geocode.router)

app.include_router(route.router, prefix="/api")
app.include_router(route.router)

app.include_router(analytics.router, prefix="/api")
app.include_router(analytics.router)

app.include_router(ml_endpoints.router)


# ---------------------------------------------------------
# Static Files & SPA Fallback (Production Frontend)
# ---------------------------------------------------------

DIST_DIR = ROOT_DIR / "frontend" / "dist"

if DIST_DIR.exists():
    logger.info(f"Serving production frontend from {DIST_DIR}")
    
    # Mount static assets
    assets_dir = DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # SPA Fallback for any non-API route
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Don't intercept API or docs routes
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("redoc") or full_path.startswith("openapi.json"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        
        file_path = DIST_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        index_file = DIST_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        
        raise HTTPException(status_code=404, detail="Page not found")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", settings.PORT))
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, reload=True)
