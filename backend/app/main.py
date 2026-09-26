import os
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("smart-fare-backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="RideCompare API",
    description="Route-aware fare estimates, provider availability, and platform analytics.",
    version="2.0.0",
    docs_url=None if settings.ENVIRONMENT.lower() in {"production", "prod"} else "/docs",
    redoc_url=None if settings.ENVIRONMENT.lower() in {"production", "prod"} else "/redoc",
    lifespan=lifespan
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_origin_regex=r"^https://.*(\.vercel\.app|\.onrender\.com)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
async def health_check():
    db_healthy = check_db_health()
    return {
        "status": "healthy" if db_healthy else "degraded",
        "service": "RideCompare API",
        "version": "2.0.0",
        "database": "connected" if db_healthy else "unavailable",
        "environment": settings.ENVIRONMENT
    }


# Include API Routers
app.include_router(geocode.router, prefix="/api")
app.include_router(geocode.router)
app.include_router(route.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(ml_endpoints.router)

PUBLIC_DIR = ROOT_DIR / "frontend" / "public"
DIST_DIR = ROOT_DIR / "frontend" / "dist"

@app.get("/sitemap.xml", include_in_schema=False)
async def get_sitemap():
    for candidate in [DIST_DIR / "sitemap.xml", PUBLIC_DIR / "sitemap.xml"]:
        if candidate.exists():
            return FileResponse(candidate, media_type="application/xml")
    raise HTTPException(status_code=404, detail="sitemap.xml not found")


@app.get("/robots.txt", include_in_schema=False)
async def get_robots():
    for candidate in [DIST_DIR / "robots.txt", PUBLIC_DIR / "robots.txt"]:
        if candidate.exists():
            return FileResponse(candidate, media_type="text/plain")
    raise HTTPException(status_code=404, detail="robots.txt not found")


# Serve built frontend in production if available

if DIST_DIR.exists():
    assets_dir = DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
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
