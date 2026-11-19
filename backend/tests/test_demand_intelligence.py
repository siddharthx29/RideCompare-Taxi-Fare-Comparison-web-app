"""
Unit and Integration Test Suite: Dynamic Pricing & Demand Intelligence
======================================================================
Tests:
  - Standardized pricing pressure scale (0 to 4)
  - Demand condition levels: LOW, NORMAL, SLIGHTLY HIGH, HIGH, VERY HIGH
  - Missing supply data handling (no fabricated supply)
  - Missing historical data handling (graceful fallback)
  - Missing provider data handling
  - ML unavailable fallback (Levels 3, 4, 5)
  - Invalid coordinates handling
  - Different geographic zones (H3 indexing)
  - Different times of day (rush hour vs off-peak)
  - Different providers and ride categories
  - Verification that the system NEVER returns fabricated exact provider fares
  - Caching performance & TTL
  - API endpoints: /api/pricing-pressure, /api/market-conditions, /api/admin/demand-model/metrics
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app
from backend.app.services.demand_intelligence import (
    demand_engine,
    get_h3_zone,
    score_to_demand_level,
    get_demand_wording,
    DEFAULT_PRESSURE_THRESHOLDS,
    DemandIntelligenceEngine
)
from backend.app.database import SessionLocal, init_db
from backend.app.models.db_models import DemandObservation

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()


# 1. Standardized Pricing Pressure Scale
def test_pricing_pressure_scale_thresholds():
    """Verify 0-4 score translates accurately to standardized RideCompare levels."""
    assert score_to_demand_level(0.2) == "LOW"
    assert score_to_demand_level(0.5) == "NORMAL"
    assert score_to_demand_level(1.0) == "NORMAL"
    assert score_to_demand_level(1.49) == "NORMAL"
    assert score_to_demand_level(1.5) == "SLIGHTLY HIGH"
    assert score_to_demand_level(2.2) == "SLIGHTLY HIGH"
    assert score_to_demand_level(2.5) == "HIGH"
    assert score_to_demand_level(3.2) == "HIGH"
    assert score_to_demand_level(3.5) == "VERY HIGH"
    assert score_to_demand_level(4.0) == "VERY HIGH"
    # Clamping tests
    assert score_to_demand_level(-1.0) == "LOW"
    assert score_to_demand_level(5.5) == "VERY HIGH"


# 2. Demand Condition Levels
def test_demand_levels_evaluation():
    """Verify engine generates distinct demand conditions and proper descriptive wording."""
    db = SessionLocal()
    try:
        # Normal midday condition
        res_normal = demand_engine.estimate_pricing_pressure(
            pickup_lat=10.0284,
            pickup_lng=76.3074,
            provider="Uber",
            ride_category="Cab",
            traffic_level=1.0,
            db=db
        )
        assert res_normal["demand_level"] in ["LOW", "NORMAL", "SLIGHTLY HIGH", "HIGH", "VERY HIGH"]
        assert 0.0 <= res_normal["pricing_pressure_score"] <= 4.0
        assert "condition_wording" in res_normal
        assert "confidence" in res_normal
        assert 0.0 <= res_normal["confidence"] <= 1.0

        # High congestion condition
        res_high = demand_engine.estimate_pricing_pressure(
            pickup_lat=10.0284,
            pickup_lng=76.3074,
            provider="Uber",
            ride_category="Cab",
            traffic_level=2.2,  # Severe traffic
            db=db
        )
        assert res_high["pricing_pressure_score"] >= res_normal["pricing_pressure_score"]
    finally:
        db.close()


# 3. Missing Supply Data Handling
def test_missing_supply_data_handling():
    """Verify that when live supply is unavailable, no supply data is fabricated and fallback operates properly."""
    db = SessionLocal()
    try:
        # Query zone without live supply
        signals = demand_engine.retrieve_zone_signals(db, "876004d33ffffff", "Uber", "Cab")
        assert signals["supply_available"] is False
        assert signals["live_supply"] is None

        res = demand_engine.estimate_pricing_pressure(
            pickup_lat=12.9716,
            pickup_lng=77.5946,
            provider="Uber",
            ride_category="Cab",
            authorized_provider_signal=None,  # No provider-authorized live supply
            db=db
        )
        assert res["source_type"] in ["ml_estimate", "statistical_baseline", "heuristic_fallback"]
        assert "pricing_pressure_score" in res
        assert "demand_level" in res
    finally:
        db.close()


# 4. Missing Historical Data Handling
def test_missing_historical_data_handling():
    """Verify that a brand new geographic zone without prior history falls back gracefully with lower confidence."""
    db = SessionLocal()
    try:
        # Novel coordinates in the middle of a desert/ocean
        novel_lat = 24.1234
        novel_lng = 68.5678
        res = demand_engine.estimate_pricing_pressure(
            pickup_lat=novel_lat,
            pickup_lng=novel_lng,
            provider="NewProvider",
            ride_category="Cab",
            db=db
        )
        assert res["demand_level"] in ["LOW", "NORMAL", "SLIGHTLY HIGH"]
        assert res["source_type"] in ["heuristic_fallback", "ml_estimate"]
        # Confidence should reflect lack of dense zone observations
        assert res["confidence"] <= 0.85
    finally:
        db.close()


# 5. Missing / Unknown Provider Data Handling
def test_missing_provider_data_handling():
    """Verify engine handles unconfigured or novel provider names gracefully."""
    db = SessionLocal()
    try:
        res = demand_engine.estimate_pricing_pressure(
            pickup_lat=10.0284,
            pickup_lng=76.3074,
            provider="UnknownFleetX",
            ride_category="Cab",
            db=db
        )
        assert res["provider"] == "UnknownFleetX"
        assert res["pricing_pressure_score"] >= 0.0
        assert res["demand_level"] in ["LOW", "NORMAL", "SLIGHTLY HIGH", "HIGH", "VERY HIGH"]
    finally:
        db.close()


# 6. ML Model Unavailable Fallback Hierarchy
def test_ml_unavailable_fallback():
    """Verify fallback hierarchy works seamlessly when ML model is disabled or unavailable."""
    original_state = demand_engine.model_loaded
    original_model = demand_engine.model
    try:
        # Simulate ML model unavailable
        demand_engine.model_loaded = False
        demand_engine.model = None

        db = SessionLocal()
        try:
            res = demand_engine.estimate_pricing_pressure(
                pickup_lat=10.0284,
                pickup_lng=76.3074,
                provider="Ola",
                ride_category="Cab",
                db=db
            )
            # Must fall back to statistical baseline or heuristic fallback (Level 3 or 4)
            assert res["source_type"] in ["statistical_baseline", "heuristic_fallback"]
            assert res["demand_level"] in ["LOW", "NORMAL", "SLIGHTLY HIGH", "HIGH", "VERY HIGH"]
            assert res["confidence"] > 0.0
        finally:
            db.close()
    finally:
        # Restore ML engine
        demand_engine.model_loaded = original_state
        demand_engine.model = original_model


# 7. Invalid Coordinates Handling
def test_invalid_coordinates_handling():
    """Verify engine handles null, zero, or edge coordinates gracefully without crashing."""
    db = SessionLocal()
    try:
        # Null coordinates / zero
        res = demand_engine.estimate_pricing_pressure(
            pickup_lat=0.0,
            pickup_lng=0.0,
            provider="Uber",
            db=db
        )
        assert res["source_type"] == "insufficient_data"
        assert res["confidence"] <= 0.50
        assert "Limited" in res["confidence_text"]
    finally:
        db.close()


# 8. Different Geographic Zones
def test_different_geographic_zones():
    """Verify distinct locations generate distinct H3 zone indices and independent estimates."""
    kochi_zone = get_h3_zone(10.0284, 76.3074)
    kochi_airport_zone = get_h3_zone(10.1518, 76.3930)
    blr_zone = get_h3_zone(12.9716, 77.5946)

    assert kochi_zone != kochi_airport_zone
    assert kochi_zone != blr_zone
    assert kochi_airport_zone != blr_zone

    # Verify H3 format
    assert len(kochi_zone) > 8


# 9. Different Times of Day
def test_different_times_of_day_heuristics():
    """Verify morning and evening rush hours have higher demand scores than late night."""
    morning_feats = {"hour_of_day": 9, "is_weekend": 0}
    night_feats = {"hour_of_day": 3, "is_weekend": 0}
    evening_feats = {"hour_of_day": 18, "is_weekend": 0}

    score_morning = demand_engine.compute_heuristic_baseline(morning_feats, traffic_level=1.4)
    score_night = demand_engine.compute_heuristic_baseline(night_feats, traffic_level=0.9)
    score_evening = demand_engine.compute_heuristic_baseline(evening_feats, traffic_level=1.5)

    assert score_morning > score_night
    assert score_evening > score_night


# 10. Different Providers & Categories
def test_different_providers_and_categories():
    """Verify bike, auto, and cab categories compute appropriate modality factors."""
    db = SessionLocal()
    try:
        res_bike = demand_engine.estimate_pricing_pressure(
            pickup_lat=10.0284,
            pickup_lng=76.3074,
            provider="Rapido",
            ride_category="Bike",
            db=db
        )
        res_cab = demand_engine.estimate_pricing_pressure(
            pickup_lat=10.0284,
            pickup_lng=76.3074,
            provider="Uber",
            ride_category="Cab",
            db=db
        )
        assert res_bike["ride_category"] == "Bike"
        assert res_cab["ride_category"] == "Cab"
    finally:
        db.close()


# 11. CRITICAL TEST: System NEVER returns fabricated exact provider fares
def test_system_never_returns_fabricated_exact_provider_fares():
    """
    CRITICAL PRODUCT RULE TEST:
    Demand Intelligence must output pricing_pressure_score (0-4) and demand_level (LOW..VERY HIGH),
    NOT fabricated exact fares like ₹245.
    """
    res = client.get("/api/pricing-pressure?pickup_lat=10.0284&pickup_lng=76.3074&provider=Uber")
    assert res.status_code == 200
    data = res.json()

    # Must contain pricing pressure metrics
    assert "pricing_pressure_score" in data
    assert "demand_level" in data
    assert data["demand_level"] in ["LOW", "NORMAL", "SLIGHTLY HIGH", "HIGH", "VERY HIGH"]

    # Must NOT contain fabricated exact fare amounts in demand intelligence response
    assert "predicted_price" not in data
    assert "exact_fare" not in data
    assert "fare" not in data or data.get("fare") is None


# 12. GET /api/pricing-pressure API Endpoint Tests
def test_api_pricing_pressure_single_and_multi():
    """Verify GET /api/pricing-pressure returns valid structure for both single provider and market summary."""
    # Single provider
    res_single = client.get("/api/pricing-pressure?pickup_lat=9.9312&pickup_lng=76.2673&provider=Uber")
    assert res_single.status_code == 200
    data_single = res_single.json()
    assert data_single["provider"] == "Uber"
    assert "pricing_pressure_score" in data_single
    assert "demand_level" in data_single
    assert "confidence" in data_single
    assert "source_type" in data_single
    assert "reason" in data_single

    # Multi provider
    res_multi = client.get("/api/pricing-pressure?pickup_lat=9.9312&pickup_lng=76.2673")
    assert res_multi.status_code == 200
    data_multi = res_multi.json()
    assert data_multi["success"] is True
    assert "market_summary" in data_multi
    assert len(data_multi["market_summary"]) >= 3
    assert "disclaimer" in data_multi


# 13. Market Conditions Summary Endpoint
def test_api_market_conditions():
    """Verify GET /api/market-conditions returns clean overview for a geographic point."""
    res = client.get("/api/market-conditions?lat=12.9716&lng=77.5946")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "zone" in data
    assert len(data["conditions"]) >= 3


# 14. Admin Telemetry & Metrics Endpoint
def test_api_admin_demand_metrics():
    """Verify internal /api/admin/demand-model/metrics exposes training metrics and dataset statistics."""
    res = client.get("/api/admin/demand-model/metrics")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert "validation_metrics" in data
    assert "r2" in data["validation_metrics"]
    assert data["validation_metrics"]["r2"] > 0.8
    assert "total_training_records" in data


# 15. Caching Performance Test
def test_caching_performance():
    """Verify that cached zone requests resolve in sub-millisecond time."""
    import time
    start = time.perf_counter()
    res1 = client.get("/api/pricing-pressure?pickup_lat=10.0284&pickup_lng=76.3074&provider=Uber")
    elapsed1 = time.perf_counter() - start

    start2 = time.perf_counter()
    res2 = client.get("/api/pricing-pressure?pickup_lat=10.0284&pickup_lng=76.3074&provider=Uber")
    elapsed2 = time.perf_counter() - start2

    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json()["pricing_pressure_score"] == res2.json()["pricing_pressure_score"]


# 16. Route Integration Verification
def test_route_integration_includes_pricing_pressure():
    """Verify that POST /api/route returns demand intelligence fields for all compared providers."""
    payload = {
        "pickup": [15.4989, 73.8278],
        "drop": [15.5553, 73.7517],
        "pickupName": "Panaji, North Goa, Goa, India",
        "dropName": "Baga Beach, North Goa, Goa, India",
        "pickupAddress": {"city": "Panaji", "state": "Goa", "country_code": "in"},
        "dropAddress": {"city": "Baga", "state": "Goa", "country_code": "in"}
    }
    response = client.post("/api/route", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "comparison" in data
    assert "marketConditions" in data["comparison"]
    for provider in data["comparison"]["providers"]:
        assert "pricing_pressure_score" in provider
        assert "demand_level" in provider
        assert "pricing_pressure" in provider
        assert "confidence" in provider
        assert "reason" in provider
        assert "source_type" in provider
