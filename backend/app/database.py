import logging
import os
from datetime import datetime, timedelta
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from backend.app.config import settings, APP_DIR
from backend.app.models.db_models import Base, User, Search, Analytics, Location, DemandObservation

logger = logging.getLogger(__name__)

DATABASE_URL = settings.DATABASE_URL
if os.getenv("VERCEL") and (not DATABASE_URL or "sqlite" in DATABASE_URL):
    import shutil
    tmp_db = Path("/tmp") / "ridecompare.db"
    src_db = APP_DIR / "ridecompare.db"
    if not tmp_db.exists() and src_db.exists():
        try:
            shutil.copyfile(src_db, tmp_db)
        except Exception:
            pass
    DATABASE_URL = f"sqlite:///{tmp_db}"

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
        sqlite_path = Path("/tmp/ridecompare.db") if os.getenv("VERCEL") else (APP_DIR / "ridecompare.db")
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

        if db.query(DemandObservation).count() == 0:
            now = datetime.utcnow()
            from backend.app.services.demand_intelligence import get_h3_zone
            kochi_edappally_zone = get_h3_zone(10.0284, 76.3074)
            kochi_airport_zone = get_h3_zone(10.1518, 76.3930)
            blr_indiranagar_zone = get_h3_zone(12.9718, 77.6411)

            seed_observations = []
            providers_sample = [
                ("Uber", "Cab", 1.8, "SLIGHTLY HIGH"),
                ("Ola", "Cab", 1.1, "NORMAL"),
                ("Rapido", "Auto", 2.9, "HIGH"),
                ("Rapido", "Bike", 3.2, "HIGH"),
                ("Local Taxi", "Cab", 0.4, "LOW"),
            ]

            for offset_hours in [1, 2, 4, 8, 16, 24, 48, 72]:
                obs_time = now - timedelta(hours=offset_hours)
                for prov, cat, score, level in providers_sample:
                    seed_observations.append(
                        DemandObservation(
                            timestamp=obs_time,
                            provider=prov,
                            pickup_zone=kochi_edappally_zone,
                            destination_zone=kochi_airport_zone,
                            ride_category=cat,
                            observed_fare_if_available=None,
                            observed_demand_signal=None,
                            observed_supply_signal=None,
                            traffic_level=1.2,
                            distance_km=21.5,
                            duration_min=42.0,
                            pricing_pressure_score=score,
                            demand_level=level,
                            confidence=0.82,
                            source_type="ml_estimate",
                            reason="Historical baseline observation for this zone.",
                            actual_observation_when_available=None
                        )
                    )
                    seed_observations.append(
                        DemandObservation(
                            timestamp=obs_time,
                            provider=prov,
                            pickup_zone=blr_indiranagar_zone,
                            destination_zone=get_h3_zone(12.9351, 77.6244),
                            ride_category=cat,
                            observed_fare_if_available=None,
                            observed_demand_signal=None,
                            observed_supply_signal=None,
                            traffic_level=1.4,
                            distance_km=5.8,
                            duration_min=20.0,
                            pricing_pressure_score=score,
                            demand_level=level,
                            confidence=0.85,
                            source_type="ml_estimate",
                            reason="Historical baseline observation for this zone.",
                            actual_observation_when_available=None
                        )
                    )
            db.add_all(seed_observations)
            db.commit()

        if db.query(Location).count() == 0:
            now = datetime.utcnow()
            popular_locations = [
                Location(
                    normalized_query="lulu mall",
                    place_name="LuLu International Shopping Mall",
                    display_name="LuLu International Shopping Mall, Edappally, Kochi, Kerala",
                    latitude=10.0284,
                    longitude=76.3074,
                    house_number="34/1000",
                    road="Old NH 47",
                    suburb="Edappally",
                    city="Kochi",
                    district="Ernakulam",
                    state="Kerala",
                    postcode="682024",
                    country="India",
                    provider="photon",
                    provider_place_id="way:248569804",
                    search_count=150,
                    created_at=now,
                    updated_at=now,
                    last_verified_at=now
                ),
                Location(
                    normalized_query="kochi airport",
                    place_name="Cochin International Airport (COK)",
                    display_name="Cochin International Airport, Nedumbassery, Kochi, Kerala",
                    latitude=10.1518,
                    longitude=76.3930,
                    road="Airport Road",
                    suburb="Nedumbassery",
                    city="Kochi",
                    district="Ernakulam",
                    state="Kerala",
                    postcode="683111",
                    country="India",
                    provider="photon",
                    provider_place_id="way:43219874",
                    search_count=120,
                    created_at=now,
                    updated_at=now,
                    last_verified_at=now
                ),
                Location(
                    normalized_query="ernakulam south",
                    place_name="Ernakulam South Railway Station",
                    display_name="Ernakulam Junction (South), Station Road, Kochi, Kerala",
                    latitude=9.9678,
                    longitude=76.2925,
                    road="Station Road",
                    suburb="South",
                    city="Kochi",
                    district="Ernakulam",
                    state="Kerala",
                    postcode="682016",
                    country="India",
                    provider="photon",
                    provider_place_id="node:12345091",
                    search_count=95,
                    created_at=now,
                    updated_at=now,
                    last_verified_at=now
                ),
                Location(
                    normalized_query="aluva metro station",
                    place_name="Aluva Metro Station",
                    display_name="Aluva Metro Station, Aluva, Ernakulam, Kerala",
                    latitude=10.1098,
                    longitude=76.3488,
                    road="Aluva - Munnar Road",
                    suburb="Aluva",
                    city="Kochi",
                    district="Ernakulam",
                    state="Kerala",
                    postcode="683101",
                    country="India",
                    provider="photon",
                    provider_place_id="node:78945612",
                    search_count=90,
                    created_at=now,
                    updated_at=now,
                    last_verified_at=now
                ),
                Location(
                    normalized_query="kalamassery",
                    place_name="Kalamassery",
                    display_name="Kalamassery, Ernakulam, Kerala",
                    latitude=10.0545,
                    longitude=76.3190,
                    suburb="Kalamassery",
                    city="Kochi",
                    district="Ernakulam",
                    state="Kerala",
                    postcode="682033",
                    country="India",
                    provider="photon",
                    provider_place_id="place:98765432",
                    search_count=85,
                    created_at=now,
                    updated_at=now,
                    last_verified_at=now
                ),
                Location(
                    normalized_query="vyttila mobility hub",
                    place_name="Vyttila Mobility Hub",
                    display_name="Vyttila Mobility Hub, Vyttila, Kochi, Kerala",
                    latitude=9.9687,
                    longitude=76.3183,
                    suburb="Vyttila",
                    city="Kochi",
                    district="Ernakulam",
                    state="Kerala",
                    postcode="682019",
                    country="India",
                    provider="photon",
                    provider_place_id="way:33445566",
                    search_count=80,
                    created_at=now,
                    updated_at=now,
                    last_verified_at=now
                ),
                Location(
                    normalized_query="fort kochi",
                    place_name="Fort Kochi",
                    display_name="Fort Kochi, Kochi, Ernakulam, Kerala",
                    latitude=9.9658,
                    longitude=76.2425,
                    suburb="Fort Kochi",
                    city="Kochi",
                    district="Ernakulam",
                    state="Kerala",
                    postcode="682001",
                    country="India",
                    provider="photon",
                    provider_place_id="place:55667788",
                    search_count=75,
                    created_at=now,
                    updated_at=now,
                    last_verified_at=now
                ),
                Location(
                    normalized_query="mg road kochi",
                    place_name="MG Road, Kochi",
                    display_name="Mahatma Gandhi Road, Ernakulam, Kochi, Kerala",
                    latitude=9.9723,
                    longitude=76.2784,
                    road="Mahatma Gandhi Road",
                    suburb="Ernakulam",
                    city="Kochi",
                    district="Ernakulam",
                    state="Kerala",
                    postcode="682011",
                    country="India",
                    provider="photon",
                    provider_place_id="way:11223344",
                    search_count=70,
                    created_at=now,
                    updated_at=now,
                    last_verified_at=now
                ),
                Location(
                    normalized_query="infopark kochi",
                    place_name="Infopark Kochi",
                    display_name="Infopark Kochi, Kakkanad, Ernakulam, Kerala",
                    latitude=10.0104,
                    longitude=76.3638,
                    road="Infopark Expressway",
                    suburb="Kakkanad",
                    city="Kochi",
                    district="Ernakulam",
                    state="Kerala",
                    postcode="682042",
                    country="India",
                    provider="photon",
                    provider_place_id="way:99887766",
                    search_count=65,
                    created_at=now,
                    updated_at=now,
                    last_verified_at=now
                ),
                Location(
                    normalized_query="edappally",
                    place_name="Edappally",
                    display_name="Edappally, Kochi, Ernakulam, Kerala",
                    latitude=10.0244,
                    longitude=76.3082,
                    suburb="Edappally",
                    city="Kochi",
                    district="Ernakulam",
                    state="Kerala",
                    postcode="682024",
                    country="India",
                    provider="mapbox",
                    provider_place_id="mbx:poi:edappally",
                    search_count=60,
                    created_at=now,
                    updated_at=now,
                    last_verified_at=now
                ),
                Location(
                    normalized_query="times square",
                    place_name="Times Square",
                    display_name="Times Square, Manhattan, New York, NY, United States",
                    latitude=40.7580,
                    longitude=-73.9855,
                    road="Broadway",
                    suburb="Manhattan",
                    city="New York",
                    district="New York County",
                    state="New York",
                    postcode="10036",
                    country="United States",
                    provider="mapbox",
                    provider_place_id="mbx:poi:times_square",
                    search_count=100,
                    created_at=now,
                    updated_at=now,
                    last_verified_at=now
                ),
                Location(
                    normalized_query="new york",
                    place_name="New York",
                    display_name="New York, NY, United States",
                    latitude=40.7128,
                    longitude=-74.0060,
                    suburb="Manhattan",
                    city="New York",
                    district="New York County",
                    state="New York",
                    postcode="10007",
                    country="United States",
                    provider="mapbox",
                    provider_place_id="mbx:place:new_york",
                    search_count=110,
                    created_at=now,
                    updated_at=now,
                    last_verified_at=now
                ),
                Location(
                    normalized_query="london bridge",
                    place_name="London Bridge",
                    display_name="London Bridge, London, Greater London, United Kingdom",
                    latitude=51.5079,
                    longitude=-0.0877,
                    road="London Bridge",
                    suburb="Southwark",
                    city="London",
                    district="Greater London",
                    state="England",
                    postcode="SE1 9RA",
                    country="United Kingdom",
                    provider="mapbox",
                    provider_place_id="mbx:poi:london_bridge",
                    search_count=95,
                    created_at=now,
                    updated_at=now,
                    last_verified_at=now
                ),
                Location(
                    normalized_query="berlin hauptbahnhof",
                    place_name="Berlin Hauptbahnhof",
                    display_name="Berlin Hauptbahnhof, Europaplatz 1, 10557 Berlin, Germany",
                    latitude=52.5251,
                    longitude=13.3694,
                    road="Europaplatz",
                    house_number="1",
                    suburb="Mitte",
                    city="Berlin",
                    state="Berlin",
                    postcode="10557",
                    country="Germany",
                    provider="mapbox",
                    provider_place_id="mbx:poi:berlin_hbf",
                    search_count=90,
                    created_at=now,
                    updated_at=now,
                    last_verified_at=now
                ),
                Location(
                    normalized_query="burj khalifa",
                    place_name="Burj Khalifa",
                    display_name="Burj Khalifa, 1 Sheikh Mohammed bin Rashid Blvd, Downtown Dubai, Dubai, UAE",
                    latitude=25.1972,
                    longitude=55.2744,
                    road="Sheikh Mohammed bin Rashid Blvd",
                    house_number="1",
                    suburb="Downtown Dubai",
                    city="Dubai",
                    state="Dubai",
                    country="United Arab Emirates",
                    provider="mapbox",
                    provider_place_id="mbx:poi:burj_khalifa",
                    search_count=105,
                    created_at=now,
                    updated_at=now,
                    last_verified_at=now
                ),
                Location(
                    normalized_query="shibuya station",
                    place_name="Shibuya Station",
                    display_name="Shibuya Station, Dogenzaka, Shibuya, Tokyo, Japan",
                    latitude=35.6580,
                    longitude=139.7016,
                    suburb="Dogenzaka",
                    city="Shibuya",
                    district="Tokyo",
                    state="Tokyo",
                    postcode="150-0043",
                    country="Japan",
                    provider="mapbox",
                    provider_place_id="mbx:poi:shibuya_station",
                    search_count=95,
                    created_at=now,
                    updated_at=now,
                    last_verified_at=now
                ),
                Location(
                    normalized_query="marina bay sands",
                    place_name="Marina Bay Sands",
                    display_name="Marina Bay Sands, 10 Bayfront Avenue, Singapore",
                    latitude=1.2834,
                    longitude=103.8607,
                    road="Bayfront Avenue",
                    house_number="10",
                    city="Singapore",
                    postcode="018956",
                    country="Singapore",
                    provider="mapbox",
                    provider_place_id="mbx:poi:marina_bay_sands",
                    search_count=90,
                    created_at=now,
                    updated_at=now,
                    last_verified_at=now
                ),
                Location(
                    normalized_query="sydney opera house",
                    place_name="Sydney Opera House",
                    display_name="Sydney Opera House, Bennelong Point, Sydney, NSW 2000, Australia",
                    latitude=-33.8568,
                    longitude=151.2153,
                    road="Bennelong Point",
                    suburb="Sydney",
                    city="Sydney",
                    state="New South Wales",
                    postcode="2000",
                    country="Australia",
                    provider="mapbox",
                    provider_place_id="mbx:poi:sydney_opera_house",
                    search_count=95,
                    created_at=now,
                    updated_at=now,
                    last_verified_at=now
                )
            ]
            db.add_all(popular_locations)
            db.commit()
            logger.info("Initialized default seed records and popular locations into database.")
    except Exception as err:
        logger.error("Database initialization encountered an error: %s", err)
        db.rollback()
    finally:
        db.close()
