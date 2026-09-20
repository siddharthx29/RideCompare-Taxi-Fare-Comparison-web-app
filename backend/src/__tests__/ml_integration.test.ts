import assert from 'assert';
import { calculateFaresAndScores } from '../services/pricing';
import { enrichFaresWithML, fetchMLModelPerformance, fetchMLClusters } from '../services/mlClient';
import { RideProviderDetails } from '../services/types';

async function testMLIntegration() {
  // Test 1: Calculate fares and scores with ML enrichment
  const result = await calculateFaresAndScores(
    12.5,
    30.0,
    'Indiranagar, Bangalore',
    'Koramangala, Bangalore',
    77.641,
    12.971,
    77.624,
    12.935,
    true
  );

  assert.ok(result, 'Comparison result should be defined');
  assert.strictEqual(result.distanceKm, 12.5);
  assert.ok(result.providers.length > 0, 'Providers list should not be empty');
  assert.ok(result.pricingRegime, 'Pricing regime should be defined');
  assert.ok(result.fareSpread >= 0, 'Fare spread should be non-negative');

  const firstProvider = result.providers[0];
  assert.ok(firstProvider.actualFare > 0, 'Actual fare must be positive');
  assert.strictEqual(firstProvider.estimatedFare, firstProvider.actualFare);
  assert.ok(firstProvider.predictedFare > 0, 'Predicted fare must be positive');
  assert.ok(firstProvider.confidenceScore >= 30, 'Confidence score should be valid');

  // Test 2: Fetch model performance metadata
  const perf = await fetchMLModelPerformance();
  assert.ok(perf.regression_metrics.r2 > 0.9, 'R2 score should be > 0.9');
  assert.ok(perf.regression_metrics.mae > 0, 'MAE should be > 0');
  assert.ok(perf.clustering_metrics.optimal_k >= 3, 'Optimal K should be >= 3');

  // Test 3: Fetch cluster profiles
  const clusters = await fetchMLClusters();
  assert.ok(clusters.optimal_k, 'Optimal K should exist');
  assert.ok(clusters.cluster_profiles, 'Cluster profiles should exist');

  // Test 4: Extreme edge cases
  const mockProviders: RideProviderDetails[] = [{
    provider: 'Uber Go',
    vehicleType: 'Cab',
    distanceKm: 0.2,
    etaMinutes: 2,
    actualFare: 50,
    estimatedFare: 50,
    predictedFare: 50,
    predictionDiff: 0,
    predictionDiffPct: 0,
    surgeMultiplier: 1.0,
    confidence: 'High',
    confidenceScore: 90,
    confidenceLevel: 'High',
    clusterId: 0,
    clusterLabel: 'Standard',
    isAnomaly: false,
    smartScore: 95,
    costPerKm: 250,
    costPerMin: 25,
    efficiencyScore: 90,
    recommendationScore: 90,
    baseFare: 50,
    distanceFare: 0,
    durationFare: 0,
    platformFee: 0,
    tollEstimate: 0,
    appDeepLink: '',
    webLink: '',
    isCheapest: true,
    isFastest: true,
    isMostEfficient: true,
    isBestValue: true
  }];

  const enriched = await enrichFaresWithML(
    0.2,
    2.0,
    'Point A',
    'Point B',
    1.0,
    'Normal',
    'Regular',
    true,
    mockProviders
  );

  assert.strictEqual(enriched.enrichedProviders.length, 1);
  assert.strictEqual(enriched.enrichedProviders[0].actualFare, 50);

  console.log('✅ All assertion checks passed successfully.');
}

testMLIntegration().catch(err => {
  console.error('❌ Assertion failed:', err);
  process.exit(1);
});
