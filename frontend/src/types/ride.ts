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
  recommendations: ComparisonRecommendations;
  insights: string[];
  routeHash?: string;
  pickupZone?: string;
  destinationZone?: string;
  marketConditions?: MarketConditionItem[];
}
