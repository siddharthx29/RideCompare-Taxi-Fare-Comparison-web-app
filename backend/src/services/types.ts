export interface RideProviderDetails {
  provider: string;
  vehicleType: 'Cab' | 'Bike' | 'Auto';
  distanceKm: number;
  etaMinutes: number;
  
  // Actual vs ML Estimated Fares
  actualFare: number;
  estimatedFare: number; // alias for actualFare to maintain 100% backward compatibility
  predictedFare: number;
  predictionDiff: number;
  predictionDiffPct: number;
  
  // Machine Learning Attributes
  surgeMultiplier: number;
  confidence: 'High' | 'Medium' | 'Low';
  confidenceScore: number;
  confidenceLevel: 'High' | 'Medium' | 'Low';
  clusterId: number;
  clusterLabel: string;
  isAnomaly: boolean;
  anomalyReason?: string;
  
  // Transparent Smart Scoring
  smartScore: number;
  scoreBreakdown?: {
    priceScore: number;
    etaScore: number;
    confidenceScore: number;
    reliabilityScore: number;
  };

  // Efficiency metrics
  costPerKm: number;
  costPerMin: number;
  efficiencyScore: number;
  recommendationScore: number;

  // Detailed components
  baseFare: number;
  distanceFare: number;
  durationFare: number;
  platformFee: number;
  tollEstimate: number;
  appDeepLink: string;
  webLink: string;

  // Visual highlights
  isCheapest: boolean;
  isFastest: boolean;
  isMostEfficient: boolean;
  isBestValue: boolean;
}

export interface ComparisonResult {
  distanceKm: number;
  durationMins: number;
  detectedCity: string;
  surgeRuleName: string;
  straightLineDistance: number;
  detourDistance: number;
  pricingRegime: string;
  fareSpread: number;
  spreadPercentage: number;
  anomalyCount: number;
  providers: RideProviderDetails[];
  recommendations: {
    cheapest: string;
    fastest: string;
    mostEfficient: string;
    bestValue: string;
    recommendationReason: string;
    distanceAdvantage: string;
    timeAdvantage: string;
    costAdvantage: string;
  };
  insights: string[];
  modelMetadata?: {
    version: string;
    algorithm: string;
    r2Score: number;
    mae: number;
  };
}

export interface MLModelPerformance {
  status: string;
  version: string;
  last_trained: string;
  total_training_records: number;
  regression_model: string;
  regression_metrics: {
    mae: number;
    rmse: number;
    mape: number;
    r2: number;
  };
  regression_comparison?: any;
  clustering_metrics: {
    optimal_k: number;
    silhouette_score: number;
    silhouette_evaluations: Record<string, number>;
  };
  anomaly_metrics: {
    contamination: number;
    training_anomalies_detected: number;
    anomaly_rate_percent: number;
  };
  cluster_profiles: Record<string, any>;
  providers_supported: string[];
  vehicle_types_supported: string[];
}
