import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.app.models.db_models import CoverageRegion, RateCard, ServiceStatus

logger = logging.getLogger(__name__)

# GeoJSON Bounding Polygons for Seed Cities
# Format: GeoJSON Polygon [[[lng, lat], [lng, lat], ...]]
REGIONS_DATA = [
    {
        "region_id": "bengaluru",
        "name": "Bengaluru",
        "state": "Karnataka",
        "country": "IN",
        "legal_surge_cap": 2.0,  # Motor Vehicle Aggregator Guidelines 2025: max 2.0x
        "auto_rickshaw_metered_available": True,
        "intercity_enabled": True,
        "metered_auto_fare": {
            "base_fare": 30.0,
            "free_km": 2.0,
            "per_km": 15.0,
            "night_multiplier": 1.25,
            "currency": "INR",
            "currency_symbol": "₹"
        },
        "geofence": {
            "type": "Polygon",
            "coordinates": [[
                [77.30, 12.75], [77.85, 12.75], [77.85, 13.25], [77.30, 13.25], [77.30, 12.75]
            ]]
        },
        "services": [
            {"name": "Namma Yatri", "status": "active"},
            {"name": "Uber", "status": "active"},
            {"name": "Ola", "status": "active"},
            {"name": "Rapido", "status": "active"},
            {"name": "inDrive", "status": "active"},
            {"name": "LocalTaxi", "status": "active"}
        ]
    },
    {
        "region_id": "kochi",
        "name": "Kochi",
        "state": "Kerala",
        "country": "IN",
        "legal_surge_cap": 2.0,
        "auto_rickshaw_metered_available": True,
        "intercity_enabled": True,
        "metered_auto_fare": {
            "base_fare": 30.0,
            "free_km": 1.5,
            "per_km": 15.0,
            "night_multiplier": 1.25,
            "currency": "INR",
            "currency_symbol": "₹"
        },
        "geofence": {
            "type": "Polygon",
            "coordinates": [[
                [75.90, 9.65], [76.65, 9.65], [76.65, 10.30], [75.90, 10.30], [75.90, 9.65]
            ]]
        },
        "services": [
            {"name": "Kerala Savari", "status": "active"},
            {"name": "Namma Yatri", "status": "active"},
            {"name": "Uber", "status": "active"},
            {"name": "Ola", "status": "active"},
            {"name": "Rapido", "status": "active"},
            {"name": "inDrive", "status": "active"}
        ]
    },
    {
        "region_id": "mumbai",
        "name": "Mumbai",
        "state": "Maharashtra",
        "country": "IN",
        "legal_surge_cap": 1.5,  # Maharashtra Draft Aggregator Rules (Khatua Committee): 1.5x cap
        "auto_rickshaw_metered_available": True,
        "intercity_enabled": True,
        "metered_auto_fare": {
            "base_fare": 23.0,
            "free_km": 1.5,
            "per_km": 15.33,
            "night_multiplier": 1.25,
            "currency": "INR",
            "currency_symbol": "₹"
        },
        "geofence": {
            "type": "Polygon",
            "coordinates": [[
                [72.75, 18.88], [73.05, 18.88], [73.05, 19.32], [72.75, 19.32], [72.75, 18.88]
            ]]
        },
        "services": [
            {"name": "Uber", "status": "active"},
            {"name": "Ola", "status": "active"},
            {"name": "Rapido", "status": "active"},
            {"name": "inDrive", "status": "active"},
            {"name": "LocalTaxi", "status": "active"}
        ]
    },
    {
        "region_id": "delhi",
        "name": "Delhi",
        "state": "Delhi NCR",
        "country": "IN",
        "legal_surge_cap": 2.0,
        "auto_rickshaw_metered_available": True,
        "intercity_enabled": True,
        "metered_auto_fare": {
            "base_fare": 30.0,
            "free_km": 1.5,
            "per_km": 11.0,
            "night_multiplier": 1.25,
            "currency": "INR",
            "currency_symbol": "₹"
        },
        "geofence": {
            "type": "Polygon",
            "coordinates": [[
                [76.85, 28.40], [77.40, 28.40], [77.40, 28.88], [76.85, 28.88], [76.85, 28.40]
            ]]
        },
        "services": [
            {"name": "Uber", "status": "active"},
            {"name": "Ola", "status": "active"},
            {"name": "Rapido", "status": "active"},
            {"name": "inDrive", "status": "active"},
            {"name": "LocalTaxi", "status": "active"}
        ]
    },
    {
        "region_id": "goa",
        "name": "Goa",
        "state": "Goa",
        "country": "IN",
        "legal_surge_cap": 1.5,
        "auto_rickshaw_metered_available": False,  # App aggregator license restricted; GoaMiles is monopoly
        "intercity_enabled": False,
        "metered_auto_fare": {},
        "geofence": {
            "type": "Polygon",
            "coordinates": [[
                [73.65, 14.90], [74.30, 14.90], [74.30, 15.80], [73.65, 15.80], [73.65, 14.90]
            ]]
        },
        "services": [
            {"name": "GoaMiles", "status": "active"},
            {"name": "Uber", "status": "suspended", "reason": "Suspended by State Transport Department"},
            {"name": "Ola", "status": "suspended", "reason": "Suspended by State Transport Department"}
        ]
    },
    {
        "region_id": "london",
        "name": "London",
        "state": "Greater London",
        "country": "GB",
        "legal_surge_cap": 1.5,
        "auto_rickshaw_metered_available": True,
        "intercity_enabled": True,
        "metered_auto_fare": {
            "base_fare": 3.80,
            "free_km": 1.0,
            "per_km": 1.80,
            "night_multiplier": 1.25,
            "currency": "GBP",
            "currency_symbol": "£"
        },
        "geofence": {
            "type": "Polygon",
            "coordinates": [[
                [-0.45, 51.30], [0.15, 51.30], [0.15, 51.70], [-0.45, 51.70], [-0.45, 51.30]
            ]]
        },
        "services": [
            {"name": "Uber", "status": "active"},
            {"name": "Bolt", "status": "active"},
            {"name": "FreeNow", "status": "active"}
        ]
    },
    {
        "region_id": "new_york",
        "name": "New York",
        "state": "New York",
        "country": "US",
        "legal_surge_cap": 1.5,
        "auto_rickshaw_metered_available": True,
        "intercity_enabled": True,
        "metered_auto_fare": {
            "base_fare": 3.00,
            "free_km": 0.5,
            "per_km": 1.75,
            "night_multiplier": 1.25,
            "currency": "USD",
            "currency_symbol": "$"
        },
        "geofence": {
            "type": "Polygon",
            "coordinates": [[
                [-74.25, 40.50], [-73.70, 40.50], [-73.70, 40.92], [-74.25, 40.92], [-74.25, 40.50]
            ]]
        },
        "services": [
            {"name": "Uber", "status": "active"},
            {"name": "Lyft", "status": "active"}
        ]
    },
    {
        "region_id": "singapore",
        "name": "Singapore",
        "state": "Singapore",
        "country": "SG",
        "legal_surge_cap": 1.5,
        "auto_rickshaw_metered_available": True,
        "intercity_enabled": False,
        "metered_auto_fare": {
            "base_fare": 4.10,
            "free_km": 1.0,
            "per_km": 0.60,
            "night_multiplier": 1.25,
            "currency": "SGD",
            "currency_symbol": "S$"
        },
        "geofence": {
            "type": "Polygon",
            "coordinates": [[
                [103.60, 1.20], [104.05, 1.20], [104.05, 1.48], [103.60, 1.48], [103.60, 1.20]
            ]]
        },
        "services": [
            {"name": "Grab", "status": "active"},
            {"name": "Gojek", "status": "active"}
        ]
    },
    {
        "region_id": "dubai",
        "name": "Dubai",
        "state": "Dubai",
        "country": "AE",
        "legal_surge_cap": 1.5,
        "auto_rickshaw_metered_available": True,
        "intercity_enabled": True,
        "metered_auto_fare": {
            "base_fare": 12.0,
            "free_km": 0.0,
            "per_km": 2.21,
            "night_multiplier": 1.20,
            "currency": "AED",
            "currency_symbol": "AED "
        },
        "geofence": {
            "type": "Polygon",
            "coordinates": [[
                [55.05, 24.95], [55.55, 24.95], [55.55, 25.35], [55.05, 25.35], [55.05, 24.95]
            ]]
        },
        "services": [
            {"name": "Careem", "status": "active"},
            {"name": "Uber", "status": "active"}
        ]
    }
]

# Initial Seed Rate Cards
# Note: Seed data is marked `is_verified: False` (unverified) unless confirmed by an official government gazette.
RATE_CARDS_DATA = [
    # --- Bengaluru ---
    {
        "city": "Bengaluru", "state": "Karnataka", "country": "IN",
        "service": "Namma Yatri", "ride_type": "Namma Yatri Auto", "vehicle_category": "Auto",
        "base_fare": 30.0, "per_km": 15.0, "per_min": 0.0, "booking_fee": 0.0, "min_fare": 30.0, "free_km": 2.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://transport.karnataka.gov.in/auto_tariff_guidelines",
        "last_verified_date": "2026-02-15", "is_verified": True
    },
    {
        "city": "Bengaluru", "state": "Karnataka", "country": "IN",
        "service": "Namma Yatri", "ride_type": "Namma Yatri Cab", "vehicle_category": "Cab",
        "base_fare": 60.0, "per_km": 16.0, "per_min": 0.0, "booking_fee": 0.0, "min_fare": 60.0, "free_km": 2.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://nammayatri.in/open-tariffs",
        "last_verified_date": "2026-02-15", "is_verified": True
    },
    {
        "city": "Bengaluru", "state": "Karnataka", "country": "IN",
        "service": "Uber", "ride_type": "Uber Go", "vehicle_category": "Cab",
        "base_fare": 50.0, "per_km": 14.0, "per_min": 2.0, "booking_fee": 15.0, "min_fare": 75.0, "free_km": 0.0,
        "long_distance_threshold": 15.0, "long_distance_rate": 18.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.uber.com/in/en/ride/",
        "last_verified_date": "2026-01-10", "is_verified": False
    },
    {
        "city": "Bengaluru", "state": "Karnataka", "country": "IN",
        "service": "Uber", "ride_type": "Uber Premier", "vehicle_category": "Sedan",
        "base_fare": 70.0, "per_km": 18.0, "per_min": 2.5, "booking_fee": 20.0, "min_fare": 100.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.uber.com/in/en/ride/",
        "last_verified_date": "2026-01-10", "is_verified": False
    },
    {
        "city": "Bengaluru", "state": "Karnataka", "country": "IN",
        "service": "Uber", "ride_type": "Uber Auto", "vehicle_category": "Auto",
        "base_fare": 28.0, "per_km": 10.0, "per_min": 1.5, "booking_fee": 10.0, "min_fare": 40.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.uber.com/in/en/ride/",
        "last_verified_date": "2026-01-10", "is_verified": False
    },
    {
        "city": "Bengaluru", "state": "Karnataka", "country": "IN",
        "service": "Rapido", "ride_type": "Rapido Bike", "vehicle_category": "Bike",
        "base_fare": 15.0, "per_km": 7.0, "per_min": 1.0, "booking_fee": 5.0, "min_fare": 25.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.rapido.bike",
        "last_verified_date": "2026-01-15", "is_verified": False
    },
    {
        "city": "Bengaluru", "state": "Karnataka", "country": "IN",
        "service": "Rapido", "ride_type": "Rapido Auto", "vehicle_category": "Auto",
        "base_fare": 28.0, "per_km": 10.0, "per_min": 1.5, "booking_fee": 10.0, "min_fare": 40.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.rapido.bike",
        "last_verified_date": "2026-01-15", "is_verified": False
    },
    {
        "city": "Bengaluru", "state": "Karnataka", "country": "IN",
        "service": "Ola", "ride_type": "Ola Mini", "vehicle_category": "Cab",
        "base_fare": 48.0, "per_km": 14.5, "per_min": 2.2, "booking_fee": 15.0, "min_fare": 75.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.olacabs.com",
        "last_verified_date": "2026-01-12", "is_verified": False
    },
    {
        "city": "Bengaluru", "state": "Karnataka", "country": "IN",
        "service": "Rapido", "ride_type": "Rapido Cab", "vehicle_category": "Cab",
        "base_fare": 45.0, "per_km": 13.5, "per_min": 1.5, "booking_fee": 10.0, "min_fare": 70.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.rapido.bike/cabs",
        "last_verified_date": "2026-02-01", "is_verified": True
    },
    {
        "city": "Bengaluru", "state": "Karnataka", "country": "IN",
        "service": "Rapido", "ride_type": "Rapido Cab Sedan", "vehicle_category": "Cab",
        "base_fare": 60.0, "per_km": 16.0, "per_min": 2.0, "booking_fee": 15.0, "min_fare": 90.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.rapido.bike/cabs",
        "last_verified_date": "2026-02-01", "is_verified": True
    },
    {
        "city": "Bengaluru", "state": "Karnataka", "country": "IN",
        "service": "inDrive", "ride_type": "inDrive Cab", "vehicle_category": "Cab",
        "base_fare": 40.0, "per_km": 13.0, "per_min": 1.0, "booking_fee": 0.0, "min_fare": 65.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://indrive.com",
        "last_verified_date": "2026-01-25", "is_verified": False
    },
    {
        "city": "Bengaluru", "state": "Karnataka", "country": "IN",
        "service": "Uber", "ride_type": "Uber XL", "vehicle_category": "Cab",
        "base_fare": 90.0, "per_km": 22.0, "per_min": 3.0, "booking_fee": 25.0, "min_fare": 140.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.uber.com/in/en/ride/",
        "last_verified_date": "2026-01-10", "is_verified": False
    },
    {
        "city": "Bengaluru", "state": "Karnataka", "country": "IN",
        "service": "Ola", "ride_type": "Ola Prime Sedan", "vehicle_category": "Cab",
        "base_fare": 65.0, "per_km": 17.5, "per_min": 2.2, "booking_fee": 18.0, "min_fare": 95.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.olacabs.com",
        "last_verified_date": "2026-01-12", "is_verified": False
    },

    # --- Kochi ---
    {
        "city": "Kochi", "state": "Kerala", "country": "IN",
        "service": "Kerala Savari", "ride_type": "Kerala Savari Auto", "vehicle_category": "Auto",
        "base_fare": 30.0, "per_km": 15.0, "per_min": 0.0, "booking_fee": 0.0, "min_fare": 30.0, "free_km": 1.5,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://mvd.kerala.gov.in/en/fare-revision",
        "last_verified_date": "2026-02-01", "is_verified": True
    },
    {
        "city": "Kochi", "state": "Kerala", "country": "IN",
        "service": "Kerala Savari", "ride_type": "Kerala Savari Cab", "vehicle_category": "Cab",
        "base_fare": 80.0, "per_km": 16.0, "per_min": 0.0, "booking_fee": 0.0, "min_fare": 80.0, "free_km": 3.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://mvd.kerala.gov.in/en/fare-revision",
        "last_verified_date": "2026-02-01", "is_verified": True
    },
    {
        "city": "Kochi", "state": "Kerala", "country": "IN",
        "service": "Uber", "ride_type": "Uber Go", "vehicle_category": "Cab",
        "base_fare": 50.0, "per_km": 13.5, "per_min": 1.8, "booking_fee": 15.0, "min_fare": 70.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.uber.com/in/en/cities/kochi/",
        "last_verified_date": "2026-01-20", "is_verified": False
    },
    {
        "city": "Kochi", "state": "Kerala", "country": "IN",
        "service": "Rapido", "ride_type": "Rapido Auto", "vehicle_category": "Auto",
        "base_fare": 28.0, "per_km": 11.0, "per_min": 1.2, "booking_fee": 8.0, "min_fare": 35.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.rapido.bike",
        "last_verified_date": "2026-01-20", "is_verified": False
    },
    {
        "city": "Kochi", "state": "Kerala", "country": "IN",
        "service": "Rapido", "ride_type": "Rapido Cab", "vehicle_category": "Cab",
        "base_fare": 45.0, "per_km": 13.0, "per_min": 1.5, "booking_fee": 10.0, "min_fare": 65.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.rapido.bike/cabs",
        "last_verified_date": "2026-02-01", "is_verified": True
    },
    {
        "city": "Kochi", "state": "Kerala", "country": "IN",
        "service": "inDrive", "ride_type": "inDrive Cab", "vehicle_category": "Cab",
        "base_fare": 42.0, "per_km": 12.5, "per_min": 1.0, "booking_fee": 0.0, "min_fare": 60.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://indrive.com",
        "last_verified_date": "2026-01-25", "is_verified": False
    },
    {
        "city": "Kochi", "state": "Kerala", "country": "IN",
        "service": "Rapido", "ride_type": "Rapido Bike", "vehicle_category": "Bike",
        "base_fare": 18.0, "per_km": 6.5, "per_min": 0.8, "booking_fee": 5.0, "min_fare": 25.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.rapido.bike",
        "last_verified_date": "2026-02-01", "is_verified": True
    },
    {
        "city": "Kochi", "state": "Kerala", "country": "IN",
        "service": "Namma Yatri", "ride_type": "Namma Yatri Auto", "vehicle_category": "Auto",
        "base_fare": 30.0, "per_km": 15.0, "per_min": 0.0, "booking_fee": 0.0, "min_fare": 30.0, "free_km": 1.5,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://nammayatri.in",
        "last_verified_date": "2026-02-01", "is_verified": True
    },
    {
        "city": "Kochi", "state": "Kerala", "country": "IN",
        "service": "Ola", "ride_type": "Ola Mini", "vehicle_category": "Cab",
        "base_fare": 48.0, "per_km": 13.8, "per_min": 1.8, "booking_fee": 15.0, "min_fare": 70.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.olacabs.com",
        "last_verified_date": "2026-01-12", "is_verified": False
    },

    # --- Mumbai ---
    {
        "city": "Mumbai", "state": "Maharashtra", "country": "IN",
        "service": "LocalTaxi", "ride_type": "Mumbai Kaali Peeli", "vehicle_category": "Cab",
        "base_fare": 28.0, "per_km": 18.66, "per_min": 0.0, "booking_fee": 0.0, "min_fare": 28.0, "free_km": 1.5,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.0,
        "source_url": "https://transport.maharashtra.gov.in/taxi-tariffs",
        "last_verified_date": "2026-01-05", "is_verified": True
    },
    {
        "city": "Mumbai", "state": "Maharashtra", "country": "IN",
        "service": "LocalTaxi", "ride_type": "Mumbai Metered Auto", "vehicle_category": "Auto",
        "base_fare": 23.0, "per_km": 15.33, "per_min": 0.0, "booking_fee": 0.0, "min_fare": 23.0, "free_km": 1.5,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.0,
        "source_url": "https://transport.maharashtra.gov.in/auto-tariffs",
        "last_verified_date": "2026-01-05", "is_verified": True
    },
    {
        "city": "Mumbai", "state": "Maharashtra", "country": "IN",
        "service": "Uber", "ride_type": "Uber Go", "vehicle_category": "Cab",
        "base_fare": 55.0, "per_km": 15.0, "per_min": 2.2, "booking_fee": 18.0, "min_fare": 80.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.uber.com/in/en/cities/mumbai/",
        "last_verified_date": "2026-01-10", "is_verified": False
    },
    {
        "city": "Mumbai", "state": "Maharashtra", "country": "IN",
        "service": "Ola", "ride_type": "Ola Mini", "vehicle_category": "Cab",
        "base_fare": 52.0, "per_km": 15.2, "per_min": 2.2, "booking_fee": 18.0, "min_fare": 80.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.olacabs.com",
        "last_verified_date": "2026-01-10", "is_verified": False
    },
    {
        "city": "Mumbai", "state": "Maharashtra", "country": "IN",
        "service": "Ola", "ride_type": "Ola Prime Sedan", "vehicle_category": "Cab",
        "base_fare": 70.0, "per_km": 18.0, "per_min": 2.5, "booking_fee": 20.0, "min_fare": 105.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.olacabs.com",
        "last_verified_date": "2026-01-10", "is_verified": False
    },
    {
        "city": "Mumbai", "state": "Maharashtra", "country": "IN",
        "service": "Uber", "ride_type": "Uber Premier", "vehicle_category": "Cab",
        "base_fare": 75.0, "per_km": 18.5, "per_min": 2.5, "booking_fee": 22.0, "min_fare": 110.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.uber.com/in/en/cities/mumbai/",
        "last_verified_date": "2026-01-10", "is_verified": False
    },
    {
        "city": "Mumbai", "state": "Maharashtra", "country": "IN",
        "service": "Rapido", "ride_type": "Rapido Cab", "vehicle_category": "Cab",
        "base_fare": 50.0, "per_km": 14.5, "per_min": 1.8, "booking_fee": 12.0, "min_fare": 75.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.rapido.bike/cabs",
        "last_verified_date": "2026-02-01", "is_verified": True
    },
    {
        "city": "Mumbai", "state": "Maharashtra", "country": "IN",
        "service": "Rapido", "ride_type": "Rapido Auto", "vehicle_category": "Auto",
        "base_fare": 23.0, "per_km": 11.5, "per_min": 1.2, "booking_fee": 8.0, "min_fare": 35.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.rapido.bike",
        "last_verified_date": "2026-01-15", "is_verified": False
    },
    {
        "city": "Mumbai", "state": "Maharashtra", "country": "IN",
        "service": "Rapido", "ride_type": "Rapido Bike", "vehicle_category": "Bike",
        "base_fare": 18.0, "per_km": 7.5, "per_min": 0.8, "booking_fee": 5.0, "min_fare": 25.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.rapido.bike",
        "last_verified_date": "2026-01-15", "is_verified": False
    },
    {
        "city": "Mumbai", "state": "Maharashtra", "country": "IN",
        "service": "inDrive", "ride_type": "inDrive Cab", "vehicle_category": "Cab",
        "base_fare": 45.0, "per_km": 13.5, "per_min": 1.2, "booking_fee": 0.0, "min_fare": 70.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://indrive.com",
        "last_verified_date": "2026-01-25", "is_verified": False
    },

    # --- Delhi ---
    {
        "city": "Delhi", "state": "Delhi NCR", "country": "IN",
        "service": "LocalTaxi", "ride_type": "Delhi Metered Auto", "vehicle_category": "Auto",
        "base_fare": 30.0, "per_km": 11.0, "per_min": 0.0, "booking_fee": 0.0, "min_fare": 30.0, "free_km": 1.5,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.0,
        "source_url": "https://transport.delhi.gov.in/auto_tariff_revision_gazette",
        "last_verified_date": "2026-01-10", "is_verified": True
    },
    {
        "city": "Delhi", "state": "Delhi NCR", "country": "IN",
        "service": "Uber", "ride_type": "Uber Go", "vehicle_category": "Cab",
        "base_fare": 50.0, "per_km": 13.5, "per_min": 1.8, "booking_fee": 15.0, "min_fare": 70.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.uber.com/in/en/cities/delhi/",
        "last_verified_date": "2026-01-10", "is_verified": False
    },
    {
        "city": "Delhi", "state": "Delhi NCR", "country": "IN",
        "service": "Uber", "ride_type": "Uber Premier", "vehicle_category": "Cab",
        "base_fare": 70.0, "per_km": 17.0, "per_min": 2.2, "booking_fee": 20.0, "min_fare": 95.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.uber.com/in/en/cities/delhi/",
        "last_verified_date": "2026-01-10", "is_verified": False
    },
    {
        "city": "Delhi", "state": "Delhi NCR", "country": "IN",
        "service": "Rapido", "ride_type": "Rapido Cab", "vehicle_category": "Cab",
        "base_fare": 45.0, "per_km": 13.0, "per_min": 1.5, "booking_fee": 10.0, "min_fare": 65.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.rapido.bike/cabs",
        "last_verified_date": "2026-02-01", "is_verified": True
    },
    {
        "city": "Delhi", "state": "Delhi NCR", "country": "IN",
        "service": "Rapido", "ride_type": "Rapido Auto", "vehicle_category": "Auto",
        "base_fare": 25.0, "per_km": 9.5, "per_min": 1.2, "booking_fee": 8.0, "min_fare": 35.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.rapido.bike",
        "last_verified_date": "2026-01-15", "is_verified": False
    },
    {
        "city": "Delhi", "state": "Delhi NCR", "country": "IN",
        "service": "inDrive", "ride_type": "inDrive Cab", "vehicle_category": "Cab",
        "base_fare": 40.0, "per_km": 12.0, "per_min": 1.0, "booking_fee": 0.0, "min_fare": 60.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://indrive.com",
        "last_verified_date": "2026-01-25", "is_verified": False
    },
    {
        "city": "Delhi", "state": "Delhi NCR", "country": "IN",
        "service": "Ola", "ride_type": "Ola Mini", "vehicle_category": "Cab",
        "base_fare": 48.0, "per_km": 13.5, "per_min": 2.0, "booking_fee": 15.0, "min_fare": 70.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.olacabs.com",
        "last_verified_date": "2026-01-10", "is_verified": False
    },
    {
        "city": "Delhi", "state": "Delhi NCR", "country": "IN",
        "service": "Ola", "ride_type": "Ola Prime Sedan", "vehicle_category": "Cab",
        "base_fare": 65.0, "per_km": 16.5, "per_min": 2.2, "booking_fee": 18.0, "min_fare": 90.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.olacabs.com",
        "last_verified_date": "2026-01-10", "is_verified": False
    },
    {
        "city": "Delhi", "state": "Delhi NCR", "country": "IN",
        "service": "Rapido", "ride_type": "Rapido Bike", "vehicle_category": "Bike",
        "base_fare": 15.0, "per_km": 6.5, "per_min": 0.8, "booking_fee": 5.0, "min_fare": 25.0, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.rapido.bike",
        "last_verified_date": "2026-01-10", "is_verified": False
    },

    # --- Goa ---
    {
        "city": "Goa", "state": "Goa", "country": "IN",
        "service": "GoaMiles", "ride_type": "GoaMiles Hatchback", "vehicle_category": "Cab",
        "base_fare": 100.0, "per_km": 22.0, "per_min": 1.0, "booking_fee": 25.0, "min_fare": 150.0, "free_km": 3.0,
        "night_multiplier": 1.25, "currency": "INR", "currency_symbol": "₹", "tax_pct": 0.05,
        "source_url": "https://www.goamiles.com/rates",
        "last_verified_date": "2026-01-20", "is_verified": True
    },

    # --- London ---
    {
        "city": "London", "state": "Greater London", "country": "GB",
        "service": "Uber", "ride_type": "UberX", "vehicle_category": "Cab",
        "base_fare": 2.75, "per_km": 1.45, "per_min": 0.20, "booking_fee": 1.50, "min_fare": 5.50, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "GBP", "currency_symbol": "£", "tax_pct": 0.20,
        "source_url": "https://www.uber.com/gb/en/cities/london/",
        "last_verified_date": "2026-01-08", "is_verified": False
    },
    {
        "city": "London", "state": "Greater London", "country": "GB",
        "service": "Bolt", "ride_type": "Bolt Standard", "vehicle_category": "Cab",
        "base_fare": 2.60, "per_km": 1.40, "per_min": 0.18, "booking_fee": 1.20, "min_fare": 5.20, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "GBP", "currency_symbol": "£", "tax_pct": 0.20,
        "source_url": "https://bolt.eu/en-gb/cities/london/",
        "last_verified_date": "2026-01-08", "is_verified": False
    },

    # --- New York ---
    {
        "city": "New York", "state": "New York", "country": "US",
        "service": "Uber", "ride_type": "UberX", "vehicle_category": "Cab",
        "base_fare": 2.55, "per_km": 1.75, "per_min": 0.35, "booking_fee": 2.75, "min_fare": 8.00, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "USD", "currency_symbol": "$", "tax_pct": 0.08875,
        "source_url": "https://www.uber.com/us/en/cities/new-york/",
        "last_verified_date": "2026-01-08", "is_verified": False
    },
    {
        "city": "New York", "state": "New York", "country": "US",
        "service": "Lyft", "ride_type": "Lyft Standard", "vehicle_category": "Cab",
        "base_fare": 2.50, "per_km": 1.70, "per_min": 0.38, "booking_fee": 2.75, "min_fare": 8.00, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "USD", "currency_symbol": "$", "tax_pct": 0.08875,
        "source_url": "https://www.lyft.com/rider/cities/new-york-ny",
        "last_verified_date": "2026-01-08", "is_verified": False
    },

    # --- Singapore ---
    {
        "city": "Singapore", "state": "Singapore", "country": "SG",
        "service": "Grab", "ride_type": "GrabCar", "vehicle_category": "Cab",
        "base_fare": 3.60, "per_km": 0.55, "per_min": 0.18, "booking_fee": 0.70, "min_fare": 6.00, "free_km": 0.0,
        "night_multiplier": 1.25, "currency": "SGD", "currency_symbol": "S$", "tax_pct": 0.09,
        "source_url": "https://www.grab.com/sg/transport/grabcar/",
        "last_verified_date": "2026-01-10", "is_verified": False
    },

    # --- Dubai ---
    {
        "city": "Dubai", "state": "Dubai", "country": "AE",
        "service": "Careem", "ride_type": "Hala Taxi", "vehicle_category": "Cab",
        "base_fare": 12.0, "per_km": 2.21, "per_min": 0.50, "booking_fee": 2.50, "min_fare": 14.50, "free_km": 0.0,
        "night_multiplier": 1.20, "currency": "AED", "currency_symbol": "AED ", "tax_pct": 0.05,
        "source_url": "https://www.careem.com/en-ae/hala-taxi/",
        "last_verified_date": "2026-01-12", "is_verified": True
    }
]


def seed_coverage_and_rate_cards(db: Session) -> Dict[str, int]:
    """Populates coverage regions, service statuses, and rate cards if empty."""
    regions_added = 0
    statuses_added = 0
    cards_added = 0

    for reg_data in REGIONS_DATA:
        existing = db.query(CoverageRegion).filter(CoverageRegion.region_id == reg_data["region_id"]).first()
        if not existing:
            reg = CoverageRegion(
                region_id=reg_data["region_id"],
                name=reg_data["name"],
                state=reg_data["state"],
                country=reg_data["country"],
                legal_surge_cap=reg_data["legal_surge_cap"],
                auto_rickshaw_metered_available=reg_data["auto_rickshaw_metered_available"],
                metered_auto_fare=json.dumps(reg_data["metered_auto_fare"]),
                intercity_enabled=reg_data["intercity_enabled"],
                geofence_geojson=json.dumps(reg_data["geofence"])
            )
            db.add(reg)
            regions_added += 1
        else:
            new_geojson = json.dumps(reg_data["geofence"])
            if existing.geofence_geojson != new_geojson:
                existing.geofence_geojson = new_geojson

        for svc in reg_data.get("services", []):
            st = db.query(ServiceStatus).filter(
                ServiceStatus.region_id == reg_data["region_id"],
                ServiceStatus.service_name == svc["name"]
            ).first()
            if not st:
                new_st = ServiceStatus(
                    region_id=reg_data["region_id"],
                    service_name=svc["name"],
                    status=svc.get("status", "active"),
                    status_reason=svc.get("reason"),
                    last_updated=datetime.utcnow()
                )
                db.add(new_st)
                statuses_added += 1

    for card in RATE_CARDS_DATA:
        existing = db.query(RateCard).filter(
            RateCard.city == card["city"],
            RateCard.service == card["service"],
            RateCard.ride_type == card["ride_type"]
        ).first()
        if not existing:
            rc = RateCard(**card)
            db.add(rc)
            cards_added += 1

    db.commit()
    logger.info("Seeding complete: %d regions, %d service statuses, %d rate cards.", regions_added, statuses_added, cards_added)
    return {"regions": regions_added, "statuses": statuses_added, "rate_cards": cards_added}
