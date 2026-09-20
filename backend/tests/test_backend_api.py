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

client = TestClient(app)


def test_health_check():
    """Verify /health endpoint returns 200 and healthy metadata."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["service"] == "Smart Taxi Fare Comparison API"
    assert "database" in data
    assert "ml_engine" in data


def test_security_headers():
    """Verify security headers are attached to responses."""
    response = client.get("/health")
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "SAMEORIGIN"
    assert response.headers.get("x-xss-protection") == "1; mode=block"


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


def test_route_calculation_and_ml_fare_intelligence():
    """Verify route calculation generates coordinates, distance, and ML-enriched fares."""
    payload = {
        "pickup": [28.6328, 77.2197],  # Connaught Place, Delhi
        "drop": [28.5355, 77.3910],    # Noida Sector 18
        "pickupName": "Connaught Place, New Delhi",
        "dropName": "Sector 18, Noida"
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
    assert len(data["fares"]) > 0

    first_fare = data["fares"][0]
    assert "provider" in first_fare
    assert "fare" in first_fare
    assert "ml_predicted_fare" in first_fare
    assert "prediction_delta" in first_fare
    assert "pricing_regime" in first_fare
    assert "confidence_score" in first_fare
    assert "smart_score" in first_fare
    assert "booking_url" in first_fare


def test_fare_compare_endpoint():
    """Verify POST /api/fare/compare calculates fares."""
    payload = {
        "pickup": "Indira Gandhi Airport",
        "drop": "Cyber Hub Gurgaon",
        "pickup_lat": 28.5562,
        "pickup_lng": 77.1000,
        "drop_lat": 28.4952,
        "drop_lng": 77.0894,
        "distance_km": 14.5,
        "duration_min": 25.0
    }
    response = client.post("/api/fare/compare", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["fares"]) > 0


def test_fare_predict_ml_endpoint():
    """Verify POST /api/fare/predict returns ML regression and anomaly insights."""
    payload = {
        "provider": "Uber",
        "ride_type": "Mini",
        "distance_km": 12.0,
        "duration_min": 30.0,
        "hour_of_day": 18,
        "day_of_week": 4,
        "is_weekend": 0,
        "traffic_density": 1.4,
        "surge_multiplier": 1.2,
        "city": "Delhi"
    }
    response = client.post("/api/fare/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "prediction" in data
    pred = data["prediction"]
    assert pred["predicted_fare"] > 0
    assert "confidence" in pred
    assert "smart_score" in pred
    assert "pricing_regime" in pred


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


def test_ml_cluster_profiles():
    """Verify GET /api/ml/clusters returns unsupervised cluster profiles."""
    response = client.get("/api/ml/clusters")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["clusters"]) >= 3


def test_ml_model_performance():
    """Verify GET /api/ml/model-performance returns validation metrics."""
    response = client.get("/api/ml/model-performance")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "metrics" in data
    metrics = data["metrics"]
    assert "r2_score" in metrics
    assert metrics["r2_score"] > 0.90


def test_ml_retrain_endpoint():
    """Verify POST /api/ml/retrain schedules retraining and returns 200."""
    response = client.post("/api/ml/retrain")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "message" in data
