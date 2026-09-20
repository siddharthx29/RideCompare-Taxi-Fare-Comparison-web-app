"""
K-Means Clustering Module (Unsupervised Learning)
Discovers underlying pricing regimes and patterns across fare observations.
Calculates Silhouette Scores across K values to determine the optimal number of clusters.
"""

from typing import Dict, Any, Tuple, List
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import joblib


# Features used for discovering pricing regimes
CLUSTER_FEATURES = [
    'distance_km',
    'duration_min',
    'actual_fare',
    'fare_per_km',
    'fare_per_min',
    'surge_multiplier',
    'traffic_level'
]


def evaluate_optimal_k(X_scaled: np.ndarray, k_range: range = range(3, 7), sample_size: int = 4000) -> Dict[int, float]:
    """
    Evaluates Silhouette Score across candidate K values to pick the optimal cluster count.
    """
    scores = {}
    
    # Subsample if dataset is large for silhouette computation efficiency
    if len(X_scaled) > sample_size:
        indices = np.random.RandomState(42).choice(len(X_scaled), sample_size, replace=False)
        X_eval = X_scaled[indices]
    else:
        X_eval = X_scaled

    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        eval_labels = labels[indices] if len(X_scaled) > sample_size else labels
        score = silhouette_score(X_eval, eval_labels)
        scores[k] = round(float(score), 4)
        print(f"  K={k} -> Silhouette Score: {scores[k]:.4f}")

    return scores


def interpret_clusters(kmeans: KMeans, scaler: StandardScaler, df_features: pd.DataFrame, cluster_labels: np.ndarray) -> Dict[int, Dict[str, Any]]:
    """
    Analyzes cluster centroids in the original feature space and generates human-readable regime descriptions.
    """
    df_temp = df_features.copy()
    df_temp['cluster'] = cluster_labels

    cluster_profiles = {}
    grouped = df_temp.groupby('cluster')

    for c_id, group in grouped:
        avg_fare = group['actual_fare'].mean()
        avg_fare_km = group['fare_per_km'].mean()
        avg_surge = group['surge_multiplier'].mean()
        avg_traffic = group['traffic_level'].mean()
        avg_dist = group['distance_km'].mean()
        avg_speed = group['speed_kmh'].mean() if 'speed_kmh' in group else 25.0

        # Heuristic interpretation based on centroids
        if avg_surge > 1.35 or avg_fare_km > 32.0:
            label = "Peak Hour Surge"
            desc = "High surge multiplier driven by peak transit hours or weather conditions."
            tag = "surge"
        elif avg_traffic >= 3.2 or (avg_speed < 16.0 and avg_dist > 5.0):
            label = "High Traffic Congestion"
            desc = "Elevated travel duration and congestion leading to increased per-minute costs."
            tag = "traffic"
        elif avg_dist > 25.0:
            label = "Long-Distance Transit"
            desc = "Extended highway routes with high baseline fares and lower per-km marginal rates."
            tag = "long_distance"
        elif avg_fare_km < 16.0 or avg_fare < 120.0:
            label = "Economy / Short Trip"
            desc = "Short distance or high-efficiency trips under standard non-surge conditions."
            tag = "economy"
        else:
            label = "Standard City Transit"
            desc = "Typical urban transit rates with standard traffic and base pricing."
            tag = "standard"

        cluster_profiles[int(c_id)] = {
            'cluster_id': int(c_id),
            'label': label,
            'tag': tag,
            'description': desc,
            'size': int(len(group)),
            'percentage': round(float(len(group) / len(df_temp) * 100), 1),
            'avg_fare': round(float(avg_fare), 2),
            'avg_fare_per_km': round(float(avg_fare_km), 2),
            'avg_surge': round(float(avg_surge), 2),
            'avg_traffic_level': round(float(avg_traffic), 2),
            'avg_distance_km': round(float(avg_dist), 2)
        }

    return cluster_profiles


def train_kmeans_pipeline(df: pd.DataFrame) -> Tuple[KMeans, StandardScaler, Dict[str, Any]]:
    """
    Fits K-Means clustering pipeline with automatic K selection and cluster profiling.
    """
    print("\n--- Training K-Means Clustering Model (Unsupervised) ---")
    
    # Feature extraction
    X = df[CLUSTER_FEATURES].copy().fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Evaluate Silhouette Scores
    silhouette_dict = evaluate_optimal_k(X_scaled, k_range=range(3, 7))
    optimal_k = max(silhouette_dict, key=silhouette_dict.get)
    best_silhouette = silhouette_dict[optimal_k]
    print(f"Optimal K selected: {optimal_k} with Silhouette Score: {best_silhouette:.4f}")

    # Fit final K-Means model
    kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=15)
    cluster_labels = kmeans.fit_predict(X_scaled)

    # Generate cluster profiles
    profiles = interpret_clusters(kmeans, scaler, df, cluster_labels)

    metadata = {
        'optimal_k': optimal_k,
        'silhouette_score': best_silhouette,
        'silhouette_evaluations': silhouette_dict,
        'features': CLUSTER_FEATURES,
        'cluster_profiles': profiles
    }

    return kmeans, scaler, metadata
