"""
RideCompare Real-Time Dynamic Pricing & Demand Intelligence Service
===================================================================
Determines CURRENT PRICING PRESSURE / DEMAND CONDITION for each ride provider.

Standardized RideCompare Scale:
  0 = LOW            (0.0 - 0.5)
  1 = NORMAL         (0.5 - 1.5)
  2 = SLIGHTLY HIGH  (1.5 - 2.5)
  3 = HIGH           (2.5 - 3.5)
  4 = VERY HIGH      (3.5 - 4.0)

Features & Design:
  - H3 Geospatial zone discretization
  - Multi-horizon rolling request windows (5m, 15m, 30m, 1h, 24h, 7d)
  - Exponential time decay
  - 5-Level Fallback Hierarchy:
      Level 1: Provider-authorized legitimate signal
      Level 2: Machine Learning estimation (Gradient Boosting / Random Forest)
      Level 3: Statistical / Historical demand model
      Level 4: Time/location heuristic fallback
      Level 5: Insufficient data
  - Confidence scoring reflecting sample density and signal recency
  - TTL-based caching per (provider, pickup_zone, ride_category)
  - Asynchronous observation persistence for continuous learning
  - NEVER fabricates exact provider fares or proprietary surge multipliers
"""

import os
import math
import time
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import threading

try:
    import h3
except ImportError:
    h3 = None

try:
    import joblib
except ImportError:
    joblib = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    import pandas as pd
except ImportError:
    pd = None

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from backend.app.config import APP_DIR, ROOT_DIR
from backend.app.models.db_models import DemandObservation, Search, HistoricalFare

logger = logging.getLogger("demand-intelligence")

# Configurable thresholds for pricing pressure score (0 to 4 scale)
DEFAULT_PRESSURE_THRESHOLDS = {
    "LOW_MAX": 0.5,
    "NORMAL_MAX": 1.5,
    "SLIGHTLY_HIGH_MAX": 2.5,
    "HIGH_MAX": 3.5,
    "VERY_HIGH_MAX": 4.0,
}

H3_DEFAULT_RESOLUTION = 7  # ~1.2km edge length, ideal taxi zone partition

SAVED_MODELS_DIR = ROOT_DIR / "ml" / "models" / "saved"
MODEL_FILE_PATH = SAVED_MODELS_DIR / "demand_intelligence_model.joblib"
METADATA_FILE_PATH = SAVED_MODELS_DIR / "demand_metadata.json"


def get_h3_zone(lat: float, lng: float, resolution: int = H3_DEFAULT_RESOLUTION) -> str:
    """Computes H3 zone index for coordinates with graceful fallback to grid cells."""
    if lat is None or lng is None:
        return "zone_unknown"
    try:
        if h3 is not None and -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0:
            if hasattr(h3, "latlng_to_cell"):
                return h3.latlng_to_cell(lat, lng, resolution)
            elif hasattr(h3, "geo_to_h3"):
                return h3.geo_to_h3(lat, lng, resolution)
    except Exception as err:
        logger.debug("H3 indexing fallback: %s", err)
    # Deterministic grid cell fallback
    grid_lat = round(lat, 2)
    grid_lng = round(lng, 2)
    return f"grid_{grid_lat}_{grid_lng}"


def score_to_demand_level(score: float, thresholds: Optional[Dict[str, float]] = None) -> str:
    """Converts a continuous pricing_pressure_score (0-4) to standardized string label."""
    th = thresholds or DEFAULT_PRESSURE_THRESHOLDS
    bounded = max(0.0, min(4.0, float(score)))
    if bounded < th.get("LOW_MAX", 0.5):
        return "LOW"
    elif bounded < th.get("NORMAL_MAX", 1.5):
        return "NORMAL"
    elif bounded < th.get("SLIGHTLY_HIGH_MAX", 2.5):
        return "SLIGHTLY HIGH"
    elif bounded < th.get("HIGH_MAX", 3.5):
        return "HIGH"
    else:
        return "VERY HIGH"


def get_demand_wording(level: str) -> str:
    """Returns compliant, non-proprietary human-readable market condition wording."""
    mapping = {
        "LOW": "Low demand conditions detected. Pricing likely at baseline.",
        "NORMAL": "Demand currently appears normal. Standard market conditions.",
        "SLIGHTLY HIGH": "Moderate demand detected. Pricing may be slightly elevated.",
        "HIGH": "High demand conditions detected. Pricing may be elevated.",
        "VERY HIGH": "Very high demand conditions detected. High pricing pressure across zone.",
        "INSUFFICIENT_DATA": "Limited real-time data is available for this provider. This estimate may be less accurate."
    }
    return mapping.get(level.upper(), "Market conditions detected.")


class PricingPressureCache:
    """Thread-safe, short-lived cache for pricing-pressure estimations."""

    def __init__(self, default_ttl_seconds: int = 60):
        self.default_ttl = default_ttl_seconds
        self._cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def _make_key(self, provider: str, pickup_zone: str, ride_category: str) -> str:
        return f"{provider.lower().strip()}:{pickup_zone.strip()}:{ride_category.lower().strip()}"

    def get(self, provider: str, pickup_zone: str, ride_category: str) -> Optional[Dict[str, Any]]:
        key = self._make_key(provider, pickup_zone, ride_category)
        now = time.time()
        with self._lock:
            entry = self._cache.get(key)
            if entry:
                expires_at, data = entry
                if now < expires_at:
                    return data
                else:
                    self._cache.pop(key, None)
        return None

    def set(self, provider: str, pickup_zone: str, ride_category: str, data: Dict[str, Any], ttl: Optional[int] = None) -> None:
        key = self._make_key(provider, pickup_zone, ride_category)
        expiry = time.time() + (ttl if ttl is not None else self.default_ttl)
        with self._lock:
            self._cache[key] = (expiry, data)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


class DemandIntelligenceEngine:
    """Core intelligence engine estimating pricing pressure using historical, geo-spatial, and real-time signals."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DemandIntelligenceEngine, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.cache = PricingPressureCache(default_ttl_seconds=60)
        self.model = None
        self.metadata: Dict[str, Any] = {}
        self.model_loaded = False
        self.thresholds = dict(DEFAULT_PRESSURE_THRESHOLDS)
        self.load_model()
        self._initialized = True

    def load_model(self) -> bool:
        """Loads trained regression model from disk if available."""
        if joblib is None:
            self.model_loaded = False
            return False
        try:
            if MODEL_FILE_PATH.exists() and METADATA_FILE_PATH.exists():
                self.model = joblib.load(str(MODEL_FILE_PATH))
                with open(METADATA_FILE_PATH, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                self.model_loaded = True
                logger.info("Successfully loaded demand intelligence ML model (version %s)", self.metadata.get("version", "v1"))
                return True
        except Exception as err:
            logger.warning("Could not load demand intelligence model (%s). Operating in statistical/heuristic mode.", err)
        self.model_loaded = False
        return False

    def extract_time_features(self, dt: Optional[datetime] = None) -> Dict[str, Any]:
        """Extracts cyclical and categorical time-based features."""
        now = dt or datetime.utcnow()
        hour = now.hour
        minute = now.minute
        hour_float = hour + minute / 60.0
        dow = now.weekday()  # 0=Monday, 6=Sunday
        is_weekend = 1 if dow in (5, 6) else 0

        # Cyclical encoding for hour (preserves continuity 23h -> 0h)
        hour_sin = math.sin(2 * math.pi * hour_float / 24.0)
        hour_cos = math.cos(2 * math.pi * hour_float / 24.0)

        # Indian / Standard public holiday heuristic (expandable)
        is_holiday = 0

        return {
            "hour_of_day": hour,
            "minute": minute,
            "hour_sin": hour_sin,
            "hour_cos": hour_cos,
            "day_of_week": dow,
            "is_weekend": is_weekend,
            "is_holiday": is_holiday,
            "timestamp": now
        }

    def compute_time_decay_weight(self, observation_time: datetime, now: Optional[datetime] = None, half_life_seconds: float = 3600.0) -> float:
        """Computes exponential time-decay weight for past observations."""
        current = now or datetime.utcnow()
        delta_seconds = max(0.0, (current - observation_time).total_seconds())
        # Exponential decay: w = 2^(-delta / half_life)
        return math.pow(2.0, -delta_seconds / max(1.0, half_life_seconds))

    def retrieve_zone_signals(
        self,
        db: Optional[Session],
        pickup_zone: str,
        provider: str,
        ride_category: str = "Cab"
    ) -> Dict[str, Any]:
        """Aggregates multi-horizon request activity and historical statistics from database."""
        now = datetime.utcnow()
        signals = {
            "recent_count_5m": 0,
            "recent_count_15m": 0,
            "recent_count_30m": 0,
            "recent_count_1h": 0,
            "recent_count_24h": 0,
            "historical_hour_avg": 2.0,
            "historical_provider_pressure": 1.2,
            "last_observation_seconds_ago": 3600.0,
            "total_zone_samples": 0,
            "historical_fare_deviation": 0.0,
            "supply_available": False,
            "live_supply": None
        }

        if db is None:
            return signals

        try:
            t_5m = now - timedelta(minutes=5)
            t_15m = now - timedelta(minutes=15)
            t_30m = now - timedelta(minutes=30)
            t_1h = now - timedelta(hours=1)
            t_24h = now - timedelta(hours=24)
            t_7d = now - timedelta(days=7)

            # Query recent demand observations for this zone
            obs_query = db.query(DemandObservation).filter(
                DemandObservation.pickup_zone == pickup_zone,
                DemandObservation.timestamp >= t_7d
            )

            observations = obs_query.all()
            signals["total_zone_samples"] = len(observations)

            count_5m = 0
            count_15m = 0
            count_30m = 0
            count_1h = 0
            count_24h = 0
            decayed_pressure_sum = 0.0
            decayed_weight_sum = 0.0
            provider_recent_pressures = []

            for obs in observations:
                t = obs.timestamp
                if t >= t_5m:
                    count_5m += 1
                if t >= t_15m:
                    count_15m += 1
                if t >= t_30m:
                    count_30m += 1
                if t >= t_1h:
                    count_1h += 1
                if t >= t_24h:
                    count_24h += 1

                w = self.compute_time_decay_weight(t, now, half_life_seconds=1800.0)
                score = obs.pricing_pressure_score if obs.pricing_pressure_score is not None else 1.0
                decayed_pressure_sum += score * w
                decayed_weight_sum += w

                if obs.provider.lower() == provider.lower():
                    provider_recent_pressures.append(score)

            signals["recent_count_5m"] = count_5m
            signals["recent_count_15m"] = count_15m
            signals["recent_count_30m"] = count_30m
            signals["recent_count_1h"] = count_1h
            signals["recent_count_24h"] = count_24h

            if decayed_weight_sum > 0:
                signals["historical_provider_pressure"] = round(decayed_pressure_sum / decayed_weight_sum, 2)
            elif provider_recent_pressures:
                signals["historical_provider_pressure"] = round(sum(provider_recent_pressures) / len(provider_recent_pressures), 2)

            # Check time since most recent observation
            if observations:
                latest = max(observations, key=lambda x: x.timestamp)
                signals["last_observation_seconds_ago"] = max(0.0, (now - latest.timestamp).total_seconds())

            # Also query searches table to incorporate active user search velocity
            recent_searches = db.query(func.count(Search.id)).filter(
                Search.created_at >= t_15m
            ).scalar() or 0
            signals["active_search_velocity"] = recent_searches

        except Exception as err:
            logger.warning("Error retrieving zone signals for zone %s: %s", pickup_zone, err)

        return signals

    def compute_heuristic_baseline(
        self,
        time_feats: Dict[str, Any],
        traffic_level: float = 1.0,
        provider: str = "Uber",
        is_airport_route: bool = False
    ) -> float:
        """
        Level 4 Fallback: Deterministic baseline heuristic based on time of day,
        day of week, traffic level, and route category.
        Standardized between 0.0 and 4.0.
        """
        hour = time_feats["hour_of_day"]
        is_weekend = time_feats["is_weekend"]

        # Base neutral pressure: 1.0 (NORMAL)
        score = 1.0

        # Morning rush hour (8:00 - 10:30 AM weekdays)
        if not is_weekend and (8 <= hour <= 10):
            score += 1.2
        # Evening rush hour (5:00 - 8:30 PM weekdays)
        elif not is_weekend and (17 <= hour <= 20):
            score += 1.4
        # Late weekend evening (9:00 PM - 2:00 AM)
        elif is_weekend and (hour >= 21 or hour <= 2):
            score += 1.1
        # Late night off-peak (2:00 AM - 5:00 AM)
        elif 2 <= hour <= 5:
            score -= 0.6
        # Mid-day normal (11:00 AM - 4:00 PM)
        else:
            score += 0.0

        # Traffic impact
        if traffic_level > 1.4:
            score += 0.7
        elif traffic_level > 1.15:
            score += 0.3

        # Airport route surcharge / demand bias
        if is_airport_route:
            score += 0.4

        # Provider operational profile tuning
        prov = provider.lower()
        if "rapido" in prov and "bike" in prov:
            score = max(0.3, score - 0.2)  # Bikes navigate traffic easier
        elif "waymo" in prov or "autonomous" in prov:
            score = max(0.5, score - 0.1)

        return max(0.1, min(3.9, round(score, 2)))

    def calculate_confidence(
        self,
        source_type: str,
        total_samples: int,
        last_obs_seconds: float,
        has_route_geometry: bool = True
    ) -> Tuple[float, str]:
        """
        Calculates a transparent confidence score (0.0 to 1.0) and human-readable level.
        Reflects model and data quality. Never presents certainty.
        """
        if source_type == "insufficient_data":
            return 0.25, "Limited data"

        base = 0.50
        if source_type == "provider_signal":
            base = 0.90
        elif source_type == "ml_estimate":
            base = 0.82
        elif source_type == "statistical_baseline":
            base = 0.72
        elif source_type == "heuristic_fallback":
            base = 0.60

        # Sample density bonus / penalty
        if total_samples >= 30:
            base += 0.08
        elif total_samples >= 10:
            base += 0.04
        elif total_samples < 3:
            base -= 0.15

        # Recency bonus / penalty
        if last_obs_seconds < 600:  # < 10 mins ago
            base += 0.05
        elif last_obs_seconds > 86400:  # > 24 hours ago
            base -= 0.10

        # Route precision
        if not has_route_geometry:
            base -= 0.05

        final_conf = max(0.20, min(0.95, round(base, 2)))
        conf_pct = int(final_conf * 100)

        if final_conf >= 0.80:
            conf_label = f"{conf_pct}% confidence"
        elif final_conf >= 0.60:
            conf_label = f"{conf_pct}% confidence"
        else:
            conf_label = "Limited data"

        return final_conf, conf_label

    def estimate_pricing_pressure(
        self,
        pickup_lat: float,
        pickup_lng: float,
        dest_lat: Optional[float] = None,
        dest_lng: Optional[float] = None,
        provider: str = "Uber",
        ride_category: str = "Cab",
        distance_km: float = 10.0,
        duration_min: float = 25.0,
        traffic_level: float = 1.0,
        osrm_success: bool = True,
        db: Optional[Session] = None,
        authorized_provider_signal: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes real-time pricing pressure / demand intelligence determination.

        Fallback Hierarchy:
          LEVEL 1: Provider-authorized legitimate data
          LEVEL 2: Machine Learning estimation
          LEVEL 3: Statistical/historical demand model
          LEVEL 4: Time/location heuristic fallback
          LEVEL 5: Insufficient data

        Returns standard RideCompare demand intelligence output.
        """
        pickup_zone = get_h3_zone(pickup_lat, pickup_lng)
        dest_zone = get_h3_zone(dest_lat, dest_lng) if (dest_lat and dest_lng) else "zone_destination_unknown"

        # Check Cache
        cached = self.cache.get(provider, pickup_zone, ride_category)
        if cached:
            return cached

        time_feats = self.extract_time_features()
        zone_signals = self.retrieve_zone_signals(db, pickup_zone, provider, ride_category)

        # Detect airport keywords or distance characteristics
        is_airport = distance_km > 25.0

        source_type = "heuristic_fallback"
        score = 1.0
        reason = "Standard baseline demand conditions for this area."

        # LEVEL 1: Legitimate Provider-Authorized Data (if supplied)
        if authorized_provider_signal and "demand_pressure" in authorized_provider_signal:
            raw_dp = float(authorized_provider_signal["demand_pressure"])
            score = max(0.0, min(4.0, raw_dp))
            source_type = "provider_signal"
            reason = authorized_provider_signal.get("reason", "Direct provider availability and request ratio.")

        # LEVEL 2: Machine Learning Prediction Layer
        elif self.model_loaded and self.model is not None:
            try:
                # Prepare features DataFrame
                # Strict ordering matching training pipeline
                req_rate = zone_signals["recent_count_15m"] / 15.0
                hist_avg = max(0.1, zone_signals["historical_hour_avg"])
                demand_dev = (req_rate - hist_avg) / hist_avg

                feature_dict = {
                    "hour_of_day": time_feats["hour_of_day"],
                    "hour_sin": time_feats["hour_sin"],
                    "hour_cos": time_feats["hour_cos"],
                    "day_of_week": time_feats["day_of_week"],
                    "is_weekend": time_feats["is_weekend"],
                    "is_holiday": time_feats["is_holiday"],
                    "latitude": pickup_lat or 12.97,
                    "longitude": pickup_lng or 77.59,
                    "route_distance": distance_km,
                    "estimated_duration": duration_min,
                    "traffic_level": traffic_level,
                    "recent_request_count_5m": zone_signals["recent_count_5m"],
                    "recent_request_count_15m": zone_signals["recent_count_15m"],
                    "recent_request_count_30m": zone_signals["recent_count_30m"],
                    "recent_request_count_1h": zone_signals["recent_count_1h"],
                    "recent_request_count_24h": zone_signals["recent_count_24h"],
                    "request_rate": req_rate,
                    "historical_request_average": hist_avg,
                    "historical_demand_deviation": demand_dev,
                    "historical_provider_pressure": zone_signals["historical_provider_pressure"],
                    "time_since_last_observation": zone_signals["last_observation_seconds_ago"],
                    "provider": provider,
                    "ride_category": ride_category
                }

                if pd is not None:
                    df_feats = pd.DataFrame([feature_dict])
                    pred_score = float(self.model.predict(df_feats)[0])
                    score = max(0.0, min(4.0, round(pred_score, 2)))
                    source_type = "ml_estimate"
                    
                    if score >= 3.0:
                        reason = "High request activity relative to historical baseline in this zone."
                    elif score >= 2.0:
                        reason = "Moderate market activity and traffic density detected."
                    elif score <= 0.6:
                        reason = "Low request activity relative to historical capacity."
                    else:
                        reason = "Demand currently aligns with normal historical baseline."
            except Exception as ml_err:
                logger.warning("ML prediction failed (%s). Falling back to statistical model.", ml_err)
                source_type = "statistical_baseline"

        # LEVEL 3: Statistical/Historical Demand Model
        if source_type == "statistical_baseline" or (not self.model_loaded and zone_signals["total_zone_samples"] >= 3):
            source_type = "statistical_baseline"
            hist_pressure = zone_signals["historical_provider_pressure"]
            # Weight by traffic and recent velocity
            traffic_bump = max(0.0, (traffic_level - 1.0) * 0.8)
            score = max(0.1, min(3.9, round(hist_pressure + traffic_bump, 2)))
            reason = "Estimated using exponential time-decay over historical zone observations."

        # LEVEL 4: Basic Time/Location Heuristic
        elif source_type == "heuristic_fallback":
            score = self.compute_heuristic_baseline(
                time_feats=time_feats,
                traffic_level=traffic_level,
                provider=provider,
                is_airport_route=is_airport
            )
            reason = "Standard baseline heuristic using time-of-day, location zone, and traffic signals."

        # LEVEL 5: Insufficient Data Verification
        if pickup_lat is None or pickup_lng is None or abs(pickup_lat) < 0.001:
            source_type = "insufficient_data"
            score = 1.0
            reason = "Limited location data available for pricing pressure evaluation."

        demand_level = score_to_demand_level(score, self.thresholds)
        confidence, confidence_text = self.calculate_confidence(
            source_type=source_type,
            total_samples=zone_signals["total_zone_samples"],
            last_obs_seconds=zone_signals["last_observation_seconds_ago"],
            has_route_geometry=osrm_success
        )

        now_iso = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

        result = {
            "provider": provider,
            "ride_category": ride_category,
            "pricing_pressure_score": score,
            "demand_level": demand_level,
            "pricing_pressure": demand_level,
            "confidence": confidence,
            "confidence_text": confidence_text,
            "confidence_score": int(confidence * 100),
            "reason": reason,
            "condition_wording": get_demand_wording(demand_level if source_type != "insufficient_data" else "INSUFFICIENT_DATA"),
            "source_type": source_type,
            "pickup_zone": pickup_zone,
            "destination_zone": dest_zone,
            "last_updated": now_iso,
            "updated_at": now_iso
        }

        # Cache result
        self.cache.set(provider, pickup_zone, ride_category, result, ttl=60)
        return result

    def log_observation(
        self,
        db: Session,
        provider: str,
        pickup_zone: str,
        destination_zone: str,
        ride_category: str,
        distance_km: float,
        duration_min: float,
        pricing_pressure_score: float,
        demand_level: str,
        confidence: float,
        source_type: str,
        reason: str,
        observed_fare: Optional[float] = None,
        traffic_level: float = 1.0,
        actual_observation: Optional[float] = None
    ) -> None:
        """Persists observation into database for continuous model retraining."""
        try:
            obs = DemandObservation(
                timestamp=datetime.utcnow(),
                provider=provider,
                pickup_zone=pickup_zone,
                destination_zone=destination_zone,
                ride_category=ride_category,
                observed_fare_if_available=observed_fare,
                observed_demand_signal=None,
                observed_supply_signal=None,
                traffic_level=traffic_level,
                distance_km=distance_km,
                duration_min=duration_min,
                pricing_pressure_score=pricing_pressure_score,
                demand_level=demand_level,
                confidence=confidence,
                source_type=source_type,
                reason=reason,
                actual_observation_when_available=actual_observation
            )
            db.add(obs)
            db.commit()
        except Exception as err:
            logger.warning("Failed to persist demand observation: %s", err)
            db.rollback()


# Singleton instance
demand_engine = DemandIntelligenceEngine()
