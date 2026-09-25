export type VehicleCategory = 'Cab' | 'Bike' | 'Auto' | 'EV' | 'Robotaxi' | string;

export interface LocationInfo {
  label: string;
  lat: number;
  lng: number;
}

export interface ScoreBreakdown {
  priceScore: number;
  etaScore: number;
  confidenceScore: number;
  reliabilityScore: number;
}

export interface FareVolatility {
  absolute_change: number;
  percentage_change: number;
  change_per_minute: number;
  volatility_score: 'LOW' | 'MODERATE' | 'HIGH';
  price_trend: 'RISING' | 'FALLING' | 'STABLE';
  recent_history: number[];
}

export interface RideProviderDetails {
  provider: string;
  vehicleType: VehicleCategory;
  distanceKm: number;
  etaMinutes: number;

  // Actual calculated fares & ML estimations
  actualFare: number;
  estimatedFare: number;
  predictedFare: number;
  predictionDiff: number;
  predictionDiffPct: number;

  // Currency & Localized formatting
  currency?: string;
  currencySymbol?: string;

  // Machine Learning insights
  surgeMultiplier: number;
  confidence: 'High' | 'Medium' | 'Low';
  confidenceScore: number;
  confidenceLevel: 'High' | 'Medium' | 'Low';
  clusterId: number;
  clusterLabel: string;
  isAnomaly: boolean;
  anomalyReason?: string;

  // Scoring & Efficiency
  smartScore: number;
  scoreBreakdown?: ScoreBreakdown;
  costPerKm: number;
  costPerMin: number;
  efficiencyScore: number;
  recommendationScore: number;

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
  volatility?: FareVolatility;

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

export interface ModelMetadata {
  version: string;
  algorithm: string;
  r2Score: number;
  mae: number;
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
  regionalNotice?: string;
  supportedRegions?: string[];
  surgeRuleName: string;
  straightLineDistance: number;
  detourDistance: number;
  pricingRegime: string;
  fareSpread: number;
  spreadPercentage: number;
  anomalyCount: number;
  providers: RideProviderDetails[];
  recommendations: ComparisonRecommendations;
  insights: string[];
  modelMetadata?: ModelMetadata;
  routeHash?: string;
}

export interface RegressionMetrics {
  mae: number;
  rmse: number;
  mape: number;
  r2: number;
}

export interface ClusteringMetrics {
  optimal_k: number;
  silhouette_score: number;
  silhouette_evaluations: Record<string, number>;
}

export interface AnomalyMetrics {
  contamination: number;
  training_anomalies_detected: number;
  anomaly_rate_percent: number;
}

export interface MLModelPerformance {
  status: string;
  version: string;
  last_trained: string;
  total_training_records: number;
  regression_model: string;
  regression_metrics: RegressionMetrics;
  clustering_metrics: ClusteringMetrics;
  anomaly_metrics: AnomalyMetrics;
  cluster_profiles: Record<string, any>;
  providers_supported: string[];
  vehicle_types_supported: string[];
}
