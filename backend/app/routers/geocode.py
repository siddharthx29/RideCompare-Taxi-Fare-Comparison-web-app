import asyncio
import logging
import math
import os
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, Query, Depends, Request
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db, SessionLocal
from backend.app.models.db_models import Location

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Geocoding"])

# Provider Endpoints
PHOTON_API_URL = f"{settings.PHOTON_BASE_URL}/api"
PHOTON_REVERSE_URL = f"{settings.PHOTON_BASE_URL}/reverse"
NOMINATIM_BASE_URL = settings.NOMINATIM_BASE_URL
GEOAPIFY_AUTOCOMPLETE_URL = "https://api.geoapify.com/v1/geocode/autocomplete"
GEOAPIFY_REVERSE_URL = "https://api.geoapify.com/v1/geocode/reverse"

DEFAULT_USER_AGENT = settings.GEOCODING_USER_AGENT
DEFAULT_HEADERS = {
    "User-Agent": f"{DEFAULT_USER_AGENT} Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}

# Caching Configuration
CACHE_TTL_SECONDS = 1800  # 30 minutes in-memory TTL
_cache: Dict[str, Tuple[float, Any]] = {}
_cache_lock = asyncio.Lock()

# Nominatim Rate Limiting Guard (respects OpenStreetMap usage policy: max 1 req/sec)
_nominatim_lock = asyncio.Lock()
_last_nominatim_request = 0.0

# Timeout configurations
PHOTON_TIMEOUT = 3.5
GEOAPIFY_TIMEOUT = 3.5
NOMINATIM_TIMEOUT = 4.0

# Indian English Place Name Abbreviations & Synonym Mapping
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


def _normalize(value: str) -> str:
    """Normalize string for robust fuzzy matching and cache key hashing."""
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _normalize_query_text(text: str) -> str:
    """
    Generalized normalization for Indian place queries:
    - Handles dots in abbreviations: 'M.G. Road' -> 'mg road'
    - Handles spaced letters in abbreviations: 'M G Road' -> 'mg road'
    - Normalizes casing and excess whitespace
    - Strips non-alphanumeric noise
    """
    s = (text or "").lower()
    # Replace dots in abbreviations like 'm.g.' -> 'mg', 'p.o.' -> 'po'
    s = re.sub(r"(?<=\b[a-z])\.(?=[a-z]\b)", "", s)
    s = re.sub(r"(?<=\b[a-z])\.(?=\s|$)", "", s)
    # Collapse spaced single letters in abbreviations like 'm g' -> 'mg'
    s = re.sub(r"\b([a-z])\s+([a-z])\b", r"\1\2", s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def _expand_query_terms(query: str) -> str:
    """
    Expand abbreviations and Indian naming patterns:
    e.g. 'MG Road' -> 'mahatma gandhi road'
    e.g. 'Cochin' -> 'kochi'
    """
    clean = _normalize_query_text(query)
    # Special abbreviation phrases
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
    if len(_cache) > 2000:
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
    suburb: str,
    city: str,
    state: str,
    country: str,
    formatted: str = "",
) -> Tuple[str, str, str]:
    """
    Format clean, concise place labels avoiding 100-character raw address strings.
    Returns: (primary_text, secondary_text, display_name)
    Example: ('Lulu Mall', 'Edappally, Kochi, Kerala', 'Lulu Mall, Edappally, Kochi, Kerala')
    """
    primary = name.strip()
    if not primary:
        if formatted:
            primary = formatted.split(",")[0].strip()
        else:
            primary = (suburb or city or "Selected Location").strip()

    norm_primary = _normalize(primary)

    # Build concise secondary text (suburb, city, state)
    secondary_parts: List[str] = []
    for part in (suburb, city, state):
        part_clean = part.strip()
        if not part_clean:
            continue
        norm_part = _normalize(part_clean)
        # Avoid repeating parts that already appear in primary name
        if norm_part not in norm_primary and not any(norm_part == _normalize(p) for p in secondary_parts):
            secondary_parts.append(part_clean)

    # If primary is already a city/state and secondary is empty, add country
    if not secondary_parts and country:
        secondary_parts.append(country.strip())

    secondary = ", ".join(secondary_parts)
    if secondary:
        display_name = f"{primary}, {secondary}"
    else:
        display_name = primary

    return primary, secondary, display_name


def _format_photon_feature(feature: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Transform Photon GeoJSON feature into unified RideCompare GeocodeResult."""
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
    """Transform OpenStreetMap Nominatim item into unified RideCompare GeocodeResult."""
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
    """Transform Geoapify GeoJSON feature into unified RideCompare GeocodeResult."""
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


def _rank_result(item: Dict[str, Any], query: str, near_lat: Optional[float], near_lon: Optional[float]) -> float:
    """
    Intelligent result relevance ranker prioritizing:
    1. Exact place name match
    2. Prefix match
    3. Locality/city match
    4. Popularity/frequency
    5. Proximity to user / nearby pin
    6. Place type relevance (POIs, malls, airports, transit hubs)
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

    # Handle Indian naming variations (e.g., MG Road / Mahatma Gandhi Road)
    if "mg road" in normalized_query and "mahatma gandhi road" in display_name:
        score += 100.0
    if "cochin" in normalized_query and ("kochi" in name or "kochi" in display_name):
        score += 50.0

    # Word-level overlap
    query_terms = [t for t in normalized_query.split() if len(t) > 1]
    matching_terms = sum(1 for term in query_terms if term in name or term in display_name)
    score += matching_terms * 18.0

    # 2. Proximity boost when near coordinates are supplied
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

    # 3. Kerala / Kochi regional priority boost
    kerala_keywords = ("kochi", "ernakulam", "kerala", "kalamassery", "edappally", "aluva", "kakkanad", "fort kochi")
    if any(kw in display_name for kw in kerala_keywords):
        score += 25.0

    # 4. Importance and Popularity boost from geocoder metadata & search count
    importance = float(item.get("importance", 0.4))
    score += min(30.0, importance * 30.0)

    # If item came from popular database cache, boost by popularity
    if item.get("source") == "cache" or item.get("provider") == "cache":
        score += 20.0

    # 5. POI and Transit category boost
    category = str(item.get("category") or "").lower()
    place_name_lower = name.lower()
    if any(hub in category or hub in place_name_lower for hub in (
        "airport", "station", "metro", "terminal", "mall", "hospital", "university", "college", "junction"
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
            if _haversine_distance_km(lat, lon, seen_lat, seen_lon) < 0.15:
                # If within 150 meters and names overlap
                if norm_name in seen_name or seen_name in norm_name:
                    is_duplicate = True
                    break

        if not is_duplicate:
            deduped.append(item)
            seen_coords.append((lat, lon, norm_name))

    return deduped


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

        # Find matching cached locations
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
                "name": loc.place_name,
                "primaryText": primary,
                "secondaryText": secondary,
                "displayName": display_name,
                "display_name": display_name,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "lat": loc.latitude,
                "lon": loc.longitude,
                "lng": loc.longitude,
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
                "provider": loc.provider or "cache",
                "place_id": loc.provider_place_id or "",
            }
            cached_results.append(item)

            # Update search count & timestamp
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
    """Store newly discovered locations into the database cache."""
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

            # Check if this place or close coordinates already exists
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
                    suburb=str(addr.get("suburb") or ""),
                    city=str(addr.get("city") or addr.get("town") or ""),
                    district=str(addr.get("district") or ""),
                    state=str(addr.get("state") or ""),
                    postcode=str(addr.get("postcode") or ""),
                    country=str(addr.get("country") or "India"),
                    provider=str(item.get("source") or item.get("provider") or "photon"),
                    provider_place_id=str(item.get("place_id") or ""),
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


async def _search_photon(
    client: httpx.AsyncClient,
    query: str,
    near_lat: Optional[float],
    near_lon: Optional[float],
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """
    Execute Photon (OpenStreetMap/Elasticsearch) search:
    - Search-as-you-type and typo-tolerant
    - Location biasing with near_lat / near_lon
    - Fast response times
    """
    params: Dict[str, Any] = {
        "q": query,
        "limit": limit,
        "lang": "en",
    }

    # Location Biasing:
    if near_lat is not None and near_lon is not None:
        params["lat"] = f"{near_lat:.5f}"
        params["lon"] = f"{near_lon:.5f}"
    else:
        # Default proximity bias towards Kerala / Kochi
        params["lat"] = "9.9312"
        params["lon"] = "76.2673"

    try:
        response = await client.get(
            PHOTON_API_URL,
            params=params,
            headers=DEFAULT_HEADERS,
            timeout=PHOTON_TIMEOUT,
        )
        if response.status_code == 200:
            data = response.json()
            features = data.get("features", [])
            formatted_list: List[Dict[str, Any]] = []
            for feat in features:
                parsed = _format_photon_feature(feat)
                if parsed:
                    formatted_list.append(parsed)
            return formatted_list
        else:
            logger.warning("Photon returned status %d: %s", response.status_code, response.text[:150])
            return []
    except Exception as err:
        logger.warning("Photon place discovery search failed: %s", err)
        return []


async def _search_geoapify(
    client: httpx.AsyncClient,
    query: str,
    near_lat: Optional[float],
    near_lon: Optional[float],
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Execute Geoapify Autocomplete search as fallback."""
    api_key = settings.GEOAPIFY_API_KEY.strip()
    if not api_key:
        return []

    params: Dict[str, Any] = {
        "text": query,
        "apiKey": api_key,
        "limit": limit,
        "lang": "en",
        "format": "json",
    }

    if near_lat is not None and near_lon is not None:
        params["bias"] = f"proximity:{near_lon:.5f},{near_lat:.5f}"
    else:
        params["bias"] = "countrycode:in"

    try:
        response = await client.get(
            GEOAPIFY_AUTOCOMPLETE_URL,
            params=params,
            timeout=GEOAPIFY_TIMEOUT,
        )
        if response.status_code == 200:
            data = response.json()
            features = data.get("features", []) or data.get("results", [])
            formatted_list: List[Dict[str, Any]] = []
            for feat in features:
                feature_dict = feat if "properties" in feat else {"properties": feat, "geometry": {"coordinates": [feat.get("lon"), feat.get("lat")]}}
                formatted = _format_geoapify_feature(feature_dict)
                if formatted:
                    formatted_list.append(formatted)
            return formatted_list
        return []
    except Exception as err:
        logger.warning("Geoapify fallback search failed: %s", err)
        return []


async def _search_nominatim(
    client: httpx.AsyncClient,
    query: str,
    near_lat: Optional[float],
    near_lon: Optional[float],
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Execute OpenStreetMap Nominatim search as rate-compliant fallback."""
    global _last_nominatim_request
    async with _nominatim_lock:
        elapsed = time.monotonic() - _last_nominatim_request
        if elapsed < 0.4:
            await asyncio.sleep(0.4 - elapsed)

        params: Dict[str, Any] = {
            "format": "jsonv2",
            "q": query,
            "addressdetails": 1,
            "limit": limit,
            "accept-language": "en",
        }
        if near_lat is not None and near_lon is not None:
            params["viewbox"] = f"{near_lon - 0.4:.4f},{near_lat + 0.3:.4f},{near_lon + 0.4:.4f},{near_lat - 0.3:.4f}"

        try:
            response = await client.get(
                f"{NOMINATIM_BASE_URL}/search",
                params=params,
                headers={"User-Agent": DEFAULT_USER_AGENT},
                timeout=NOMINATIM_TIMEOUT,
            )
            _last_nominatim_request = time.monotonic()
            if response.status_code == 200:
                raw_results = response.json()
                if isinstance(raw_results, list):
                    formatted_list = [
                        _format_nominatim_item(item)
                        for item in raw_results
                        if _format_nominatim_item(item) is not None
                    ]
                    return [item for item in formatted_list if item is not None]
            return []
        except Exception as err:
            logger.warning("Nominatim fallback search failed: %s", err)
            _last_nominatim_request = time.monotonic()
            return []


async def _perform_location_search(
    query: str,
    near_lat: Optional[float] = None,
    near_lon: Optional[float] = None,
    context: Optional[str] = None,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """
    Unified layered place search pipeline:
    1. Check in-memory TTL cache (sub-millisecond)
    2. Check persistent database cache (seeded popular places & past queries)
    3. Primary: Photon place discovery (typo-tolerant, fast search-as-you-type)
    4. Fallback: Geoapify (if key configured) -> Nominatim search
    5. Rank by relevance, exactness, popularity, and proximity
    6. Deduplicate results and persist into cache
    """
    clean_query = " ".join(query.split())
    norm_query = _normalize(clean_query)
    norm_context = _normalize(context or "")
    rounded_lat = round(near_lat, 2) if near_lat is not None else None
    rounded_lon = round(near_lon, 2) if near_lon is not None else None

    # Step 1: Check In-Memory Cache
    cache_key = f"geo:{norm_query}:{norm_context}:{rounded_lat}:{rounded_lon}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    # Step 2: Check Local Database Cache
    db_cached: List[Dict[str, Any]] = []
    if settings.GEOCODING_PROVIDER.lower() != "geoapify":
        db_cached = _lookup_db_cache(clean_query, near_lat, near_lon, limit=limit)
        if len(db_cached) >= limit:
            db_cached.sort(key=lambda item: _rank_result(item, clean_query, near_lat, near_lon), reverse=True)
            deduped = _deduplicate_results(db_cached)[:limit]
            _cache_set(cache_key, deduped)
            return deduped

    results: List[Dict[str, Any]] = list(db_cached)
    expanded_query = _expand_query_terms(clean_query)

    async with httpx.AsyncClient(headers=DEFAULT_HEADERS) as client:
        # Step 3A: If Geoapify is explicitly chosen provider and has API key, try it first
        if settings.GEOCODING_PROVIDER.lower() == "geoapify" and settings.GEOAPIFY_API_KEY.strip():
            geo_results = await _search_geoapify(client, clean_query, near_lat, near_lon, limit=limit)
            if geo_results:
                results.extend(geo_results)

        # Step 3B: Primary place discovery via Photon (default)
        if not results:
            search_candidates = [clean_query]
            if expanded_query != clean_query:
                search_candidates.append(expanded_query)
            if context:
                search_candidates.append(f"{clean_query}, {context}")

            for candidate in search_candidates:
                photon_results = await _search_photon(client, candidate, near_lat, near_lon, limit=limit)
                if photon_results:
                    results.extend(photon_results)
                    break

        # Step 4: Fallback to Geoapify (if key configured and not already tried) if Photon produced no results
        if not results and settings.GEOAPIFY_API_KEY.strip():
            geo_results = await _search_geoapify(client, clean_query, near_lat, near_lon, limit=limit)
            if geo_results:
                results.extend(geo_results)

        # Step 5: Fallback to Nominatim search if still empty
        if not results:
            nom_results = await _search_nominatim(client, clean_query, near_lat, near_lon, limit=limit)
            if nom_results:
                results.extend(nom_results)

    # Step 6: Rank by relevance, exactness, and proximity
    results.sort(key=lambda item: _rank_result(item, clean_query, near_lat, near_lon), reverse=True)

    # Step 7: Deduplicate and trim to requested limit
    deduped = _deduplicate_results(results)[:limit]

    # Step 8: Cache successful results
    if deduped:
        _cache_set(cache_key, deduped)
        # Store in database cache asynchronously in background thread
        asyncio.create_task(asyncio.to_thread(_store_db_cache, deduped, clean_query))

    return deduped


async def _perform_reverse_geocode(lat: float, lon: float) -> Dict[str, Any]:
    """
    Reverse geocoding pipeline:
    1. Check in-memory & database cache
    2. Primary: OpenStreetMap Nominatim reverse for detailed address breakdown
    3. Fallback: Photon reverse
    4. Fallback: Geoapify reverse (if key configured)
    """
    cache_key = f"rev:{round(lat, 5)}:{round(lon, 5)}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    # Check Database cache within ~50 meters
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
        if match and match.road:
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
                "latitude": match.latitude,
                "longitude": match.longitude,
                "lat": match.latitude,
                "lon": match.longitude,
                "lng": match.longitude,
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
                "source": "cache",
            }
            _cache_set(cache_key, db_item)
            return db_item
    except Exception as err:
        logger.debug("Database reverse geocode check error: %s", err)
    finally:
        db.close()

    formatted: Dict[str, Any] = {}

    async with httpx.AsyncClient(headers=DEFAULT_HEADERS) as client:
        # Step 1: Primary - Nominatim Reverse for detailed address breakdown
        global _last_nominatim_request
        async with _nominatim_lock:
            elapsed = time.monotonic() - _last_nominatim_request
            if elapsed < 0.4:
                await asyncio.sleep(0.4 - elapsed)

            try:
                nom_resp = await client.get(
                    f"{NOMINATIM_BASE_URL}/reverse",
                    params={
                        "format": "jsonv2",
                        "lat": lat,
                        "lon": lon,
                        "zoom": 18,
                        "addressdetails": 1,
                        "accept-language": "en",
                    },
                    headers={"User-Agent": DEFAULT_USER_AGENT},
                    timeout=NOMINATIM_TIMEOUT,
                )
                _last_nominatim_request = time.monotonic()
                if nom_resp.status_code == 200:
                    parsed = _format_nominatim_item(nom_resp.json())
                    if parsed:
                        formatted = parsed
            except Exception as err:
                logger.warning("Nominatim reverse geocode failed: %s", err)
                _last_nominatim_request = time.monotonic()

        # Step 2: Fallback - Photon Reverse
        if not formatted:
            try:
                photon_resp = await client.get(
                    PHOTON_REVERSE_URL,
                    params={"lat": lat, "lon": lon},
                    headers=DEFAULT_HEADERS,
                    timeout=PHOTON_TIMEOUT,
                )
                if photon_resp.status_code == 200:
                    features = photon_resp.json().get("features", [])
                    if features:
                        parsed = _format_photon_feature(features[0])
                        if parsed:
                            formatted = parsed
            except Exception as err:
                logger.warning("Photon reverse geocode fallback failed: %s", err)

        # Step 3: Fallback - Geoapify Reverse (if API key present)
        if not formatted and settings.GEOAPIFY_API_KEY.strip():
            try:
                geo_resp = await client.get(
                    GEOAPIFY_REVERSE_URL,
                    params={
                        "lat": lat,
                        "lon": lon,
                        "apiKey": settings.GEOAPIFY_API_KEY.strip(),
                        "lang": "en",
                        "format": "json",
                    },
                    timeout=GEOAPIFY_TIMEOUT,
                )
                if geo_resp.status_code == 200:
                    features = geo_resp.json().get("features", [])
                    if features:
                        parsed = _format_geoapify_feature(features[0])
                        if parsed:
                            formatted = parsed
            except Exception as err:
                logger.warning("Geoapify reverse geocode fallback failed: %s", err)

    # Step 4: Graceful coordinate fallback if all external providers fail
    if not formatted:
        label = f"Location ({lat:.4f}, {lon:.4f})"
        formatted = {
            "name": label,
            "primaryText": label,
            "secondaryText": "",
            "displayName": label,
            "display_name": label,
            "latitude": lat,
            "longitude": lon,
            "lat": lat,
            "lon": lon,
            "lng": lon,
            "address": {
                "road": "",
                "suburb": "",
                "city": "",
                "state": "",
                "postcode": "",
                "country": "India",
            },
            "source": "fallback",
        }

    _cache_set(cache_key, formatted)
    return formatted


# =====================================================================
# REST API Endpoints
# =====================================================================

@router.get("/location/search")
@router.get("/location/autocomplete")
async def location_search_endpoint(
    q: str = Query(..., min_length=2, max_length=200, description="Location search query"),
    near_lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitude for location biasing"),
    near_lon: Optional[float] = Query(None, ge=-180, le=180, description="Longitude for location biasing"),
    context: Optional[str] = Query(None, max_length=200, description="Regional context, e.g. city or state"),
    limit: int = Query(8, ge=1, le=20, description="Maximum number of results to return"),
):
    """
    Unified Location Search & Autocomplete API:
    - Layered architecture: In-memory cache -> Database cache -> Photon -> Fallbacks
    - Returns structured results with name, latitude, longitude, and address components.
    """
    results = await _perform_location_search(
        query=q,
        near_lat=near_lat,
        near_lon=near_lon,
        context=context,
        limit=limit,
    )
    return {"results": results, "count": len(results)}


@router.get("/location/reverse")
async def location_reverse_endpoint(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Longitude"),
    lng: Optional[float] = Query(None, ge=-180, le=180, description="Longitude alias"),
):
    """
    Reverse geocoding to retrieve detailed structured local address.
    """
    actual_lon = lon if lon is not None else lng
    if actual_lon is None:
        raise ValueError("Missing longitude coordinate ('lon' or 'lng').")

    return await _perform_reverse_geocode(lat=lat, lon=actual_lon)


@router.get("/geocode")
async def geocode_legacy_endpoint(
    q: str = Query(..., min_length=2, max_length=200),
    near_lat: Optional[float] = Query(None, ge=-90, le=90),
    near_lon: Optional[float] = Query(None, ge=-180, le=180),
    context: Optional[str] = Query(None, max_length=200),
    limit: int = Query(8, ge=1, le=20),
    format: Optional[str] = Query("list", description="Return format: 'list' or 'object'"),
):
    """
    Backwards-compatible Geocode endpoint:
    - Returns a list by default for legacy clients and test suites.
    - If format='object', returns {"results": [...]}.
    """
    results = await _perform_location_search(
        query=q,
        near_lat=near_lat,
        near_lon=near_lon,
        context=context,
        limit=limit,
    )
    if format == "object":
        return {"results": results, "count": len(results)}
    return results


@router.get("/geocode/reverse")
async def geocode_reverse_legacy_endpoint(
    lat: float = Query(..., ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    lng: Optional[float] = Query(None, ge=-180, le=180),
):
    """
    Backwards-compatible Reverse Geocode endpoint.
    """
    actual_lon = lon if lon is not None else lng
    if actual_lon is None:
        raise ValueError("Missing longitude coordinate ('lon' or 'lng').")

    return await _perform_reverse_geocode(lat=lat, lon=actual_lon)