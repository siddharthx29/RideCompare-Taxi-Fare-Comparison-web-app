"""
Anomaly Detection Module
Uses Isolation Forest and Statistical Residual Bounds to identify anomalous or irregular fare quotes.
"""

from typing import Dict, Any, Tuple, List
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


ANOMALY_FEATURES = [
    'distance_km',
    'duration_min',
    'actual_fare',
    'fare_per_km',
    'fare_per_min',
    'surge_multiplier'
]


def train_anomaly_detector(df: pd.DataFrame, contamination: float = 0.03) -> Tuple[IsolationForest, StandardScaler, Dict[str, Any]]:
    """
    Fits an Isolation Forest anomaly detector on standardized multivariate pricing features.
    """
    print("\n--- Training Isolation Forest Anomaly Detector ---")

    X = df[ANOMALY_FEATURES].copy().fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    iso_forest = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=42,
        n_jobs=-1
    )
    iso_forest.fit(X_scaled)

    # Predict anomalies on dataset to verify rate
    preds = iso_forest.predict(X_scaled)  # -1 for anomaly, 1 for normal
    anomaly_count = int((preds == -1).sum())
    anomaly_rate = round(float(anomaly_count / len(X) * 100), 2)
    print(f"Detected {anomaly_count} anomalies in historical training set ({anomaly_rate}%)")

    metadata = {
        'contamination': contamination,
        'features': ANOMALY_FEATURES,
        'training_anomalies_detected': anomaly_count,
        'anomaly_rate_percent': anomaly_rate
    }

    return iso_forest, scaler, metadata


def evaluate_anomaly(
    iso_forest: IsolationForest,
    scaler: StandardScaler,
    feature_dict: Dict[str, Any],
    predicted_fare: float,
    actual_fare: float
) -> Tuple[bool, float, str]:
    """
    Evaluates whether a real-time fare observation is anomalous.
    Combines Isolation Forest multivariate score with regression residual z-score.
    """
    vec = pd.DataFrame([{
        'distance_km': float(feature_dict.get('distance_km', 1.0)),
        'duration_min': float(feature_dict.get('duration_min', 5.0)),
        'actual_fare': float(actual_fare),
        'fare_per_km': float(feature_dict.get('fare_per_km', actual_fare / max(0.1, feature_dict.get('distance_km', 1.0)))),
        'fare_per_min': float(feature_dict.get('fare_per_min', actual_fare / max(1.0, feature_dict.get('duration_min', 5.0)))),
        'surge_multiplier': float(feature_dict.get('surge_multiplier', 1.0))
    }], columns=ANOMALY_FEATURES)

    vec_scaled = scaler.transform(vec)
    iso_pred = iso_forest.predict(vec_scaled)[0] # -1 = anomaly, 1 = normal
    anomaly_score = float(-iso_forest.score_samples(vec_scaled)[0]) # higher = more anomalous

    # Regression residual deviation
    diff = actual_fare - predicted_fare
    diff_pct = (diff / max(1.0, predicted_fare)) * 100.0

    is_anomaly = False
    reason = ""

    # Flag if Isolation Forest votes anomaly OR extreme residual difference (>65% or <-50%)
    if iso_pred == -1 or diff_pct > 65.0 or diff_pct < -50.0:
        is_anomaly = True
        if diff > 0:
            reason = f"Unusually high fare (+{round(diff_pct)}% vs ML estimated baseline). Possible acute surge or high congestion."
        else:
            reason = f"Unusually low fare ({round(diff_pct)}% vs ML estimated baseline). High promotional or off-peak discount."
    else:
        reason = "Within standard expected pricing envelope."

    return is_anomaly, round(anomaly_score, 3), reason
