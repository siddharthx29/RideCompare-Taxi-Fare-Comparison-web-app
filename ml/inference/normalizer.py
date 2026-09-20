from typing import Dict, Any
import numpy as np
import pandas as pd


def normalize_fare_record(record: Dict[str, Any]) -> Dict[str, Any]:
    distance_km = max(0.1, float(record.get('distance_km', 1.0)))
    duration_min = max(1.0, float(record.get('duration_min', 5.0)))
    actual_fare = float(record.get('actual_fare', 0.0))
    base_fare = float(record.get('base_fare', 0.0))
    platform_fee = float(record.get('platform_fee', 0.0))
    toll_fee = float(record.get('toll_fee', 0.0))
    surge_multiplier = max(1.0, float(record.get('surge_multiplier', 1.0)))

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
        'fare_per_km': fare_per_km,
        'fare_per_min': fare_per_min,
        'effective_dist_rate': effective_dist_rate,
        'normalized_fare': normalized_fare,
        'surge_multiplier': surge_multiplier
    }


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if 'distance_km' not in df.columns:
        df['distance_km'] = 1.0
    if 'duration_min' not in df.columns:
        df['duration_min'] = 5.0
    if 'actual_fare' not in df.columns:
        df['actual_fare'] = 50.0
    if 'surge_multiplier' not in df.columns:
        df['surge_multiplier'] = 1.0

    df['distance_km'] = df['distance_km'].astype(float).clip(lower=0.1)
    df['duration_min'] = df['duration_min'].astype(float).clip(lower=1.0)
    df['actual_fare'] = df['actual_fare'].astype(float).clip(lower=10.0)
    df['surge_multiplier'] = df['surge_multiplier'].astype(float).fillna(1.0).clip(lower=1.0)

    df['fare_per_km'] = (df['actual_fare'] / df['distance_km']).round(2)
    df['fare_per_min'] = (df['actual_fare'] / df['duration_min']).round(2)
    df['speed_kmh'] = ((df['distance_km'] / (df['duration_min'] / 60.0))).clip(upper=120.0).round(2)

    traffic_map = {
        'low': 1.0,
        'normal': 2.0,
        'moderate': 2.5,
        'heavy': 3.5,
        'severe': 4.5
    }
    traffic_col = df['traffic_condition'] if 'traffic_condition' in df.columns else pd.Series(['normal'] * len(df))
    df['traffic_level'] = traffic_col.astype(str).str.lower().map(traffic_map).fillna(2.0)

    if 'hour' in df.columns:
        df['hour_val'] = df['hour'].astype(float)
    else:
        tod_map = {
            'morning peak': 8.5,
            'evening peak': 18.5,
            'night': 23.5,
            'regular': 14.0,
            'afternoon': 14.0
        }
        tod_col = df['time_of_day'] if 'time_of_day' in df.columns else pd.Series(['regular'] * len(df))
        df['hour_val'] = tod_col.astype(str).str.lower().map(tod_map).fillna(12.0)

    df['hour_sin'] = np.sin(2 * np.pi * df['hour_val'] / 24.0)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour_val'] / 24.0)

    weekend_days = {'saturday', 'sunday'}
    dow_col = df['day_of_week'] if 'day_of_week' in df.columns else pd.Series(['monday'] * len(df))
    df['is_weekend'] = dow_col.astype(str).str.lower().isin(weekend_days).astype(int)

    vehicle_map = {'bike': 1, 'auto': 2, 'cab': 3}
    veh_col = df['vehicle_type'] if 'vehicle_type' in df.columns else pd.Series(['Cab'] * len(df))
    df['vehicle_category'] = veh_col.astype(str).str.lower().map(vehicle_map).fillna(3)

    if 'provider' not in df.columns:
        df['provider'] = 'Uber Go'
    if 'vehicle_type' not in df.columns:
        df['vehicle_type'] = 'Cab'

    return df
