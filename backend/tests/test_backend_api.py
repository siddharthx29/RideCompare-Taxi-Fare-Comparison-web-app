"""
Comprehensive Python Test Suite for FastAPI Backend and ML Subsystem.
Tests all endpoints, security headers, database fallbacks, routing, and ML inference.
"""

import pytest
from fastapi.testclient import TestClient
import os
import sys
from pathlib import Path

# Ensure root & backend are in python path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app
from backend.app.config import Settings

client = TestClient(app)


def test_production_cors_uses_only_explicit_origins():
    assert Settings(ENVIRONMENT="production").allowed_origins_list == []
    assert Settings(
        ENVIRONMENT="production",
        CORS_ORIGINS="https://app.example.com,https://admin.example.com",
    ).allowed_origins_list == ["https://app.example.com", "https://admin.example.com"]


def test_health_check():
    """Verify /health endpoint returns 200 and healthy metadata."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["service"] == "RideCompare API"
    assert "database" in data
    assert "ml_engine" not in data


def test_security_headers():
    """Verify security headers are attached to responses."""
    response = client.get("/health")
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "SAMEORIGIN"
    assert response.headers.get("permissions-policy") == "camera=(), microphone=(), geolocation=(self)"
    assert response.headers.get("strict-transport-security") is None


def test_geocode_nominatim_proxy():
    """Verify geocoding endpoint returns structured place suggestions."""
    response = client.get("/api/geocode?q=Connaught+Place")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        place = data[0]
        assert "lat" in place
        assert "lng" in place
        assert "displayName" in place


def test_route_calculation_returns_only_public_fare_fields():
    """Verify route results keep fare details without exposing model internals."""
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
    assert data["success"] is True
    assert "route" in data
    assert data["route"]["distance_km"] > 0
    assert data["route"]["duration_min"] > 0
    assert len(data["route"]["coordinates"]) > 0

    assert "fares" in data
    assert data["isServiceable"] is True
    assert len(data["fares"]) > 0

    first_fare = data["fares"][0]
    assert "provider" in first_fare
    assert "fare" in first_fare
    assert "booking_url" in first_fare
    # Raw debugging metrics should not leak into public comparison
    assert not {"modelMetadata", "rawMetrics", "mae", "rmse", "r2", "loss"} & set(data["comparison"])
    for provider in data["comparison"]["providers"]:
        # Both Live provider pricing and ML pricing intelligence are available
        assert "actualFare" in provider
        assert "isLive" in provider
        assert "predictedFare" in provider
        assert "typicalFareRange" in provider
        assert "demandLevel" in provider
        # Raw internal training metrics should not be present in public provider card
        assert not {"mae", "rmse", "r2", "rawLoss", "hyperparameters"} & set(provider)
        assert provider["provider"].startswith(("GoaMiles", "GTDC"))


def test_admin_ml_metrics_endpoint():
    """Verify internal /api/admin/ml-metrics returns model evaluation metrics."""
    response = client.get("/api/admin/ml-metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Gradient Boosting" in data["model_type"]
    assert data["model_version"].startswith("v")
    assert data["metrics"]["mae"] > 0
    assert data["metrics"]["r2"] > 0.9
    assert data["total_training_records"] == 12000
    assert "features" in data
    assert "clustering" in data
    assert "anomaly_detection" in data


def test_admin_ml_metrics_auth_in_production(monkeypatch):
    """Verify that in production with ADMIN_KEY set, unauthenticated requests are rejected with 403."""
    from backend.app.config import settings
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "ADMIN_KEY", "secret-token-xyz")

    # Unauthorized attempt
    unauth = client.get("/api/admin/ml-metrics")
    assert unauth.status_code == 403

    # Authorized with Header
    auth_header = client.get("/api/admin/ml-metrics", headers={"X-Admin-Key": "secret-token-xyz"})
    assert auth_header.status_code == 200

    # Authorized with query parameter
    auth_query = client.get("/api/admin/ml-metrics?key=secret-token-xyz")
    assert auth_query.status_code == 200


def test_fare_compare_endpoint():
    """Verify POST /api/fare/compare calculates fares."""
    payload = {
        "pickup": "Indiranagar, Bengaluru, India",
        "drop": "Kempegowda International Airport, Bengaluru, India",
        "pickup_lat": 12.971891,
        "pickup_lng": 77.641151,
        "drop_lat": 13.1986,
        "drop_lng": 77.7066,
        "distance_km": 35.0,
        "duration_min": 55.0
    }
    response = client.post("/api/fare/compare", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["isServiceable"] is True
    assert len(data["fares"]) > 0
    providers = {fare["provider"] for fare in data["fares"]}
    assert all(name.startswith(("KSTDC", "Namma Yatri", "Uber", "Ola", "Rapido")) for name in providers)


def test_kochi_route_returns_only_configured_regional_services():
    response = client.post("/api/fare/compare", json={
        "pickup": "MG Road, Kochi, Kerala, India",
        "drop": "Cochin International Airport, Kochi, Kerala, India",
        "pickup_lat": 9.9723,
        "pickup_lng": 76.2784,
        "drop_lat": 10.1518,
        "drop_lng": 76.3930,
        "pickup_address": {"city": "Kochi", "state": "Kerala", "country_code": "in"},
        "drop_address": {"city": "Kochi", "state": "Kerala", "country_code": "in"},
        "distance_km": 30.0,
        "duration_min": 50.0
    })
    assert response.status_code == 200
    data = response.json()
    assert data["isServiceable"] is True
    providers = {fare["provider"] for fare in data["fares"]}
    assert providers
    assert all(name.startswith(("Kerala Savari", "Uber", "Ola", "Rapido", "Namma Yatri")) for name in providers)
    assert not {"GoaMiles Hatchback", "GTDC Tourist Taxi", "Local Metered Taxi"} & providers


def test_unsupported_route_has_no_fabricated_provider():
    response = client.post("/api/fare/compare", json={
        "pickup": "Unsupported City, India",
        "drop": "Unsupported City, India",
        "pickup_lat": 18.0,
        "pickup_lng": 79.0,
        "drop_lat": 18.1,
        "drop_lng": 79.1,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["isServiceable"] is False
    assert data["comparison"]["providers"] == []
    assert data["message"] == "No supported ride services are currently configured for this location."


def test_analytics_endpoints():
    """Verify GET /api/analytics returns dashboard metrics."""
    response = client.get("/api/analytics")
    assert response.status_code == 200
    data = response.json()
    assert "totalSearches" in data
    assert "averageSavings" in data
    assert "topRoutes" in data
    assert "providerClickShare" in data
    assert "dailyTrends" in data


def test_booking_redirect_logging():
    """Verify POST /api/redirect logs a click and returns redirect URL."""
    payload = {
        "provider": "Uber",
        "ride_type": "Go",
        "fare": 320,
        "pickup": "CP",
        "drop": "Noida",
        "city": "Delhi"
    }
    response = client.post("/api/redirect", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "redirect_url" in data


@pytest.mark.parametrize("method,path", [
    ("post", "/api/fare/predict"),
    ("get", "/api/ml/clusters"),
    ("get", "/api/ml/model-performance"),
    ("post", "/api/ml/retrain"),
])
def test_internal_ml_endpoints_are_not_public(method, path):
    response = getattr(client, method)(path)
    assert response.status_code in {404, 405}
