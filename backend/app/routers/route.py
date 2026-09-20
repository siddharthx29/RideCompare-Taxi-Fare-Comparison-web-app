from typing import Optional, List
from fastapi import APIRouter, Query, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
import httpx

from backend.app.database import get_db, SessionLocal
from backend.app.models.db_models import Search, HistoricalFare
from backend.app.services.pricing import calculate_fares_and_scores, calculate_haversine_distance

router = APIRouter(tags=["Routing"])


class RoutePostPayload(BaseModel):
    pickup: List[float]
    drop: List[float]
    pickupName: Optional[str] = "Pickup Location"
    dropName: Optional[str] = "Drop Location"


def log_historical_observations(comparison: dict, source: str, dest: str, lat1: float, lon1: float, lat2: float, lon2: float, distance_km: float, duration_min: float):
    db = SessionLocal()
    try:
        for p in comparison.get("providers", []):
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
                actual_fare=p["actualFare"],
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
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


async def _process_route_calculation(
    lon1: float, lat1: float, lon2: float, lat2: float,
    source_label: str, dest_label: str,
    db: Session,
    background_tasks: Optional[BackgroundTasks] = None
):
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
    except Exception:
        pass

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

    comparison = calculate_fares_and_scores(
        distance_km=distance_km,
        duration_mins=duration_mins,
        source=source_label,
        destination=dest_label,
        start_lon=lon1,
        start_lat=lat1,
        end_lon=lon2,
        end_lat=lat2,
        osrm_success=osrm_success
    )

    fares = [p["actualFare"] for p in comparison["providers"]]
    max_fare = max(fares) if fares else 0
    min_fare = min(fares) if fares else 0
    potential_savings = max_fare - min_fare

    search_rec = Search(
        source=source_label,
        destination=dest_label,
        source_lat=lat1,
        source_lng=lon1,
        dest_lat=lat2,
        dest_lng=lon2,
        distance_km=round(distance_km, 1),
        duration_min=round(duration_mins),
        cheapest_provider=comparison["recommendations"]["cheapest"],
        fastest_provider=comparison["recommendations"]["fastest"],
        best_provider=comparison["recommendations"]["mostEfficient"],
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

    return {
        "success": True,
        "searchId": search_rec.id,
        "geometry": geometry,
        "comparison": comparison,
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
                "fare": p["actualFare"],
                "estimatedFare": p["actualFare"],
                "eta_minutes": p["etaMinutes"],
                "ml_predicted_fare": p.get("predictedFare", p["actualFare"]),
                "prediction_delta": p.get("predictionDiff", 0),
                "pricing_regime": comparison.get("pricingRegime", "Standard"),
                "confidence_score": p.get("confidenceScore", 90.0),
                "smart_score": p.get("smartScore", 85.0),
                "is_anomaly": p.get("isAnomaly", False),
                "anomaly_reason": p.get("anomalyReason", ""),
                "booking_url": p.get("webLink", "https://m.uber.com")
            }
            for p in comparison.get("providers", [])
        ]
    }


@router.get("/route")
async def get_route_and_comparison_get(
    start: str = Query(...),
    end: str = Query(...),
    sourceName: Optional[str] = Query(None),
    destName: Optional[str] = Query(None),
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
        background_tasks=background_tasks
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
        background_tasks=background_tasks
    )
