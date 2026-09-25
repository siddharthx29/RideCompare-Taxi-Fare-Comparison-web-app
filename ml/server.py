"""Loopback-only internal inference service."""

import logging
import os
import sys
from typing import List, Optional

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ml.inference.predictor import FareIntelligenceEngine

logger = logging.getLogger(__name__)

app = FastAPI(
    title="RideCompare Internal Inference Service",
    description="Internal inference API. Do not expose this service directly to the public internet.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("ML_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:8080").split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

engine = FareIntelligenceEngine()


class ProviderFareRequest(BaseModel):
    provider: str
    vehicle_type: str = "Cab"
    distance_km: float = Field(..., gt=0)
    duration_min: float = Field(..., gt=0)
    actual_fare: float = Field(..., gt=0)
    base_fare: Optional[float] = 0.0
    platform_fee: Optional[float] = 0.0
    toll_fee: Optional[float] = 0.0
    surge_multiplier: Optional[float] = 1.0
    traffic_condition: Optional[str] = "Normal"
    weather_condition: Optional[str] = "Clear"
    time_of_day: Optional[str] = "Regular"
    day_of_week: Optional[str] = "Monday"
    eta_minutes: Optional[int] = 10


class CompareRequest(BaseModel):
    distance_km: float = Field(..., gt=0)
    duration_min: float = Field(..., gt=0)
    source: Optional[str] = "Origin"
    destination: Optional[str] = "Destination"
    traffic_condition: Optional[str] = "Normal"
    weather_condition: Optional[str] = "Clear"
    time_of_day: Optional[str] = "Regular"
    day_of_week: Optional[str] = "Monday"
    surge_multiplier: Optional[float] = 1.0
    osrm_success: Optional[bool] = True
    providers: List[ProviderFareRequest]


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "RideCompare Internal Inference Service"}


@app.post("/predict")
def predict_fare(payload: ProviderFareRequest):
    try:
        return engine.predict_provider_fare(payload.model_dump())
    except Exception as error:
        logger.exception("Internal inference request failed")
        raise HTTPException(status_code=500, detail="Inference request failed.") from error


@app.post("/compare")
def compare_and_enrich_fares(payload: CompareRequest):
    try:
        provider_dicts = []
        for provider in payload.providers:
            item = provider.model_dump()
            item["distance_km"] = payload.distance_km
            item["duration_min"] = payload.duration_min
            item["traffic_condition"] = payload.traffic_condition
            item["weather_condition"] = payload.weather_condition
            item["time_of_day"] = payload.time_of_day
            item["day_of_week"] = payload.day_of_week
            item["surge_multiplier"] = max(item.get("surge_multiplier", 1.0), payload.surge_multiplier)
            provider_dicts.append(item)

        result = engine.rank_and_compare_providers(provider_dicts, osrm_success=payload.osrm_success)
        return {
            "distance_km": payload.distance_km,
            "duration_min": payload.duration_min,
            "source": payload.source,
            "destination": payload.destination,
            "pricing_regime": result["insights"].get("current_pricing_regime", "Standard"),
            "fare_spread": result["insights"].get("fare_spread", 0),
            "spread_percentage": result["insights"].get("spread_percentage", 0),
            "anomaly_count": result["insights"].get("anomaly_count", 0),
            "providers": result["providers"],
            "insights": result["insights"],
        }
    except Exception as error:
        logger.exception("Internal comparison request failed")
        raise HTTPException(status_code=500, detail="Comparison request failed.") from error


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5001, log_level="info")