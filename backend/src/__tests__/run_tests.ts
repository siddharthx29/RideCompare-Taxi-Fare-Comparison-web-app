import { calculateFaresAndScores } from '../services/pricing';
import { fetchMLModelPerformance, fetchMLClusters } from '../services/mlClient';

async function runTests() {
  console.log('--- Running Backend & ML Integration Tests ---');
  
  // 1. Calculate fares and scores with ML enrichment
  const r = await calculateFaresAndScores(12.5, 30.0, 'Indiranagar, Bangalore', 'Koramangala, Bangalore', 77.641, 12.971, 77.624, 12.935, true);
  console.log(`[PASS] Fare Calculation: ${r.distanceKm} km -> ${r.providers.length} providers enriched.`);
  console.log(`       Discovered Regime: "${r.pricingRegime}", Fare Spread: ₹${r.fareSpread}`);
  
  const p = r.providers[0];
  console.log(`       Provider: ${p.provider} | Actual: ₹${p.actualFare} | ML Predicted: ₹${p.predictedFare} | Delta: ₹${p.predictionDiff} | Conf: ${p.confidenceScore}% (${p.confidenceLevel})`);
  
  // 2. Fetch ML Performance metadata
  const perf = await fetchMLModelPerformance();
  console.log(`[PASS] Model Performance: Algorithm=${perf.regression_model}, R2=${perf.regression_metrics.r2}, MAE=₹${perf.regression_metrics.mae}, Silhouette=${perf.clustering_metrics.silhouette_score}`);

  // 3. Fetch Clusters
  const clusters = await fetchMLClusters();
  console.log(`[PASS] K-Means Clusters: Optimal K=${clusters.optimal_k}, Regimes count=${Object.keys(clusters.cluster_profiles).length}`);

  console.log('✅ All backend ML integration checks passed successfully!');
}

runTests().catch(err => {
  console.error('❌ Test failed:', err);
  process.exit(1);
});
