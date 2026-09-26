"""
Unit and integration tests for Geoapify geocoding, fallback to Nominatim,
caching, relevance ranking, and reverse geocoding.
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
from backend.app.routers.geocode import (
    _clean_place_texts,
    _format_geoapify_feature,
    _format_nominatim_item,
    _rank_result,
    _deduplicate_results,
    _cache,
)

client = TestClient(app)


def test_clean_place_texts():
    primary, secondary, display = _clean_place_texts(
        name="Lulu Mall",
        suburb="Edappally",
        city="Kochi",
        state="Kerala",
        country="India",
        formatted="Lulu Mall, 34/1000, NH 66, Edappally, Kochi, Kerala, India",
    )
    assert primary == "Lulu Mall"
    assert secondary == "Edappally, Kochi, Kerala"
    assert display == "Lulu Mall, Edappally, Kochi, Kerala"


def test_format_geoapify_feature():
    feature = {
        "type": "Feature",
        "properties": {
            "name": "Cochin International Airport",
            "address_line1": "Cochin International Airport",
            "address_line2": "Nedumbassery, Kochi, Kerala, India",
            "suburb": "Nedumbassery",
            "city": "Kochi",
            "state": "Kerala",
            "country": "India",
            "country_code": "in",
            "street": "Airport Road",
            "category": "aeroway.aerodrome",
            "lat": 10.1518,
            "lon": 76.3930,
            "rank": {"importance": 0.9, "popularity": 0.95},
        },
        "geometry": {
            "type": "Point",
            "coordinates": [76.3930, 10.1518],
        },
    }
    result = _format_geoapify_feature(feature)
    assert result is not None
    assert result["name"] == "Cochin International Airport"
    assert result["lat"] == 10.1518
    assert result["lng"] == 76.3930
    assert result["source"] == "geoapify"
    assert result["address"]["city"] == "Kochi"
    assert result["address"]["state"] == "Kerala"
    assert "Nedumbassery" in result["secondaryText"]


def test_rank_result_proximity_bonus():
    item_kochi = {
        "name": "Rajagiri College of Social Sciences",
        "displayName": "Rajagiri College, Kalamassery, Kochi",
        "secondaryText": "Kalamassery, Kochi",
        "lat": 10.0545,
        "lon": 76.3190,
        "category": "education",
        "importance": 0.7,
    }
    item_other = {
        "name": "Rajagiri Public School",
        "displayName": "Rajagiri Public School, Distant City, Tamil Nadu",
        "secondaryText": "Distant City, Tamil Nadu",
        "lat": 13.0827,
        "lon": 80.2707,
        "category": "education",
        "importance": 0.4,
    }

    # When searching around Kochi (near_lat=10.0, near_lon=76.3)
    score_kochi = _rank_result(item_kochi, "Rajagiri", near_lat=10.0, near_lon=76.3)
    score_other = _rank_result(item_other, "Rajagiri", near_lat=10.0, near_lon=76.3)

    assert score_kochi > score_other


def test_deduplicate_results():
    items = [
        {
            "name": "Lulu Mall",
            "displayName": "Lulu Mall, Edappally, Kochi",
            "lat": 10.0284,
            "lon": 76.3074,
            "importance": 0.9,
        },
        {
            "name": "Lulu Mall Edappally",
            "displayName": "Lulu Mall Edappally, Kochi",
            "lat": 10.0285,  # within 15 meters
            "lon": 76.3075,
            "importance": 0.8,
        },
        {
            "name": "Oberon Mall",
            "displayName": "Oberon Mall, Edappally, Kochi",
            "lat": 10.0150,
            "lon": 76.3120,
            "importance": 0.7,
        },
    ]
    deduped = _deduplicate_results(items)
    # The duplicate Lulu Mall should be merged
    assert len(deduped) == 2
    names = [i["name"] for i in deduped]
    assert "Oberon Mall" in names


def test_geocode_endpoint_caching():
    _cache.clear()
    query = "Kalamassery"
    resp1 = client.get(f"/api/geocode?q={query}")
    assert resp1.status_code == 200

    # Ensure cache has been populated
    cache_keys = [k for k in _cache.keys() if "kalamassery" in k]
    assert len(cache_keys) > 0

    # Second call should return identical cached result immediately
    resp2 = client.get(f"/api/geocode?q={query}")
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()


def test_geocode_geoapify_mocked_response(monkeypatch):
    monkeypatch.setattr(settings, "GEOCODING_PROVIDER", "geoapify")
    monkeypatch.setattr(settings, "GEOAPIFY_API_KEY", "test_mock_api_key_123")

    mock_geo_resp = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Lulu International Shopping Mall",
                    "address_line1": "Lulu International Shopping Mall",
                    "address_line2": "Edappally, Kochi, Kerala 682024, India",
                    "suburb": "Edappally",
                    "city": "Kochi",
                    "state": "Kerala",
                    "country": "India",
                    "country_code": "in",
                    "street": "Old NH 47",
                    "postcode": "682024",
                    "category": "commercial.shopping_mall",
                    "lat": 10.0284,
                    "lon": 76.3074,
                    "rank": {"importance": 0.95, "popularity": 0.98},
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [76.3074, 10.0284],
                },
            }
        ],
    }

    # Clear cache
    _cache.clear()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_geo_resp
        mock_get.return_value = mock_response

        response = client.get("/api/geocode?q=Lulu+Mall&near_lat=9.93&near_lon=76.26")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        item = data[0]
        assert "Lulu" in item["name"]
        assert item["source"] == "geoapify"
        assert item["lat"] == 10.0284
        assert item["lng"] == 76.3074
        assert item["address"]["city"] == "Kochi"


def test_geocode_reverse_endpoint():
    # Test reverse geocoding
    response = client.get("/api/geocode/reverse?lat=9.9723&lon=76.2784")
    assert response.status_code == 200
    data = response.json()
    assert "lat" in data
    assert "lon" in data
    assert "displayName" in data
