import asyncio
import logging
import math
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, Query

from backend.app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Geocoding"])

# Provider Endpoints
GEOAPIFY_AUTOCOMPLETE_URL = "https://api.geoapify.com/v1/geocode/autocomplete"
GEOAPIFY_REVERSE_URL = "https://api.geoapify.com/v1/geocode/reverse"

NOMINATIM_BASE_URL = os.getenv("GEOCODING_BASE_URL", "https://nominatim.openstreetmap.org").rstrip("/")
GEOCODING_USER_AGENT = os.getenv(
    "GEOCODING_USER_AGENT", "RideCompare/2.2 (https://ridecompare.world; contact: tech@ridecompare.world)"
)

# Caching Configuration
CACHE_TTL_SECONDS = 1800  # 30 minutes
_cache: Dict[str, Tuple[float, Any]] = {}
_cache_lock = asyncio.Lock()

# Nominatim Rate Limiting Guard (to respect OpenStreetMap ToS when falling back)
_nominatim_lock = asyncio.Lock()
_last_nominatim_request = 0.0

# Timeout configurations
GEOAPIFY_TIMEOUT = 3.5
NOMINATIM_TIMEOUT = 4.0


def _normalize(value: str) -> str:
    """Normalize string for robust fuzzy matching and cache key hashing."""
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


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
        # Evict expired entries
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
    Example: ('Lulu Mall', 'Edappally, Kochi', 'Lulu Mall, Edappally, Kochi')
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
            "lat": lat,
            "lon": lon,
            "lng": lon,
            "category": category,
            "importance": max(importance, popularity),
            "address": {
                "name": primary,
                "amenity": primary if category in {"amenity", "commercial", "tourism", "education", "transport"} else "",
                "road": street,
                "suburb": suburb,
                "neighbourhood": suburb,
                "city": city,
                "town": city,
                "state": state,
                "country": country,
                "country_code": country_code,
                "postcode": postcode,
            },
            "source": "geoapify",
        }
    except (ValueError, TypeError, KeyError) as err:
        logger.debug("Failed parsing Geoapify feature: %s", err)
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
        formatted = item.get("display_name") or ""
        category = item.get("type") or item.get("class") or ""

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
            "lat": lat,
            "lon": lon,
            "lng": lon,
            "category": category,
            "importance": importance,
            "address": {
                **addr,
                "name": primary,
                "road": street,
                "suburb": suburb,
                "city": city,
                "state": state,
                "country": country,
                "country_code": country_code,
                "postcode": postcode,
            },
            "source": "nominatim",
        }
    except (ValueError, TypeError, KeyError) as err:
        logger.debug("Failed parsing Nominatim item: %s", err)
        return None


def _rank_result(item: Dict[str, Any], query: str, near_lat: Optional[float], near_lon: Optional[float]) -> float:
    """
    Intelligent result relevance ranker prioritizing:
    1. Exact place name match
    2. Prefix match
    3. Proximity to user / nearby pin
    4. Important landmarks & transit categories
    5. Local / regional relevance
    """
    normalized_query = _normalize(query)
    name = _normalize(str(item.get("name") or ""))
    display_name = _normalize(str(item.get("displayName") or ""))
    secondary = _normalize(str(item.get("secondaryText") or ""))
    score = 0.0

    # 1. Exact match
    if name == normalized_query:
        score += 150.0
    elif name.startswith(normalized_query):
        score += 100.0
    elif normalized_query in name:
        score += 70.0
    elif normalized_query in display_name:
        score += 45.0
    elif normalized_query in secondary:
        score += 30.0

    # Word-level overlap
    query_terms = [t for t in normalized_query.split() if len(t) > 1]
    matching_terms = sum(1 for term in query_terms if term in name or term in display_name)
    score += matching_terms * 15.0

    # 2. Proximity boost when near coordinates are supplied
    if near_lat is not None and near_lon is not None:
        try:
            lat = float(item["lat"])
            lon = float(item["lon"])
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
                # Slight penalty for distant places
                score -= min(30.0, (dist_km - 150.0) * 0.1)
        except (ValueError, TypeError, KeyError):
            pass

    # 3. Kerala / Kochi regional priority boost (for terms like Kalamassery, Lulu, Rajagiri, etc.)
    kerala_keywords = ("kochi", "ernakulam", "kerala", "kalamassery", "edappally", "aluva", "kakkanad")
    if any(kw in display_name for kw in kerala_keywords):
        score += 20.0

    # 4. Importance and Popularity boost from geocoder metadata
    importance = float(item.get("importance", 0.4))
    score += min(30.0, importance * 30.0)

    # 5. POI and Transit category boost
    category = str(item.get("category") or "").lower()
    if any(hub in category or hub in name for hub in ("airport", "station", "metro", "terminal", "mall", "hospital", "university", "college")):
        score += 25.0

    return score


def _deduplicate_results(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove spatial and textual duplicates within ~150 meters."""
    deduped: List[Dict[str, Any]] = []
    seen_coords: List[Tuple[float, float, str]] = []

    for item in items:
        lat = float(item["lat"])
        lon = float(item["lon"])
        norm_name = _normalize(item["name"])

        is_duplicate = False
        for seen_lat, seen_lon, seen_name in seen_coords:
            if norm_name == seen_name:
                is_duplicate = True
                break
            if _haversine_distance_km(lat, lon, seen_lat, seen_lon) < 0.15:
                # If within 150 meters and names are very similar
                if norm_name in seen_name or seen_name in norm_name:
                    is_duplicate = True
                    break

        if not is_duplicate:
            deduped.append(item)
            seen_coords.append((lat, lon, norm_name))

    return deduped


async def _search_geoapify(
    client: httpx.AsyncClient,
    query: str,
    near_lat: Optional[float],
    near_lon: Optional[float],
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Execute Geoapify Autocomplete search with location biasing."""
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

    # Location Biasing:
    # If explicit coordinates are provided, bias by proximity.
    # Otherwise, default bias towards India (with Kochi priority).
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
                # Geoapify may return GeoJSON Feature or direct properties dict
                feature_dict = feat if "properties" in feat else {"properties": feat, "geometry": {"coordinates": [feat.get("lon"), feat.get("lat")]}}
                formatted = _format_geoapify_feature(feature_dict)
                if formatted:
                    formatted_list.append(formatted)
            return formatted_list
        else:
            logger.warning(
                "Geoapify returned status %d: %s",
                response.status_code,
                response.text[:200],
            )
            return []
    except Exception as err:
        logger.warning("Geoapify autocomplete request failed: %s", err)
        return []


async def _search_nominatim(
    client: httpx.AsyncClient,
    query: str,
    near_lat: Optional[float],
    near_lon: Optional[float],
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Execute OpenStreetMap Nominatim search as reliable, rate-compliant fallback."""
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
            # Soft bounding box viewbox around reference location
            params["viewbox"] = f"{near_lon - 0.4:.4f},{near_lat + 0.3:.4f},{near_lon + 0.4:.4f},{near_lat - 0.3:.4f}"

        try:
            response = await client.get(
                f"{NOMINATIM_BASE_URL}/search",
                params=params,
                headers={"User-Agent": GEOCODING_USER_AGENT},
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
            logger.warning("Nominatim fallback search request failed: %s", err)
            _last_nominatim_request = time.monotonic()
            return []


@router.get("/geocode")
async def geocode_query(
    q: str = Query(..., min_length=2, max_length=200),
    near_lat: Optional[float] = Query(None, ge=-90, le=90),
    near_lon: Optional[float] = Query(None, ge=-180, le=180),
    context: Optional[str] = Query(None, max_length=200),
    limit: int = Query(8, ge=1, le=20),
):
    """
    Production Place Search Endpoint:
    1. Checks in-memory TTL cache for instant sub-millisecond response.
    2. Uses Geoapify Autocomplete API as primary provider with location biasing.
    3. Seamlessly falls back to OpenStreetMap Nominatim on any provider error or absence of API key.
    4. Ranks, deduplicates, and formats clean concise results for both pickup & destination.
    """
    clean_query = " ".join(q.split())
    norm_query = _normalize(clean_query)
    norm_context = _normalize(context or "")
    rounded_lat = round(near_lat, 2) if near_lat is not None else None
    rounded_lon = round(near_lon, 2) if near_lon is not None else None

    cache_key = f"geo:{norm_query}:{norm_context}:{rounded_lat}:{rounded_lon}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    results: List[Dict[str, Any]] = []

    async with httpx.AsyncClient() as client:
        # Step 1: Try Geoapify Autocomplete if configured
        if settings.GEOAPIFY_API_KEY.strip():
            # Query with context if provided
            search_text = f"{clean_query}, {context}" if context else clean_query
            results = await _search_geoapify(client, search_text, near_lat, near_lon, limit=limit)
            if not results and context:
                results = await _search_geoapify(client, clean_query, near_lat, near_lon, limit=limit)

        # Step 2: Fallback to Nominatim if Geoapify returned empty or is unconfigured
        if not results:
            target_query = f"{clean_query}, {context}" if context else clean_query
            results = await _search_nominatim(client, target_query, near_lat, near_lon, limit=limit)
            if not results and context:
                results = await _search_nominatim(client, clean_query, near_lat, near_lon, limit=limit)

    # Step 3: Rank by relevance, exactness, and proximity
    results.sort(key=lambda item: _rank_result(item, clean_query, near_lat, near_lon), reverse=True)

    # Step 4: Deduplicate and trim to requested limit
    deduped = _deduplicate_results(results)[:limit]

    # Step 5: Cache successful results
    if deduped:
        _cache_set(cache_key, deduped)

    return deduped


@router.get("/geocode/reverse")
async def reverse_geocode(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
):
    """
    Reverse geocoding with Geoapify primary and OpenStreetMap Nominatim fallback.
    """
    cache_key = f"rev:{round(lat, 5)}:{round(lon, 5)}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    formatted: Dict[str, Any] = {}

    async with httpx.AsyncClient() as client:
        # Step 1: Try Geoapify Reverse
        if settings.GEOAPIFY_API_KEY.strip():
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
                    data = geo_resp.json()
                    features = data.get("features", []) or data.get("results", [])
                    if features:
                        feat = features[0]
                        feature_dict = feat if "properties" in feat else {"properties": feat, "geometry": {"coordinates": [lon, lat]}}
                        parsed = _format_geoapify_feature(feature_dict)
                        if parsed:
                            formatted = parsed
            except Exception as err:
                logger.warning("Geoapify reverse geocode failed: %s", err)

        # Step 2: Fallback to Nominatim Reverse
        if not formatted:
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
                        headers={"User-Agent": GEOCODING_USER_AGENT},
                        timeout=NOMINATIM_TIMEOUT,
                    )
                    _last_nominatim_request = time.monotonic()
                    if nom_resp.status_code == 200:
                        parsed = _format_nominatim_item(nom_resp.json())
                        if parsed:
                            formatted = parsed
                except Exception as err:
                    logger.warning("Nominatim reverse geocode fallback failed: %s", err)
                    _last_nominatim_request = time.monotonic()

    # Step 3: Graceful fallback if both APIs are unreachable
    if not formatted:
        label = f"Location ({lat:.4f}, {lon:.4f})"
        formatted = {
            "name": label,
            "primaryText": label,
            "secondaryText": "",
            "displayName": label,
            "display_name": label,
            "lat": lat,
            "lon": lon,
            "lng": lon,
            "address": {},
            "source": "fallback",
        }

    _cache_set(cache_key, formatted)
    return formatted