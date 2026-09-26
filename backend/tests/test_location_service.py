"""
Comprehensive tests for RideCompare Layered Location Service:
- Photon primary discovery
- Nominatim detailed reverse geocoding
- In-memory & database caching
- Indian/Kerala place discovery & typo tolerance
- End-to-end integration with ride comparison
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app
from backend.app.config import settings
from backend.app.database import SessionLocal, init_db
from backend.app.models.db_models import Location
from backend.app.routers.geocode import (
    _normalize_query_text,
    _expand_query_terms,
    _clean_place_texts,
    _format_photon_feature,
    _rank_result,
    _lookup_db_cache,
    _cache,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_normalization_and_synonym_expansion():
    # Abbreviations and dots
    assert _normalize_query_text("M.G. Road") == "mg road"
    assert _normalize_query_text("M G Road") == "mg road"
    assert _normalize_query_text("P.O. Box") == "po box"
    
    # Synonym expansions
    assert "mahatma gandhi road" in _expand_query_terms("MG Road Kochi")
    assert "kochi" in _expand_query_terms("Cochin Airport")
    assert "station" in _expand_query_terms("Aluva Metro Stn")
    assert "railway" in _expand_query_terms("Ernakulam Rly Station")


def test_database_seeded_popular_locations():
    db = SessionLocal()
    try:
        lulu = db.query(Location).filter(Location.normalized_query == "lulu mall").first()
        assert lulu is not None
        assert "lulu" in lulu.place_name.lower()
        assert lulu.city == "Kochi"
        assert lulu.postcode == "682024"
        assert lulu.latitude == pytest.approx(10.0284, abs=0.01)
        assert lulu.longitude == pytest.approx(76.3074, abs=0.01)

        airport = db.query(Location).filter(Location.normalized_query == "kochi airport").first()
        assert airport is not None
        assert "airport" in airport.place_name.lower()
        assert airport.latitude == pytest.approx(10.1518, abs=0.01)
    finally:
        db.close()


def test_db_cache_lookup_instant_hit():
    results = _lookup_db_cache("Lulu Mall", limit=5)
    assert len(results) >= 1
    hit = results[0]
    assert "lulu" in hit["name"].lower()
    assert hit["source"] == "cache"
    assert hit["latitude"] == pytest.approx(10.0284, abs=0.01)
    assert hit["longitude"] == pytest.approx(76.3074, abs=0.01)
    assert hit["address"]["postcode"] == "682024"


def test_location_search_api_endpoint():
    _cache.clear()
    response = client.get("/api/location/search?q=Lulu+Mall")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) >= 1
    first = data["results"][0]
    assert "name" in first
    assert "latitude" in first
    assert "longitude" in first
    assert "address" in first
    assert first["address"]["country"] == "India"


def test_location_autocomplete_api_endpoint():
    response = client.get("/api/location/autocomplete?q=Aluva+Metro")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) >= 1
    assert any("Aluva" in item["name"] for item in data["results"])


def test_location_search_without_api_prefix():
    response = client.get("/location/search?q=Kalamassery")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) >= 1


def test_empty_and_short_queries():
    # Short query (<2 chars) should return 422 validation error
    res_short = client.get("/api/location/search?q=a")
    assert res_short.status_code == 422


def test_format_photon_feature():
    photon_feature = {
        "type": "Feature",
        "properties": {
            "name": "LuLu International Shopping Mall",
            "street": "Old NH 47",
            "housenumber": "34/1000",
            "district": "Edappally",
            "city": "Kochi",
            "state": "Kerala",
            "country": "India",
            "countrycode": "IN",
            "postcode": "682024",
            "osm_key": "shop",
            "osm_value": "mall",
            "osm_type": "W",
            "osm_id": 248569804,
        },
        "geometry": {
            "type": "Point",
            "coordinates": [76.3074, 10.0284],
        },
    }
    formatted = _format_photon_feature(photon_feature)
    assert formatted is not None
    assert formatted["name"] == "LuLu International Shopping Mall"
    assert formatted["latitude"] == 10.0284
    assert formatted["longitude"] == 76.3074
    assert formatted["lat"] == 10.0284
    assert formatted["lng"] == 76.3074
    assert formatted["address"]["road"] == "Old NH 47"
    assert formatted["address"]["suburb"] == "Edappally"
    assert formatted["address"]["city"] == "Kochi"
    assert formatted["address"]["state"] == "Kerala"
    assert formatted["address"]["postcode"] == "682024"
    assert formatted["source"] == "photon"


def test_reverse_geocoding_detailed_address():
    # Using LuLu Mall coordinates
    response = client.get("/api/location/reverse?lat=10.0284&lon=76.3074")
    assert response.status_code == 200
    data = response.json()
    assert "latitude" in data or "lat" in data
    assert "address" in data
    addr = data["address"]
    # Check that structured fields exist
    for field in ("road", "suburb", "city", "state", "country"):
        assert field in addr


def test_location_to_ride_fare_integration():
    """
    Ensure locations discovered by search produce valid coordinates that
    feed directly into RideCompare route calculation and return fare estimates.
    """
    # 1. Search Pickup (Lulu Mall)
    src_resp = client.get("/api/location/search?q=Lulu+Mall")
    assert src_resp.status_code == 200
    src_item = src_resp.json()["results"][0]

    # 2. Search Drop (Kochi Airport)
    dst_resp = client.get("/api/location/search?q=Kochi+Airport")
    assert dst_resp.status_code == 200
    dst_item = dst_resp.json()["results"][0]

    # 3. Call RideCompare Route endpoint with these coordinates
    route_resp = client.get(
        f"/api/route?start={src_item['longitude']},{src_item['latitude']}"
        f"&end={dst_item['longitude']},{dst_item['latitude']}"
        f"&sourceName={src_item['displayName']}&destName={dst_item['displayName']}"
    )
    assert route_resp.status_code == 200
    route_data = route_resp.json()
    assert route_data["success"] is True
    assert "comparison" in route_data
    assert len(route_data["comparison"]["providers"]) >= 3
    assert route_data["route"]["distance_km"] > 10.0
