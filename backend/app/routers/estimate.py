import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Union, Tuple
from fastapi import APIRouter, Depends, Query, HTTPException, Header, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.db_models import CoverageRegion, ServiceStatus, RateCard
from backend.app.services.geo_fence import evaluate_trip_availability, resolve_region
from backend.app.services.fare_engine import (
    get_route_distance_and_duration,
    get_service_estimates,
    compute_metered_auto_estimate,
    haversine_distance
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Fare Estimation & Availability"])


class LocationPoint(BaseModel):
    lat: float
    lng: float
    address: Optional[str] = None
    name: Optional[str] = None


class EstimateRequest(BaseModel):
    # Support both object `{lat, lng, address}` and array `[lat, lng]`
    pickup: Union[LocationPoint, List[float], Dict[str, Any]]
    drop: Union[LocationPoint, List[float], Dict[str, Any]]
    depart_at: Optional[Union[datetime, str]] = None


def _parse_coordinate(point: Union[LocationPoint, List[float], Dict[str, Any]]) -> Tuple[float, float, str]:
    """Helper to extract (lat, lng, address/name) across multiple input schemas."""
    if isinstance(point, LocationPoint):
        return point.lat, point.lng, point.address or point.name or ""
    elif isinstance(point, (list, tuple)) and len(point) >= 2:
        return float(point[0]), float(point[1]), ""
    elif isinstance(point, dict):
        lat = float(point.get("lat") or point.get("latitude") or 0.0)
        lng = float(point.get("lng") or point.get("longitude") or point.get("lon") or 0.0)
        name = point.get("address") or point.get("name") or point.get("label") or ""
        return lat, lng, name
    raise ValueError("Invalid coordinate format")


def verify_admin(
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    key: Optional[str] = Query(None)
):
    if settings.ENVIRONMENT.lower() in {"production", "prod"} and settings.ADMIN_KEY:
        token = x_admin_key or key
        if not token or token != settings.ADMIN_KEY:
            raise HTTPException(status_code=403, detail="Unauthorized: Invalid admin key")
    return True


@router.post("/estimate")
async def estimate_fares(payload: EstimateRequest, db: Session = Depends(get_db)):
    """
    Primary fare engine endpoint:
    1. Availability Gating: Evaluates point-in-polygon geofences for pickup and drop.
    2. Case Gating:
       - Case A: Compares active app services, sorted cheapest first.
       - Case B: No app services, but metered autos/taxis available -> Fallback estimate.
       - Case C: Outside geofences or no services -> HTTP 422 with OUT_OF_COVERAGE.
       - Case D: Intercity trip -> Notice returned.
    """
    try:
        p_lat, p_lng, p_name = _parse_coordinate(payload.pickup)
        d_lat, d_lng, d_name = _parse_coordinate(payload.drop)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed coordinates in request: {str(exc)}"
        )

    # Validate coordinate boundaries
    if not (-90 <= p_lat <= 90 and -180 <= p_lng <= 180 and -90 <= d_lat <= 90 and -180 <= d_lng <= 180):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Latitude or longitude out of bounds")

    depart_dt: Optional[datetime] = None
    if payload.depart_at:
        if isinstance(payload.depart_at, datetime):
            depart_dt = payload.depart_at
        elif isinstance(payload.depart_at, str):
            try:
                depart_dt = datetime.fromisoformat(payload.depart_at.replace("Z", "+00:00"))
            except Exception:
                depart_dt = datetime.utcnow()

    # Step 1: Availability Evaluation (Cases A, B, C, D)
    avail = evaluate_trip_availability(
        pickup_lat=p_lat,
        pickup_lng=p_lng,
        drop_lat=d_lat,
        drop_lng=d_lng,
        pickup_address=p_name,
        drop_address=d_name,
        db=db
    )

    # Case C Gating: Block API immediately with HTTP 422
    if avail.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": avail.message or "Ride services are not available in this area.",
                "reason_code": avail.reason_code,
                "pickup_region": avail.pickup_region_id,
                "drop_region": avail.drop_region_id
            }
        )

    # Step 2: Calculate Route Distance & Duration
    distance_km, duration_min = await get_route_distance_and_duration(p_lat, p_lng, d_lat, d_lng)

    # Case D: Intercity Notice
    if avail.case == "D":
        return {
            "region": "intercity",
            "region_name": f"{avail.region.name if avail.region else 'Origin'} to Destination",
            "distance_km": distance_km,
            "duration_min": duration_min,
            "available_services": [],
            "fallback": {"type": "none"},
            "reason_code": "INTERCITY_TRIP",
            "notice": avail.message,
            "disclaimer": "Actual fare is shown in the app and may differ due to live demand, traffic, tolls and taxes."
        }

    # Case B: No ride-hailing apps operate here, typical metered auto fare estimate
    if avail.case == "B":
        dt = depart_dt or datetime.utcnow()
        is_night = dt.hour >= 23 or dt.hour < 5
        auto_low, auto_high, curr, sym = compute_metered_auto_estimate(
            avail.metered_auto_fare, distance_km, is_night=is_night
        )
        return {
            "region": avail.region.region_id if avail.region else "",
            "region_name": avail.region.name if avail.region else "",
            "distance_km": distance_km,
            "duration_min": duration_min,
            "available_services": [],
            "fallback": {
                "type": "auto",
                "message": "No ride-hailing apps operate here. Typical metered auto fare estimate:",
                "estimate": {
                    "service": "Normal Auto / Local Taxi",
                    "ride_type": "Government Metered Auto",
                    "vehicle_category": "Auto",
                    "low": auto_low,
                    "high": auto_high,
                    "currency": curr,
                    "currency_symbol": sym,
                    "is_verified": True,
                    "rate_card_verified_at": avail.region.last_updated.strftime("%Y-%m-%d") if avail.region and avail.region.last_updated else "2026-01-01"
                }
            },
            "reason_code": "METERED_ONLY",
            "notice": "No ride-hailing apps operate here. Typical metered auto fare estimate:",
            "disclaimer": "Actual fare is shown in the app and may differ due to live demand, traffic, tolls and taxes."
        }

    # Case A: Normal Comparison with active apps, sorted cheapest first
    services = get_service_estimates(
        region=avail.region,
        active_service_names=avail.active_services,
        distance_km=distance_km,
        duration_min=duration_min,
        pickup_lat=p_lat,
        pickup_lng=p_lng,
        drop_lat=d_lat,
        drop_lng=d_lng,
        pickup_name=p_name,
        drop_name=d_name,
        depart_at=depart_dt,
        db=db
    )

    return {
        "region": avail.region.region_id if avail.region else "",
        "region_name": avail.region.name if avail.region else "",
        "state": avail.region.state if avail.region else "",
        "country": avail.region.country if avail.region else "",
        "legal_surge_cap": avail.region.legal_surge_cap if avail.region else 2.0,
        "distance_km": distance_km,
        "duration_min": duration_min,
        "available_services": services,
        "fallback": {"type": "none"},
        "suspended_services": avail.suspended_services,
        "reason_code": "AVAILABLE",
        "disclaimer": "Actual fare is shown in the app and may differ due to live demand, traffic, tolls and taxes."
    }


@router.get("/coverage")
async def get_coverage(
    lat: float = Query(...),
    lng: float = Query(...),
    address: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Returns the services active at the given GPS or geocoded coordinate."""
    region = resolve_region(lat, lng, address=address, db=db)
    if not region:
        return {
            "covered": False,
            "message": "Ride services are not available in this area."
        }

    statuses = db.query(ServiceStatus).filter(ServiceStatus.region_id == region.region_id).all()
    active = [s.service_name for s in statuses if s.status == "active"]
    suspended = [{"service": s.service_name, "reason": s.status_reason} for s in statuses if s.status == "suspended"]

    return {
        "covered": True,
        "region_id": region.region_id,
        "name": region.name,
        "state": region.state,
        "country": region.country,
        "legal_surge_cap": region.legal_surge_cap,
        "auto_rickshaw_metered_available": region.auto_rickshaw_metered_available,
        "active_services": active,
        "suspended_services": suspended,
        "last_updated": region.last_updated.isoformat() if region.last_updated else None
    }


# ------------------------------------------------------------------------------
# Admin Endpoints: Rate Cards & Service Status Management
# ------------------------------------------------------------------------------

class RateCardUpdatePayload(BaseModel):
    base_fare: Optional[float] = None
    per_km: Optional[float] = None
    per_min: Optional[float] = None
    booking_fee: Optional[float] = None
    min_fare: Optional[float] = None
    free_km: Optional[float] = None
    long_distance_threshold: Optional[float] = None
    long_distance_rate: Optional[float] = None
    night_multiplier: Optional[float] = None
    tax_pct: Optional[float] = None
    source_url: Optional[str] = None
    last_verified_date: Optional[str] = None
    is_verified: Optional[bool] = None


class ServiceStatusUpdatePayload(BaseModel):
    region_id: str
    service_name: str
    status: str  # "active", "suspended", "unavailable"
    status_reason: Optional[str] = None


@router.get("/admin/rate-cards", dependencies=[Depends(verify_admin)])
async def list_rate_cards(city: Optional[str] = None, service: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(RateCard)
    if city:
        query = query.filter(RateCard.city.ilike(f"%{city}%"))
    if service:
        query = query.filter(RateCard.service.ilike(f"%{service}%"))
    cards = query.all()
    return {"count": len(cards), "rate_cards": cards}


@router.put("/admin/rate-cards/{card_id}", dependencies=[Depends(verify_admin)])
async def update_rate_card(card_id: int, payload: RateCardUpdatePayload, db: Session = Depends(get_db)):
    card = db.query(RateCard).filter(RateCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Rate card not found")

    update_dict = payload.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(card, field, val)

    card.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(card)
    return {"success": True, "rate_card": card}


@router.get("/admin/regions", dependencies=[Depends(verify_admin)])
async def list_regions(db: Session = Depends(get_db)):
    regions = db.query(CoverageRegion).all()
    return {"count": len(regions), "regions": regions}


@router.get("/admin/service-statuses", dependencies=[Depends(verify_admin)])
async def list_service_statuses(region_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(ServiceStatus)
    if region_id:
        query = query.filter(ServiceStatus.region_id == region_id)
    statuses = query.all()
    return {"count": len(statuses), "service_statuses": statuses}


@router.post("/admin/rate-cards", dependencies=[Depends(verify_admin)])
async def create_rate_card(payload: dict, db: Session = Depends(get_db)):
    card = RateCard(**payload)
    card.updated_at = datetime.utcnow()
    db.add(card)
    db.commit()
    db.refresh(card)
    return {"success": True, "rate_card": card}


@router.post("/admin/rate-cards/import-json", dependencies=[Depends(verify_admin)])
async def import_rate_cards_json(payload: List[dict], db: Session = Depends(get_db)):
    created = 0
    updated = 0
    for item in payload:
        existing = db.query(RateCard).filter(
            RateCard.city == item.get("city"),
            RateCard.service == item.get("service"),
            RateCard.ride_type == item.get("ride_type")
        ).first()
        if existing:
            for k, v in item.items():
                if k != "id":
                    setattr(existing, k, v)
            existing.updated_at = datetime.utcnow()
            updated += 1
        else:
            new_card = RateCard(**item)
            new_card.updated_at = datetime.utcnow()
            db.add(new_card)
            created += 1
    db.commit()
    return {"success": True, "created": created, "updated": updated}


@router.put("/admin/service-status", dependencies=[Depends(verify_admin)])
async def update_service_status(payload: ServiceStatusUpdatePayload, db: Session = Depends(get_db)):
    """Allows regulators or administrators to toggle service status (e.g. license suspension)."""
    st = db.query(ServiceStatus).filter(
        ServiceStatus.region_id == payload.region_id,
        ServiceStatus.service_name == payload.service_name
    ).first()

    if not st:
        st = ServiceStatus(
            region_id=payload.region_id,
            service_name=payload.service_name,
            status=payload.status,
            status_reason=payload.status_reason,
            last_updated=datetime.utcnow()
        )
        db.add(st)
    else:
        st.status = payload.status
        st.status_reason = payload.status_reason
        st.last_updated = datetime.utcnow()

    db.commit()
    db.refresh(st)
    return {
        "success": True,
        "region_id": st.region_id,
        "service_name": st.service_name,
        "status": st.status,
        "status_reason": st.status_reason,
        "last_updated": st.last_updated.isoformat()
    }
