import os
import json
import numpy as np
import pandas as pd
import joblib
from typing import Dict, Any, List, Optional
from ml.inference.normalizer import normalize_fare_record, engineer_features
from ml.training.anomaly_detection import evaluate_anomaly


class FareIntelligenceEngine:
    def __init__(self, models_dir: Optional[str] = None):
        if models_dir is None:
            models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'saved')
        
        self.models_dir = models_dir
        self.loaded = False
        self.regressor = None
        self.kmeans = None
        self.kmeans_scaler = None
        self.iso_forest = None
        self.iso_scaler = None
        self.metadata: Dict[str, Any] = {}

        self.ranking_weights = {
            'price': 0.40,
            'eta': 0.30,
            'confidence': 0.15,
            'reliability': 0.15
        }

        self.load_models()

    def load_models(self) -> bool:
        try:
            reg_path = os.path.join(self.models_dir, 'fare_regressor.joblib')
            kmeans_path = os.path.join(self.models_dir, 'kmeans_cluster.joblib')
            kmeans_scaler_path = os.path.join(self.models_dir, 'kmeans_scaler.joblib')
            iso_path = os.path.join(self.models_dir, 'anomaly_detector.joblib')
            iso_scaler_path = os.path.join(self.models_dir, 'anomaly_scaler.joblib')
            meta_path = os.path.join(self.models_dir, 'model_metadata.json')

            if not all(os.path.exists(p) for p in [reg_path, kmeans_path, kmeans_scaler_path, iso_path, iso_scaler_path, meta_path]):
                self.loaded = False
                return False

            self.regressor = joblib.load(reg_path)
            self.kmeans = joblib.load(kmeans_path)
            self.kmeans_scaler = joblib.load(kmeans_scaler_path)
            self.iso_forest = joblib.load(iso_path)
            self.iso_scaler = joblib.load(iso_scaler_path)

            with open(meta_path, 'r') as f:
                self.metadata = json.load(f)

            self.loaded = True
            return True
        except Exception:
            self.loaded = False
            return False

    def calculate_confidence(
        self,
        distance_km: float,
        duration_min: float,
        provider: str,
        osrm_success: bool = True,
        diff_pct: float = 0.0
    ) -> Dict[str, Any]:
        base_score = float(self.metadata.get('regression_metrics', {}).get('r2', 0.92)) * 80.0

        dist_score = 10.0
        if distance_km < 0.8:
            dist_score = 5.0
        elif distance_km > 35.0:
            dist_score = max(2.0, 10.0 - (distance_km - 35.0) * 0.4)

        routing_score = 10.0 if osrm_success else 4.0

        res_penalty = 0.0
        abs_diff_pct = abs(diff_pct)
        if abs_diff_pct > 40.0:
            res_penalty = min(20.0, (abs_diff_pct - 40.0) * 0.5)

        total_confidence = max(30.0, min(99.0, base_score + dist_score + routing_score - res_penalty))
        total_confidence = round(total_confidence, 1)

        if total_confidence >= 85.0:
            level = "High"
        elif total_confidence >= 65.0:
            level = "Medium"
        else:
            level = "Low"

        return {
            'confidence_score': total_confidence,
            'confidence_level': level
        }

    def predict_provider_fare(
        self,
        provider_record: Dict[str, Any],
        osrm_success: bool = True
    ) -> Dict[str, Any]:
        norm_rec = normalize_fare_record(provider_record)
        df_single = pd.DataFrame([norm_rec])
        df_feat = engineer_features(df_single)

        actual_fare = float(norm_rec['actual_fare'])
        distance_km = float(norm_rec['distance_km'])
        duration_min = float(norm_rec['duration_min'])
        provider = str(norm_rec.get('provider', 'Unknown'))
        vehicle_type = str(norm_rec.get('vehicle_type', 'Cab'))

        if not self.loaded:
            est_fare = round(actual_fare * 0.98, 2)
            cluster_id = 0
            cluster_label = "Standard Transit"
            is_anomaly = False
            anomaly_reason = "Model in fallback mode"
            conf = {'confidence_score': 85.0, 'confidence_level': 'Medium'}
        else:
            cluster_features = [
                'distance_km', 'duration_min', 'actual_fare',
                'fare_per_km', 'fare_per_min', 'surge_multiplier', 'traffic_level'
            ]
            X_cluster = df_feat[cluster_features]
            X_cluster_scaled = self.kmeans_scaler.transform(X_cluster)
            cluster_id = int(self.kmeans.predict(X_cluster_scaled)[0])
            
            cluster_profiles = self.metadata.get('cluster_profiles', {})
            profile = cluster_profiles.get(str(cluster_id), {})
            cluster_label = profile.get('label', f'Pricing Regime {cluster_id}')

            df_feat['cluster_id'] = cluster_id
            num_cols = self.metadata.get('regression_features', {}).get('numerical', [
                'distance_km', 'duration_min', 'surge_multiplier', 'traffic_level',
                'hour_sin', 'hour_cos', 'is_weekend', 'cluster_id'
            ])
            cat_cols = self.metadata.get('regression_features', {}).get('categorical', ['provider', 'vehicle_type'])
            
            X_reg = df_feat[num_cols + cat_cols]
            pred_val = float(self.regressor.predict(X_reg)[0])
            est_fare = max(15.0, round(pred_val, 2))

            is_anomaly, anomaly_score, anomaly_reason = evaluate_anomaly(
                self.iso_forest,
                self.iso_scaler,
                norm_rec,
                predicted_fare=est_fare,
                actual_fare=actual_fare
            )

            diff = actual_fare - est_fare
            diff_pct = (diff / max(1.0, est_fare)) * 100.0
            conf = self.calculate_confidence(distance_km, duration_min, provider, osrm_success, diff_pct)

        pred_diff = round(actual_fare - est_fare, 2)
        pred_diff_pct = round((pred_diff / max(1.0, est_fare)) * 100.0, 1)

        return {
            **norm_rec,
            'predicted_fare': est_fare,
            'prediction_diff': pred_diff,
            'prediction_diff_pct': pred_diff_pct,
            'confidence_score': conf['confidence_score'],
            'confidence_level': conf['confidence_level'],
            'cluster_id': cluster_id,
            'cluster_label': cluster_label,
            'is_anomaly': is_anomaly,
            'anomaly_reason': anomaly_reason
        }

    def predict_fare(
        self,
        provider: str = "Uber",
        ride_type: str = "Mini",
        distance_km: float = 10.0,
        duration_min: float = 20.0,
        hour_of_day: int = 14,
        day_of_week: int = 2,
        is_weekend: int = 0,
        traffic_density: float = 1.0,
        surge_multiplier: float = 1.0,
        city: str = "Delhi"
    ) -> Dict[str, Any]:
        raw_fare = 50.0 + (distance_km * 14.0) + (duration_min * 2.0) * surge_multiplier
        rec = {
            "provider": provider,
            "vehicle_type": ride_type,
            "distance_km": distance_km,
            "duration_min": duration_min,
            "actual_fare": round(raw_fare, 2),
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "traffic_density": traffic_density,
            "surge_multiplier": surge_multiplier,
            "city": city
        }
        res = self.predict_provider_fare(rec)
        res["confidence"] = res["confidence_level"]
        res["pricing_regime"] = res["cluster_label"]
        res["smart_score"] = round(max(50.0, min(98.0, 95.0 - (res["prediction_diff_pct"] * 0.4))), 1)
        return res

    def rank_and_compare_providers(
        self,
        provider_records: List[Dict[str, Any]],
        osrm_success: bool = True
    ) -> Dict[str, Any]:
        enriched_providers = []
        for p in provider_records:
            enriched_providers.append(self.predict_provider_fare(p, osrm_success=osrm_success))

        if not enriched_providers:
            return {'providers': [], 'insights': {}, 'best_provider': None}

        min_fare = min(p['actual_fare'] for p in enriched_providers)
        max_fare = max(p['actual_fare'] for p in enriched_providers)
        min_eta = min(p.get('eta_minutes', 10) for p in enriched_providers)
        max_eta = max(p.get('eta_minutes', 10) for p in enriched_providers)

        w = self.ranking_weights
        for p in enriched_providers:
            price_score = 100.0 if max_fare == min_fare else ((max_fare - p['actual_fare']) / (max_fare - min_fare)) * 100.0
            eta = p.get('eta_minutes', 10)
            eta_score = 100.0 if max_eta == min_eta else ((max_eta - eta) / (max_eta - min_eta)) * 100.0
            conf_score = p['confidence_score']
            rel_score = 95.0 if 'Premier' in p['provider'] else (90.0 if 'Uber' in p['provider'] or 'Ola' in p['provider'] else 85.0)

            smart_score = round(
                (w['price'] * price_score) +
                (w['eta'] * eta_score) +
                (w['confidence'] * conf_score) +
                (w['reliability'] * rel_score),
                1
            )
            p['smart_score'] = smart_score
            p['score_breakdown'] = {
                'price_score': round(price_score, 1),
                'eta_score': round(eta_score, 1),
                'confidence_score': round(conf_score, 1),
                'reliability_score': round(rel_score, 1)
            }

        cheapest = min(enriched_providers, key=lambda x: x['actual_fare'])
        fastest = min(enriched_providers, key=lambda x: x.get('eta_minutes', 999))
        highest_score = max(enriched_providers, key=lambda x: x['smart_score'])

        for p in enriched_providers:
            p['is_cheapest'] = (p['provider'] == cheapest['provider'])
            p['is_fastest'] = (p['provider'] == fastest['provider'])
            p['is_best_value'] = (p['provider'] == highest_score['provider'])

        fare_spread = round(max_fare - min_fare, 2)
        spread_pct = round((fare_spread / max(1.0, min_fare)) * 100.0, 1) if min_fare > 0 else 0.0

        insights = {
            'cheapest_provider': cheapest['provider'],
            'lowest_fare': cheapest['actual_fare'],
            'fastest_provider': fastest['provider'],
            'best_value_provider': highest_score['provider'],
            'fare_spread': fare_spread,
            'spread_percentage': spread_pct,
            'anomaly_count': sum(1 for p in enriched_providers if p['is_anomaly']),
            'current_pricing_regime': enriched_providers[0]['cluster_label'] if enriched_providers else 'Normal'
        }

        return {
            'providers': enriched_providers,
            'insights': insights,
            'best_provider': highest_score['provider']
        }
