"""
Automated Test Suite for ML Intelligence System
Tests fare normalization, feature engineering, clustering, regression inference,
anomaly detection, confidence calculations, and edge cases.
"""

import unittest
import numpy as np
import pandas as pd
from ml.inference.normalizer import normalize_fare_record, engineer_features
from ml.inference.predictor import FareIntelligenceEngine


class TestMLPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = FareIntelligenceEngine()

    def test_01_fare_normalization(self):
        """Tests that fare normalization calculates unit economics and components correctly."""
        record = {
            'provider': 'Uber Go',
            'vehicle_type': 'Cab',
            'distance_km': 10.0,
            'duration_min': 25.0,
            'actual_fare': 250.0,
            'base_fare': 50.0,
            'platform_fee': 15.0,
            'toll_fee': 0.0,
            'surge_multiplier': 1.0
        }
        normalized = normalize_fare_record(record)
        self.assertEqual(normalized['fare_per_km'], 25.0)
        self.assertEqual(normalized['fare_per_min'], 10.0)
        self.assertEqual(normalized['actual_fare'], 250.0)
        self.assertGreater(normalized['normalized_fare'], 0.0)

    def test_02_feature_engineering(self):
        """Tests feature extraction for tabular models."""
        df = pd.DataFrame([{
            'distance_km': 12.5,
            'duration_min': 30.0,
            'actual_fare': 285.0,
            'surge_multiplier': 1.4,
            'traffic_condition': 'Heavy',
            'time_of_day': 'Evening Peak',
            'day_of_week': 'Friday',
            'vehicle_type': 'Cab',
            'provider': 'Uber Go'
        }])
        feat_df = engineer_features(df)
        self.assertIn('fare_per_km', feat_df.columns)
        self.assertIn('speed_kmh', feat_df.columns)
        self.assertIn('traffic_level', feat_df.columns)
        self.assertIn('hour_sin', feat_df.columns)
        self.assertIn('hour_cos', feat_df.columns)
        self.assertEqual(feat_df['traffic_level'].iloc[0], 3.5)

    def test_03_supervised_regression_prediction(self):
        """Tests that supervised regression model predicts reasonable expected fares."""
        record = {
            'provider': 'Uber Go',
            'vehicle_type': 'Cab',
            'distance_km': 10.0,
            'duration_min': 25.0,
            'actual_fare': 220.0,
            'base_fare': 50.0,
            'platform_fee': 15.0,
            'toll_fee': 0.0,
            'surge_multiplier': 1.0,
            'traffic_condition': 'Normal',
            'time_of_day': 'Regular',
            'day_of_week': 'Wednesday'
        }
        result = self.engine.predict_provider_fare(record)
        self.assertIn('predicted_fare', result)
        self.assertIn('prediction_diff', result)
        self.assertGreater(result['predicted_fare'], 50.0)
        self.assertLess(result['predicted_fare'], 500.0)

    def test_04_anomaly_detection_normal_vs_extreme(self):
        """Tests that normal fares pass while extreme fare spikes are flagged as anomalies."""
        normal_record = {
            'provider': 'Uber Go',
            'vehicle_type': 'Cab',
            'distance_km': 10.0,
            'duration_min': 25.0,
            'actual_fare': 220.0,
            'base_fare': 50.0,
            'platform_fee': 15.0,
            'surge_multiplier': 1.0,
            'traffic_condition': 'Normal'
        }
        res_normal = self.engine.predict_provider_fare(normal_record)
        self.assertFalse(res_normal['is_anomaly'])

        # Extreme 4x price spike on a short trip
        anomalous_record = {
            'provider': 'Uber Go',
            'vehicle_type': 'Cab',
            'distance_km': 10.0,
            'duration_min': 25.0,
            'actual_fare': 950.0,
            'base_fare': 50.0,
            'platform_fee': 15.0,
            'surge_multiplier': 1.0,
            'traffic_condition': 'Normal'
        }
        res_anomalous = self.engine.predict_provider_fare(anomalous_record)
        self.assertTrue(res_anomalous['is_anomaly'])
        self.assertIn("Unusually high", res_anomalous['anomaly_reason'])

    def test_05_confidence_scoring(self):
        """Tests that confidence scoring properly rates standard vs uncertain trips."""
        conf_high = self.engine.calculate_confidence(distance_km=10.0, duration_min=25.0, provider='Uber Go', osrm_success=True)
        self.assertEqual(conf_high['confidence_level'], 'High')
        self.assertGreaterEqual(conf_high['confidence_score'], 80.0)

        # Non-OSRM fallback with extreme discrepancy
        conf_low = self.engine.calculate_confidence(distance_km=60.0, duration_min=120.0, provider='Unknown', osrm_success=False, diff_pct=80.0)
        self.assertIn(conf_low['confidence_level'], ['Medium', 'Low'])
        self.assertLess(conf_low['confidence_score'], conf_high['confidence_score'])

    def test_06_edge_cases(self):
        """Tests extreme edge cases: very short trip, long highway trip, missing features."""
        short_trip = {
            'provider': 'Rapido Bike',
            'vehicle_type': 'Bike',
            'distance_km': 0.3,
            'duration_min': 2.0,
            'actual_fare': 25.0
        }
        res_short = self.engine.predict_provider_fare(short_trip)
        self.assertGreater(res_short['predicted_fare'], 0.0)

        long_trip = {
            'provider': 'Uber Premier',
            'vehicle_type': 'Cab',
            'distance_km': 55.0,
            'duration_min': 90.0,
            'actual_fare': 1200.0,
            'surge_multiplier': 1.5
        }
        res_long = self.engine.predict_provider_fare(long_trip)
        self.assertGreater(res_long['predicted_fare'], 500.0)


if __name__ == '__main__':
    unittest.main()
