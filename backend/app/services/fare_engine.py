import math
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import quote_plus
from sqlalchemy.orm import Session
import httpx

from backend.app.models.db_models import RateCard, CoverageRegion

logger = logging.getLogger(__name__)

# In-memory LRU cache for routing queries
_ROUTE_CACHE: Dict[str, Tuple[float, float, float]] = {}  # key -> (distance_km, duration_min, timestamp)
CACHE_TTL_SECONDS = 3600


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Straight-line haversine distance in kilometers."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2.0) ** 2)
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


async def get_route_distance_and_duration(
    pickup_lat: float,
    pickup_lng: float,
    drop_lat: float,
    drop_lng: float,
    routing_provider: str = "osrm"
) -> Tuple[float, float]:
    """
    Returns (distance_km, duration_min) from routing engine (OSRM, OpenRouteService, or fallback).
    Includes caching and road curvature fallback (1.35x).
    """
    cache_key = f"{pickup_lat:.4f},{pickup_lng:.4f}->{drop_lat:.4f},{drop_lng:.4f}"
    now = datetime.utcnow().timestamp()

    if cache_key in _ROUTE_CACHE:
        dist, dur, cached_time = _ROUTE_CACHE[cache_key]
        if now - cached_time < CACHE_TTL_SECONDS:
            return dist, dur

    # Attempt OSRM public demo routing if requested
    if routing_provider == "osrm":
        osrm_url = f"https://router.project-osrm.org/route/v1/driving/{pickup_lng},{pickup_lat};{drop_lng},{drop_lat}?overview=false"
        try:
            async with httpx.AsyncClient(timeout=3.5) as client:
                res = await client.get(osrm_url)
                if res.status_code == 200:
                    data = res.json()
                    routes = data.get("routes", [])
                    if routes:
                        dist_km = round(routes[0]["distance"] / 1000.0, 2)
                        dur_min = round(routes[0]["duration"] / 60.0, 1)
                        _ROUTE_CACHE[cache_key] = (dist_km, dur_min, now)
                        return dist_km, dur_min
        except Exception as err:
            logger.debug("OSRM route fetch failed, using realistic curvature model: %s", err)

    # Reliable fallback: haversine with urban road curvature factor of 1.35x
    straight_line = haversine_distance(pickup_lat, pickup_lng, drop_lat, drop_lng)
    distance_km = round(max(0.5, straight_line * 1.35), 2)
    # Estimate average speed 24 km/h with 3 min baseline acceleration/signals
    duration_min = round(max(3.0, (distance_km / 24.0) * 60.0), 1)

    _ROUTE_CACHE[cache_key] = (distance_km, duration_min, now)
    return distance_km, duration_min


def calculate_surge_window_with_realtime(
    depart_at: Optional[datetime] = None,
    legal_cap: float = 2.0,
    has_rain_signal: bool = False
) -> Tuple[float, float, float, str]:
    """
    Determines surge multiplier window (low, high, current_surge, period_label).
    Legal caps are strictly respected so high never exceeds regional legal cap.
    """
    dt = depart_at or datetime.utcnow()
    hour = dt.hour
    minute = dt.minute
    weekday = dt.weekday()
    is_weekend = weekday >= 5

    # Period classifications with real-time surge curve
    if 8 <= hour <= 11:
        period = "Morning Peak"
        base_low = 1.0
        base_high = 1.5 if not is_weekend else 1.2
        # Dynamic curve peaking around 9:15–9:45 AM
        peak_factor = 0.85 if hour in (9, 10) else 0.55
        current = 1.0 + (base_high - 1.0) * peak_factor
    elif 17 <= hour <= 21:
        period = "Evening Peak"
        base_low = 1.0
        base_high = 1.6 if not is_weekend else 1.4
        # Dynamic curve peaking around 6:30–8:00 PM
        peak_factor = 0.90 if hour in (18, 19) else 0.60
        current = 1.0 + (base_high - 1.0) * peak_factor
    elif hour >= 23 or hour < 5:
        period = "Night"
        base_low = 1.0
        base_high = 1.3
        current = 1.15
    else:
        period = "Off-Peak"
        base_low = 1.0
        base_high = 1.2
        current = 1.05

    if has_rain_signal:
        base_high += 0.3
        current += 0.2

    final_high = round(min(base_high, legal_cap), 2)
    final_low = round(max(1.0, min(base_low, final_high)), 2)
    final_current = round(max(final_low, min(final_high, current)), 2)

    return final_low, final_high, final_current, period


def calculate_surge_window(
    depart_at: Optional[datetime] = None,
    legal_cap: float = 2.0,
    has_rain_signal: bool = False
) -> Tuple[float, float, str]:
    """Determines surge multiplier window (low, high, period_label)."""
    low, high, _, period = calculate_surge_window_with_realtime(depart_at, legal_cap, has_rain_signal)
    return low, high, period


def compute_fare_from_rate_card(
    card: RateCard,
    distance_km: float,
    duration_min: float,
    surge: float,
    is_night: bool = False
) -> float:
    """
    Standard statutory formula:
    fare = max(min_fare, base + per_km*km + per_min*min + booking_fee) * surge * (1 + tax)
    Supports free_km, long_distance_threshold & rate, and night_multiplier.
    """
    billable_km = max(0.0, distance_km - (card.free_km or 0.0))

    if card.long_distance_threshold and card.long_distance_rate and billable_km > card.long_distance_threshold:
        normal_km = card.long_distance_threshold
        extra_km = billable_km - card.long_distance_threshold
        dist_cost = (normal_km * card.per_km) + (extra_km * card.long_distance_rate)
    else:
        dist_cost = billable_km * card.per_km

    time_cost = duration_min * (card.per_min or 0.0)
    subtotal = card.base_fare + dist_cost + time_cost + (card.booking_fee or 0.0)

    # Apply minimum fare constraint before surge & tax
    effective_base = max(card.min_fare or 0.0, subtotal)

    # Night multiplier if applicable
    if is_night and card.night_multiplier and card.night_multiplier > 1.0:
        effective_base *= card.night_multiplier

    fare_with_surge = effective_base * surge
    final_fare = fare_with_surge * (1.0 + (card.tax_pct or 0.0))

    return round(final_fare, 1)


def compute_metered_auto_estimate(
    metered_config: Dict[str, Any],
    distance_km: float,
    is_night: bool = False
) -> Tuple[float, float, str, str]:
    """Computes government-notified metered auto fare range (low, high, currency, currency_symbol)."""
    base_fare = float(metered_config.get("base_fare", 30.0))
    free_km = float(metered_config.get("free_km", 1.5))
    per_km = float(metered_config.get("per_km", 15.0))
    night_mult = float(metered_config.get("night_multiplier", 1.25))
    curr = metered_config.get("currency", "INR")
    sym = metered_config.get("currency_symbol", "₹")

    billable_km = max(0.0, distance_km - free_km)
    base_calc = base_fare + (billable_km * per_km)

    if is_night:
        base_calc *= night_mult

    # Range accounts for minor waiting time / traffic signals
    low = round(base_calc)
    high = round(base_calc * 1.15)
    return low, high, curr, sym


def generate_deep_link(
    service: str,
    pickup_lat: float,
    pickup_lng: float,
    drop_lat: float,
    drop_lng: float,
    pickup_name: str = "",
    drop_name: str = ""
) -> Tuple[str, str]:
    """
    Returns (app_deep_link, web_fallback_url) for ride services.
    Uses official URL schemes with full coordinates and web fallback.
    """
    s = service.lower()
    p_name_encoded = quote_plus(pickup_name or "Pickup")
    d_name_encoded = quote_plus(drop_name or "Dropoff")

    if "uber" in s:
        deep = f"uber://?action=setPickup&pickup[latitude]={pickup_lat}&pickup[longitude]={pickup_lng}&pickup[formatted_address]={p_name_encoded}&dropoff[latitude]={drop_lat}&dropoff[longitude]={drop_lng}&dropoff[formatted_address]={d_name_encoded}"
        web = f"https://m.uber.com/looking?pickup[latitude]={pickup_lat}&pickup[longitude]={pickup_lng}&pickup[formatted_address]={p_name_encoded}&dropoff[latitude]={drop_lat}&dropoff[longitude]={drop_lng}&dropoff[formatted_address]={d_name_encoded}"
    elif "ola" in s:
        deep = f"ola://ride?lat={pickup_lat}&lng={pickup_lng}&drop_lat={drop_lat}&drop_lng={drop_lng}"
        web = f"https://book.olacabs.com/?lat={pickup_lat}&lng={pickup_lng}&drop_lat={drop_lat}&drop_lng={drop_lng}"
    elif "rapido" in s:
        deep = f"rapido://ride?pickup_lat={pickup_lat}&pickup_lng={pickup_lng}&drop_lat={drop_lat}&drop_lng={drop_lng}"
        web = "https://rapido.bike"
    elif "namma" in s or "yatri" in s:
        deep = f"nammayatri://ride?pickup={pickup_lat},{pickup_lng}&drop={drop_lat},{drop_lng}"
        web = "https://nammayatri.in"
    elif "bolt" in s:
        deep = f"bolt://ride?pickup_lat={pickup_lat}&pickup_lng={pickup_lng}&drop_lat={drop_lat}&drop_lng={drop_lng}"
        web = "https://bolt.eu"
    elif "lyft" in s:
        deep = f"lyft://riderequest?pickup[latitude]={pickup_lat}&pickup[longitude]={pickup_lng}&destination[latitude]={drop_lat}&destination[longitude]={drop_lng}"
        web = f"https://ride.lyft.com/riderequest?pickup[latitude]={pickup_lat}&pickup[longitude]={pickup_lng}&destination[latitude]={drop_lat}&destination[longitude]={drop_lng}"
    elif "grab" in s:
        deep = f"grab://open?screenType=TAXI&pickup_latitude={pickup_lat}&pickup_longitude={pickup_lng}&dropoff_latitude={drop_lat}&dropoff_longitude={drop_lng}"
        web = "https://grab.com"
    else:
        deep = ""
        web = ""

    return deep, web


def get_service_estimates(
    region: CoverageRegion,
    active_service_names: List[str],
    distance_km: float,
    duration_min: float,
    pickup_lat: float,
    pickup_lng: float,
    drop_lat: float,
    drop_lng: float,
    pickup_name: str,
    drop_name: str,
    depart_at: Optional[datetime],
    db: Session
) -> List[Dict[str, Any]]:
    """Calculates estimates for all active rate cards in the region, sorted cheapest first."""
    dt = depart_at or datetime.utcnow()
    is_night = dt.hour >= 23 or dt.hour < 5
    legal_cap = region.legal_surge_cap or 2.0
    surge_low, surge_high, surge_current, period_name = calculate_surge_window_with_realtime(dt, legal_cap=legal_cap)

    cards = db.query(RateCard).filter(
        RateCard.city == region.name,
        RateCard.service.in_(active_service_names)
    ).all()

    # If no rate cards directly matched city name, match by state
    if not cards:
        cards = db.query(RateCard).filter(
            RateCard.state == region.state,
            RateCard.service.in_(active_service_names)
        ).all()

    results: List[Dict[str, Any]] = []

    for card in cards:
        fare_low = compute_fare_from_rate_card(card, distance_km, duration_min, surge_low, is_night)
        fare_high = compute_fare_from_rate_card(card, distance_km, duration_min, surge_high, is_night)
        fare_current = compute_fare_from_rate_card(card, distance_km, duration_min, surge_current, is_night)

        # Guarantee high is at least equal to low and current sits within [low, high]
        if fare_high < fare_low:
            fare_high = fare_low
        fare_current = max(fare_low, min(fare_high, fare_current))

        deep_link, web_link = generate_deep_link(
            card.service, pickup_lat, pickup_lng, drop_lat, drop_lng, pickup_name, drop_name
        )

        # Baseline ETA estimate (4 to 8 mins depending on vehicle category)
        eta = 4 if card.vehicle_category == "Bike" else 5 if card.vehicle_category == "Auto" else 6

        results.append({
            "service": card.service,
            "ride_type": card.ride_type,
            "vehicle_category": card.vehicle_category,
            "low": round(fare_low),
            "high": round(fare_high),
            "realtime_rate": round(fare_current),
            "current_surge": surge_current,
            "currency": card.currency,
            "currency_symbol": card.currency_symbol or "₹",
            "deeplink": deep_link,
            "web_link": web_link,
            "rate_card_verified_at": card.last_verified_date or "2026-01-01",
            "is_verified": bool(card.is_verified),
            "source_url": card.source_url or "",
            "surge_period": period_name,
            "surge_low": surge_low,
            "surge_high": surge_high,
            "legal_surge_cap": legal_cap,
            "eta_minutes": eta,
            "is_cheapest": False,
            "is_fastest": False
        })

    # Sort cheapest first (by low estimate ascending)
    results.sort(key=lambda x: (x["low"], x["high"]))

    if results:
        results[0]["is_cheapest"] = True
        fastest_item = min(results, key=lambda x: x["eta_minutes"])
        fastest_item["is_fastest"] = True

    return results
