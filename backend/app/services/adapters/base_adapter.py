from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional


@dataclass
class QuoteObject:
    provider: str
    vehicle_type: str
    actual_fare: Optional[float] = None
    fare_min: Optional[float] = None
    fare_max: Optional[float] = None
    currency: str = "INR"
    currency_symbol: str = "₹"
    eta_minutes: int = 5
    distance_km: float = 0.0
    duration_minutes: float = 0.0
    surge_multiplier: float = 1.0
    availability: bool = True
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str = field(default_factory=lambda: (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat())
    source: str = "live_provider_api"
    is_live: bool = True
    live_available: bool = True
    base_fare: float = 0.0
    distance_fare: float = 0.0
    duration_fare: float = 0.0
    platform_fee: float = 0.0
    toll_estimate: float = 0.0
    cost_per_km: float = 0.0
    cost_per_min: float = 0.0
    rating: float = 4.5
    app_deep_link: str = ""
    web_link: str = ""
    is_stale: bool = False
    quote_age_seconds: float = 0.0
    is_government_backed: bool = False
    category_tag: str = "Private Aggregator"
    regulatory_body: Optional[str] = None
    zero_surge: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "vehicleType": self.vehicle_type,
            "vehicle_type": self.vehicle_type,
            "actualFare": self.actual_fare,
            "estimatedFare": self.actual_fare,
            "fare_min": self.fare_min,
            "fare_max": self.fare_max,
            "fareMin": self.fare_min,
            "fareMax": self.fare_max,
            "currency": self.currency,
            "currencySymbol": self.currency_symbol,
            "etaMinutes": self.eta_minutes,
            "distanceKm": self.distance_km,
            "durationMinutes": self.duration_minutes,
            "surgeMultiplier": self.surge_multiplier,
            "availability": self.availability,
            "is_live": self.is_live,
            "isLive": self.is_live,
            "live_available": self.live_available,
            "liveAvailable": self.live_available,
            "retrieved_at": self.retrieved_at,
            "expires_at": self.expires_at,
            "source": self.source,
            "baseFare": self.base_fare,
            "distanceFare": self.distance_fare,
            "durationFare": self.duration_fare,
            "platformFee": self.platform_fee,
            "tollEstimate": self.toll_estimate,
            "costPerKm": self.cost_per_km,
            "costPerMin": self.cost_per_min,
            "rating": self.rating,
            "appDeepLink": self.app_deep_link,
            "webLink": self.web_link,
            "is_stale": self.is_stale,
            "quote_age_seconds": round(self.quote_age_seconds, 1),
            "isGovernmentBacked": self.is_government_backed,
            "categoryTag": self.category_tag,
            "regulatoryBody": self.regulatory_body,
            "zeroSurge": self.zero_surge
        }


class ProviderAdapter(ABC):
    """Base interface for regional ride-hailing and government-backed public transit adapters."""

    def __init__(self, name: str, enabled: bool = True, timeout_seconds: float = 3.0):
        self.name = name
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds
        self.consecutive_failures = 0
        self.circuit_open = False
        self.circuit_opened_at: Optional[datetime] = None

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        if self.circuit_open:
            if self.circuit_opened_at and (datetime.now(timezone.utc) - self.circuit_opened_at).total_seconds() > 30:
                self.circuit_open = False
                self.consecutive_failures = 0
                return True
            return False
        return True

    def check_circuit(self) -> bool:
        return self.is_available()

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.circuit_open = False

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= 3:
            self.circuit_open = True
            self.circuit_opened_at = datetime.now(timezone.utc)

    @abstractmethod
    async def get_quotes(
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
        toll_charge: float = 0.0
    ) -> List[QuoteObject]:
        pass

    @abstractmethod
    def get_vehicle_categories(self) -> List[str]:
        pass
