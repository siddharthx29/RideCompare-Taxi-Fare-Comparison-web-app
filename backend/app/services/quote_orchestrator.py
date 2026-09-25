import asyncio
import hashlib
import logging
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.services.adapters.base_adapter import ProviderAdapter, QuoteObject
from backend.app.services.adapters.provider_adapters import (
    UberAdapter,
    OlaAdapter,
    RapidoAdapter,
    NammaYatriAdapter,
    KeralaSavariAdapter,
    GoaMilesAdapter,
    YatriSathiAdapter,
    FastTrackAdapter,
    LocalTaxiAdapter,
    WaymoAdapter,
    LyftAdapter,
    CurbTaxiAdapter,
    TfLBlackCabAdapter,
    FreeNowAdapter,
    BoltAdapter,
    G7ParisAdapter,
    DubaiTaxiAdapter,
    CareemAdapter,
    CDGZigAdapter,
    GrabAdapter,
    XanhSMAdapter,
    GoAppJapanAdapter,
    KakaoTaxiAdapter,
    Cabs13Adapter,
    App99Adapter
)
from backend.app.models.db_models import FareSnapshot

logger = logging.getLogger(__name__)


class QuoteOrchestrator:
    """Coordinates concurrent fare inquiries across regional ride providers, calculates quote staleness, and tracks price volatility."""

    def __init__(self, adapters: Optional[List[ProviderAdapter]] = None):
        self.adapters = adapters or [
            UberAdapter(enabled=True),
            OlaAdapter(enabled=True),
            RapidoAdapter(enabled=True),
            NammaYatriAdapter(enabled=True),
            KeralaSavariAdapter(enabled=True),
            GoaMilesAdapter(enabled=True),
            YatriSathiAdapter(enabled=True),
            FastTrackAdapter(enabled=True),
            LocalTaxiAdapter(enabled=True),
            WaymoAdapter(enabled=True),
            LyftAdapter(enabled=True),
            CurbTaxiAdapter(enabled=True),
            TfLBlackCabAdapter(enabled=True),
            FreeNowAdapter(enabled=True),
            BoltAdapter(enabled=True),
            G7ParisAdapter(enabled=True),
            DubaiTaxiAdapter(enabled=True),
            CareemAdapter(enabled=True),
            CDGZigAdapter(enabled=True),
            GrabAdapter(enabled=True),
            XanhSMAdapter(enabled=True),
            GoAppJapanAdapter(enabled=True),
            KakaoTaxiAdapter(enabled=True),
            Cabs13Adapter(enabled=True),
            App99Adapter(enabled=True)
        ]
        self.comparison_window_seconds = 15.0
        self.quote_stale_after_seconds = 45.0

    @staticmethod
    def generate_route_hash(lat1: float, lon1: float, lat2: float, lon2: float, vehicle_type: str = "ALL") -> str:
        raw_key = f"{round(lat1, 2)},{round(lon1, 2)}->{round(lat2, 2)},{round(lon2, 2)}:{vehicle_type.upper()}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]

    async def fetch_all_quotes(
        self,
        source: str,
        destination: str,
        distance_km: float,
        duration_mins: float,
        pickup_lat: float,
        pickup_lng: float,
        drop_lat: float,
        drop_lng: float,
        city: str,
        surge_multiplier: float = 1.0,
        toll_charge: float = 0.0,
        allowed_adapters: Optional[List[str]] = None
    ) -> List[QuoteObject]:
        allowed = set(allowed_adapters or [])
        tasks = [
            asyncio.wait_for(
                adapter.get_quotes(
                    source=source,
                    destination=destination,
                    distance_km=distance_km,
                    duration_mins=duration_mins,
                    pickup_lat=pickup_lat,
                    pickup_lng=pickup_lng,
                    drop_lat=drop_lat,
                    drop_lng=drop_lng,
                    city=city,
                    surge_multiplier=surge_multiplier,
                    toll_charge=toll_charge
                ),
                timeout=adapter.timeout_seconds
            )
            for adapter in self.adapters
            if adapter.is_available() and adapter.name in allowed
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        quotes: List[QuoteObject] = []
        now = datetime.now(timezone.utc)

        for res in results:
            if isinstance(res, list):
                for quote in res:
                    retrieved_dt = datetime.fromisoformat(quote.retrieved_at)
                    age = max(0.0, (now - retrieved_dt).total_seconds())
                    quote.quote_age_seconds = age
                    quote.is_stale = age > self.comparison_window_seconds
                    quotes.append(quote)
            elif isinstance(res, Exception):
                logger.warning("Provider adapter quote fetch failed: %s", res)

        return quotes

    def compute_volatility_metrics(
        self,
        provider: str,
        route_hash: str,
        current_fare: float,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        default_metrics = {
            "absolute_change": 0.0,
            "percentage_change": 0.0,
            "change_per_minute": 0.0,
            "volatility_score": "LOW",
            "price_trend": "STABLE",
            "recent_history": [current_fare]
        }

        if db is None:
            return default_metrics

        try:
            cutoff = datetime.utcnow() - timedelta(hours=2)
            recent_snaps = (
                db.query(FareSnapshot)
                .filter(
                    FareSnapshot.provider == provider,
                    FareSnapshot.route_hash == route_hash,
                    FareSnapshot.timestamp >= cutoff
                )
                .order_by(FareSnapshot.timestamp.desc())
                .limit(10)
                .all()
            )

            if not recent_snaps:
                return default_metrics

            fares = [s.fare for s in reversed(recent_snaps)]
            fares.append(current_fare)

            prev_fare = recent_snaps[0].fare
            abs_change = round(current_fare - prev_fare, 1)
            pct_change = round((abs_change / max(1.0, prev_fare)) * 100, 1)

            time_diff = max(1.0, (datetime.utcnow() - recent_snaps[0].timestamp).total_seconds())
            change_per_min = round((abs_change / time_diff) * 60, 2)

            if len(fares) > 2:
                cv = (float(np.std(fares)) / max(1.0, float(np.mean(fares)))) * 100
                if cv > 15:
                    volatility = "HIGH"
                elif cv > 6:
                    volatility = "MODERATE"
                else:
                    volatility = "LOW"
            else:
                volatility = "LOW"

            if abs_change > 20:
                trend = "RISING"
            elif abs_change < -20:
                trend = "FALLING"
            else:
                trend = "STABLE"

            return {
                "absolute_change": abs_change,
                "percentage_change": pct_change,
                "change_per_minute": change_per_min,
                "volatility_score": volatility,
                "price_trend": trend,
                "recent_history": fares[-6:]
            }
        except Exception as err:
            logger.debug("Volatility calculation fallback: %s", err)
            return default_metrics
