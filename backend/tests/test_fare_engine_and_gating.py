import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.database import SessionLocal, init_db
from backend.app.models.db_models import CoverageRegion, RateCard, ServiceStatus
from backend.app.services.geo_fence import point_in_polygon, evaluate_trip_availability, resolve_region
from backend.app.services.fare_engine import (
    compute_fare_from_rate_card,
    calculate_surge_window,
    compute_metered_auto_estimate,
    haversine_distance
)

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()


def test_point_in_polygon_raycasting():
    # Polygon square around (10, 10) to (20, 20) in [lng, lat]
    square = [[10.0, 10.0], [20.0, 10.0], [20.0, 20.0], [10.0, 20.0], [10.0, 10.0]]

    # Inside point (lat=15, lng=15)
    assert point_in_polygon(lat=15.0, lng=15.0, polygon_coords=square) is True

    # Outside point (lat=25, lng=25)
    assert point_in_polygon(lat=25.0, lng=25.0, polygon_coords=square) is False

    # Outside point (lat=5, lng=15)
    assert point_in_polygon(lat=5.0, lng=15.0, polygon_coords=square) is False


def test_fare_formula_calculation():
    # Create mock rate card:
    # base 50, per_km 15, per_min 2, booking 10, min_fare 80, free_km 1.0, tax 5% (0.05)
    card = RateCard(
        city="TestCity", state="TestState", country="IN",
        service="TestCab", ride_type="Sedan", vehicle_category="Cab",
        base_fare=50.0, per_km=15.0, per_min=2.0, booking_fee=10.0,
        min_fare=80.0, free_km=1.0, tax_pct=0.05
    )

    # 10 km, 20 mins, surge 1.0
    # Billable km = 10 - 1 = 9 km.
    # Dist cost = 9 * 15 = 135.
    # Time cost = 20 * 2 = 40.
    # Subtotal = 50 + 135 + 40 + 10 = 235.
    # Min fare is 80 -> effective = 235.
    # Surge 1.0 -> 235 * 1.05 = 246.75 -> round = 246.8.
    fare = compute_fare_from_rate_card(card, distance_km=10.0, duration_min=20.0, surge=1.0)
    assert fare == 246.8

    # Test short trip below min_fare:
    # 0.5 km, 2 mins:
    # Billable km = 0.
    # Subtotal = 50 + 0 + 4 + 10 = 64.
    # Min fare is 80 -> effective = 80.
    # Tax 5% -> 80 * 1.05 = 84.0.
    short_fare = compute_fare_from_rate_card(card, distance_km=0.5, duration_min=2.0, surge=1.0)
    assert short_fare == 84.0


def test_long_distance_threshold_rate():
    card = RateCard(
        city="TestCity", state="TestState", country="IN",
        service="TestCab", ride_type="Sedan", vehicle_category="Cab",
        base_fare=0.0, per_km=10.0, per_min=0.0, booking_fee=0.0,
        min_fare=0.0, free_km=0.0, tax_pct=0.0,
        long_distance_threshold=15.0, long_distance_rate=20.0
    )

    # 25 km trip: 15 km @ 10 = 150; 10 km @ 20 = 200. Total = 350.
    fare = compute_fare_from_rate_card(card, distance_km=25.0, duration_min=30.0, surge=1.0)
    assert fare == 350.0


def test_surge_caps_and_legal_limits():
    # Morning peak 9 AM
    peak_time = datetime(2026, 11, 23, 9, 30)  # Monday morning
    low, high, period = calculate_surge_window(depart_at=peak_time, legal_cap=2.0, has_rain_signal=True)
    assert period == "Morning Peak"
    assert low == 1.0
    assert high <= 2.0  # Must not exceed Karnataka legal cap

    # Maharashtra Khatua Committee Rule: 1.5x cap
    low_mh, high_mh, period_mh = calculate_surge_window(depart_at=peak_time, legal_cap=1.5, has_rain_signal=True)
    assert high_mh == 1.5  # Strictly capped at 1.5x despite high rain signal!


def test_case_a_intra_city_comparison():
    # Ride within Bengaluru (Indiranagar to Koramangala)
    res = client.post("/api/estimate", json={
        "pickup": {"lat": 12.971891, "lng": 77.641151, "name": "Indiranagar, Bengaluru"},
        "drop": {"lat": 12.935192, "lng": 77.624480, "name": "Koramangala, Bengaluru"}
    })

    assert res.status_code == 200
    data = res.json()
    assert data["region"] == "bengaluru"
    assert data["reason_code"] == "AVAILABLE"
    assert len(data["available_services"]) > 0

    services = data["available_services"]
    # Check range display: low <= high
    for s in services:
        assert s["low"] <= s["high"]
        assert "currency_symbol" in s
        assert s["deeplink"].startswith(("uber://", "ola://", "rapido://", "nammayatri://", "tel:"))
        assert s["web_link"].startswith("http")
        assert "rate_card_verified_at" in s

    # Verify sorted cheapest first
    lows = [s["low"] for s in services]
    assert lows == sorted(lows)
    assert services[0]["is_cheapest"] is True


def test_case_b_metered_fallback_when_no_apps():
    db: Session = SessionLocal()
    # Create temporary metered-only region: "Wayanad"
    import json
    wayanad = db.query(CoverageRegion).filter(CoverageRegion.region_id == "wayanad_test").first()
    if not wayanad:
        wayanad = CoverageRegion(
            region_id="wayanad_test",
            name="Wayanad Test",
            state="Kerala",
            country="IN",
            legal_surge_cap=2.0,
            auto_rickshaw_metered_available=True,
            metered_auto_fare=json.dumps({"base_fare": 30.0, "free_km": 1.5, "per_km": 15.0, "currency": "INR", "currency_symbol": "₹"}),
            intercity_enabled=True,
            geofence_geojson=json.dumps({
                "type": "Polygon",
                "coordinates": [[[75.8, 11.5], [76.4, 11.5], [76.4, 12.0], [75.8, 12.0], [75.8, 11.5]]]
            })
        )
        db.add(wayanad)
        db.commit()

    # Query within Wayanad (no app services active)
    res = client.post("/api/estimate", json={
        "pickup": {"lat": 11.70, "lng": 76.05, "name": "Kalpetta, Wayanad"},
        "drop": {"lat": 11.75, "lng": 76.10, "name": "Sulthan Bathery, Wayanad"}
    })

    assert res.status_code == 200
    data = res.json()
    assert data["reason_code"] == "METERED_ONLY"
    assert data["available_services"] == []
    assert data["fallback"]["type"] == "auto"
    assert "No ride-hailing apps operate here" in data["fallback"]["message"]
    est = data["fallback"]["estimate"]
    assert est["low"] <= est["high"]
    assert est["currency"] == "INR"


def test_case_c_out_of_coverage_blocks_api():
    # Coordinates in Antarctica / Pacific Ocean
    res = client.post("/api/estimate", json={
        "pickup": {"lat": -80.0, "lng": 0.0, "name": "Antarctica Ice Shelf"},
        "drop": {"lat": -81.0, "lng": 1.0, "name": "South Pole"}
    })

    # Hard requirement: block API with HTTP 422
    assert res.status_code == 422
    data = res.json()
    assert "detail" in data
    assert data["detail"]["reason_code"] == "OUT_OF_COVERAGE"
    assert "Ride services are not available in this area." in data["detail"]["message"]


def test_case_d_intercity_trip():
    # Pickup in Bengaluru, Drop in Mumbai
    res = client.post("/api/estimate", json={
        "pickup": {"lat": 12.971891, "lng": 77.641151, "name": "Bengaluru"},
        "drop": {"lat": 19.0760, "lng": 72.8777, "name": "Mumbai"}
    })

    assert res.status_code == 200
    data = res.json()
    assert data["reason_code"] == "INTERCITY_TRIP"
    assert data["available_services"] == []
    assert "intercity" in data["notice"].lower()


def test_coverage_endpoint():
    res = client.get("/api/coverage?lat=12.9716&lng=77.5946")
    assert res.status_code == 200
    data = res.json()
    assert data["covered"] is True
    assert data["name"] == "Bengaluru"
    assert "Uber" in data["active_services"]


def test_admin_service_status_toggle():
    # Toggle Uber status in Bengaluru via admin endpoint
    res = client.put("/api/admin/service-status", json={
        "region_id": "bengaluru",
        "service_name": "Uber",
        "status": "suspended",
        "status_reason": "Temporary licence inspection"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "suspended"

    # Re-activate it
    res2 = client.put("/api/admin/service-status", json={
        "region_id": "bengaluru",
        "service_name": "Uber",
        "status": "active"
    })
    assert res2.status_code == 200
    assert res2.json()["status"] == "active"
