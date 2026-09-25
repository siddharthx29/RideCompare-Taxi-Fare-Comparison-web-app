from typing import Dict, Any
import numpy as np
import pandas as pd


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely casts any value to float, handling None, NaN, and conversion errors."""
    if value is None:
        return default
    try:
        val = float(value)
        return default if np.isnan(val) or np.isinf(val) else val
    except (ValueError, TypeError):
        return default


def normalize_fare_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes a raw single ride quote record, imputing missing financial fields,
    bounding physical limits, and calculating unit economic derivatives.
    """
    distance_km = max(0.1, min(100.0, _safe_float(record.get('distance_km'), 1.0)))
    duration_min = max(1.0, min(300.0, _safe_float(record.get('duration_min'), 5.0)))
    actual_fare = max(0.0, _safe_float(record.get('actual_fare'), 0.0))
    base_fare = max(0.0, _safe_float(record.get('base_fare'), 0.0))
    platform_fee = max(0.0, _safe_float(record.get('platform_fee'), 0.0))
    toll_fee = max(0.0, _safe_float(record.get('toll_fee'), 0.0))
    surge_multiplier = max(1.0, min(5.0, _safe_float(record.get('surge_multiplier'), 1.0)))

    fare_per_km = round(actual_fare / distance_km, 2)
    fare_per_min = round(actual_fare / duration_min, 2)

    variable_fare = max(0.0, actual_fare - (base_fare * surge_multiplier) - platform_fee - toll_fee)
    effective_dist_rate = round(variable_fare / (distance_km + 0.001), 2)
    normalized_fare = round(base_fare + (actual_fare - platform_fee - toll_fee) / surge_multiplier, 2)

    return {
        **record,
        'distance_km': round(distance_km, 2),
        'duration_min': round(duration_min, 1),
        'actual_fare': round(actual_fare, 2),
        'base_fare': round(base_fare, 2),
        'platform_fee': round(platform_fee, 2),
        'toll_fee': round(toll_fee, 2),
        'fare_per_km': fare_per_km,
        'fare_per_min': fare_per_min,
        'effective_dist_rate': effective_dist_rate,
        'normalized_fare': normalized_fare,
        'surge_multiplier': surge_multiplier
    }


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms raw tabular transit data:
    - Handles missing values via median and mode imputation
    - Validates and bounds physical features
    - Engineers continuous unit rates (fare/km, fare/min, speed)
    - Maps ordinal traffic congestion
    - Performs cyclic sin/cos encoding on 24-hour time
    - Encodes weekend indicator and vehicle category
    """
    df = df.copy()

    # Robust numeric conversion and imputation for essential numerical features
    df['distance_km'] = (
        pd.to_numeric(df.get('distance_km', pd.Series(1.0, index=df.index)), errors='coerce')
        .fillna(df.get('distance_km', pd.Series(1.0, index=df.index)).median() if len(df) > 0 and pd.to_numeric(df.get('distance_km'), errors='coerce').notnull().any() else 1.0)
        .clip(lower=0.1, upper=100.0)
        .astype(float)
    )

    df['duration_min'] = (
        pd.to_numeric(df.get('duration_min', pd.Series(5.0, index=df.index)), errors='coerce')
        .fillna(df.get('duration_min', pd.Series(5.0, index=df.index)).median() if len(df) > 0 and pd.to_numeric(df.get('duration_min'), errors='coerce').notnull().any() else 5.0)
        .clip(lower=1.0, upper=300.0)
        .astype(float)
    )

    df['actual_fare'] = (
        pd.to_numeric(df.get('actual_fare', pd.Series(50.0, index=df.index)), errors='coerce')
        .fillna(50.0)
        .clip(lower=10.0, upper=10000.0)
        .astype(float)
    )

    df['surge_multiplier'] = (
        pd.to_numeric(df.get('surge_multiplier', pd.Series(1.0, index=df.index)), errors='coerce')
        .fillna(1.0)
        .clip(lower=1.0, upper=5.0)
        .astype(float)
    )

    # Unit economics & speed kinetics
    df['fare_per_km'] = (df['actual_fare'] / df['distance_km']).round(2)
    df['fare_per_min'] = (df['actual_fare'] / df['duration_min']).round(2)
    df['speed_kmh'] = (df['distance_km'] / (df['duration_min'] / 60.0)).clip(lower=1.0, upper=120.0).round(2)

    # Traffic level ordinal mapping
    traffic_map = {
        'low': 1.0,
        'normal': 2.0,
        'moderate': 2.5,
        'heavy': 3.5,
        'severe': 4.5
    }
    traffic_col = df['traffic_condition'] if 'traffic_condition' in df.columns else pd.Series(['normal'] * len(df), index=df.index)
    df['traffic_level'] = traffic_col.fillna('normal').astype(str).str.lower().map(traffic_map).fillna(2.0)

    # Cyclic hour transformation
    if 'hour' in df.columns:
        hour_val = pd.to_numeric(df['hour'], errors='coerce').fillna(12.0)
    else:
        tod_map = {
            'morning peak': 8.5,
            'evening peak': 18.5,
            'night': 23.5,
            'regular': 14.0,
            'afternoon': 14.0
        }
        tod_col = df['time_of_day'] if 'time_of_day' in df.columns else pd.Series(['regular'] * len(df), index=df.index)
        hour_val = tod_col.fillna('regular').astype(str).str.lower().map(tod_map).fillna(12.0)

    df['hour_val'] = hour_val.clip(lower=0.0, upper=23.9)
    df['hour_sin'] = np.sin(2 * np.pi * df['hour_val'] / 24.0).round(4)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour_val'] / 24.0).round(4)

    # Weekend binary indicator
    weekend_days = {'saturday', 'sunday'}
    dow_col = df['day_of_week'] if 'day_of_week' in df.columns else pd.Series(['monday'] * len(df), index=df.index)
    df['is_weekend'] = dow_col.fillna('monday').astype(str).str.lower().isin(weekend_days).astype(int)

    # Vehicle category ordinal mapping
    vehicle_map = {'bike': 1, 'auto': 2, 'cab': 3}
    veh_col = df['vehicle_type'] if 'vehicle_type' in df.columns else pd.Series(['Cab'] * len(df), index=df.index)
    df['vehicle_category'] = veh_col.fillna('Cab').astype(str).str.lower().map(vehicle_map).fillna(3).astype(int)

    # Provider & vehicle type categorical defaults
    if 'provider' not in df.columns:
        df['provider'] = 'Uber Go'
    else:
        df['provider'] = df['provider'].fillna('Uber Go').astype(str)

    if 'vehicle_type' not in df.columns:
        df['vehicle_type'] = 'Cab'
    else:
        df['vehicle_type'] = df['vehicle_type'].fillna('Cab').astype(str)

    return df
