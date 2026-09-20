"""
Database Engine & Session Management for Python Backend
Supports PostgreSQL with automated SQLite fallback and table auto-initialization.
"""

import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from backend.app.config import settings
from backend.app.models.db_models import Base, User, Search, Analytics

DATABASE_URL = settings.DATABASE_URL

# Handle PostgreSQL vs SQLite fallback connection
try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    # Test connection
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("[Database] Successfully connected to PostgreSQL database.")
except Exception as e:
    print(f"[Database] PostgreSQL connection unavailable ({e}). Using SQLite local database fallback.")
    sqlite_path = os.path.join(os.path.dirname(__file__), "ridecompare.db")
    DATABASE_URL = f"sqlite:///{sqlite_path}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Auto-create tables on module load
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"[Database] Warning creating tables: {e}")


def get_db():
    """Dependency generator for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_health() -> bool:
    """Verifies active connection to database."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def init_db():
    """Creates database tables and seeds initial mock data if empty."""
    Base.metadata.create_all(bind=engine)
    
    # Check if searches are already seeded
    db: Session = SessionLocal()
    try:
        user_count = db.query(User).count()
        if user_count == 0:
            demo_user = User(name="Demo User", email="demo@ridecompare.com")
            db.add(demo_user)
            db.commit()

        search_count = db.query(Search).count()
        if search_count == 0:
            print("[Database] Seeding initial mock search and analytics data...")
            now = datetime.utcnow()
            mock_searches = [
                Search(
                    source="Indiranagar, Bengaluru", destination="Koramangala, Bengaluru",
                    source_lat=12.971891, source_lng=77.641151, dest_lat=12.935192, dest_lng=77.624480,
                    distance_km=5.8, duration_min=18.0, cheapest_provider="Rapido Bike",
                    fastest_provider="Uber Go", best_provider="Ola Mini", selected_provider="Rapido Bike",
                    savings=35.0, created_at=now - timedelta(days=6)
                ),
                Search(
                    source="Whitefield, Bengaluru", destination="Electronic City, Bengaluru",
                    source_lat=12.9698, source_lng=77.7499, dest_lat=12.8399, dest_lng=77.6770,
                    distance_km=24.5, duration_min=52.0, cheapest_provider="Rapido Bike",
                    fastest_provider="Uber Go", best_provider="Uber Go", selected_provider="Uber Go",
                    savings=15.0, created_at=now - timedelta(days=5)
                ),
                Search(
                    source="Majestic, Bengaluru", destination="Kempegowda International Airport",
                    source_lat=12.9779, source_lng=77.5724, dest_lat=13.1986, dest_lng=77.7066,
                    distance_km=36.2, duration_min=45.0, cheapest_provider="Ola Mini",
                    fastest_provider="Uber Go", best_provider="Ola Mini", selected_provider="Ola Mini",
                    savings=50.0, created_at=now - timedelta(days=4)
                ),
                Search(
                    source="HSR Layout, Bengaluru", destination="Jayanagar, Bengaluru",
                    source_lat=12.9116, source_lng=77.6388, dest_lat=12.9298, dest_lng=77.5833,
                    distance_km=8.1, duration_min=24.0, cheapest_provider="Rapido Auto",
                    fastest_provider="Ola Mini", best_provider="Ola Mini", selected_provider="Ola Mini",
                    savings=20.0, created_at=now - timedelta(days=3)
                ),
                Search(
                    source="Malleswaram, Bengaluru", destination="MG Road, Bengaluru",
                    source_lat=12.9960, source_lng=77.5712, dest_lat=12.9733, dest_lng=77.6117,
                    distance_km=7.2, duration_min=22.0, cheapest_provider="Rapido Bike",
                    fastest_provider="Uber Go", best_provider="Rapido Bike", selected_provider="Rapido Bike",
                    savings=40.0, created_at=now - timedelta(days=2)
                ),
                Search(
                    source="Koramangala, Bengaluru", destination="Indiranagar, Bengaluru",
                    source_lat=12.9351, source_lng=77.6244, dest_lat=12.9718, dest_lng=77.6411,
                    distance_km=6.0, duration_min=20.0, cheapest_provider="Rapido Bike",
                    fastest_provider="Ola Mini", best_provider="Ola Mini", selected_provider="Ola Mini",
                    savings=25.0, created_at=now - timedelta(days=1)
                ),
                Search(
                    source="MG Road, Bengaluru", destination="Indiranagar, Bengaluru",
                    source_lat=12.9733, source_lng=77.6117, dest_lat=12.9718, dest_lng=77.6411,
                    distance_km=4.2, duration_min=12.0, cheapest_provider="Rapido Bike",
                    fastest_provider="Uber Go", best_provider="Uber Go", selected_provider="Uber Go",
                    savings=10.0, created_at=now
                )
            ]
            db.add_all(mock_searches)

            mock_analytics = [
                Analytics(provider="Uber Go", clicks=40, redirects=32, fare=600.0, created_at=now - timedelta(days=3)),
                Analytics(provider="Ola Mini", clicks=48, redirects=40, fare=550.0, created_at=now - timedelta(days=2)),
                Analytics(provider="Rapido Bike", clicks=67, redirects=60, fare=230.0, created_at=now - timedelta(days=1)),
                Analytics(provider="Rapido Auto", clicks=37, redirects=35, fare=370.0, created_at=now)
            ]
            db.add_all(mock_analytics)
            db.commit()
            print("[Database] Initial mock seed data successfully written.")
    except Exception as err:
        db.rollback()
        print(f"[Database] Error initializing database seed: {err}")
    finally:
        db.close()
