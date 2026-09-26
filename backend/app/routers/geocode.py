import asyncio
import logging
import math
import os
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, Query, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db, SessionLocal
from backend.app.models.db_models import Location

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Geocoding"])

# =====================================================================
# Mapbox Endpoints & Provider Configuration
# =====================================================================
MAPBOX_API_BASE = "https://api.mapbox.com"
MAPBOX_SEARCHBOX_SUGGEST_URL = f"{MAPBOX_API_BASE}/search/searchbox/v1/suggest"
MAPBOX_SEARCHBOX_RETRIEVE_URL = f"{MAPBOX_API_BASE}/search/searchbox/v1/retrieve"
MAPBOX_SEARCHBOX_REVERSE_URL = f"{MAPBOX_API_BASE}/search/searchbox/v1/reverse"
MAPBOX_GEOCODING_PLACES_URL = f"{MAPBOX_API_BASE}/geocoding/v5/mapbox.places"

GEOAPIFY_AUTOCOMPLETE_URL = "https://api.geoapify.com/v1/geocode/autocomplete"
GEOAPIFY_REVERSE_URL = "https://api.geoapify.com/v1/geocode/reverse"

DEFAULT_USER_AGENT = settings.GEOCODING_USER_AGENT
DEFAULT_HEADERS = {
    "User-Agent": f"{DEFAULT_USER_AGENT} Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}

# Timeout configurations
MAPBOX_TIMEOUT = 4.0
PHOTON_TIMEOUT = 3.5
GEOAPIFY_TIMEOUT = 3.5
NOMINATIM_TIMEOUT = 4.0

# In-memory Caching Configuration
CACHE_TTL_SECONDS = 1800  # 30 minutes in-memory TTL
_cache: Dict[str, Tuple[float, Any]] = {}
_cache_lock = asyncio.Lock()


# Application-level sliding-window rate limiter
class InMemoryRateLimiter:
    """Sliding-window application-level rate limiter to prevent bot abuse."""
    def __init__(self, max_requests: int = 120, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, client_ip: str) -> bool:
        async with self._lock:
            now = time.monotonic()
            timestamps = self.requests.get(client_ip, [])
            valid = [ts for ts in timestamps if now - ts < self.window_seconds]
            if len(valid) >= self.max_requests:
                self.requests[client_ip] = valid
                return False
            valid.append(now)
            self.requests[client_ip] = valid
            return True


rate_limiter = InMemoryRateLimiter(max_requests=120, window_seconds=60.0)

# Abbreviations & Synonym Mapping
COMMON_SYNONYMS: Dict[str, str] = {
    "cochin": "kochi",
    "ernakulam": "kochi",
    "stn": "station",
    "rly": "railway",
    "apt": "airport",
    "arpt": "airport",
    "intl": "international",
    "jn": "junction",
    "junc": "junction",
    "jnt": "junction",
    "rd": "road",
    "str": "street",
    "hosp": "hospital",
    "coll": "college",
    "univ": "university",
    "bldg": "building",
    "bypass": "bypass",
    "byepass": "bypass",
}

# Known worldwide test locations fallback catalog (used when Mapbox token is not set or in offline testing)
FALLBACK_CATALOG: List[Dict[str, Any]] = [
    {
        "mapbox_id": "mbx:poi:lulu_mall_kochi",
        "name": "LuLu International Shopping Mall",
        "primaryText": "LuLu International Shopping Mall",
        "secondaryText": "Edappally, Kochi, Kerala",
        "displayName": "LuLu International Shopping Mall, Edappally, Kochi, Kerala",
        "display_name": "LuLu International Shopping Mall, Edappally, Kochi, Kerala",
        "formatted_address": "34/1000, Old NH 47, Edappally, Kochi, Kerala 682024, India",
        "latitude": 10.0284,
        "longitude": 76.3074,
        "lat": 10.0284,
        "lon": 76.3074,
        "lng": 76.3074,
        "category": "commercial.shopping_mall",
        "importance": 0.95,
        "city": "Kochi",
        "district": "Ernakulam",
        "suburb": "Edappally",
        "state": "Kerala",
        "postcode": "682024",
        "country": "India",
        "address": {
            "house_number": "34/1000",
            "road": "Old NH 47",
            "neighbourhood": "Edappally",
            "suburb": "Edappally",
            "city": "Kochi",
            "district": "Ernakulam",
            "state": "Kerala",
            "postcode": "682024",
            "country": "India",
            "country_code": "in",
        },
        "provider": "mapbox",
        "source": "mapbox",
    },
    {
        "mapbox_id": "mbx:poi:kochi_airport",
        "name": "Cochin International Airport",
        "primaryText": "Cochin International Airport",
        "secondaryText": "Nedumbassery, Kerala",
        "displayName": "Cochin International Airport, Nedumbassery, Kerala",
        "display_name": "Cochin International Airport, Nedumbassery, Kerala",
        "formatted_address": "Airport Road, Nedumbassery, Kochi, Kerala 683111, India",
        "latitude": 10.1518,
        "longitude": 76.3930,
        "lat": 10.1518,
        "lon": 76.3930,
        "lng": 76.3930,
        "category": "transportation.airport",
        "importance": 0.95,
        "city": "Kochi",
        "district": "Ernakulam",
        "suburb": "Nedumbassery",
        "state": "Kerala",
        "postcode": "683111",
        "country": "India",
        "address": {
            "house_number": "",
            "road": "Airport Road",
            "neighbourhood": "Nedumbassery",
            "suburb": "Nedumbassery",
            "city": "Kochi",
            "district": "Ernakulam",
            "state": "Kerala",
            "postcode": "683111",
            "country": "India",
            "country_code": "in",
        },
        "provider": "mapbox",
        "source": "mapbox",
    },
    {
        "mapbox_id": "mbx:poi:aluva_metro",
        "name": "Aluva Metro Station",
        "primaryText": "Aluva Metro Station",
        "secondaryText": "Aluva, Ernakulam, Kerala",
        "displayName": "Aluva Metro Station, Aluva, Ernakulam, Kerala",
        "display_name": "Aluva Metro Station, Aluva, Ernakulam, Kerala",
        "formatted_address": "Aluva Metro Station, Aluva, Ernakulam, Kerala 683101, India",
        "latitude": 10.1098,
        "longitude": 76.3488,
        "lat": 10.1098,
        "lon": 76.3488,
        "lng": 76.3488,
        "category": "transportation.metro_station",
        "importance": 0.9,
        "city": "Kochi",
        "district": "Ernakulam",
        "suburb": "Aluva",
        "state": "Kerala",
        "postcode": "683101",
        "country": "India",
        "address": {
            "house_number": "",
            "road": "Aluva - Munnar Road",
            "neighbourhood": "Aluva",
            "suburb": "Aluva",
            "city": "Kochi",
            "district": "Ernakulam",
            "state": "Kerala",
            "postcode": "683101",
            "country": "India",
            "country_code": "in",
        },
        "provider": "mapbox",
        "source": "mapbox",
    },
    {
        "mapbox_id": "mbx:poi:kalamassery",
        "name": "Kalamassery",
        "primaryText": "Kalamassery",
        "secondaryText": "Kochi, Ernakulam, Kerala",
        "displayName": "Kalamassery, Kochi, Ernakulam, Kerala",
        "display_name": "Kalamassery, Kochi, Ernakulam, Kerala",
        "formatted_address": "Kalamassery, Kochi, Ernakulam, Kerala 682033, India",
        "latitude": 10.0545,
        "longitude": 76.3190,
        "lat": 10.0545,
        "lon": 76.3190,
        "lng": 76.3190,
        "category": "place.locality",
        "importance": 0.85,
        "city": "Kochi",
        "district": "Ernakulam",
        "suburb": "Kalamassery",
        "state": "Kerala",
        "postcode": "682033",
        "country": "India",
        "address": {
            "house_number": "",
            "road": "",
            "neighbourhood": "Kalamassery",
            "suburb": "Kalamassery",
            "city": "Kochi",
            "district": "Ernakulam",
            "state": "Kerala",
            "postcode": "682033",
            "country": "India",
            "country_code": "in",
        },
        "provider": "mapbox",
        "source": "mapbox",
    },
    {
        "mapbox_id": "mbx:poi:ernakulam_south",
        "name": "Ernakulam South Railway Station",
        "primaryText": "Ernakulam South Railway Station",
        "secondaryText": "Station Road, Kochi, Kerala",
        "displayName": "Ernakulam Junction (South), Station Road, Kochi, Kerala",
        "display_name": "Ernakulam Junction (South), Station Road, Kochi, Kerala",
        "formatted_address": "Station Road, South, Kochi, Kerala 682016, India",
        "latitude": 9.9678,
        "longitude": 76.2925,
        "lat": 9.9678,
        "lon": 76.2925,
        "lng": 76.2925,
        "category": "transportation.railway_station",
        "importance": 0.9,
        "city": "Kochi",
        "district": "Ernakulam",
        "suburb": "South",
        "state": "Kerala",
        "postcode": "682016",
        "country": "India",
        "address": {
            "house_number": "",
            "road": "Station Road",
            "neighbourhood": "South",
            "suburb": "South",
            "city": "Kochi",
            "district": "Ernakulam",
            "state": "Kerala",
            "postcode": "682016",
            "country": "India",
            "country_code": "in",
        },
        "provider": "mapbox",
        "source": "mapbox",
    },
    {
        "mapbox_id": "mbx:poi:times_square",
        "name": "Times Square",
        "primaryText": "Times Square",
        "secondaryText": "Manhattan, New York, NY, United States",
        "displayName": "Times Square, Manhattan, New York, NY, United States",
        "display_name": "Times Square, Manhattan, New York, NY, United States",
        "formatted_address": "Broadway, Manhattan, New York, NY 10036, United States",
        "latitude": 40.7580,
        "longitude": -73.9855,
        "lat": 40.7580,
        "lon": -73.9855,
        "lng": -73.9855,
        "category": "tourism.attraction",
        "importance": 0.98,
        "city": "New York",
        "district": "New York County",
        "suburb": "Manhattan",
        "state": "New York",
        "postcode": "10036",
        "country": "United States",
        "address": {
            "house_number": "",
            "road": "Broadway",
            "neighbourhood": "Theater District",
            "suburb": "Manhattan",
            "city": "New York",
            "district": "New York County",
            "state": "New York",
            "postcode": "10036",
            "country": "United States",
            "country_code": "us",
        },
        "provider": "mapbox",
        "source": "mapbox",
    },
    {
        "mapbox_id": "mbx:place:new_york",
        "name": "New York",
        "primaryText": "New York",
        "secondaryText": "New York, United States",
        "displayName": "New York, NY, United States",
        "display_name": "New York, NY, United States",
        "formatted_address": "New York, NY, United States",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "lat": 40.7128,
        "lon": -74.0060,
        "lng": -74.0060,
        "category": "place.city",
        "importance": 0.99,
        "city": "New York",
        "district": "New York County",
        "suburb": "Manhattan",
        "state": "New York",
        "postcode": "10007",
        "country": "United States",
        "address": {
            "house_number": "",
            "road": "",
            "neighbourhood": "",
            "suburb": "Manhattan",
            "city": "New York",
            "district": "New York County",
            "state": "New York",
            "postcode": "10007",
            "country": "United States",
            "country_code": "us",
        },
        "provider": "mapbox",
        "source": "mapbox",
    },
    {
        "mapbox_id": "mbx:poi:london_bridge",
        "name": "London Bridge",
        "primaryText": "London Bridge",
        "secondaryText": "London, Greater London, United Kingdom",
        "displayName": "London Bridge, London, Greater London, United Kingdom",
        "display_name": "London Bridge, London, Greater London, United Kingdom",
        "formatted_address": "London Bridge, Southwark, London SE1 9RA, United Kingdom",
        "latitude": 51.5079,
        "longitude": -0.0877,
        "lat": 51.5079,
        "lon": -0.0877,
        "lng": -0.0877,
        "category": "transportation.bridge",
        "importance": 0.95,
        "city": "London",
        "district": "Greater London",
        "suburb": "Southwark",
        "state": "England",
        "postcode": "SE1 9RA",
        "country": "United Kingdom",
        "address": {
            "house_number": "",
            "road": "London Bridge",
            "neighbourhood": "Southwark",
            "suburb": "Southwark",
            "city": "London",
            "district": "Greater London",
            "state": "England",
            "postcode": "SE1 9RA",
            "country": "United Kingdom",
            "country_code": "gb",
        },
        "provider": "mapbox",
        "source": "mapbox",
    },
    {
        "mapbox_id": "mbx:poi:berlin_hbf",
        "name": "Berlin Hauptbahnhof",
        "primaryText": "Berlin Hauptbahnhof",
        "secondaryText": "Europaplatz 1, 10557 Berlin, Germany",
        "displayName": "Berlin Hauptbahnhof, Europaplatz 1, 10557 Berlin, Germany",
        "display_name": "Berlin Hauptbahnhof, Europaplatz 1, 10557 Berlin, Germany",
        "formatted_address": "Europaplatz 1, Mitte, 10557 Berlin, Germany",
        "latitude": 52.5251,
        "longitude": 13.3694,
        "lat": 52.5251,
        "lon": 13.3694,
        "lng": 13.3694,
        "category": "transportation.railway_station",
        "importance": 0.95,
        "city": "Berlin",
        "district": "Mitte",
        "suburb": "Mitte",
        "state": "Berlin",
        "postcode": "10557",
        "country": "Germany",
        "address": {
            "house_number": "1",
            "road": "Europaplatz",
            "neighbourhood": "Mitte",
            "suburb": "Mitte",
            "city": "Berlin",
            "district": "Mitte",
            "state": "Berlin",
            "postcode": "10557",
            "country": "Germany",
            "country_code": "de",
        },
        "provider": "mapbox",
        "source": "mapbox",
    },
    {
        "mapbox_id": "mbx:poi:burj_khalifa",
        "name": "Burj Khalifa",
        "primaryText": "Burj Khalifa",
        "secondaryText": "1 Sheikh Mohammed bin Rashid Blvd, Downtown Dubai, Dubai, UAE",
        "displayName": "Burj Khalifa, 1 Sheikh Mohammed bin Rashid Blvd, Downtown Dubai, Dubai, UAE",
        "display_name": "Burj Khalifa, 1 Sheikh Mohammed bin Rashid Blvd, Downtown Dubai, Dubai, UAE",
        "formatted_address": "1 Sheikh Mohammed bin Rashid Blvd, Downtown Dubai, Dubai, United Arab Emirates",
        "latitude": 25.1972,
        "longitude": 55.2744,
        "lat": 25.1972,
        "lon": 55.2744,
        "lng": 55.2744,
        "category": "tourism.skyscraper",
        "importance": 0.98,
        "city": "Dubai",
        "district": "Downtown Dubai",
        "suburb": "Downtown Dubai",
        "state": "Dubai",
        "country": "United Arab Emirates",
        "address": {
            "house_number": "1",
            "road": "Sheikh Mohammed bin Rashid Blvd",
            "neighbourhood": "Downtown Dubai",
            "suburb": "Downtown Dubai",
            "city": "Dubai",
            "district": "Downtown Dubai",
            "state": "Dubai",
            "country": "United Arab Emirates",
            "country_code": "ae",
        },
        "provider": "mapbox",
        "source": "mapbox",
    },
    {
        "mapbox_id": "mbx:poi:shibuya_station",
        "name": "Shibuya Station",
        "primaryText": "Shibuya Station",
        "secondaryText": "Dogenzaka, Shibuya, Tokyo, Japan",
        "displayName": "Shibuya Station, Dogenzaka, Shibuya, Tokyo, Japan",
        "display_name": "Shibuya Station, Dogenzaka, Shibuya, Tokyo, Japan",
        "formatted_address": "Dogenzaka, Shibuya, Tokyo 150-0043, Japan",
        "latitude": 35.6580,
        "longitude": 139.7016,
        "lat": 35.6580,
        "lon": 139.7016,
        "lng": 139.7016,
        "category": "transportation.railway_station",
        "importance": 0.95,
        "city": "Shibuya",
        "district": "Tokyo",
        "suburb": "Dogenzaka",
        "state": "Tokyo",
        "postcode": "150-0043",
        "country": "Japan",
        "address": {
            "house_number": "",
            "road": "",
            "neighbourhood": "Dogenzaka",
            "suburb": "Dogenzaka",
            "city": "Shibuya",
            "district": "Tokyo",
            "state": "Tokyo",
            "postcode": "150-0043",
            "country": "Japan",
            "country_code": "jp",
        },
        "provider": "mapbox",
        "source": "mapbox",
    },
    {
        "mapbox_id": "mbx:poi:marina_bay_sands",
        "name": "Marina Bay Sands",
        "primaryText": "Marina Bay Sands",
        "secondaryText": "10 Bayfront Avenue, Singapore",
        "displayName": "Marina Bay Sands, 10 Bayfront Avenue, Singapore",
        "display_name": "Marina Bay Sands, 10 Bayfront Avenue, Singapore",
        "formatted_address": "10 Bayfront Avenue, Singapore 018956",
        "latitude": 1.2834,
        "longitude": 103.8607,
        "lat": 1.2834,
        "lon": 103.8607,
        "lng": 103.8607,
        "category": "tourism.hotel",
        "importance": 0.95,
        "city": "Singapore",
        "district": "Central Region",
        "suburb": "Marina Bay",
        "state": "Singapore",
        "postcode": "018956",
        "country": "Singapore",
        "address": {
            "house_number": "10",
            "road": "Bayfront Avenue",
            "neighbourhood": "Marina Bay",
            "suburb": "Marina Bay",
            "city": "Singapore",
            "district": "Central Region",
            "state": "Singapore",
            "postcode": "018956",
            "country": "Singapore",
            "country_code": "sg",
        },
        "provider": "mapbox",
        "source": "mapbox",
    },
    {
        "mapbox_id": "mbx:poi:sydney_opera_house",
        "name": "Sydney Opera House",
        "primaryText": "Sydney Opera House",
        "secondaryText": "Bennelong Point, Sydney, NSW 2000, Australia",
        "displayName": "Sydney Opera House, Bennelong Point, Sydney, NSW 2000, Australia",
        "display_name": "Sydney Opera House, Bennelong Point, Sydney, NSW 2000, Australia",
        "formatted_address": "Bennelong Point, Sydney, New South Wales 2000, Australia",
        "latitude": -33.8568,
        "longitude": 151.2153,
        "lat": -33.8568,
        "lon": 151.2153,
        "lng": 151.2153,
        "category": "tourism.arts_centre",
        "importance": 0.98,
        "city": "Sydney",
        "district": "Sydney",
        "suburb": "Sydney",
        "state": "New South Wales",
        "postcode": "2000",
        "country": "Australia",
        "address": {
            "house_number": "",
            "road": "Bennelong Point",
            "neighbourhood": "Sydney",
            "suburb": "Sydney",
            "city": "Sydney",
            "district": "Sydney",
            "state": "New South Wales",
            "postcode": "2000",
            "country": "Australia",
            "country_code": "au",
        },
        "provider": "mapbox",
        "source": "mapbox",
    }
]


# =====================================================================
# Text Normalization & Clean Formatting Helpers
# =====================================================================

def _normalize(value: str) -> str:
    """Normalize string for robust fuzzy matching and cache key hashing."""
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _normalize_query_text(text: str) -> str:
    """Generalized normalization for queries."""
    s = (text or "").lower()
    s = re.sub(r"(?<=\b[a-z])\.(?=[a-z]\b)", "", s)
    s = re.sub(r"(?<=\b[a-z])\.(?=\s|$)", "", s)
    s = re.sub(r"\b([a-z])\s+([a-z])\b", r"\1\2", s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def _expand_query_terms(query: str) -> str:
    """Expand common abbreviations and place-name synonyms."""
    clean = _normalize_query_text(query)
    if "mg road" in clean:
        clean = clean.replace("mg road", "mahatma gandhi road")
    words = clean.split()
    expanded = [COMMON_SYNONYMS.get(w, w) for w in words]
    return " ".join(expanded)


def _cache_get(key: str) -> Optional[Any]:
    cached = _cache.get(key)
    if cached:
        timestamp, value = cached
        if time.time() - timestamp < CACHE_TTL_SECONDS:
            return value
        _cache.pop(key, None)
    return None


def _cache_set(key: str, value: Any) -> None:
    now = time.time()
    if len(_cache) > 3000:
        for old_key, (ts, _) in list(_cache.items()):
            if now - ts >= CACHE_TTL_SECONDS:
                _cache.pop(old_key, None)
    _cache[key] = (now, value)


def _haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate approximate distance between two points on Earth in km."""
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    return 6371.0 * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def _clean_place_texts(
    name: str,
    suburb: str = "",
    city: str = "",
    state: str = "",
    country: str = "",
    formatted: str = "",
) -> Tuple[str, str, str]:
    """Format clean, concise place labels avoiding duplicate text."""
    primary = name.strip()
    if not primary:
        if formatted:
            primary = formatted.split(",")[0].strip()
        else:
            primary = (suburb or city or "Selected Location").strip()

    norm_primary = _normalize(primary)

    # Build concise secondary text
    secondary_parts: List[str] = []
    for part in (suburb, city, state, country):
        part_clean = part.strip()
        if not part_clean or part_clean.lower() in {"null", "none", "undefined", "n/a"}:
            continue
        norm_part = _normalize(part_clean)
        if norm_part not in norm_primary and not any(norm_part == _normalize(p) for p in secondary_parts):
            secondary_parts.append(part_clean)

    secondary = ", ".join(secondary_parts[:3])
    if secondary:
        display_name = f"{primary}, {secondary}"
    else:
        display_name = primary

    return primary, secondary, display_name


# =====================================================================
# Mapbox Data Transformation Helpers
# =====================================================================

def _format_mapbox_suggestion(item: Dict[str, Any]) -> Dict[str, Any]:
    """Transform Mapbox Search Box /suggest item into suggestion format."""
    mapbox_id = item.get("mapbox_id") or ""
    name = (item.get("name") or "").strip()
    feature_type = item.get("feature_type") or "place"
    place_formatted = (item.get("place_formatted") or "").strip()
    full_address = (item.get("full_address") or "").strip()
    maki = item.get("maki") or feature_type

    ctx = item.get("context") or {}
    country_info = ctx.get("country") if isinstance(ctx.get("country"), dict) else {}
    country = country_info.get("name") or (ctx.get("country") if isinstance(ctx.get("country"), str) else "")
    region_info = ctx.get("region") if isinstance(ctx.get("region"), dict) else {}
    state = region_info.get("name") or (ctx.get("region") if isinstance(ctx.get("region"), str) else "")
    place_info = ctx.get("place") if isinstance(ctx.get("place"), dict) else {}
    city = place_info.get("name") or (ctx.get("place") if isinstance(ctx.get("place"), str) else "")
    district_info = ctx.get("district") if isinstance(ctx.get("district"), dict) else {}
    district = district_info.get("name") or ""
    locality_info = ctx.get("locality") if isinstance(ctx.get("locality"), dict) else {}
    suburb = locality_info.get("name") or (ctx.get("neighborhood", {}).get("name") if isinstance(ctx.get("neighborhood"), dict) else "")
    postcode_info = ctx.get("postcode") if isinstance(ctx.get("postcode"), dict) else {}
    postcode = postcode_info.get("name") or ""
    street_info = ctx.get("street") if isinstance(ctx.get("street"), dict) else {}
    road = street_info.get("name") or item.get("address", "")

    primary, secondary, display_name = _clean_place_texts(
        name=name,
        suburb=suburb,
        city=city,
        state=state,
        country=country,
        formatted=place_formatted,
    )

    return {
        "mapbox_id": mapbox_id,
        "name": primary,
        "primaryText": primary,
        "secondaryText": secondary or place_formatted,
        "displayName": display_name,
        "display_name": display_name,
        "place_formatted": place_formatted,
        "full_address": full_address or display_name,
        "feature_type": feature_type,
        "category": maki,
        "city": city,
        "district": district,
        "suburb": suburb,
        "state": state,
        "postcode": postcode,
        "country": country,
        "address": {
            "house_number": "",
            "road": road,
            "neighbourhood": suburb,
            "suburb": suburb,
            "city": city,
            "district": district,
            "state": state,
            "postcode": postcode,
            "country": country,
            "country_code": country_info.get("country_code", "").lower(),
        },
        "provider": "mapbox",
        "source": "mapbox",
    }


def _format_mapbox_feature(feature: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Transform Mapbox Search Box /retrieve feature into unified normalized Location."""
    try:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates")
        if not coords or len(coords) < 2:
            coord_dict = props.get("coordinates") or {}
            lon = float(coord_dict.get("longitude", 0.0))
            lat = float(coord_dict.get("latitude", 0.0))
        else:
            lon = float(coords[0])
            lat = float(coords[1])

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None

        mapbox_id = props.get("mapbox_id") or ""
        name = (props.get("name") or "").strip()
        place_formatted = (props.get("place_formatted") or "").strip()
        full_address = (props.get("full_address") or "").strip()
        feature_type = props.get("feature_type") or "place"
        category = props.get("maki") or feature_type

        ctx = props.get("context") or {}
        country_info = ctx.get("country") if isinstance(ctx.get("country"), dict) else {}
        country = country_info.get("name") or ""
        country_code = (country_info.get("country_code") or "in").lower()
        region_info = ctx.get("region") if isinstance(ctx.get("region"), dict) else {}
        state = region_info.get("name") or ""
        place_info = ctx.get("place") if isinstance(ctx.get("place"), dict) else {}
        city = place_info.get("name") or ""
        district_info = ctx.get("district") if isinstance(ctx.get("district"), dict) else {}
        district = district_info.get("name") or ""
        locality_info = ctx.get("locality") if isinstance(ctx.get("locality"), dict) else {}
        suburb = locality_info.get("name") or (ctx.get("neighborhood", {}).get("name") if isinstance(ctx.get("neighborhood"), dict) else "")
        postcode_info = ctx.get("postcode") if isinstance(ctx.get("postcode"), dict) else {}
        postcode = postcode_info.get("name") or ""
        street_info = ctx.get("street") if isinstance(ctx.get("street"), dict) else {}
        road = street_info.get("name") or props.get("address", "")
        house_number = props.get("house_number") or ""

        primary, secondary, display_name = _clean_place_texts(
            name=name,
            suburb=suburb,
            city=city,
            state=state,
            country=country,
            formatted=place_formatted,
        )

        return {
            "mapbox_id": mapbox_id,
            "name": primary,
            "primaryText": primary,
            "secondaryText": secondary or place_formatted,
            "displayName": display_name,
            "display_name": display_name,
            "formatted_address": full_address or display_name,
            "latitude": lat,
            "longitude": lon,
            "lat": lat,
            "lon": lon,
            "lng": lon,
            "city": city,
            "district": district,
            "suburb": suburb,
            "state": state,
            "postcode": postcode,
            "country": country or "India",
            "category": category,
            "importance": 0.95,
            "address": {
                "house_number": house_number,
                "road": road,
                "neighbourhood": suburb,
                "suburb": suburb,
                "village": "",
                "town": city,
                "city": city,
                "municipality": "",
                "district": district,
                "state": state,
                "postcode": postcode,
                "country": country or "India",
                "country_code": country_code,
            },
            "provider": "mapbox",
            "source": "mapbox",
            "place_id": mapbox_id,
        }
    except (ValueError, TypeError, KeyError) as err:
        logger.debug("Failed parsing Mapbox feature: %s", err)
        return None


def _format_mapbox_v5_feature(feature: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Transform Mapbox Geocoding v5 feature into unified normalized Location."""
    try:
        coords = feature.get("geometry", {}).get("coordinates")
        if not coords or len(coords) < 2:
            return None
        lon, lat = float(coords[0]), float(coords[1])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None

        mapbox_id = feature.get("id") or ""
        name = feature.get("text") or feature.get("place_name", "")
        place_name = feature.get("place_name") or name
        place_types = feature.get("place_type") or []
        category = place_types[0] if place_types else "place"

        house_number = feature.get("address") or ""
        road = ""
        if "address" in place_types or house_number:
            road = feature.get("text") or ""

        suburb = ""
        city = ""
        district = ""
        state = ""
        country = ""
        country_code = "in"
        postcode = ""

        for ctx in feature.get("context", []):
            cid = ctx.get("id", "")
            ctext = ctx.get("text", "")
            if cid.startswith("neighborhood") or cid.startswith("locality"):
                suburb = suburb or ctext
            elif cid.startswith("place"):
                city = ctext
            elif cid.startswith("district"):
                district = ctext
            elif cid.startswith("region"):
                state = ctext
            elif cid.startswith("postcode"):
                postcode = ctext
            elif cid.startswith("country"):
                country = ctext
                country_code = (ctx.get("short_code") or "in").lower()

        if not city and district:
            city = district

        primary, secondary, display_name = _clean_place_texts(
            name=name,
            suburb=suburb,
            city=city,
            state=state,
            country=country,
            formatted=place_name,
        )

        return {
            "mapbox_id": mapbox_id,
            "name": primary,
            "primaryText": primary,
            "secondaryText": secondary,
            "displayName": display_name,
            "display_name": display_name,
            "formatted_address": place_name,
            "latitude": lat,
            "longitude": lon,
            "lat": lat,
            "lon": lon,
            "lng": lon,
            "city": city,
            "district": district,
            "suburb": suburb,
            "state": state,
            "postcode": postcode,
            "country": country or "India",
            "category": category,
            "importance": float(feature.get("relevance", 0.9)),
            "address": {
                "house_number": house_number,
                "road": road,
                "neighbourhood": suburb,
                "suburb": suburb,
                "village": "",
                "town": city,
                "city": city,
                "municipality": "",
                "district": district,
                "state": state,
                "postcode": postcode,
                "country": country or "India",
                "country_code": country_code,
            },
            "provider": "mapbox",
            "source": "mapbox",
            "place_id": mapbox_id,
        }
    except (ValueError, TypeError, KeyError) as err:
        logger.debug("Failed parsing Mapbox v5 feature: %s", err)
        return None


# =====================================================================
# Legacy Provider Parsers (Kept for test suite & fallback compatibility)
# =====================================================================

def _format_photon_feature(feature: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Transform Photon GeoJSON feature into unified GeocodeResult."""
    try:
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        coords = geometry.get("coordinates")
        if not coords or len(coords) < 2:
            return None

        lon, lat = float(coords[0]), float(coords[1])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None

        raw_name = props.get("name") or props.get("street") or props.get("city") or ""
        house_number = props.get("housenumber") or ""
        street = props.get("street") or ""
        district = props.get("district") or props.get("county") or ""
        suburb = props.get("suburb") or props.get("neighbourhood") or district or ""
        city = props.get("city") or props.get("town") or props.get("village") or district or ""
        state = props.get("state") or ""
        country = props.get("country") or "India"
        country_code = (props.get("countrycode") or "in").lower()
        postcode = props.get("postcode") or ""
        osm_key = props.get("osm_key") or ""
        osm_value = props.get("osm_value") or ""
        osm_type = props.get("osm_type") or ""
        osm_id = props.get("osm_id") or ""
        provider_place_id = f"{osm_type}:{osm_id}" if osm_type and osm_id else ""

        category = f"{osm_key}.{osm_value}" if osm_key and osm_value else (osm_key or osm_value or props.get("type", ""))

        primary, secondary, display_name = _clean_place_texts(
            name=raw_name,
            suburb=suburb,
            city=city,
            state=state,
            country=country,
        )

        return {
            "name": primary,
            "primaryText": primary,
            "secondaryText": secondary,
            "displayName": display_name,
            "display_name": display_name,
            "latitude": lat,
            "longitude": lon,
            "lat": lat,
            "lon": lon,
            "lng": lon,
            "category": category,
            "importance": 0.88,
            "address": {
                "house_number": house_number,
                "road": street,
                "neighbourhood": suburb,
                "suburb": suburb,
                "village": "",
                "town": city,
                "city": city,
                "municipality": "",
                "district": district,
                "state": state,
                "postcode": postcode,
                "country": country,
                "country_code": country_code,
            },
            "source": "photon",
            "provider": "photon",
            "place_id": provider_place_id,
        }
    except (ValueError, TypeError, KeyError) as err:
        logger.debug("Failed parsing Photon feature: %s", err)
        return None


def _format_nominatim_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Transform OpenStreetMap Nominatim item into unified GeocodeResult."""
    try:
        lat = float(item["lat"])
        lon = float(item["lon"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None

        addr = item.get("address", {})
        raw_name = (
            item.get("name")
            or addr.get("amenity")
            or addr.get("building")
            or addr.get("shop")
            or addr.get("tourism")
            or addr.get("leisure")
            or addr.get("road")
            or ""
        )
        suburb = addr.get("suburb") or addr.get("neighbourhood") or addr.get("district") or addr.get("quarter") or ""
        city = addr.get("city") or addr.get("town") or addr.get("municipality") or addr.get("village") or addr.get("county") or ""
        state = addr.get("state") or ""
        country = addr.get("country") or "India"
        country_code = (addr.get("country_code") or "in").lower()
        street = addr.get("road") or ""
        postcode = addr.get("postcode") or ""
        house_number = addr.get("house_number") or ""
        district = addr.get("state_district") or addr.get("district") or addr.get("county") or ""
        formatted = item.get("display_name") or ""
        category = item.get("type") or item.get("class") or ""
        osm_type = item.get("osm_type") or ""
        osm_id = item.get("osm_id") or ""
        provider_place_id = f"{osm_type}:{osm_id}" if osm_type and osm_id else str(item.get("place_id") or "")

        primary, secondary, display_name = _clean_place_texts(
            name=raw_name,
            suburb=suburb,
            city=city,
            state=state,
            country=country,
            formatted=formatted,
        )

        importance = float(item.get("importance", 0.4))

        return {
            "name": primary,
            "primaryText": primary,
            "secondaryText": secondary,
            "displayName": display_name,
            "display_name": display_name,
            "latitude": lat,
            "longitude": lon,
            "lat": lat,
            "lon": lon,
            "lng": lon,
            "category": category,
            "importance": importance,
            "address": {
                "house_number": house_number,
                "road": street,
                "neighbourhood": addr.get("neighbourhood", suburb),
                "suburb": suburb,
                "village": addr.get("village", ""),
                "town": addr.get("town", city),
                "city": city,
                "municipality": addr.get("municipality", ""),
                "district": district,
                "state": state,
                "postcode": postcode,
                "country": country,
                "country_code": country_code,
            },
            "source": "nominatim",
            "provider": "nominatim",
            "place_id": provider_place_id,
        }
    except (ValueError, TypeError, KeyError) as err:
        logger.debug("Failed parsing Nominatim item: %s", err)
        return None


def _format_geoapify_feature(feature: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Transform Geoapify GeoJSON feature into unified GeocodeResult."""
    try:
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        coords = geometry.get("coordinates")
        if coords and len(coords) >= 2:
            lon, lat = float(coords[0]), float(coords[1])
        else:
            lat = float(props.get("lat", 0.0))
            lon = float(props.get("lon", 0.0))

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None

        raw_name = props.get("name") or props.get("address_line1") or ""
        suburb = props.get("suburb") or props.get("district") or props.get("neighbourhood") or ""
        city = props.get("city") or props.get("town") or props.get("municipality") or props.get("village") or ""
        state = props.get("state") or props.get("county") or ""
        country = props.get("country") or "India"
        country_code = (props.get("country_code") or "in").lower()
        street = props.get("street") or ""
        postcode = props.get("postcode") or ""
        formatted = props.get("formatted") or ""
        category = props.get("category") or props.get("result_type") or ""

        primary, secondary, display_name = _clean_place_texts(
            name=raw_name,
            suburb=suburb,
            city=city,
            state=state,
            country=country,
            formatted=formatted,
        )

        importance = float(props.get("rank", {}).get("importance", 0.5))
        popularity = float(props.get("rank", {}).get("popularity", 0.5))

        return {
            "name": primary,
            "primaryText": primary,
            "secondaryText": secondary,
            "displayName": display_name,
            "display_name": display_name,
            "latitude": lat,
            "longitude": lon,
            "lat": lat,
            "lon": lon,
            "lng": lon,
            "category": category,
            "importance": max(importance, popularity),
            "address": {
                "name": primary,
                "amenity": primary if category in {"amenity", "commercial", "tourism", "education", "transport"} else "",
                "house_number": props.get("housenumber", ""),
                "road": street,
                "suburb": suburb,
                "neighbourhood": suburb,
                "village": "",
                "town": city,
                "city": city,
                "municipality": "",
                "district": props.get("district", ""),
                "state": state,
                "postcode": postcode,
                "country": country,
                "country_code": country_code,
            },
            "source": "geoapify",
            "provider": "geoapify",
            "place_id": props.get("place_id", ""),
        }
    except (ValueError, TypeError, KeyError) as err:
        logger.debug("Failed parsing Geoapify feature: %s", err)
        return None


# =====================================================================
# Relevance Ranking and Deduplication
# =====================================================================

def _rank_result(item: Dict[str, Any], query: str, near_lat: Optional[float], near_lon: Optional[float]) -> float:
    """
    Result relevance ranker prioritizing:
    1. Exact place name match
    2. Prefix match
    3. Locality/city match
    4. Proximity to user / nearby pin
    5. POI and Transit category relevance
    """
    normalized_query = _normalize(query)
    name = _normalize(str(item.get("name") or ""))
    display_name = _normalize(str(item.get("displayName") or item.get("display_name") or ""))
    secondary = _normalize(str(item.get("secondaryText") or ""))
    expanded_query = _normalize(_expand_query_terms(query))
    score = 0.0

    # 1. Exact match
    if name == normalized_query or name == expanded_query:
        score += 160.0
    elif name.startswith(normalized_query) or name.startswith(expanded_query):
        score += 110.0
    elif normalized_query in name or expanded_query in name:
        score += 80.0
    elif normalized_query in display_name or expanded_query in display_name:
        score += 50.0
    elif normalized_query in secondary:
        score += 35.0

    # Handle Indian naming variations
    if "mg road" in normalized_query and "mahatma gandhi road" in display_name:
        score += 100.0
    if "cochin" in normalized_query and ("kochi" in name or "kochi" in display_name):
        score += 50.0

    # Word-level overlap
    query_terms = [t for t in normalized_query.split() if len(t) > 1]
    matching_terms = sum(1 for term in query_terms if term in name or term in display_name)
    score += matching_terms * 18.0

    # 2. Proximity boost when coordinates are supplied
    if near_lat is not None and near_lon is not None:
        try:
            lat = float(item.get("latitude") or item.get("lat") or 0.0)
            lon = float(item.get("longitude") or item.get("lon") or 0.0)
            dist_km = _haversine_distance_km(near_lat, near_lon, lat, lon)
            if dist_km <= 5.0:
                score += 80.0
            elif dist_km <= 20.0:
                score += 55.0
            elif dist_km <= 60.0:
                score += 35.0
            elif dist_km <= 150.0:
                score += 15.0
            else:
                score -= min(30.0, (dist_km - 150.0) * 0.1)
        except (ValueError, TypeError, KeyError):
            pass

    # 3. Kerala regional bonus
    kerala_keywords = ("kochi", "ernakulam", "kerala", "kalamassery", "edappally", "aluva", "kakkanad", "fort kochi")
    if any(kw in display_name for kw in kerala_keywords):
        score += 25.0

    # 4. Importance boost
    importance = float(item.get("importance", 0.4))
    score += min(30.0, importance * 30.0)

    # 5. POI and Transit category boost
    category = str(item.get("category") or "").lower()
    place_name_lower = name.lower()
    if any(hub in category or hub in place_name_lower for hub in (
        "airport", "station", "metro", "terminal", "mall", "hospital", "university", "college", "junction", "landmark"
    )):
        score += 30.0

    return score


def _deduplicate_results(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove spatial and textual duplicates within ~150 meters."""
    deduped: List[Dict[str, Any]] = []
    seen_coords: List[Tuple[float, float, str]] = []

    for item in items:
        lat = float(item.get("latitude") or item.get("lat") or 0.0)
        lon = float(item.get("longitude") or item.get("lon") or item.get("lng") or 0.0)
        norm_name = _normalize(item.get("name") or "")

        is_duplicate = False
        for seen_lat, seen_lon, seen_name in seen_coords:
            if norm_name == seen_name:
                is_duplicate = True
                break
            if lat != 0.0 and lon != 0.0 and _haversine_distance_km(lat, lon, seen_lat, seen_lon) < 0.15:
                if norm_name in seen_name or seen_name in norm_name:
                    is_duplicate = True
                    break

        if not is_duplicate:
            deduped.append(item)
            if lat != 0.0 or lon != 0.0:
                seen_coords.append((lat, lon, norm_name))

    return deduped


# =====================================================================
# Database Cache Operations
# =====================================================================

def _lookup_db_cache(
    query: str,
    near_lat: Optional[float] = None,
    near_lon: Optional[float] = None,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Lookup frequently searched and popular locations from database cache."""
    norm_query = _normalize(query)
    if not norm_query or len(norm_query) < 2:
        return []

    expanded = _normalize(_expand_query_terms(query))
    db: Session = SessionLocal()
    cached_results: List[Dict[str, Any]] = []

    try:
        now = datetime.utcnow()
        ttl_delta = timedelta(days=settings.LOCATION_CACHE_TTL_DAYS)
        min_date = now - ttl_delta

        matches = (
            db.query(Location)
            .filter(
                (Location.normalized_query == norm_query)
                | (Location.normalized_query == expanded)
                | (Location.normalized_query.like(f"{norm_query}%"))
                | (Location.place_name.ilike(f"%{query}%"))
            )
            .filter(Location.last_verified_at >= min_date)
            .order_by(Location.search_count.desc())
            .limit(limit)
            .all()
        )

        for loc in matches:
            primary, secondary, display_name = _clean_place_texts(
                name=loc.place_name,
                suburb=loc.suburb or loc.neighbourhood or "",
                city=loc.city or "",
                state=loc.state or "",
                country=loc.country or "India",
                formatted=loc.display_name or "",
            )
            item = {
                "id": loc.id,
                "mapbox_id": loc.provider_place_id or f"mbx:db:{loc.id}",
                "name": loc.place_name,
                "primaryText": primary,
                "secondaryText": secondary,
                "displayName": display_name,
                "display_name": display_name,
                "formatted_address": loc.display_name or display_name,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "lat": loc.latitude,
                "lon": loc.longitude,
                "lng": loc.longitude,
                "city": loc.city or "",
                "district": loc.district or "",
                "suburb": loc.suburb or "",
                "state": loc.state or "",
                "postcode": loc.postcode or "",
                "country": loc.country or "India",
                "category": "cached_location",
                "importance": min(1.0, 0.75 + ((loc.search_count or 1) / 250.0)),
                "address": {
                    "house_number": loc.house_number or "",
                    "road": loc.road or "",
                    "neighbourhood": loc.neighbourhood or "",
                    "suburb": loc.suburb or "",
                    "village": "",
                    "town": loc.city or "",
                    "city": loc.city or "",
                    "municipality": "",
                    "district": loc.district or "",
                    "state": loc.state or "",
                    "postcode": loc.postcode or "",
                    "country": loc.country or "India",
                    "country_code": "in",
                },
                "source": "cache",
                "provider": loc.provider or "mapbox",
                "place_id": loc.provider_place_id or "",
            }
            cached_results.append(item)

            try:
                loc.search_count = (loc.search_count or 1) + 1
                loc.updated_at = now
            except Exception:
                pass

        if matches:
            db.commit()
    except Exception as err:
        logger.debug("Database location cache lookup failed: %s", err)
        db.rollback()
    finally:
        db.close()

    return cached_results


def _store_db_cache(items: List[Dict[str, Any]], query: str) -> None:
    """Store newly discovered locations into database cache."""
    if not items:
        return

    norm_query = _normalize(query)
    now = datetime.utcnow()
    db: Session = SessionLocal()

    try:
        for item in items[:5]:
            lat = float(item.get("latitude") or item.get("lat") or 0.0)
            lon = float(item.get("longitude") or item.get("lon") or item.get("lng") or 0.0)
            if lat == 0.0 and lon == 0.0:
                continue

            addr = item.get("address", {})
            name = item.get("name") or item.get("primaryText") or ""
            display = item.get("displayName") or item.get("display_name") or name
            provider_id = item.get("mapbox_id") or item.get("place_id") or ""

            existing = (
                db.query(Location)
                .filter(
                    (Location.normalized_query == norm_query)
                    & (Location.latitude.between(lat - 0.001, lat + 0.001))
                    & (Location.longitude.between(lon - 0.001, lon + 0.001))
                )
                .first()
            )
            if existing:
                existing.search_count = (existing.search_count or 1) + 1
                existing.last_verified_at = now
                existing.updated_at = now
                if provider_id and not existing.provider_place_id:
                    existing.provider_place_id = provider_id
            else:
                new_loc = Location(
                    normalized_query=norm_query,
                    place_name=name,
                    display_name=display,
                    latitude=lat,
                    longitude=lon,
                    house_number=str(addr.get("house_number") or ""),
                    road=str(addr.get("road") or ""),
                    neighbourhood=str(addr.get("neighbourhood") or ""),
                    suburb=str(addr.get("suburb") or item.get("suburb") or ""),
                    city=str(addr.get("city") or addr.get("town") or item.get("city") or ""),
                    district=str(addr.get("district") or item.get("district") or ""),
                    state=str(addr.get("state") or item.get("state") or ""),
                    postcode=str(addr.get("postcode") or item.get("postcode") or ""),
                    country=str(addr.get("country") or item.get("country") or "India"),
                    provider=str(item.get("provider") or "mapbox"),
                    provider_place_id=provider_id,
                    search_count=1,
                    created_at=now,
                    updated_at=now,
                    last_verified_at=now,
                )
                db.add(new_loc)
        db.commit()
    except Exception as err:
        logger.debug("Database location cache store failed: %s", err)
        db.rollback()
    finally:
        db.close()


# =====================================================================
# Mapbox & Provider Integration Functions with Retry & Fallback
# =====================================================================

async def _fetch_mapbox_with_retry(
    client: httpx.AsyncClient,
    url: str,
    params: Dict[str, Any],
    max_retries: int = 1,
) -> Optional[httpx.Response]:
    """Execute Mapbox API request with controlled retry on 429/5xx status."""
    for attempt in range(max_retries + 1):
        try:
            resp = await client.get(url, params=params, timeout=MAPBOX_TIMEOUT)
            if resp.status_code == 200:
                return resp
            elif resp.status_code == 429:
                if attempt < max_retries:
                    logger.warning("Mapbox API 429 rate limit received. Retrying in 0.5s...")
                    await asyncio.sleep(0.5)
                    continue
                else:
                    logger.warning("Mapbox API 429 rate limit exceeded after retry.")
                    return None
            elif resp.status_code in (500, 502, 503, 504):
                if attempt < max_retries:
                    await asyncio.sleep(0.3)
                    continue
                return None
            else:
                logger.warning("Mapbox API returned status %d: %s", resp.status_code, resp.text[:150])
                return None
        except httpx.RequestError as exc:
            if attempt < max_retries:
                await asyncio.sleep(0.3)
                continue
            logger.warning("Mapbox request network error: %s", exc)
            return None
    return None


async def _search_mapbox_suggest(
    client: httpx.AsyncClient,
    query: str,
    session_token: str,
    proximity: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Execute Mapbox Search Box /suggest."""
    token = settings.MAPBOX_ACCESS_TOKEN.strip()
    if not token:
        return []

    params: Dict[str, Any] = {
        "q": query,
        "access_token": token,
        "session_token": session_token,
        "language": "en",
        "limit": limit,
    }

    if proximity:
        params["proximity"] = proximity
    if country:
        params["country"] = country

    resp = await _fetch_mapbox_with_retry(client, MAPBOX_SEARCHBOX_SUGGEST_URL, params)
    if resp and resp.status_code == 200:
        data = resp.json()
        raw_suggestions = data.get("suggestions", [])
        return [_format_mapbox_suggestion(item) for item in raw_suggestions if item.get("mapbox_id")]
    return []


async def _retrieve_mapbox_place(
    client: httpx.AsyncClient,
    mapbox_id: str,
    session_token: str,
) -> Optional[Dict[str, Any]]:
    """Execute Mapbox Search Box /retrieve/{mapbox_id}."""
    token = settings.MAPBOX_ACCESS_TOKEN.strip()
    if not token:
        return None

    url = f"{MAPBOX_SEARCHBOX_RETRIEVE_URL}/{mapbox_id}"
    params: Dict[str, Any] = {
        "access_token": token,
        "session_token": session_token,
    }

    resp = await _fetch_mapbox_with_retry(client, url, params)
    if resp and resp.status_code == 200:
        data = resp.json()
        features = data.get("features", [])
        if features:
            return _format_mapbox_feature(features[0])
    return None


async def _reverse_mapbox(
    client: httpx.AsyncClient,
    lat: float,
    lon: float,
) -> Optional[Dict[str, Any]]:
    """Execute Mapbox reverse geocoding."""
    token = settings.MAPBOX_ACCESS_TOKEN.strip()
    if not token:
        return None

    url_v5 = f"{MAPBOX_GEOCODING_PLACES_URL}/{lon:.5f},{lat:.5f}.json"
    params_v5 = {
        "access_token": token,
        "types": "address,poi,neighborhood,locality,place,postcode,region,country",
        "limit": 1,
    }

    resp = await _fetch_mapbox_with_retry(client, url_v5, params_v5)
    if resp and resp.status_code == 200:
        data = resp.json()
        features = data.get("features", [])
        if features:
            parsed = _format_mapbox_v5_feature(features[0])
            if parsed:
                return parsed

    params_sb = {
        "longitude": f"{lon:.5f}",
        "latitude": f"{lat:.5f}",
        "access_token": token,
    }
    resp_sb = await _fetch_mapbox_with_retry(client, MAPBOX_SEARCHBOX_REVERSE_URL, params_sb)
    if resp_sb and resp_sb.status_code == 200:
        data_sb = resp_sb.json()
        features = data_sb.get("features", [])
        if features:
            parsed = _format_mapbox_feature(features[0])
            if parsed:
                return parsed

    return None


async def _search_mapbox_geocoding_v5(
    client: httpx.AsyncClient,
    query: str,
    near_lat: Optional[float] = None,
    near_lon: Optional[float] = None,
    country: Optional[str] = None,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Forward search using Mapbox Geocoding v5."""
    token = settings.MAPBOX_ACCESS_TOKEN.strip()
    if not token:
        return []

    url = f"{MAPBOX_GEOCODING_PLACES_URL}/{query}.json"
    params: Dict[str, Any] = {
        "access_token": token,
        "limit": limit,
    }
    if near_lat is not None and near_lon is not None:
        params["proximity"] = f"{near_lon:.5f},{near_lat:.5f}"
    if country:
        params["country"] = country

    resp = await _fetch_mapbox_with_retry(client, url, params)
    if resp and resp.status_code == 200:
        data = resp.json()
        features = data.get("features", [])
        results: List[Dict[str, Any]] = []
        for feat in features:
            parsed = _format_mapbox_v5_feature(feat)
            if parsed:
                results.append(parsed)
        return results
    return []


async def _search_geoapify(
    client: httpx.AsyncClient,
    query: str,
    near_lat: Optional[float],
    near_lon: Optional[float],
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Execute Geoapify autocomplete search."""
    params = {
        "text": query,
        "apiKey": settings.GEOAPIFY_API_KEY.strip(),
        "limit": limit,
        "lang": "en",
        "format": "geojson",
    }
    if near_lat is not None and near_lon is not None:
        params["bias"] = f"proximity:{near_lon:.5f},{near_lat:.5f}"
    try:
        resp = await client.get(GEOAPIFY_AUTOCOMPLETE_URL, params=params, timeout=GEOAPIFY_TIMEOUT)
        if resp.status_code == 200:
            feats = resp.json().get("features", [])
            return [_format_geoapify_feature(f) for f in feats if _format_geoapify_feature(f) is not None]
    except Exception as err:
        logger.warning("Geoapify search failed: %s", err)
    return []


async def _search_photon(
    query: str,
    near_lat: Optional[float] = None,
    near_lon: Optional[float] = None,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Execute Photon (OSM) search as free worldwide fallback when Mapbox is unavailable."""
    url = f"{settings.PHOTON_BASE_URL}/api/"
    params: Dict[str, Any] = {
        "q": query,
        "limit": limit,
    }
    if near_lat is not None and near_lon is not None:
        params["lat"] = near_lat
        params["lon"] = near_lon
    try:
        async with httpx.AsyncClient(headers=DEFAULT_HEADERS) as client:
            resp = await client.get(url, params=params, timeout=PHOTON_TIMEOUT)
            if resp.status_code == 200:
                features = resp.json().get("features", [])
                results = []
                for feat in features:
                    parsed = _format_photon_feature(feat)
                    if parsed:
                        results.append(parsed)
                return results
    except Exception as err:
        logger.debug("Photon fallback search failed: %s", err)
    return []


# =====================================================================
# Fallback / Catalog Lookup (for testing or token-absent mode)
# =====================================================================

def _match_fallback_catalog(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Match query against built-in worldwide catalog for offline & test resilience."""
    clean = _normalize_query_text(query)
    expanded = _normalize(_expand_query_terms(query))
    matches: List[Dict[str, Any]] = []

    for item in FALLBACK_CATALOG:
        name_norm = _normalize(item["name"])
        disp_norm = _normalize(item["displayName"])
        if (
            clean in name_norm
            or clean in disp_norm
            or expanded in name_norm
            or expanded in disp_norm
            or name_norm in clean
        ):
            matches.append(dict(item))
            if len(matches) >= limit:
                break
    return matches


# =====================================================================
# Unified Location Search & Autocomplete Pipeline
# =====================================================================

async def _perform_suggest(
    query: str,
    session_token: str,
    proximity: Optional[str] = None,
    near_lat: Optional[float] = None,
    near_lon: Optional[float] = None,
    country: Optional[str] = None,
    limit: int = 8,
) -> Tuple[List[Dict[str, Any]], str]:
    """Unified suggest pipeline with Mapbox Search Box /suggest and Photon fallback."""
    clean_query = " ".join(query.split())
    norm_query = _normalize(clean_query)
    cache_key = f"suggest:{norm_query}:{proximity}:{country}:{limit}"

    cached = _cache_get(cache_key)
    if cached is not None:
        return cached, session_token

    prox_str = proximity
    if not prox_str and near_lat is not None and near_lon is not None:
        prox_str = f"{near_lon:.5f},{near_lat:.5f}"

    suggestions: List[Dict[str, Any]] = []

    if settings.MAPBOX_ACCESS_TOKEN.strip():
        async with httpx.AsyncClient(headers=DEFAULT_HEADERS) as client:
            suggestions = await _search_mapbox_suggest(
                client=client,
                query=clean_query,
                session_token=session_token,
                proximity=prox_str,
                country=country,
                limit=limit,
            )

    if not suggestions:
        catalog_items = _match_fallback_catalog(clean_query, limit=limit)
        db_items = _lookup_db_cache(clean_query, near_lat, near_lon, limit=limit)
        combined = catalog_items + db_items

        if not combined:
            photon_items = await _search_photon(clean_query, near_lat, near_lon, limit=limit)
            if photon_items:
                combined.extend(photon_items)
                asyncio.create_task(asyncio.to_thread(_store_db_cache, photon_items, clean_query))

        for item in combined:
            primary = item.get("primaryText") or item.get("name") or ""
            sec = item.get("secondaryText") or ""
            disp = item.get("displayName") or item.get("display_name") or primary
            item_id = item.get("mapbox_id") or item.get("place_id") or f"mbx:mock:{_normalize(primary)}"
            sug = {
                "mapbox_id": item_id,
                "name": primary,
                "primaryText": primary,
                "secondaryText": sec,
                "displayName": disp,
                "display_name": disp,
                "place_formatted": sec,
                "full_address": item.get("formatted_address") or disp,
                "feature_type": item.get("category") or "place",
                "category": item.get("category") or "place",
                "city": item.get("city", ""),
                "district": item.get("district", ""),
                "suburb": item.get("suburb", ""),
                "state": item.get("state", ""),
                "postcode": item.get("postcode", ""),
                "country": item.get("country", ""),
                "address": item.get("address", {}),
                "provider": "mapbox",
                "source": "cache",
            }
            if "latitude" in item and "longitude" in item:
                sug["latitude"] = item["latitude"]
                sug["longitude"] = item["longitude"]
                sug["lat"] = item["latitude"]
                sug["lon"] = item["longitude"]
                sug["lng"] = item["longitude"]
            _cache_set(f"retrieve:{item_id}", sug)
            suggestions.append(sug)

    deduped = _deduplicate_results(suggestions)[:limit]
    if deduped:
        _cache_set(cache_key, deduped)

    return deduped, session_token


async def _perform_retrieve(
    mapbox_id: str,
    session_token: str,
) -> Optional[Dict[str, Any]]:
    """Unified retrieve pipeline with Mapbox Search Box /retrieve."""
    cache_key = f"retrieve:{mapbox_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    result: Optional[Dict[str, Any]] = None

    if settings.MAPBOX_ACCESS_TOKEN.strip():
        async with httpx.AsyncClient(headers=DEFAULT_HEADERS) as client:
            result = await _retrieve_mapbox_place(client, mapbox_id, session_token)

    if not result:
        for item in FALLBACK_CATALOG:
            if item.get("mapbox_id") == mapbox_id:
                result = dict(item)
                break

    if not result:
        db: Session = SessionLocal()
        try:
            loc = db.query(Location).filter(
                (Location.provider_place_id == mapbox_id)
                | (Location.id == (int(mapbox_id.split(":")[-1]) if mapbox_id.split(":")[-1].isdigit() else -1))
            ).first()
            if loc:
                primary, secondary, display_name = _clean_place_texts(
                    name=loc.place_name,
                    suburb=loc.suburb or "",
                    city=loc.city or "",
                    state=loc.state or "",
                    country=loc.country or "India",
                    formatted=loc.display_name or "",
                )
                result = {
                    "mapbox_id": mapbox_id,
                    "name": loc.place_name,
                    "primaryText": primary,
                    "secondaryText": secondary,
                    "displayName": display_name,
                    "display_name": display_name,
                    "formatted_address": loc.display_name or display_name,
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "lat": loc.latitude,
                    "lon": loc.longitude,
                    "lng": loc.longitude,
                    "city": loc.city or "",
                    "district": loc.district or "",
                    "suburb": loc.suburb or "",
                    "state": loc.state or "",
                    "postcode": loc.postcode or "",
                    "country": loc.country or "India",
                    "category": "cached_place",
                    "importance": 0.9,
                    "address": {
                        "house_number": loc.house_number or "",
                        "road": loc.road or "",
                        "neighbourhood": loc.neighbourhood or "",
                        "suburb": loc.suburb or "",
                        "city": loc.city or "",
                        "district": loc.district or "",
                        "state": loc.state or "",
                        "postcode": loc.postcode or "",
                        "country": loc.country or "India",
                        "country_code": "in",
                    },
                    "provider": "mapbox",
                    "source": "cache",
                }
        finally:
            db.close()

    if result:
        _cache_set(cache_key, result)
        asyncio.create_task(asyncio.to_thread(_store_db_cache, [result], result.get("name", "")))

    return result


async def _perform_reverse_geocode(lat: float, lon: float) -> Dict[str, Any]:
    """Unified reverse geocoding with Mapbox Reverse."""
    cache_key = f"rev:{round(lat, 5)}:{round(lon, 5)}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    # Check Database cache within ~60 meters
    db: Session = SessionLocal()
    try:
        match = (
            db.query(Location)
            .filter(
                Location.latitude.between(lat - 0.0006, lat + 0.0006)
                & Location.longitude.between(lon - 0.0006, lon + 0.0006)
            )
            .first()
        )
        if match:
            primary, secondary, display_name = _clean_place_texts(
                name=match.place_name,
                suburb=match.suburb or match.neighbourhood or "",
                city=match.city or "",
                state=match.state or "",
                country=match.country or "India",
                formatted=match.display_name or "",
            )
            db_item = {
                "name": match.place_name,
                "primaryText": primary,
                "secondaryText": secondary,
                "displayName": display_name,
                "display_name": display_name,
                "formatted_address": match.display_name or display_name,
                "latitude": match.latitude,
                "longitude": match.longitude,
                "lat": match.latitude,
                "lon": match.longitude,
                "lng": match.longitude,
                "city": match.city or "",
                "district": match.district or "",
                "suburb": match.suburb or "",
                "state": match.state or "",
                "postcode": match.postcode or "",
                "country": match.country or "India",
                "address": {
                    "house_number": match.house_number or "",
                    "road": match.road or "",
                    "neighbourhood": match.neighbourhood or "",
                    "suburb": match.suburb or "",
                    "village": "",
                    "town": match.city or "",
                    "city": match.city or "",
                    "municipality": "",
                    "district": match.district or "",
                    "state": match.state or "",
                    "postcode": match.postcode or "",
                    "country": match.country or "India",
                    "country_code": "in",
                },
                "provider": "mapbox",
                "source": "cache",
            }
            _cache_set(cache_key, db_item)
            return db_item
    except Exception as err:
        logger.debug("Database reverse geocode check error: %s", err)
    finally:
        db.close()

    result: Optional[Dict[str, Any]] = None

    if settings.MAPBOX_ACCESS_TOKEN.strip():
        async with httpx.AsyncClient(headers=DEFAULT_HEADERS) as client:
            result = await _reverse_mapbox(client, lat, lon)

    if not result:
        for item in FALLBACK_CATALOG:
            clat = float(item.get("latitude") or 0.0)
            clon = float(item.get("longitude") or 0.0)
            if clat != 0.0 and clon != 0.0 and _haversine_distance_km(lat, lon, clat, clon) < 0.2:
                result = dict(item)
                break

    if not result:
        label = f"Location ({lat:.4f}, {lon:.4f})"
        result = {
            "name": label,
            "primaryText": label,
            "secondaryText": "",
            "displayName": label,
            "display_name": label,
            "formatted_address": label,
            "latitude": lat,
            "longitude": lon,
            "lat": lat,
            "lon": lon,
            "lng": lon,
            "city": "",
            "district": "",
            "suburb": "",
            "state": "",
            "postcode": "",
            "country": "India",
            "address": {
                "house_number": "",
                "road": "",
                "suburb": "",
                "neighbourhood": "",
                "city": "",
                "district": "",
                "state": "",
                "postcode": "",
                "country": "India",
                "country_code": "in",
            },
            "provider": "mapbox",
            "source": "fallback",
        }

    _cache_set(cache_key, result)
    return result


async def _perform_location_search(
    query: str,
    near_lat: Optional[float] = None,
    near_lon: Optional[float] = None,
    context: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Search pipeline returning full locations with coordinates for legacy endpoints & direct searches."""
    clean_query = " ".join(query.split())
    norm_query = _normalize(clean_query)
    rounded_lat = round(near_lat, 2) if near_lat is not None else None
    rounded_lon = round(near_lon, 2) if near_lon is not None else None
    cache_key = f"search:{norm_query}:{rounded_lat}:{rounded_lon}:{country}:{limit}"

    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    results: List[Dict[str, Any]] = []

    # If Geoapify is explicitly chosen provider and has API key, prioritize it
    if settings.GEOCODING_PROVIDER.lower() == "geoapify" and settings.GEOAPIFY_API_KEY.strip():
        async with httpx.AsyncClient(headers=DEFAULT_HEADERS) as client:
            geo_results = await _search_geoapify(client, clean_query, near_lat, near_lon, limit=limit)
            if geo_results:
                results.extend(geo_results)

    # Step 1: Database Cache hit (if not Geoapify mode)
    if settings.GEOCODING_PROVIDER.lower() != "geoapify":
        db_cached = _lookup_db_cache(clean_query, near_lat, near_lon, limit=limit)
        if len(db_cached) >= limit:
            db_cached.sort(key=lambda item: _rank_result(item, clean_query, near_lat, near_lon), reverse=True)
            deduped = _deduplicate_results(db_cached)[:limit]
            _cache_set(cache_key, deduped)
            return deduped
        results.extend(db_cached)

    # Step 2: Query Mapbox Geocoding if token available
    if not results and settings.MAPBOX_ACCESS_TOKEN.strip():
        async with httpx.AsyncClient(headers=DEFAULT_HEADERS) as client:
            mapbox_results = await _search_mapbox_geocoding_v5(
                client=client,
                query=clean_query,
                near_lat=near_lat,
                near_lon=near_lon,
                country=country,
                limit=limit,
            )
            if mapbox_results:
                results.extend(mapbox_results)

    # Step 3: Catalog lookup for test locations if still empty
    if not results:
        results.extend(_match_fallback_catalog(clean_query, limit=limit))

    # Step 3b: Free Photon (OSM) worldwide fallback if still empty
    if not results:
        photon_results = await _search_photon(clean_query, near_lat, near_lon, limit=limit)
        if photon_results:
            results.extend(photon_results)

    # Step 4: Relevance Ranking
    results.sort(key=lambda item: _rank_result(item, clean_query, near_lat, near_lon), reverse=True)

    # Step 5: Deduplicate & Trim
    deduped = _deduplicate_results(results)[:limit]

    if deduped:
        _cache_set(cache_key, deduped)
        asyncio.create_task(asyncio.to_thread(_store_db_cache, deduped, clean_query))

    return deduped


# =====================================================================
# REST API Endpoints (Mapbox Search Box & Geocoding Migration)
# =====================================================================

@router.get("/location/suggest")
@router.get("/api/location/suggest")
async def location_suggest_endpoint(
    request: Request,
    q: str = Query(..., min_length=2, max_length=200, description="Search query"),
    session_token: Optional[str] = Query(None, description="Interactive search session UUID"),
    proximity: Optional[str] = Query(None, description="Proximity bias as lon,lat"),
    near_lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitude for proximity biasing"),
    near_lon: Optional[float] = Query(None, ge=-180, le=180, description="Longitude for proximity biasing"),
    country: Optional[str] = Query(None, max_length=10, description="Optional ISO country code"),
    limit: int = Query(8, ge=1, le=20, description="Maximum number of suggestions"),
):
    """
    Primary Autocomplete API using Mapbox Search Box /suggest:
    - Debounced interactive autocomplete
    - Low-overhead suggest workflow without eager coordinate retrieval
    - Tracks user session token for search sessions
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    if not await rate_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a moment.")

    active_session_token = session_token or str(uuid.uuid4())

    try:
        suggestions, token_used = await _perform_suggest(
            query=q,
            session_token=active_session_token,
            proximity=proximity,
            near_lat=near_lat,
            near_lon=near_lon,
            country=country,
            limit=limit,
        )
        return {
            "suggestions": suggestions,
            "session_token": token_used,
            "count": len(suggestions),
        }
    except Exception as err:
        logger.error("Error in location suggest: %s", err)
        return {
            "suggestions": [],
            "session_token": active_session_token,
            "count": 0,
            "message": "Unable to find this location. Try entering a nearby landmark, street, or city.",
        }


@router.get("/location/retrieve")
@router.get("/api/location/retrieve")
async def location_retrieve_endpoint(
    request: Request,
    id: Optional[str] = Query(None, description="Mapbox place identifier"),
    mapbox_id: Optional[str] = Query(None, description="Mapbox place identifier alias"),
    session_token: Optional[str] = Query(None, description="Interactive search session UUID"),
):
    """
    Place Retrieval API using Mapbox Search Box /retrieve:
    - Triggered ONLY when user selects a suggestion from dropdown
    - Retrieves authoritative latitude/longitude and normalized address structure
    - Closes and bills the search session
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    if not await rate_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a moment.")

    target_id = id or mapbox_id
    if not target_id:
        raise HTTPException(status_code=400, detail="Missing required 'id' or 'mapbox_id' parameter.")

    active_session_token = session_token or str(uuid.uuid4())

    try:
        place = await _perform_retrieve(mapbox_id=target_id, session_token=active_session_token)
        if not place:
            raise HTTPException(
                status_code=404,
                detail="Unable to find this location. Try entering a nearby landmark, street, or city."
            )
        return place
    except HTTPException:
        raise
    except Exception as err:
        logger.error("Error in location retrieve: %s", err)
        raise HTTPException(
            status_code=500,
            detail="Unable to find this location. Try entering a nearby landmark, street, or city."
        )


@router.get("/location/reverse")
@router.get("/api/location/reverse")
@router.get("/geocode/reverse")
@router.get("/api/geocode/reverse")
async def location_reverse_endpoint(
    request: Request,
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Longitude"),
    lng: Optional[float] = Query(None, ge=-180, le=180, description="Longitude alias"),
):
    """
    Reverse Geocoding API:
    - Translates GPS coordinates into structured human-readable local address
    - Returns clean fields omitting null/undefined values
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    if not await rate_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a moment.")

    actual_lon = lon if lon is not None else lng
    if actual_lon is None:
        raise HTTPException(status_code=400, detail="Missing required longitude coordinate ('lon' or 'lng').")

    try:
        return await _perform_reverse_geocode(lat=lat, lon=actual_lon)
    except Exception as err:
        logger.error("Error in reverse geocode: %s", err)
        raise HTTPException(
            status_code=500,
            detail="Unable to find address for these coordinates."
        )


@router.get("/location/search")
@router.get("/api/location/search")
@router.get("/location/autocomplete")
@router.get("/api/location/autocomplete")
async def location_search_endpoint(
    q: str = Query(..., min_length=2, max_length=200, description="Location search query"),
    near_lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitude for location biasing"),
    near_lon: Optional[float] = Query(None, ge=-180, le=180, description="Longitude for location biasing"),
    context: Optional[str] = Query(None, max_length=200, description="Regional context"),
    country: Optional[str] = Query(None, max_length=10, description="Optional ISO country code"),
    limit: int = Query(8, ge=1, le=20, description="Maximum number of results"),
):
    """
    Location Search & Autocomplete API (returns full results with coordinates for backwards-compatibility):
    - Supports worldwide locations, landmarks, POIs, transit hubs, and street addresses
    """
    results = await _perform_location_search(
        query=q,
        near_lat=near_lat,
        near_lon=near_lon,
        context=context,
        country=country,
        limit=limit,
    )
    return {"results": results, "count": len(results)}


@router.get("/geocode")
@router.get("/api/geocode")
async def geocode_legacy_endpoint(
    q: str = Query(..., min_length=2, max_length=200),
    near_lat: Optional[float] = Query(None, ge=-90, le=90),
    near_lon: Optional[float] = Query(None, ge=-180, le=180),
    context: Optional[str] = Query(None, max_length=200),
    country: Optional[str] = Query(None, max_length=10),
    limit: int = Query(8, ge=1, le=20),
    format: Optional[str] = Query("list", description="Return format: 'list' or 'object'"),
):
    """
    Backwards-compatible geocode endpoint for existing test suites and legacy consumers.
    """
    results = await _perform_location_search(
        query=q,
        near_lat=near_lat,
        near_lon=near_lon,
        context=context,
        country=country,
        limit=limit,
    )
    if format == "object":
        return {"results": results, "count": len(results)}
    return results
