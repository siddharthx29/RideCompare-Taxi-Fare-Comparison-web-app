import logging
import os
from datetime import datetime, timedelta
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from backend.app.config import settings, APP_DIR
from backend.app.models.db_models import Base, User, Search, Analytics

logger = logging.getLogger(__name__)

DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite:"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Successfully connected to configured PostgreSQL database.")
    except Exception as err:
        logger.error("Failed to connect to configured PostgreSQL database: %s", err)
        logger.warning("Falling back to local SQLite database so the application stays operational.")
        sqlite_path = APP_DIR / "ridecompare.db"
        DATABASE_URL = f"sqlite:///{sqlite_path}"
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_health() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add(User(name="Demo User", email="demo@ridecompare.com"))
            db.commit()

        if db.query(Search).count() == 0:
            now = datetime.utcnow()
            seed_searches = [
                Search(
                    source="Indiranagar, Bengaluru",
                    destination="Koramangala, Bengaluru",
                    source_lat=12.971891,
                    source_lng=77.641151,
                    dest_lat=12.935192,
                    dest_lng=77.624480,
                    distance_km=5.8,
                    duration_min=18.0,
                    cheapest_provider="Rapido Bike",
                    fastest_provider="Uber Go",
                    best_provider="Ola Mini",
                    selected_provider="Rapido Bike",
                    savings=35.0,
                    created_at=now - timedelta(days=6)
                ),
                Search(
                    source="Whitefield, Bengaluru",
                    destination="Electronic City, Bengaluru",
                    source_lat=12.9698,
                    source_lng=77.7499,
                    dest_lat=12.8399,
                    dest_lng=77.6770,
                    distance_km=24.5,
                    duration_min=52.0,
                    cheapest_provider="Rapido Bike",
                    fastest_provider="Uber Go",
                    best_provider="Uber Go",
                    selected_provider="Uber Go",
                    savings=15.0,
                    created_at=now - timedelta(days=5)
                ),
                Search(
                    source="Majestic, Bengaluru",
                    destination="Kempegowda International Airport",
                    source_lat=12.9779,
                    source_lng=77.5724,
                    dest_lat=13.1986,
                    dest_lng=77.7066,
                    distance_km=36.2,
                    duration_min=45.0,
                    cheapest_provider="Ola Mini",
                    fastest_provider="Uber Go",
                    best_provider="Ola Mini",
                    selected_provider="Ola Mini",
                    savings=50.0,
                    created_at=now - timedelta(days=4)
                ),
                Search(
                    source="HSR Layout, Bengaluru",
                    destination="Jayanagar, Bengaluru",
                    source_lat=12.9116,
                    source_lng=77.6388,
                    dest_lat=12.9298,
                    dest_lng=77.5833,
                    distance_km=8.1,
                    duration_min=24.0,
                    cheapest_provider="Rapido Auto",
                    fastest_provider="Ola Mini",
                    best_provider="Ola Mini",
                    selected_provider="Ola Mini",
                    savings=20.0,
                    created_at=now - timedelta(days=3)
                ),
                Search(
                    source="Malleswaram, Bengaluru",
                    destination="MG Road, Bengaluru",
                    source_lat=12.9960,
                    source_lng=77.5712,
                    dest_lat=12.9733,
                    dest_lng=77.6117,
                    distance_km=7.2,
                    duration_min=22.0,
                    cheapest_provider="Rapido Bike",
                    fastest_provider="Uber Go",
                    best_provider="Rapido Bike",
                    selected_provider="Rapido Bike",
                    savings=40.0,
                    created_at=now - timedelta(days=2)
                )
            ]
            db.add_all(seed_searches)

            seed_analytics = [
                Analytics(provider="Uber Go", clicks=40, redirects=32, fare=600.0, created_at=now - timedelta(days=3)),
                Analytics(provider="Ola Mini", clicks=48, redirects=40, fare=550.0, created_at=now - timedelta(days=2)),
                Analytics(provider="Rapido Bike", clicks=67, redirects=60, fare=230.0, created_at=now - timedelta(days=1)),
                Analytics(provider="Rapido Auto", clicks=37, redirects=35, fare=370.0, created_at=now)
            ]
            db.add_all(seed_analytics)
            db.commit()
            logger.info("Initialized default seed records into database.")
    except Exception as err:
        logger.error("Database initialization encountered an error: %s", err)
        db.rollback()
    finally:
        db.close()
