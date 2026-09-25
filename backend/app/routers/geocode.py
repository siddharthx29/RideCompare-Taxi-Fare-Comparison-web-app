import asyncio
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Geocoding"])

GEOCODING_BASE_URL = os.getenv("GEOCODING_BASE_URL", "https://nominatim.openstreetmap.org").rstrip("/")
GEOCODING_USER_AGENT = os.getenv(
    "GEOCODING_USER_AGENT", "RideCompare/2.1 (https://ridecompare.com; contact: support@ridecompare.com)"
)
CACHE_TTL_SECONDS = 900
_cache: Dict[str, Tuple[float, Any]] = {}
_request_lock = asyncio.Lock()
_last_provider_request = 0.0


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _cache_get(key: str) -> Optional[Any]:
    cached = _cache.get(key)
    if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]
    _cache.pop(key, None)
    return None


def _cache_set(key: str, value: Any) -> None:
    if len(_cache) > 1000:
        now = time.time()
        for old_key, (timestamp, _) in list(_cache.items()):
            if now - timestamp >= CACHE_TTL_SECONDS:
                _cache.pop(old_key, None)
    _cache[key] = (time.time(), value)


def _format_result(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **item,
        "displayName": item.get("display_name", ""),
        "lng": item.get("lon", "0"),
        "address": item.get("address", {}),
    }


def _rank_result(item: Dict[str, Any], query: str, near_lat: Optional[float], near_lon: Optional[float]) -> float:
    normalized_query = _normalize(query)
    name = _normalize(str(item.get("name") or ""))
    display_name = _normalize(str(item.get("display_name") or ""))
    address = item.get("address", {})
    address_text = _normalize(" ".join(str(value) for value in address.values()))
    score = 0.0
    if name == normalized_query:
        score += 100
    elif normalized_query and normalized_query in name:
        score += 70
    elif normalized_query and normalized_query in display_name:
        score += 55
    elif normalized_query and normalized_query in address_text:
        score += 35

    query_terms = [term for term in normalized_query.split() if len(term) > 1]
    score += 5 * sum(term in display_name for term in query_terms)
    if near_lat is not None and near_lon is not None:
        try:
            lat, lon = float(item["lat"]), float(item["lon"])
            score -= min(20.0, ((lat - near_lat) ** 2 + (lon - near_lon) ** 2) ** 0.5 * 15)
        except (KeyError, TypeError, ValueError):
            pass
    return score


def _viewbox(latitude: float, longitude: float) -> str:
    return f"{longitude - 0.35},{latitude + 0.25},{longitude + 0.35},{latitude - 0.25}"


async def _provider_get(client: httpx.AsyncClient, endpoint: str, params: Dict[str, Any]) -> httpx.Response:
    global _last_provider_request
    async with _request_lock:
        elapsed = time.monotonic() - _last_provider_request
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
        response = await client.get(f"{GEOCODING_BASE_URL}{endpoint}", params=params)
        _last_provider_request = time.monotonic()
        return response


async def _search_nominatim(
    client: httpx.AsyncClient,
    query: str,
    near_lat: Optional[float],
    near_lon: Optional[float],
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "format": "jsonv2",
        "q": query,
        "addressdetails": 1,
        "limit": 5,
        "accept-language": "en",
        "layer": "address,poi",
    }
    if near_lat is not None and near_lon is not None:
        params["viewbox"] = _viewbox(near_lat, near_lon)
    response = await _provider_get(client, "/search", params)
    response.raise_for_status()
    results = response.json()
    return results if isinstance(results, list) else []


@router.get("/geocode")
async def geocode_query(
    q: str = Query(..., min_length=3, max_length=200),
    near_lat: Optional[float] = Query(None, ge=-90, le=90),
    near_lon: Optional[float] = Query(None, ge=-180, le=180),
    context: Optional[str] = Query(None, max_length=200),
):
    query = " ".join(q.split())
    normalized_context = _normalize(context or "")
    key = f"search:{_normalize(query)}:{normalized_context}:{round(near_lat or 0, 2)}:{round(near_lon or 0, 2)}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    target_query = ", ".join(part for part in (query, context) if part)
    try:
        async with httpx.AsyncClient(timeout=5.0, headers={"User-Agent": GEOCODING_USER_AGENT}) as client:
            results = await _search_nominatim(client, target_query, near_lat, near_lon)
            if not results and target_query != query:
                results = await _search_nominatim(client, query, near_lat, near_lon)
    except (httpx.HTTPError, ValueError) as error:
        logger.warning("Geocoding provider request failed: %s", error)
        results = []

    results.sort(key=lambda item: _rank_result(item, query, near_lat, near_lon), reverse=True)
    formatted = [_format_result(item) for item in results[:5]]
    _cache_set(key, formatted)
    return formatted


@router.get("/geocode/reverse")
async def reverse_geocode(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
):
    key = f"reverse:{round(lat, 5)}:{round(lon, 5)}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        async with httpx.AsyncClient(timeout=5.0, headers={"User-Agent": GEOCODING_USER_AGENT}) as client:
            response = await _provider_get(
                client,
                "/reverse",
                {"format": "jsonv2", "lat": lat, "lon": lon, "zoom": 18, "addressdetails": 1, "accept-language": "en"},
            )
            response.raise_for_status()
            result = response.json()
            formatted = _format_result(result) if isinstance(result, dict) else {}
    except (httpx.HTTPError, ValueError) as error:
        logger.warning("Reverse geocoding request failed: %s", error)
        formatted = {}
    _cache_set(key, formatted)
    return formatted