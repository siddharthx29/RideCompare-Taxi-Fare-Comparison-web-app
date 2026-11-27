import json
import logging
import math
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.models.db_models import CoverageRegion, ServiceStatus

logger = logging.getLogger(__name__)


def point_in_polygon(lat: float, lng: float, polygon_coords: List[List[float]]) -> bool:
    """
    Ray-casting algorithm to determine if (lat, lng) is within GeoJSON coordinates [[lng, lat], ...].
    GeoJSON coordinates format is [longitude, latitude].
    """
    if not polygon_coords or len(polygon_coords) < 3:
        return False

    inside = False
    n = len(polygon_coords)
    j = n - 1

    for i in range(n):
        xi, yi = polygon_coords[i][0], polygon_coords[i][1]  # xi=lng, yi=lat
        xj, yj = polygon_coords[j][0], polygon_coords[j][1]

        # Check ray crossing
        if ((yi > lat) != (yj > lat)):
            denom = yj - yi
            if abs(denom) > 1e-12:
                x_intersect = (xj - xi) * (lat - yi) / denom + xi
                if lng < x_intersect:
                    inside = not inside
        j = i

    return inside


def point_in_geojson_geometry(lat: float, lng: float, geometry: Dict[str, Any]) -> bool:
    """Supports Polygon and MultiPolygon GeoJSON structures."""
    geom_type = geometry.get("type", "")
    coords = geometry.get("coordinates", [])

    if geom_type == "Polygon":
        # First ring is exterior boundary
        if coords and len(coords) > 0:
            return point_in_polygon(lat, lng, coords[0])
    elif geom_type == "MultiPolygon":
        for poly in coords:
            if poly and len(poly) > 0:
                if point_in_polygon(lat, lng, poly[0]):
                    return True

    return False


def resolve_region(
    lat: float,
    lng: float,
    address: Optional[str] = None,
    db: Optional[Session] = None
) -> Optional[CoverageRegion]:
    """Resolves coordinates against coverage regions in the database."""
    if db is None:
        return None

    regions = db.query(CoverageRegion).all()
    for region in regions:
        try:
            geom = json.loads(region.geofence_geojson)
            if point_in_geojson_geometry(lat, lng, geom):
                return region
        except Exception as e:
            logger.warning("Error parsing geofence for %s: %s", region.region_id, e)

    # Secondary fallback: check configured service_coverage bounds & city aliases
    # Only matches regions that actually exist in CoverageRegion (with active cab/ride services)
    try:
        from backend.app.services.serviceability import SERVICE_REGIONS, _point_in_region, _normalize
    except Exception:
        SERVICE_REGIONS = {}
        _point_in_region = None
        _normalize = lambda v: str(v or "").lower().strip()

    norm_address = _normalize(address) if address else ""
    region_by_name = {r.name.lower(): r for r in regions}
    region_alias_map = {
        "bengaluru": "bangalore",
        "bangalore": "bengaluru",
    }

    if SERVICE_REGIONS and _point_in_region is not None:
        for cfg_name, cfg in SERVICE_REGIONS.items():
            if not cfg.get("providers"):
                continue
            if _point_in_region(cfg, lat, lng):
                db_region = region_by_name.get(cfg_name.lower()) or region_by_name.get(
                    region_alias_map.get(cfg_name.lower(), "")
                )
                if db_region is not None:
                    return db_region

    # Tertiary fallback for named addresses if slightly outside exact polygon boundary
    if norm_address:
        for region in regions:
            aliases = [region.name.lower()]
            cfg = SERVICE_REGIONS.get(region.name) or SERVICE_REGIONS.get(
                "Bangalore" if region.region_id == "bengaluru" else ""
            )
            if cfg:
                aliases.extend(_normalize(a) for a in cfg.get("city_aliases", []))
            if any(alias and alias in norm_address for alias in aliases):
                # Confirm coarse bounds
                try:
                    geom = json.loads(region.geofence_geojson)
                    coords = geom.get("coordinates", [[]])[0]
                    if coords:
                        lats = [c[1] for c in coords]
                        lngs = [c[0] for c in coords]
                        min_lat, max_lat = min(lats) - 0.25, max(lats) + 0.25
                        min_lng, max_lng = min(lngs) - 0.25, max(lngs) + 0.25
                        if min_lat <= lat <= max_lat and min_lng <= lng <= max_lng:
                            return region
                except Exception:
                    pass

    return None


class AvailabilityEvaluation:
    def __init__(
        self,
        case: str,
        region: Optional[CoverageRegion] = None,
        pickup_region_id: Optional[str] = None,
        drop_region_id: Optional[str] = None,
        active_services: Optional[List[str]] = None,
        suspended_services: Optional[List[Dict[str, str]]] = None,
        metered_auto_available: bool = False,
        metered_auto_fare: Optional[Dict[str, Any]] = None,
        reason_code: str = "AVAILABLE",
        message: Optional[str] = None,
        is_blocked: bool = False
    ):
        self.case = case
        self.region = region
        self.pickup_region_id = pickup_region_id
        self.drop_region_id = drop_region_id
        self.active_services = active_services or []
        self.suspended_services = suspended_services or []
        self.metered_auto_available = metered_auto_available
        self.metered_auto_fare = metered_auto_fare or {}
        self.reason_code = reason_code
        self.message = message
        self.is_blocked = is_blocked


def evaluate_trip_availability(
    pickup_lat: float,
    pickup_lng: float,
    drop_lat: float,
    drop_lng: float,
    pickup_address: Optional[str] = None,
    drop_address: Optional[str] = None,
    db: Optional[Session] = None
) -> AvailabilityEvaluation:
    """
    Evaluates the 4 strict availability cases:
      Case A: Pickup AND drop inside same geofence with >= 1 active app service.
      Case B: No active app service, but metered autos/taxis available (Normal Auto Card).
      Case C: No service of any kind or outside all geofences (Disable & block HTTP 422).
      Case D: Pickup and drop in different cities/regions (Intercity trip notice).
    """
    pickup_reg = resolve_region(pickup_lat, pickup_lng, pickup_address, db)
    drop_reg = resolve_region(drop_lat, drop_lng, drop_address, db)

    # Case C (Outside all geofences)
    if not pickup_reg or not drop_reg:
        return AvailabilityEvaluation(
            case="C",
            pickup_region_id=pickup_reg.region_id if pickup_reg else None,
            drop_region_id=drop_reg.region_id if drop_reg else None,
            reason_code="OUT_OF_COVERAGE",
            message="Ride services are not available in this area.",
            is_blocked=True
        )

    # Case D (Pickup and drop in different regions)
    if pickup_reg.region_id != drop_reg.region_id:
        return AvailabilityEvaluation(
            case="D",
            region=pickup_reg,
            pickup_region_id=pickup_reg.region_id,
            drop_region_id=drop_reg.region_id,
            reason_code="INTERCITY_TRIP",
            message=f"Pickup ({pickup_reg.name}) and drop ({drop_reg.name}) are in different regions. Standard city-ride fares do not apply for intercity/outstation trips.",
            is_blocked=False
        )

    # Both points inside same region
    statuses = db.query(ServiceStatus).filter(ServiceStatus.region_id == pickup_reg.region_id).all() if db else []
    active = [s.service_name for s in statuses if s.status == "active"]
    suspended = [{"service": s.service_name, "reason": s.status_reason or "Suspended by Regulator"} for s in statuses if s.status == "suspended"]

    metered_fare = {}
    if pickup_reg.metered_auto_fare:
        try:
            metered_fare = json.loads(pickup_reg.metered_auto_fare)
        except Exception:
            metered_fare = {}

    # Case A: At least one active app service operates in the region
    if len(active) > 0:
        return AvailabilityEvaluation(
            case="A",
            region=pickup_reg,
            pickup_region_id=pickup_reg.region_id,
            drop_region_id=drop_reg.region_id,
            active_services=active,
            suspended_services=suspended,
            metered_auto_available=pickup_reg.auto_rickshaw_metered_available,
            metered_auto_fare=metered_fare,
            reason_code="AVAILABLE",
            is_blocked=False
        )

    # Case B: No app service, but metered autos / taxis exist
    if pickup_reg.auto_rickshaw_metered_available and metered_fare:
        return AvailabilityEvaluation(
            case="B",
            region=pickup_reg,
            pickup_region_id=pickup_reg.region_id,
            drop_region_id=drop_reg.region_id,
            active_services=[],
            suspended_services=suspended,
            metered_auto_available=True,
            metered_auto_fare=metered_fare,
            reason_code="METERED_ONLY",
            message="No ride-hailing apps operate here. Typical metered auto fare estimate:",
            is_blocked=False
        )

    # Case C: No service of any kind available
    return AvailabilityEvaluation(
        case="C",
        region=pickup_reg,
        pickup_region_id=pickup_reg.region_id,
        drop_region_id=drop_reg.region_id,
        reason_code="NO_SERVICES_AVAILABLE",
        message="Ride services are not available in this area.",
        is_blocked=True
    )
