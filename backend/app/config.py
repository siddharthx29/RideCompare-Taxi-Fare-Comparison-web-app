import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
ROOT_DIR = BACKEND_DIR.parent
CONFIG_DIR = APP_DIR / "config"
FARES_CONFIG_PATH = CONFIG_DIR / "fares.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    PORT: int = int(os.getenv("PORT", "5000"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{APP_DIR / 'ridecompare.db'}")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", os.getenv("ENV", "development"))

    @property
    def ENV(self) -> str:
        return self.ENVIRONMENT
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", os.getenv("ALLOWED_ORIGINS", ""))
    ADMIN_KEY: str = os.getenv("ADMIN_KEY", "")
    MAPBOX_ACCESS_TOKEN: str = os.getenv("MAPBOX_ACCESS_TOKEN", os.getenv("MAPBOX_SERVER_TOKEN", ""))
    MAPBOX_PUBLIC_TOKEN: str = os.getenv("MAPBOX_PUBLIC_TOKEN", "")
    GEOCODING_PROVIDER: str = os.getenv("GEOCODING_PROVIDER", "mapbox")
    GEOAPIFY_API_KEY: str = os.getenv("GEOAPIFY_API_KEY", "")
    PHOTON_BASE_URL: str = os.getenv("PHOTON_BASE_URL", "https://photon.komoot.io").rstrip("/")
    NOMINATIM_BASE_URL: str = os.getenv("NOMINATIM_BASE_URL", os.getenv("GEOCODING_BASE_URL", "https://nominatim.openstreetmap.org")).rstrip("/")
    GEOCODING_USER_AGENT: str = os.getenv(
        "GEOCODING_USER_AGENT",
        "RideCompare/3.0 (https://ridecompare.world; contact: support@ridecompare.world)"
    )
    LOCATION_CACHE_TTL_DAYS: int = int(os.getenv("LOCATION_CACHE_TTL_DAYS", "14"))

    @property
    def allowed_origins_list(self) -> List[str]:
        origins = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        if origins:
            return list(dict.fromkeys(origins))
        if self.ENVIRONMENT.lower() in {"production", "prod"}:
            return []
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8080",
            "http://localhost:3000",
            "http://127.0.0.1:3000"
        ]


settings = Settings()
