"""
Standalone test runner using Python unittest and FastAPI TestClient.
"""

import unittest
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from backend.app.main import app

class TestFastAPIBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_health_check(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("status", data)
        self.assertEqual(data["service"], "Smart Taxi Fare Comparison API")

    def test_02_security_headers(self):
        res = self.client.get("/health")
        self.assertEqual(res.headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(res.headers.get("x-frame-options"), "SAMEORIGIN")

    def test_03_geocode(self):
        res = self.client.get("/api/geocode?q=Connaught+Place")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)

    def test_04_route_fare_calculation(self):
        payload = {
            "pickup": [28.6328, 77.2197],
            "drop": [28.5355, 77.3910],
            "pickupName": "Connaught Place, New Delhi",
            "dropName": "Sector 18, Noida"
        }
        res = self.client.post("/api/route", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertGreater(data["route"]["distance_km"], 0)
        self.assertGreater(len(data["fares"]), 0)
        
        # Verify ML enrichment fields
        fare0 = data["fares"][0]
        self.assertIn("ml_predicted_fare", fare0)
        self.assertIn("prediction_delta", fare0)
        self.assertIn("pricing_regime", fare0)
        self.assertIn("confidence_score", fare0)
        self.assertIn("smart_score", fare0)

    def test_05_fare_compare(self):
        payload = {
            "pickup": "Indira Gandhi Airport",
            "drop": "Cyber Hub Gurgaon",
            "pickup_lat": 28.5562,
            "pickup_lng": 77.1000,
            "drop_lat": 28.4952,
            "drop_lng": 77.0894,
            "distance_km": 14.5,
            "duration_min": 25.0
        }
        res = self.client.post("/api/fare/compare", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertGreater(len(data["fares"]), 0)

    def test_06_fare_predict(self):
        payload = {
            "provider": "Uber",
            "ride_type": "Mini",
            "distance_km": 12.0,
            "duration_min": 30.0,
            "hour_of_day": 18,
            "day_of_week": 4,
            "is_weekend": 0,
            "traffic_density": 1.4,
            "surge_multiplier": 1.2,
            "city": "Delhi"
        }
        res = self.client.post("/api/fare/predict", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        pred = data["prediction"]
        self.assertGreater(pred["predicted_fare"], 0)
        self.assertIn("confidence", pred)

    def test_07_analytics(self):
        res = self.client.get("/api/analytics")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("totalSearches", data)
        self.assertIn("averageSavings", data)
        self.assertIn("topRoutes", data)

    def test_08_booking_redirect(self):
        payload = {
            "provider": "Uber",
            "ride_type": "Go",
            "fare": 320,
            "pickup": "CP",
            "drop": "Noida",
            "city": "Delhi"
        }
        res = self.client.post("/api/redirect", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("redirect_url", data)

    def test_09_ml_clusters(self):
        res = self.client.get("/api/ml/clusters")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(len(data["clusters"]), 3)

    def test_10_ml_performance(self):
        res = self.client.get("/api/ml/model-performance")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertGreater(data["metrics"]["r2_score"], 0.90)


if __name__ == "__main__":
    unittest.main()
