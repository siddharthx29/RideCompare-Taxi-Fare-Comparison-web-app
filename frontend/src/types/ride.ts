export type VehicleCategory = 'Cab' | 'Bike' | 'Auto' | 'EV' | 'Robotaxi' | string;

export interface LocationInfo {
  label: string;
  lat: number;
  lng: number;
  address?: Record<string, string>;
  placeName?: string;
  locality?: string;
  city?: string;
  state?: string;
  country?: string;
}

export interface RouteGeometry {
  type: 'LineString';
  coordinates: [number, number][];
}

export interface FareHistory {
  fares: number[];
  trend: 'RISING' | 'FALLING' | 'STABLE';
}

export interface RideProviderDetails {
  provider: string;
  vehicleType: VehicleCategory;
  distanceKm: number;
  etaMinutes: number;

  // Real-time Provider Pricing (authoritative source)
  actualFare: number | null;
  estimatedFare: number;
  fareMin?: number;
  fareMax?: number;
  fare_min?: number;
  fare_max?: number;
  isLive?: boolean;
  liveAvailable?: boolean;

  // ML Pricing Intelligence
  predictedFare?: number;
  predictedFareMin?: number;
  predictedFareMax?: number;
  typicalFareRange?: string;
  predictionDiff?: number;
  predictionDiffPct?: number;
  demandLevel?: string;
  priceTrend?: string;
  priceAnomaly?: string;
  anomalyReason?: string;
  mlInsight?: string;
  clusterId?: number;
  clusterLabel?: string;
  confidenceLevel?: string;
  confidenceScore?: number;
  smartScore?: number;

  // Currency & Localized formatting
  currency?: string;
  currencySymbol?: string;

  // Pricing details
  surgeMultiplier: number;

  // Comparison and efficiency
  costPerKm: number;
  costPerMin: number;

  // Itemized fee components
  baseFare: number;
  distanceFare: number;
  durationFare: number;
  platformFee: number;
  tollEstimate: number;
  appDeepLink: string;
  webLink: string;

  // Badges & Stale flags
  isCheapest: boolean;
  isFastest: boolean;
  isMostEfficient: boolean;
  isBestValue: boolean;
  isStale?: boolean;
  quoteAgeSeconds?: number;
  retrieved_at?: string;
  priceHistory?: FareHistory;

  // Regional & Government-Backed Public Mobility
  isGovernmentBacked?: boolean;
  categoryTag?: string;
  regulatoryBody?: string;
  zeroSurge?: boolean;

  // Real-Time Dynamic Pricing & Demand Intelligence
  pricingPressureScore?: number;
  pricing_pressure_score?: number;
  demand_level?: 'LOW' | 'NORMAL' | 'SLIGHTLY HIGH' | 'HIGH' | 'VERY HIGH' | string;
  pricingPressure?: string;
  pricing_pressure?: string;
  confidence_text?: string;
  confidence_score?: number;
  demandReason?: string;
  reason?: string;
  conditionWording?: string;
  condition_wording?: string;
  sourceType?: string;
  source_type?: string;
  pickupZone?: string;
  pickup_zone?: string;
  destinationZone?: string;
  destination_zone?: string;
  lastUpdated?: string;
  last_updated?: string;

  // Agentic AI & Route Eligibility
  eligibility?: 'DIRECT' | 'PARTIAL' | 'UNSUPPORTED' | string;
  eligibilityReason?: string;
  suitabilityLevel?: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNSUITABLE' | string;
  suitabilityScore?: number;
  routeSupported?: boolean;
  coverageConfidence?: string;
  vehicleSuitabilityConfidence?: string;
  evaluationExplanations?: string[];
  partialBoundary?: string;
  warning?: string;
}

export interface RouteClassification {
  origin_label: string;
  destination_label: string;
  distance_km: number;
  duration_mins: number;
  route_type: 'LOCAL' | 'SHORT_DISTANCE' | 'MEDIUM_DISTANCE' | 'LONG_DISTANCE' | 'INTERCITY' | 'OUTSTATION' | 'AIRPORT_TRANSFER' | string;
  origin_city?: string;
  destination_city?: string;
  is_intercity?: boolean;
  is_outstation?: boolean;
  is_airport_transfer?: boolean;
  classification_reason?: string;
}

export interface MultimodalLeg {
  leg_number: number;
  mode: string;
  provider: string;
  vehicle_type: string;
  from_location: string;
  to_location: string;
  distance_km: number;
  duration_mins: number;
  estimated_fare: number;
  currency_symbol?: string;
  instructions: string;
}

export interface MultimodalOption {
  type: string;
  title: string;
  summary: string;
  total_distance_km: number;
  total_duration_mins: number;
  total_estimated_fare: number;
  currency_symbol?: string;
  transfer_count: number;
  legs: MultimodalLeg[];
  recommendation_note?: string;
}

export interface AgentReasoning {
  headline: string;
  routeClassification: string;
  routeDistanceKm: number;
  auditSummary: string;
  feasibleDirectCount: number;
  excludedCount: number;
  partialCount: number;
  cheapestDirect?: string;
  recommendedDirect?: string;
  rapidoBikeExcluded?: boolean;
  exclusionHighlights?: string[];
}

export interface MarketConditionItem {
  provider: string;
  vehicleType?: string;
  demand_level: 'LOW' | 'NORMAL' | 'SLIGHTLY HIGH' | 'HIGH' | 'VERY HIGH' | string;
  pricing_pressure: string;
  pricing_pressure_score?: number;
  confidence: number;
  confidence_text?: string;
  reason?: string;
  source_type?: string;
  last_updated?: string;
}

export interface ComparisonRecommendations {
  cheapest: string;
  fastest: string;
  mostEfficient: string;
  bestValue: string;
  recommended?: string;
  recommendationReason: string;
  distanceAdvantage: string;
  timeAdvantage: string;
  costAdvantage: string;
}

export interface ComparisonResult {
  distanceKm: number;
  durationMins: number;
  detectedCity: string;
  state?: string;
  country?: string;
  currency?: string;
  currencySymbol?: string;
  isServiceable?: boolean;
  message?: string;
  regionalNotice?: string;
  supportedRegions?: string[];
  surgeRuleName: string;
  straightLineDistance: number;
  detourDistance: number;
  pricingRegime: string;
  fareSpread: number;
  spreadPercentage: number;
  providers: RideProviderDetails[];
  directProviders?: RideProviderDetails[];
  excludedProviders?: RideProviderDetails[];
  partialProviders?: RideProviderDetails[];
  multimodalOption?: MultimodalOption;
  agentReasoning?: AgentReasoning;
  routeClassification?: RouteClassification;
  recommendations: ComparisonRecommendations;
  insights: string[];
  routeHash?: string;
  pickupZone?: string;
  destinationZone?: string;
  marketConditions?: MarketConditionItem[];
}

