import logging
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import httpx

from backend.app.database import get_db, SessionLocal
from backend.app.models.db_models import Search, HistoricalFare, FareSnapshot, Analytics
from backend.app.services.pricing import calculate_fares_and_scores, calculate_haversine_distance, quote_orchestrator
from backend.app.services.demand_intelligence import demand_engine, get_h3_zone

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Routing"])


class RoutePostPayload(BaseModel):
    pickup: List[float] = Field(..., description="[lat, lng] for pickup location")
    drop: List[float] = Field(..., description="[lat, lng] for drop location")
    pickupName: Optional[str] = "Pickup Location"
    dropName: Optional[str] = "Drop Location"
    pickupAddress: Optional[Dict[str, Any]] = None
    dropAddress: Optional[Dict[str, Any]] = None


class FareComparePayload(BaseModel):
    pickup: str
    drop: str
    pickup_lat: float
    pickup_lng: float
    drop_lat: float
    drop_lng: float
    distance_km: Optional[float] = None
    duration_min: Optional[float] = None
    pickup_address: Optional[Dict[str, Any]] = None
    drop_address: Optional[Dict[str, Any]] = None


class RedirectPayload(BaseModel):
    provider: str
    ride_type: Optional[str] = "Standard"
    fare: float = 0.0
    pickup: Optional[str] = ""
    drop: Optional[str] = ""
    city: Optional[str] = "Bangalore"


PUBLIC_PROVIDER_FIELDS = (
    "provider", "vehicleType", "distanceKm", "etaMinutes", "actualFare", "estimatedFare",
    "fareMin", "fareMax", "fare_min", "fare_max", "currency",
    "currencySymbol", "surgeMultiplier", "baseFare", "distanceFare", "durationFare",
    "platformFee", "tollEstimate", "costPerKm", "costPerMin", "appDeepLink", "webLink",
    "isCheapest", "isFastest", "isMostEfficient", "isBestValue", "isStale", "quoteAgeSeconds", "retrieved_at",
    "isGovernmentBacked", "categoryTag", "regulatoryBody", "zeroSurge",
    # Live vs ML separation
    "isLive", "is_live", "liveAvailable", "live_available", "source",
    # ML Intelligence fields
    "predictedFare", "predictedFareMin", "predictedFareMax", "typicalFareRange",
    "predictionDiff", "predictionDiffPct", "demandLevel", "priceTrend", "priceAnomaly",
    "anomalyReason", "mlInsight", "clusterId", "clusterLabel", "confidence",
    "confidenceScore", "confidenceLevel", "smartScore", "scoreBreakdown",
    # Dynamic Pricing & Demand Intelligence fields
    "pricing_pressure_score", "pricingPressureScore", "demand_level",
    "pricing_pressure", "pricingPressure", "confidence_score", "confidence_text",
    "demandReason", "reason", "conditionWording", "condition_wording", "source_type", "sourceType",
    "pickup_zone", "pickupZone", "destination_zone", "destinationZone", "last_updated", "lastUpdated",
    # Agentic AI & Route Eligibility fields
    "eligibility", "eligibilityReason", "suitabilityLevel", "suitabilityScore",
    "routeSupported", "coverageConfidence", "vehicleSuitabilityConfidence",
    "evaluationExplanations", "partialBoundary", "warning"
)


def _format_provider_dict(provider: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **{key: provider[key] for key in PUBLIC_PROVIDER_FIELDS if key in provider},
        "actualFare": provider.get("actualFare"),
        "estimatedFare": provider.get("actualFare") if provider.get("liveAvailable", True) and provider.get("actualFare") is not None else provider.get("predictedFare", 0),
        "fareMin": provider.get("fareMin", provider.get("fare_min")),
        "fareMax": provider.get("fareMax", provider.get("fare_max")),
        "fare_min": provider.get("fare_min", provider.get("fareMin")),
        "fare_max": provider.get("fare_max", provider.get("fareMax")),
        "isLive": provider.get("isLive", provider.get("is_live", True)),
        "liveAvailable": provider.get("liveAvailable", provider.get("live_available", True)),
        "isStale": provider.get("is_stale", provider.get("isStale", False)),
        "quoteAgeSeconds": provider.get("quote_age_seconds", provider.get("quoteAgeSeconds", 0.0)),
        "pricing_pressure_score": provider.get("pricing_pressure_score", provider.get("pricingPressureScore", 1.0)),
        "demand_level": provider.get("demand_level", provider.get("demandLevel", "NORMAL")),
        "pricing_pressure": provider.get("pricing_pressure", provider.get("pricingPressure", "NORMAL")),
        "confidence": provider.get("confidence", 0.8),
        "confidence_text": provider.get("confidence_text", provider.get("confidenceLevel", "80% confidence")),
        "reason": provider.get("reason", provider.get("demandReason", "Standard baseline demand conditions for this area.")),
        "source_type": provider.get("source_type", provider.get("sourceType", "ml_estimate")),
        "last_updated": provider.get("last_updated", provider.get("lastUpdated")),
        "priceHistory": {
            "fares": provider.get("volatility", {}).get("recent_history", []),
            "trend": provider.get("volatility", {}).get("price_trend", provider.get("priceTrend", "STABLE")),
        },
        "eligibility": provider.get("eligibility", "DIRECT"),
        "eligibilityReason": provider.get("eligibilityReason", ""),
        "suitabilityLevel": provider.get("suitabilityLevel", "HIGH"),
        "suitabilityScore": provider.get("suitabilityScore", 1.0),
        "routeSupported": provider.get("routeSupported", True),
        "coverageConfidence": provider.get("coverageConfidence", "HIGH"),
        "vehicleSuitabilityConfidence": provider.get("vehicleSuitabilityConfidence", "HIGH"),
        "evaluationExplanations": provider.get("evaluationExplanations", []),
        "partialBoundary": provider.get("partialBoundary"),
        "warning": provider.get("warning")
    }


def _public_comparison(comparison: Dict[str, Any]) -> Dict[str, Any]:
    public_fields = (
        "distanceKm", "durationMins", "detectedCity", "state", "country", "currency",
        "currencySymbol", "isServiceable", "message", "regionalNotice", "surgeRuleName",
        "straightLineDistance", "detourDistance", "pricingRegime", "fareSpread",
        "spreadPercentage", "providers", "recommendations", "insights", "routeHash",
        "pickupZone", "destinationZone", "marketConditions",
        "directProviders", "excludedProviders", "partialProviders",
        "multimodalOption", "agentReasoning", "routeClassification"
    )
    result = {key: comparison[key] for key in public_fields if key in comparison}
    result["providers"] = [_format_provider_dict(p) for p in comparison.get("providers", [])]
    if "excludedProviders" in comparison:
        result["excludedProviders"] = [_format_provider_dict(p) for p in comparison.get("excludedProviders", [])]
    if "partialProviders" in comparison:
        result["partialProviders"] = [_format_provider_dict(p) for p in comparison.get("partialProviders", [])]
    if "directProviders" in comparison:
        result["directProviders"] = [_format_provider_dict(p) for p in comparison.get("directProviders", [])]
    return result


def _parse_address_context(value: Optional[str]) -> Optional[Dict[str, Any]]:
    if not value:
        return None
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else None
    except (TypeError, ValueError):
        return None


def log_historical_observations(
    comparison: dict,
    source: str,
    dest: str,
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    distance_km: float,
    duration_min: float
) -> None:
    db = SessionLocal()
    try:
        route_hash = comparison.get("routeHash") or quote_orchestrator.generate_route_hash(lat1, lon1, lat2, lon2)
        for p in comparison.get("providers", []):
            fare_val = p.get("actualFare") or p.get("actual_fare")
            if fare_val is None or float(fare_val) <= 0:
                continue
            rec = HistoricalFare(
                provider=p["provider"],
                vehicle_type=p["vehicleType"],
                source=source,
                destination=dest,
                source_lat=lat1,
                source_lng=lon1,
                dest_lat=lat2,
                dest_lng=lon2,
                distance_km=distance_km,
                duration_min=duration_min,
                actual_fare=float(fare_val),
                base_fare=p["baseFare"],
                surge_multiplier=p["surgeMultiplier"],
                platform_fee=p["platformFee"],
                toll_fee=p["tollEstimate"],
                traffic_condition="Heavy" if p["surgeMultiplier"] > 1.3 else "Normal",
                weather_condition="Clear",
                time_of_day=p.get("time_of_day", "Regular"),
                day_of_week="Monday",
                fare_per_km=p["costPerKm"],
                fare_per_min=p["costPerMin"],
                cluster_id=p.get("clusterId", 0),
                cluster_label=p.get("clusterLabel", "Standard"),
                is_anomaly=p.get("isAnomaly", False)
            )
            db.add(rec)

            snap = FareSnapshot(
                provider=p["provider"],
                route_hash=route_hash,
                vehicle_type=p["vehicleType"],
                fare=p["actualFare"],
                fare_min=p.get("fare_min", round(p["actualFare"] * 0.95)),
                fare_max=p.get("fare_max", round(p["actualFare"] * 1.05)),
                eta_minutes=p["etaMinutes"],
                distance_km=distance_km,
                duration_minutes=duration_min,
                surge_multiplier=p["surgeMultiplier"],
                traffic_condition="Heavy" if p["surgeMultiplier"] > 1.3 else "Normal",
                quote_age_seconds=p.get("quote_age_seconds", 0.0),
                is_anomaly=p.get("isAnomaly", False),
                cluster_id=p.get("clusterId", 0),
                cluster_label=p.get("clusterLabel", "Standard"),
                predicted_fare=p.get("predictedFare", p["actualFare"]),
                confidence_score=p.get("confidenceScore", 90.0),
                smart_score=p.get("smartScore", 85.0),
                source=p.get("source", "permitted_tariff"),
                timestamp=datetime.utcnow()
            )
            db.add(snap)

            # Persist demand intelligence observation for continuous learning
            demand_engine.log_observation(
                db=db,
                provider=p["provider"],
                pickup_zone=p.get("pickup_zone") or get_h3_zone(lat1, lon1),
                destination_zone=p.get("destination_zone") or get_h3_zone(lat2, lon2),
                ride_category=p["vehicleType"],
                distance_km=distance_km,
                duration_min=duration_min,
                pricing_pressure_score=p.get("pricing_pressure_score", 1.0),
                demand_level=p.get("demand_level", "NORMAL"),
                confidence=p.get("confidence", 0.8),
                source_type=p.get("source_type", "ml_estimate"),
                reason=p.get("reason", "Standard baseline demand conditions for this area."),
                observed_fare=fare_val,
                traffic_level=1.4 if p["surgeMultiplier"] > 1.3 else 1.0
            )

        db.commit()
    except Exception as err:
        logger.error("Failed persisting background historical observations: %s", err)
        db.rollback()
    finally:
        db.close()


async def _process_route_calculation(
    lon1: float,
    lat1: float,
    lon2: float,
    lat2: float,
    source_label: str,
    dest_label: str,
    db: Session,
    background_tasks: Optional[BackgroundTasks] = None,
    pickup_address: Optional[Dict[str, Any]] = None,
    drop_address: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    distance_km = 0.0
    duration_mins = 0.0
    geometry = None
    osrm_success = False

    try:
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
        async with httpx.AsyncClient(timeout=4.0) as client:
            res = await client.get(osrm_url)
            if res.status_code == 200:
                data = res.json()
                if data.get("routes") and len(data["routes"]) > 0:
                    route = data["routes"][0]
                    distance_km = route["distance"] / 1000.0
                    duration_mins = route["duration"] / 60.0
                    geometry = route["geometry"]
                    osrm_success = True
    except Exception as err:
        logger.debug("OSRM routing service unavailable (%s). Using Haversine estimation.", err)

    if not osrm_success:
        straight_dist = calculate_haversine_distance(lat1, lon1, lat2, lon2)
        distance_km = max(0.5, straight_dist * 1.25)
        duration_mins = (distance_km / 25.0) * 60.0
        geometry = {
            "type": "LineString",
            "coordinates": [
                [lon1, lat1],
                [lon2, lat2]
            ]
        }

    # Restrict to realistic intra-city / inter-city taxi distances
    if distance_km > 300.0:
        raise HTTPException(
            status_code=400,
            detail=f"Route distance ({round(distance_km, 1)} km) exceeds the 300 km threshold for on-demand taxi fare comparison."
        )

    comparison = calculate_fares_and_scores(
        distance_km=distance_km,
        duration_mins=duration_mins,
        source=source_label,
        destination=dest_label,
        start_lon=lon1,
        start_lat=lat1,
        end_lon=lon2,
        end_lat=lat2,
        osrm_success=osrm_success,
        db=db,
        pickup_address=pickup_address,
        drop_address=drop_address
    )

    valid_fares = [p["actualFare"] for p in comparison.get("providers", []) if p.get("actualFare") is not None]
    potential_savings = (max(valid_fares) - min(valid_fares)) if valid_fares else 0.0

    def _extract_name(rec):
        if isinstance(rec, dict):
            return rec.get("provider", "None")
        return str(rec) if rec else "None"

    rec_cheapest = _extract_name(comparison.get("recommendations", {}).get("cheapest"))
    rec_fastest = _extract_name(comparison.get("recommendations", {}).get("fastest"))
    rec_best = _extract_name(comparison.get("recommendations", {}).get("mostEfficient") or comparison.get("recommendations", {}).get("bestValue"))

    search_rec = Search(
        source=source_label,
        destination=dest_label,
        source_lat=lat1,
        source_lng=lon1,
        dest_lat=lat2,
        dest_lng=lon2,
        distance_km=round(distance_km, 1),
        duration_min=round(duration_mins),
        cheapest_provider=rec_cheapest,
        fastest_provider=rec_fastest,
        best_provider=rec_best,
        savings=float(potential_savings)
    )
    db.add(search_rec)
    db.commit()
    db.refresh(search_rec)

    if background_tasks:
        background_tasks.add_task(
            log_historical_observations,
            comparison, source_label, dest_label, lat1, lon1, lat2, lon2,
            distance_km, duration_mins
        )

    public_comparison = _public_comparison(comparison)
    return {
        "success": True,
        "searchId": search_rec.id,
        "geometry": geometry,
        "comparison": public_comparison,
        "isServiceable": public_comparison.get("isServiceable", False),
        "message": public_comparison.get("message", ""),
        "route": {
            "distance_km": round(distance_km, 1),
            "duration_min": round(duration_mins, 1),
            "coordinates": geometry.get("coordinates", []),
            "pickup_name": source_label,
            "drop_name": dest_label
        },
        "fares": [
            {
                "provider": p["provider"],
                "ride_type": p["vehicleType"],
                "fare": p.get("actualFare"),
                "estimatedFare": p.get("estimatedFare", p.get("actualFare")),
                "is_live": p.get("isLive", True),
                "predicted_fare": p.get("predictedFare"),
                "typical_fare_range": p.get("typicalFareRange"),
                "eta_minutes": p["etaMinutes"],
                "booking_url": p.get("webLink", ""),
                "retrieved_at": p.get("retrieved_at", datetime.utcnow().isoformat()),
                "quote_age_seconds": p.get("quoteAgeSeconds", p.get("quote_age_seconds", 0.0)),
                "is_stale": p.get("isStale", False),
                "demand_level": p.get("demand_level", "NORMAL"),
                "pricing_pressure": p.get("pricing_pressure", "NORMAL"),
                "pricing_pressure_score": p.get("pricing_pressure_score", 1.0),
                "confidence": p.get("confidence", 0.8),
                "confidence_text": p.get("confidence_text", "80% confidence"),
                "demand_reason": p.get("reason", "Standard baseline demand conditions for this area."),
                "source_type": p.get("source_type", "ml_estimate")
            }
            for p in public_comparison.get("providers", [])
        ]
    }


@router.get("/route")
async def get_route_and_comparison_get(
    start: str = Query(..., description="lng,lat format"),
    end: str = Query(..., description="lng,lat format"),
    sourceName: Optional[str] = Query(None),
    destName: Optional[str] = Query(None),
    sourceAddress: Optional[str] = Query(None),
    destAddress: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    try:
        start_coords = start.split(",")
        end_coords = end.split(",")
        lon1, lat1 = float(start_coords[0]), float(start_coords[1])
        lon2, lat2 = float(end_coords[0]), float(end_coords[1])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid coordinates format. Expected 'lng,lat'.")

    return await _process_route_calculation(
        lon1=lon1, lat1=lat1, lon2=lon2, lat2=lat2,
        source_label=sourceName or "Source Location",
        dest_label=destName or "Destination Location",
        db=db,
        background_tasks=background_tasks,
        pickup_address=_parse_address_context(sourceAddress),
        drop_address=_parse_address_context(destAddress)
    )


@router.post("/route")
async def get_route_and_comparison_post(
    payload: RoutePostPayload,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    lat1, lon1 = payload.pickup[0], payload.pickup[1]
    lat2, lon2 = payload.drop[0], payload.drop[1]

    return await _process_route_calculation(
        lon1=lon1, lat1=lat1, lon2=lon2, lat2=lat2,
        source_label=payload.pickupName or "Pickup Location",
        dest_label=payload.dropName or "Drop Location",
        db=db,
        background_tasks=background_tasks,
        pickup_address=payload.pickupAddress,
        drop_address=payload.dropAddress
    )


@router.post("/fare/compare")
async def compare_fares_endpoint(
    payload: FareComparePayload,
    db: Session = Depends(get_db)
):
    dist_km = payload.distance_km
    dur_min = payload.duration_min

    if dist_km is None or dur_min is None:
        straight = calculate_haversine_distance(payload.pickup_lat, payload.pickup_lng, payload.drop_lat, payload.drop_lng)
        dist_km = max(0.5, straight * 1.25)
        dur_min = (dist_km / 25.0) * 60.0

    comparison = calculate_fares_and_scores(
        distance_km=dist_km,
        duration_mins=dur_min,
        source=payload.pickup,
        destination=payload.drop,
        start_lon=payload.pickup_lng,
        start_lat=payload.pickup_lat,
        end_lon=payload.drop_lng,
        end_lat=payload.drop_lat,
        db=db,
        pickup_address=payload.pickup_address,
        drop_address=payload.drop_address
    )
    public_comparison = _public_comparison(comparison)

    return {
        "success": True,
        "comparison": public_comparison,
        "isServiceable": public_comparison.get("isServiceable", False),
        "message": public_comparison.get("message", ""),
        "fares": [
            {
                "provider": p["provider"],
                "ride_type": p["vehicleType"],
                "fare": p["actualFare"],
                "estimatedFare": p["actualFare"],
                "eta_minutes": p["etaMinutes"],
                "booking_url": p.get("webLink", "")
            }
            for p in public_comparison.get("providers", [])
        ]
    }


@router.post("/redirect")
async def log_provider_redirect(
    payload: RedirectPayload,
    db: Session = Depends(get_db)
):
    try:
        analytics_entry = Analytics(
            provider=payload.provider,
            clicks=1,
            redirects=1,
            fare=payload.fare,
            created_at=datetime.utcnow()
        )
        db.add(analytics_entry)
        db.commit()
    except Exception as err:
        logger.warning("Failed recording analytics click: %s", err)
        db.rollback()

    provider_clean = payload.provider.lower()
    if "uber" in provider_clean:
        redirect_url = "https://m.uber.com"
    elif "ola" in provider_clean:
        redirect_url = "https://book.olacabs.com"
    elif "rapido" in provider_clean:
        redirect_url = "https://rapido.bike"
    else:
        redirect_url = "https://www.google.com/search?q=taxi+near+me"

    return {
        "success": True,
        "redirect_url": redirect_url,
        "message": f"Redirecting to {payload.provider}"
    }
