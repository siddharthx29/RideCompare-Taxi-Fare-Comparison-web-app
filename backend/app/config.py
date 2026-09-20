import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PORT: int = int(os.getenv("PORT", "5000"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgrespassword@localhost:5432/ridecompare")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", os.getenv("NODE_ENV", "development"))
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://localhost:3000,http://127.0.0.1:3000"
    )
    ALLOWED_ORIGINS: list[str] = [
        origin.strip() for origin in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://localhost:3000,https://taxi-fare-comparison-web-app.onrender.com,https://ridecompare.onrender.com"
        ).split(",") if origin.strip()
    ]

    class Config:
        extra = "ignore"


settings = Settings()
