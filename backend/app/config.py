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
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgrespassword@localhost:5432/ridecompare")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", os.getenv("ENV", "development"))

    @property
    def ENV(self) -> str:
        return self.ENVIRONMENT
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://localhost:3000,http://127.0.0.1:3000"
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        origins = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        defaults = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8080",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5000",
            "http://127.0.0.1:5000"
        ]
        for d in defaults:
            if d not in origins:
                origins.append(d)
        return origins


settings = Settings()
