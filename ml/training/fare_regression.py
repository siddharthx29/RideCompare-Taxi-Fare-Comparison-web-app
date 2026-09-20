"""
Supervised Fare Regression Module
Trains and compares Random Forest Regressor and Gradient Boosting Regressor for expected fare prediction.
"""

from typing import Dict, Any, Tuple, List
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from ml.evaluation.evaluate_metrics import calculate_regression_metrics

# Categorical and numerical features for regression
NUMERICAL_FEATURES = [
    'distance_km',
    'duration_min',
    'surge_multiplier',
    'traffic_level',
    'hour_sin',
    'hour_cos',
    'is_weekend',
    'cluster_id'
]

CATEGORICAL_FEATURES = [
    'provider',
    'vehicle_type'
]


def train_and_compare_regressors(df: pd.DataFrame) -> Tuple[Pipeline, Dict[str, Any], Dict[str, Any]]:
    """
    Fits Random Forest vs Gradient Boosting models on train split, evaluates on test split,
    and returns the best performing model pipeline.
    """
    print("\n--- Training Supervised Fare Regression Models ---")

    # Filter out anomalous extreme records from baseline training data to avoid regression distortion
    clean_df = df[df.get('is_anomaly', False) == False].copy()
    if len(clean_df) < 500:
        clean_df = df.copy()

    X = clean_df[NUMERICAL_FEATURES + CATEGORICAL_FEATURES]
    y = clean_df['actual_fare'].values

    # Train / Test split (80% train, 20% test) with fixed random seed
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42)

    # Preprocessing ColumnTransformer
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', 'passthrough', NUMERICAL_FEATURES),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), CATEGORICAL_FEATURES)
        ]
    )

    # 1. Random Forest Regressor
    rf_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1))
    ])
    print("Fitting Random Forest Regressor...")
    rf_pipeline.fit(X_train, y_train)
    rf_preds = rf_pipeline.predict(X_test)
    rf_metrics = calculate_regression_metrics(y_test, rf_preds)
    print(f"  Random Forest -> MAE: Rs.{rf_metrics['mae']}, RMSE: Rs.{rf_metrics['rmse']}, MAPE: {rf_metrics['mape']}%, R2: {rf_metrics['r2']}")

    # 2. Gradient Boosting Regressor
    gb_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', GradientBoostingRegressor(n_estimators=120, max_depth=6, learning_rate=0.08, random_state=42))
    ])
    print("Fitting Gradient Boosting Regressor...")
    gb_pipeline.fit(X_train, y_train)
    gb_preds = gb_pipeline.predict(X_test)
    gb_metrics = calculate_regression_metrics(y_test, gb_preds)
    print(f"  Gradient Boosting -> MAE: Rs.{gb_metrics['mae']}, RMSE: Rs.{gb_metrics['rmse']}, MAPE: {gb_metrics['mape']}%, R2: {gb_metrics['r2']}")

    # Select best model based on higher R2 score and lower MAE
    if gb_metrics['r2'] >= rf_metrics['r2']:
        best_name = "Gradient Boosting Regressor"
        best_pipeline = gb_pipeline
        best_metrics = gb_metrics
    else:
        best_name = "Random Forest Regressor"
        best_pipeline = rf_pipeline
        best_metrics = rf_metrics

    print(f"Selected Best Model: {best_name} (R2 = {best_metrics['r2']})")

    comparison_results = {
        'selected_model': best_name,
        'metrics': best_metrics,
        'comparison': {
            'random_forest': rf_metrics,
            'gradient_boosting': gb_metrics
        },
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'features': {
            'numerical': NUMERICAL_FEATURES,
            'categorical': CATEGORICAL_FEATURES
        }
    }

    return best_pipeline, best_metrics, comparison_results
