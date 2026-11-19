from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class RouteType(str, Enum):
    LOCAL = "LOCAL"
    SHORT_DISTANCE = "SHORT_DISTANCE"
    MEDIUM_DISTANCE = "MEDIUM_DISTANCE"
    LONG_DISTANCE = "LONG_DISTANCE"
    INTERCITY = "INTERCITY"
    OUTSTATION = "OUTSTATION"
    AIRPORT_TRANSFER = "AIRPORT_TRANSFER"


class RecommendationCategory(str, Enum):
    DIRECT = "DIRECT"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"
    MULTIMODAL = "MULTIMODAL"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class SuitabilityLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNSUITABLE = "UNSUITABLE"


class RouteContext(BaseModel):
    origin_label: str
    destination_label: str
    distance_km: float
    duration_mins: float
    route_type: RouteType
    origin_city: Optional[str] = None
    destination_city: Optional[str] = None
    is_intercity: bool = False
    is_outstation: bool = False
    is_airport_transfer: bool = False
    pickup_coords: Optional[List[float]] = None  # [lat, lng]
    drop_coords: Optional[List[float]] = None    # [lat, lng]
    pickup_address: Optional[Dict[str, Any]] = None
    drop_address: Optional[Dict[str, Any]] = None
    classification_reason: str = ""


class ProviderCoverageRecord(BaseModel):
    id: str
    name: str
    vehicle_type: str
    service_type: str  # local, intercity, outstation, airport
    coverage_type: str  # metro, state, intercity_corridor, point_to_point, airport
    coverage_regions: List[str] = Field(default_factory=list)
    areas: List[str] = Field(default_factory=list)
    supported_routes: List[str] = Field(default_factory=list)
    destinations: List[str] = Field(default_factory=list)
    intercity_supported: bool = False
    outstation_supported: bool = False
    minimum_distance: float = 0.5
    maximum_distance: float = 300.0
    last_verified: str = "2026-09"
    verification_source: str = "Regulatory & Transport Policy Knowledge Base"
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    base_fare: float = 50.0
    per_km_rate: float = 14.0
    per_min_rate: float = 2.0
    platform_fee: float = 15.0
    rating: float = 4.5
    is_government_backed: bool = False
    category_tag: str = "Private Aggregator"
    regulatory_body: Optional[str] = None
    zero_surge: bool = False
    restrictions: List[str] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    provider: str
    vehicle_type: str
    eligible: bool
    category: RecommendationCategory
    reason: str
    suitability_level: SuitabilityLevel
    suitability_score: float
    route_supported: bool
    coverage_confidence: ConfidenceLevel
    vehicle_suitability: ConfidenceLevel
    partial_boundary_reached: Optional[str] = None
    warning: Optional[str] = None
    explanations: List[str] = Field(default_factory=list)


class MultimodalLeg(BaseModel):
    leg_number: int
    mode: str
    provider: str
    vehicle_type: str
    from_location: str
    to_location: str
    distance_km: float
    duration_mins: float
    estimated_fare: float
    currency_symbol: str = "₹"
    instructions: str


class MultimodalOption(BaseModel):
    type: str = "MULTIMODAL"
    title: str
    summary: str
    total_distance_km: float
    total_duration_mins: float
    total_estimated_fare: float
    currency_symbol: str = "₹"
    transfer_count: int
    legs: List[MultimodalLeg]
    recommendation_note: str
