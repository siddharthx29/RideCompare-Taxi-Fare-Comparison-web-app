export type VehicleCategory = 'Cab' | 'Bike' | 'Auto' | 'EV' | 'Robotaxi' | string;

export interface LocationInfo {
  label: string;
  lat: number;
  lng: number;
  address?: Record<string, string>;
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
}
