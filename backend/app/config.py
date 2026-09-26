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
    GEOAPIFY_API_KEY: str = os.getenv("GEOAPIFY_API_KEY", "")
    GEOCODING_PROVIDER: str = os.getenv("GEOCODING_PROVIDER", "geoapify")

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
