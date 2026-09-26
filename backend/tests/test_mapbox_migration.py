"""
Comprehensive verification test suite for RideCompare Mapbox Search Box & Geocoding Migration:
1. Mapbox Search Box /suggest endpoint with session token and proximity
2. Mapbox Search Box /retrieve endpoint triggered only upon selection
3. Mapbox reverse geocoding returning clean human-readable address
4. Worldwide location discovery across India, US, UK, Germany, UAE, Japan, Singapore, Australia
5. Application-level rate limiting and request validation
6. End-to-end integration: Mapbox location coordinates -> Ride provider comparison & fares
"""

import asyncio
import pytest
import uuid
from fastapi.testclient import TestClient
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app
from backend.app.config import settings
from backend.app.database import init_db
from backend.app.routers.geocode import (
    _format_mapbox_suggestion,
    _format_mapbox_feature,
    _format_mapbox_v5_feature,
    _clean_place_texts,
    rate_limiter,
    _cache,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    _cache.clear()


def test_clean_place_texts_omits_null_undefined():
    primary, secondary, display = _clean_place_texts(
        name="Burj Khalifa",
        suburb="Downtown Dubai",
        city="Dubai",
        state="null",
        country="United Arab Emirates"
    )
    assert primary == "Burj Khalifa"
    assert "null" not in secondary.lower()
    assert "undefined" not in secondary.lower()
    assert "n/a" not in secondary.lower()
    assert "Dubai" in secondary
    assert display == "Burj Khalifa, Downtown Dubai, Dubai, United Arab Emirates"


def test_format_mapbox_suggestion_and_feature():
    raw_suggestion = {
        "name": "LuLu International Shopping Mall",
        "mapbox_id": "mbx:poi:f4a9b2",
        "feature_type": "poi",
        "address": "34/1000, Old NH 47",
        "full_address": "34/1000, Old NH 47, Edappally, Kochi, Kerala 682024, India",
        "place_formatted": "Edappally, Kochi, Kerala 682024, India",
        "context": {
            "country": {"name": "India", "country_code": "IN"},
            "region": {"name": "Kerala"},
            "district": {"name": "Ernakulam"},
            "place": {"name": "Kochi"},
            "locality": {"name": "Edappally"},
            "postcode": {"name": "682024"},
            "street": {"name": "Old NH 47"}
        },
        "maki": "shop"
    }

    sug = _format_mapbox_suggestion(raw_suggestion)
    assert sug["mapbox_id"] == "mbx:poi:f4a9b2"
    assert sug["name"] == "LuLu International Shopping Mall"
    assert sug["city"] == "Kochi"
    assert sug["state"] == "Kerala"
    assert sug["country"] == "India"
    assert sug["provider"] == "mapbox"

    raw_feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [76.3074, 10.0284]
        },
        "properties": {
            "name": "LuLu International Shopping Mall",
            "mapbox_id": "mbx:poi:f4a9b2",
            "feature_type": "poi",
            "address": "34/1000, Old NH 47",
            "full_address": "34/1000, Old NH 47, Edappally, Kochi, Kerala 682024, India",
            "place_formatted": "Edappally, Kochi, Kerala 682024, India",
            "context": {
                "country": {"name": "India", "country_code": "IN"},
                "region": {"name": "Kerala"},
                "district": {"name": "Ernakulam"},
                "place": {"name": "Kochi"},
                "locality": {"name": "Edappally"},
                "postcode": {"name": "682024"},
                "street": {"name": "Old NH 47"}
            },
            "coordinates": {
                "latitude": 10.0284,
                "longitude": 76.3074
            }
        }
    }

    feat = _format_mapbox_feature(raw_feature)
    assert feat is not None
    assert feat["latitude"] == 10.0284
    assert feat["longitude"] == 76.3074
    assert feat["city"] == "Kochi"
    assert feat["district"] == "Ernakulam"
    assert feat["state"] == "Kerala"
    assert feat["postcode"] == "682024"
    assert feat["provider"] == "mapbox"
    assert feat["address"]["road"] == "Old NH 47"


def test_suggest_endpoint_workflow():
    session_token = str(uuid.uuid4())
    resp = client.get(f"/api/location/suggest?q=Lulu+Mall&session_token={session_token}&near_lat=10.0&near_lon=76.3")
    assert resp.status_code == 200
    data = resp.json()
    assert "suggestions" in data
    assert "session_token" in data
    assert data["session_token"] == session_token
    assert len(data["suggestions"]) >= 1

    first = data["suggestions"][0]
    assert "mapbox_id" in first
    assert "primaryText" in first
    assert "secondaryText" in first
    assert "displayName" in first
    assert first["provider"] == "mapbox"


def test_retrieve_endpoint_workflow():
    session_token = str(uuid.uuid4())
    # Retrieve using a known mapbox_id
    resp = client.get(f"/api/location/retrieve?id=mbx:poi:lulu_mall_kochi&session_token={session_token}")
    assert resp.status_code == 200
    place = resp.json()
    assert place["name"] == "LuLu International Shopping Mall"
    assert place["latitude"] == pytest.approx(10.0284, abs=0.01)
    assert place["longitude"] == pytest.approx(76.3074, abs=0.01)
    assert place["city"] == "Kochi"
    assert place["state"] == "Kerala"
    assert place["country"] == "India"
    assert place["provider"] == "mapbox"
    assert "address" in place
    assert place["address"]["postcode"] == "682024"


def test_reverse_endpoint_clean_address():
    # LuLu Mall coordinates
    resp = client.get("/api/location/reverse?lat=10.0284&lon=76.3074")
    assert resp.status_code == 200
    data = resp.json()
    assert "latitude" in data
    assert "longitude" in data
    assert data["latitude"] == pytest.approx(10.0284, abs=0.01)
    assert data["longitude"] == pytest.approx(76.3074, abs=0.01)
    assert "address" in data
    # Confirm no null string values
    for val in data["address"].values():
        assert val != "null"
        assert val != "undefined"
        assert val != "None"


def test_worldwide_locations_discovery():
    test_locations = [
        # India
        ("Lulu Mall", "Kochi"),
        ("Kochi Airport", "Nedumbassery"),
        ("Aluva Metro", "Aluva"),
        ("Kalamassery", "Kochi"),
        ("Ernakulam South", "Kochi"),
        # USA
        ("Times Square", "New York"),
        ("New York", "United States"),
        # UK
        ("London Bridge", "London"),
        # Germany
        ("Berlin Hauptbahnhof", "Berlin"),
        # UAE
        ("Burj Khalifa", "Dubai"),
        # Japan
        ("Shibuya Station", "Tokyo"),
        # Singapore
        ("Marina Bay Sands", "Singapore"),
        # Australia
        ("Sydney Opera House", "Sydney"),
    ]

    for query, expected_text in test_locations:
        resp = client.get(f"/api/location/suggest?q={query}")
        assert resp.status_code == 200, f"Suggest failed for {query}"
        data = resp.json()
        assert len(data["suggestions"]) >= 1, f"No suggestions found for {query}"
        matching = any(expected_text.lower() in (s["displayName"] + " " + s["secondaryText"] + " " + s["country"]).lower() for s in data["suggestions"])
        assert matching, f"Expected '{expected_text}' in suggestions for '{query}': {[s['displayName'] for s in data['suggestions']]}"


def test_rate_limiting_protection():
    # Verify rate limiter allows valid requests
    allowed = asyncio.run(rate_limiter.is_allowed("192.168.1.100"))
    assert allowed is True


def test_end_to_end_location_to_ride_fare_comparison():
    """
    Simulate full user flow:
    1. User searches pickup location (suggest -> retrieve)
    2. User searches destination location (suggest -> retrieve)
    3. Pass coordinates into RideCompare route & fare engine
    4. Verify providers, actual fares, ETAs, and recommendations
    """
    pickup_session = str(uuid.uuid4())
    sug_pickup = client.get(f"/api/location/suggest?q=Lulu+Mall&session_token={pickup_session}").json()
    assert len(sug_pickup["suggestions"]) >= 1
    pickup_id = sug_pickup["suggestions"][0]["mapbox_id"]
    pickup_place = client.get(f"/api/location/retrieve?id={pickup_id}&session_token={pickup_session}").json()
    assert pickup_place["latitude"] is not None
    assert pickup_place["longitude"] is not None

    dest_session = str(uuid.uuid4())
    sug_dest = client.get(f"/api/location/suggest?q=Kochi+Airport&session_token={dest_session}").json()
    assert len(sug_dest["suggestions"]) >= 1
    dest_id = sug_dest["suggestions"][0]["mapbox_id"]
    dest_place = client.get(f"/api/location/retrieve?id={dest_id}&session_token={dest_session}").json()
    assert dest_place["latitude"] is not None
    assert dest_place["longitude"] is not None

    # Call RideCompare Route endpoint
    route_resp = client.get(
        f"/api/route?start={pickup_place['longitude']},{pickup_place['latitude']}"
        f"&end={dest_place['longitude']},{dest_place['latitude']}"
        f"&sourceName={pickup_place['displayName']}&destName={dest_place['displayName']}"
    )
    assert route_resp.status_code == 200
    route_data = route_resp.json()
    assert route_data["success"] is True
    assert "comparison" in route_data
    comparison = route_data["comparison"]
    assert len(comparison["providers"]) >= 3
    assert comparison["distanceKm"] > 10.0
    assert "recommendations" in comparison
    assert comparison["recommendations"]["cheapest"] != ""
