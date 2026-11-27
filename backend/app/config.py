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
    MAPBOX_ACCESS_TOKEN: str = os.getenv(
        "MAPBOX_ACCESS_TOKEN",
        os.getenv("MAPBOX_SECRET_TOKEN", os.getenv("MAPBOX_SERVER_TOKEN", ""))
    )
    MAPBOX_PUBLIC_TOKEN: str = os.getenv("MAPBOX_PUBLIC_TOKEN", "")
    GEOCODING_PROVIDER: str = os.getenv("GEOCODING_PROVIDER", "mapbox")
    GEOAPIFY_API_KEY: str = os.getenv("GEOAPIFY_API_KEY", "")
    UBER_API_KEY: str = os.getenv("UBER_API_KEY", "")
    LYFT_API_KEY: str = os.getenv("LYFT_API_KEY", "")
    OLA_API_KEY: str = os.getenv("OLA_API_KEY", "")
    RAPIDO_API_KEY: str = os.getenv("RAPIDO_API_KEY", "")
    BOLT_API_KEY: str = os.getenv("BOLT_API_KEY", "")
    GRAB_API_KEY: str = os.getenv("GRAB_API_KEY", "")
    PHOTON_BASE_URL: str = os.getenv("PHOTON_BASE_URL", "https://photon.komoot.io").rstrip("/")
    NOMINATIM_BASE_URL: str = os.getenv("NOMINATIM_BASE_URL", os.getenv("GEOCODING_BASE_URL", "https://nominatim.openstreetmap.org")).rstrip("/")
    GEOCODING_USER_AGENT: str = os.getenv(
        "GEOCODING_USER_AGENT",
        "RideCompare/3.0 (https://ridecompare.world; contact: support@ridecompare.world)"
    )
    LOCATION_CACHE_TTL_DAYS: int = int(os.getenv("LOCATION_CACHE_TTL_DAYS", "14"))
    SITE_URL: str = os.getenv("SITE_URL", "https://ridecompare.world").rstrip("/")
    GSC_SITE_URL: str = os.getenv("GSC_SITE_URL", "")
    GOOGLE_SERVICE_ACCOUNT_JSON: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    BING_WEBMASTER_API_KEY: str = os.getenv("BING_WEBMASTER_API_KEY", "")
    GA4_PROPERTY_ID: str = os.getenv("GA4_PROPERTY_ID", "")
    CRON_SECRET: str = os.getenv("CRON_SECRET", "")

    @property
    def allowed_origins_list(self) -> List[str]:
        origins = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        if origins:
            return list(dict.fromkeys(origins))
        if self.ENVIRONMENT.lower() in {"production", "prod"}:
            return [
                "https://ridecompare.world",
                "https://www.ridecompare.world",
                "https://ridecompare.vercel.app"
            ]
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8080",
            "http://localhost:3000",
            "http://127.0.0.1:3000"
        ]


settings = Settings()
