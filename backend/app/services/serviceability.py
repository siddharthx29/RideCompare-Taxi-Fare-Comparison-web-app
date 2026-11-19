import json
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

SERVICE_COVERAGE_PATH = Path(__file__).resolve().parents[1] / "config" / "service_coverage.json"


def _load_regions() -> Dict[str, Dict[str, Any]]:
    with SERVICE_COVERAGE_PATH.open("r", encoding="utf-8") as coverage_file:
        return json.load(coverage_file).get("regions", {})


SERVICE_REGIONS = _load_regions()


def _normalize(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _point_in_region(region: Dict[str, Any], latitude: float, longitude: float) -> bool:
    bounds = region["bounds"]
    return (
        bounds["south"] <= latitude <= bounds["north"]
        and bounds["west"] <= longitude <= bounds["east"]
    )


def _context_matches_region(
    region_name: str,
    region: Dict[str, Any],
    label: str,
    address: Optional[Dict[str, Any]],
) -> bool:
    address = address or {}
    address_text = _normalize(" ".join(str(value) for value in address.values() if value))
    if address.get("country_code") and _normalize(address["country_code"]) != _normalize(region["country_code"]):
        return False

    locality = _normalize(" ".join(str(address.get(key, "")) for key in (
        "city", "town", "municipality", "village", "suburb", "neighbourhood", "county"
    )))
    state = _normalize(" ".join(str(address.get(key, "")) for key in ("state", "state_district", "province")))
    aliases = [_normalize(region_name), *(_normalize(alias) for alias in region["city_aliases"])]
    state_aliases = [_normalize(alias) for alias in region["state_aliases"]]
    normalized_label = _normalize(label)
    locality_match = any(alias and re.search(rf"\b{re.escape(alias)}\b", locality) for alias in aliases)
    label_match = any(alias and re.search(rf"\b{re.escape(alias)}\b", normalized_label) for alias in aliases)
    state_match = not state or any(alias and re.search(rf"\b{re.escape(alias)}\b", state) for alias in state_aliases)
    return state_match and (locality_match or label_match)


def resolve_service_region(
    label: str,
    latitude: float,
    longitude: float,
    address: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Return a configured region only when geocoding context and bounded coordinates agree."""
    coordinate_matches = [
        region_name for region_name, region in SERVICE_REGIONS.items()
        if _point_in_region(region, latitude, longitude)
    ]
    for region_name, region in SERVICE_REGIONS.items():
        context_match = _context_matches_region(region_name, region, label, address)
        if context_match and _point_in_region(region, latitude, longitude):
            return region_name
    if not label.strip() and not address and len(coordinate_matches) == 1:
        return coordinate_matches[0]
    return None


def _quick_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2.0) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2.0) ** 2
    return 6371.0 * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def resolve_trip_serviceability(
    pickup_label: str,
    pickup_lat: float,
    pickup_lng: float,
    drop_label: str,
    drop_lat: float,
    drop_lng: float,
    pickup_address: Optional[Dict[str, Any]] = None,
    drop_address: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[str], Tuple[str, ...], Tuple[str, ...]]:
    pickup_region = resolve_service_region(pickup_label, pickup_lat, pickup_lng, pickup_address)
    drop_region = resolve_service_region(drop_label, drop_lat, drop_lng, drop_address)

    if not pickup_region:
        return None, (), ()

    region = SERVICE_REGIONS[pickup_region]

    # Standard intra-regional transit
    if pickup_region == drop_region:
        return pickup_region, tuple(region["providers"]), tuple(region["quote_names"])

    # Outstation and intercity transit check
    if region.get("intercity") and pickup_lat and pickup_lng and drop_lat and drop_lng:
        dist = _quick_haversine(pickup_lat, pickup_lng, drop_lat, drop_lng)
        if 15.0 <= dist <= 300.0:
            norm_drop = _normalize(drop_label)
            outstation_dests = region.get("outstation_destinations", [])
            dest_match = any(d and d in norm_drop for d in outstation_dests)

            drop_addr = drop_address or {}
            drop_state = _normalize(drop_addr.get("state", ""))
            state_aliases = region.get("state_aliases", [])
            state_match = bool(drop_state) and any(alias and alias in drop_state for alias in state_aliases)

            if dest_match or state_match:
                combined_providers = tuple(dict.fromkeys(list(region.get("providers", [])) + list(region.get("outstation_providers", []))))
                combined_quotes = tuple(dict.fromkeys(list(region.get("quote_names", [])) + list(region.get("outstation_quote_names", []))))
                return pickup_region, combined_providers, combined_quotes


    return None, (), ()