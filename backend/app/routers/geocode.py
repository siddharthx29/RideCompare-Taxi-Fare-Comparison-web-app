import time
import urllib.parse
from typing import Dict, Any, List
from fastapi import APIRouter, Query, HTTPException
import httpx

router = APIRouter(tags=["Geocoding"])

_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 600

FALLBACK_LANDMARKS = [
    {"display_name": "Connaught Place, New Delhi, Delhi, India", "lat": "28.6328", "lon": "77.2197", "displayName": "Connaught Place, New Delhi, Delhi, India", "lng": "77.2197"},
    {"display_name": "Indira Gandhi International Airport, New Delhi, Delhi, India", "lat": "28.5562", "lon": "77.1000", "displayName": "Indira Gandhi International Airport, New Delhi, Delhi, India", "lng": "77.1000"},
    {"display_name": "Sector 18, Noida, Uttar Pradesh, India", "lat": "28.5355", "lon": "77.3910", "displayName": "Sector 18, Noida, Uttar Pradesh, India", "lng": "77.3910"},
    {"display_name": "Cyber Hub, DLF Phase 2, Gurugram, Haryana, India", "lat": "28.4952", "lon": "77.0894", "displayName": "Cyber Hub, DLF Phase 2, Gurugram, Haryana, India", "lng": "77.0894"},
    {"display_name": "Indiranagar, Bengaluru, Karnataka, India", "lat": "12.971891", "lon": "77.641151", "displayName": "Indiranagar, Bengaluru, Karnataka, India", "lng": "77.641151"},
    {"display_name": "Koramangala, Bengaluru, Karnataka, India", "lat": "12.935192", "lon": "77.624480", "displayName": "Koramangala, Bengaluru, Karnataka, India", "lng": "77.624480"},
    {"display_name": "Kempegowda International Airport, Bengaluru, Karnataka, India", "lat": "13.1986", "lon": "77.7066", "displayName": "Kempegowda International Airport, Bengaluru, Karnataka, India", "lng": "77.7066"},
    {"display_name": "Bandra Kurla Complex, Mumbai, Maharashtra, India", "lat": "19.0688", "lon": "72.8704", "displayName": "Bandra Kurla Complex, Mumbai, Maharashtra, India", "lng": "72.8704"},
    {"display_name": "Marine Drive, Mumbai, Maharashtra, India", "lat": "18.9432", "lon": "72.8230", "displayName": "Marine Drive, Mumbai, Maharashtra, India", "lng": "72.8230"},
    {"display_name": "Marina Beach, Chennai, Tamil Nadu, India", "lat": "13.0500", "lon": "80.2824", "displayName": "Marina Beach, Chennai, Tamil Nadu, India", "lng": "80.2824"},
    {"display_name": "Hitech City, Hyderabad, Telangana, India", "lat": "17.4435", "lon": "78.3772", "displayName": "Hitech City, Hyderabad, Telangana, India", "lng": "78.3772"}
]


@router.get("/geocode")
async def geocode_query(q: str = Query(..., min_length=1)):
    normalized_q = q.strip().lower()
    now = time.time()

    if normalized_q in _cache:
        cached = _cache[normalized_q]
        if now - cached["timestamp"] < CACHE_TTL:
            return cached["data"]

    url = f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(q)}&addressdetails=1&limit=5&accept-language=en"

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            headers = {"User-Agent": "RideCompare-App/2.0.0 (contact@ridecompare.com)"}
            res = await client.get(url, headers=headers)

            if res.status_code == 200:
                raw_data = res.json()
                if raw_data:
                    formatted = [
                        {
                            **item,
                            "displayName": item.get("display_name", ""),
                            "lng": item.get("lon", "0.0")
                        }
                        for item in raw_data
                    ]
                    _cache[normalized_q] = {"data": formatted, "timestamp": now}
                    return formatted
    except Exception:
        pass

    matches = [
        item for item in FALLBACK_LANDMARKS
        if any(term in item["displayName"].lower() for term in normalized_q.split())
    ]
    if not matches:
        matches = FALLBACK_LANDMARKS[:3]

    _cache[normalized_q] = {"data": matches, "timestamp": now}
    return matches
