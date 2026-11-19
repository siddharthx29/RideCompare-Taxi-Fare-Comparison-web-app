"""
RideCompare Demand Intelligence & Dynamic Pricing Pressure Router
================================================================
Endpoints:
  - GET  /api/pricing-pressure: Real-time demand & pricing pressure estimation
  - GET  /api/market-conditions: Multi-provider market conditions summary
  - GET  /api/admin/demand-model/metrics: Model performance, training metrics & telemetry
  - POST /api/admin/demand-model/retrain: Trigger model retraining pipeline
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.db_models import DemandObservation
from backend.app.services.demand_intelligence import (
    demand_engine,
    get_h3_zone,
    score_to_demand_level,
    get_demand_wording,
    METADATA_FILE_PATH
)
from ml.training.train_demand_model import train_demand_intelligence_pipeline

router = APIRouter(prefix="/api", tags=["Dynamic Pricing & Demand Intelligence"])


def verify_admin_access(
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    admin_key: Optional[str] = Query(None, alias="key")
):
    """Enforces authorization on internal endpoints when deployed in production."""
    if settings.ENVIRONMENT.lower() in {"production", "prod"} and settings.ADMIN_KEY:
        token = x_admin_key or admin_key
        if not token or token != settings.ADMIN_KEY:
            raise HTTPException(status_code=403, detail="Unauthorized: Invalid admin credentials")
    return True


class DemandPressureResponse(BaseModel):
    provider: str
    pricing_pressure_score: float
    demand_level: str
    confidence: float
    source_type: str
    reason: str
    updated_at: str
    last_updated: Optional[str] = None
    pricing_pressure: Optional[str] = None
    confidence_text: Optional[str] = None
    confidence_score: Optional[int] = None
    condition_wording: Optional[str] = None
    pickup_zone: Optional[str] = None
    destination_zone: Optional[str] = None
    ride_category: Optional[str] = None


@router.get("/pricing-pressure")
async def get_pricing_pressure(
    pickup_lat: float = Query(..., description="Pickup latitude", ge=-90.0, le=90.0),
    pickup_lng: float = Query(..., description="Pickup longitude", ge=-180.0, le=180.0),
    destination_lat: Optional[float] = Query(None, description="Destination latitude", ge=-90.0, le=90.0),
    destination_lng: Optional[float] = Query(None, description="Destination longitude", ge=-180.0, le=180.0),
    provider: Optional[str] = Query(None, description="Specific provider name (e.g. Uber, Ola, Rapido)"),
    ride_category: Optional[str] = Query("Cab", description="Category: Cab, Bike, Auto"),
    distance_km: Optional[float] = Query(10.0, ge=0.1, le=500.0),
    duration_min: Optional[float] = Query(25.0, ge=1.0, le=720.0),
    traffic_level: Optional[float] = Query(1.0, ge=0.5, le=3.0),
    db: Session = Depends(get_db)
):
    """
    Returns RideCompare independent demand condition and pricing pressure estimation.
    Does NOT calculate or output fabricated exact provider fares.
    """
    try:
        # If a single provider is requested, return the direct response format specified in prompt
        if provider:
            est = demand_engine.estimate_pricing_pressure(
                pickup_lat=pickup_lat,
                pickup_lng=pickup_lng,
                dest_lat=destination_lat,
                dest_lng=destination_lng,
                provider=provider,
                ride_category=ride_category or "Cab",
                distance_km=distance_km or 10.0,
                duration_min=duration_min or 25.0,
                traffic_level=traffic_level or 1.0,
                db=db
            )
            return {
                "provider": est["provider"],
                "pricing_pressure_score": est["pricing_pressure_score"],
                "demand_level": est["demand_level"],
                "confidence": est["confidence"],
                "source_type": est["source_type"],
                "reason": est["reason"],
                "updated_at": est["updated_at"],
                "last_updated": est["last_updated"],
                "pricing_pressure": est["pricing_pressure"],
                "confidence_text": est["confidence_text"],
                "confidence_score": est["confidence_score"],
                "condition_wording": est["condition_wording"],
                "pickup_zone": est["pickup_zone"],
                "destination_zone": est["destination_zone"],
                "ride_category": est["ride_category"]
            }

        # Multi-provider comparison response
        default_providers = [
            ("Uber", "Cab"),
            ("Ola", "Cab"),
            ("Rapido", "Bike" if (ride_category or "").lower() == "bike" else ("Auto" if (ride_category or "").lower() == "auto" else "Cab")),
            ("Local Taxi", "Cab")
        ]

        results = []
        for prov_name, cat in default_providers:
            est = demand_engine.estimate_pricing_pressure(
                pickup_lat=pickup_lat,
                pickup_lng=pickup_lng,
                dest_lat=destination_lat,
                dest_lng=destination_lng,
                provider=prov_name,
                ride_category=cat,
                distance_km=distance_km or 10.0,
                duration_min=duration_min or 25.0,
                traffic_level=traffic_level or 1.0,
                db=db
            )
            results.append(est)

        pickup_zone = get_h3_zone(pickup_lat, pickup_lng)
        dest_zone = get_h3_zone(destination_lat, destination_lng) if (destination_lat and destination_lng) else "zone_destination_unknown"

        return {
            "success": True,
            "pickup_zone": pickup_zone,
            "destination_zone": dest_zone,
            "market_summary": [
                {
                    "provider": r["provider"],
                    "demand_level": r["demand_level"],
                    "pricing_pressure": r["pricing_pressure"],
                    "confidence": r["confidence"],
                    "confidence_text": r["confidence_text"],
                    "reason": r["reason"],
                    "last_updated": r["last_updated"],
                    "source_type": r["source_type"]
                }
                for r in results
            ],
            "providers": results,
            "disclaimer": "Demand indicators are RideCompare independent estimates based on available market signals. They do not represent proprietary provider surge multipliers."
        }
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Pricing pressure estimation error: {str(err)}")


@router.get("/market-conditions")
async def get_market_conditions(
    lat: float = Query(..., description="Latitude", ge=-90.0, le=90.0),
    lng: float = Query(..., description="Longitude", ge=-180.0, le=180.0),
    db: Session = Depends(get_db)
):
    """Returns overview of current market condition across core providers for a geographic point."""
    providers = ["Uber", "Ola", "Rapido"]
    overview = []
    zone = get_h3_zone(lat, lng)

    for prov in providers:
        res = demand_engine.estimate_pricing_pressure(
            pickup_lat=lat,
            pickup_lng=lng,
            provider=prov,
            db=db
        )
        overview.append({
            "provider": prov,
            "demand_level": res["demand_level"],
            "pricing_pressure": res["pricing_pressure"],
            "confidence": res["confidence"],
            "confidence_text": res["confidence_text"],
            "source_type": res["source_type"],
            "reason": res["reason"]
        })

    return {
        "success": True,
        "zone": zone,
        "conditions": overview,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@router.get("/admin/demand-model/metrics", dependencies=[Depends(verify_admin_access)])
async def get_demand_model_metrics(db: Session = Depends(get_db)):
    """Admin endpoint to retrieve ML model training telemetry, validation metrics, and dataset statistics."""
    metadata = {}
    if METADATA_FILE_PATH.exists():
        try:
            with open(METADATA_FILE_PATH, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception:
            metadata = {}

    db_obs_count = db.query(DemandObservation).count()

    return {
        "status": "healthy",
        "model_loaded": demand_engine.model_loaded,
        "model_name": metadata.get("model_name", "Gradient Boosting Regressor"),
        "version": metadata.get("version", "v1.0"),
        "target": metadata.get("target", "pricing_pressure_score (0.0 to 4.0)"),
        "last_trained": metadata.get("last_trained"),
        "total_training_records": metadata.get("total_training_records", 12000),
        "validation_metrics": metadata.get("validation_metrics", {}),
        "model_comparison": metadata.get("model_comparison", {}),
        "top_feature_importances": metadata.get("top_feature_importances", {}),
        "thresholds": metadata.get("thresholds", demand_engine.thresholds),
        "h3_resolution": metadata.get("h3_resolution", 7),
        "database_observations_collected": db_obs_count
    }


@router.post("/admin/demand-model/retrain", dependencies=[Depends(verify_admin_access)])
async def retrain_demand_model(
    background_tasks: BackgroundTasks,
    sample_size: int = Query(12000, ge=1000, le=100000)
):
    """Triggers scheduled or on-demand retraining of the dynamic pricing pressure model."""
    try:
        meta = train_demand_intelligence_pipeline()
        # Reload model into singleton engine
        demand_engine.load_model()
        return {
            "success": True,
            "message": "Demand intelligence model retrained and deployed successfully.",
            "version": meta.get("version"),
            "model_name": meta.get("model_name"),
            "validation_metrics": meta.get("validation_metrics")
        }
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Model retraining failed: {str(err)}")
