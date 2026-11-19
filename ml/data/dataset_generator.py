"""
Historical Fare Dataset Generator
Generates realistic multi-provider ride-hailing historical dataset for model training and evaluation.
"""

import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Provider rate cards
PROVIDERS_CONFIG = {
    'Bangalore': {
        'Uber Go': {'vehicleType': 'Cab', 'baseFare': 50, 'perKmRate': 14.0, 'perMinRate': 2.0, 'platformFee': 15, 'reliability': 0.95},
        'Uber Premier': {'vehicleType': 'Cab', 'baseFare': 70, 'perKmRate': 18.0, 'perMinRate': 2.5, 'platformFee': 20, 'reliability': 0.98},
        'Rapido Bike': {'vehicleType': 'Bike', 'baseFare': 15, 'perKmRate': 7.0, 'perMinRate': 1.0, 'platformFee': 5, 'reliability': 0.90},
        'Rapido Auto': {'vehicleType': 'Auto', 'baseFare': 28, 'perKmRate': 10.0, 'perMinRate': 1.5, 'platformFee': 10, 'reliability': 0.92},
        'Ola Mini': {'vehicleType': 'Cab', 'baseFare': 48, 'perKmRate': 14.5, 'perMinRate': 2.2, 'platformFee': 15, 'reliability': 0.93},
        'Ola Prime': {'vehicleType': 'Cab', 'baseFare': 65, 'perKmRate': 17.5, 'perMinRate': 2.4, 'platformFee': 18, 'reliability': 0.96},
        'Local Taxi': {'vehicleType': 'Cab', 'baseFare': 60, 'perKmRate': 16.0, 'perMinRate': 0.0, 'platformFee': 0, 'reliability': 0.85}
    },
    'Delhi': {
        'Uber Go': {'vehicleType': 'Cab', 'baseFare': 45, 'perKmRate': 13.5, 'perMinRate': 1.8, 'platformFee': 15, 'reliability': 0.94},
        'Ola Mini': {'vehicleType': 'Cab', 'baseFare': 45, 'perKmRate': 14.0, 'perMinRate': 2.0, 'platformFee': 15, 'reliability': 0.92},
        'Rapido Bike': {'vehicleType': 'Bike', 'baseFare': 15, 'perKmRate': 6.5, 'perMinRate': 1.0, 'platformFee': 5, 'reliability': 0.89},
        'Rapido Auto': {'vehicleType': 'Auto', 'baseFare': 25, 'perKmRate': 9.5, 'perMinRate': 1.4, 'platformFee': 10, 'reliability': 0.91}
    },
    'Mumbai': {
        'Uber Go': {'vehicleType': 'Cab', 'baseFare': 55, 'perKmRate': 15.0, 'perMinRate': 2.2, 'platformFee': 15, 'reliability': 0.95},
        'Ola Mini': {'vehicleType': 'Cab', 'baseFare': 52, 'perKmRate': 15.5, 'perMinRate': 2.3, 'platformFee': 15, 'reliability': 0.93},
        'Local Taxi': {'vehicleType': 'Cab', 'baseFare': 28, 'perKmRate': 18.0, 'perMinRate': 0.0, 'platformFee': 0, 'reliability': 0.90}
    }
}

LOCATIONS = [
    ('Indiranagar, Bangalore', 12.971891, 77.641151),
    ('Koramangala, Bangalore', 12.935192, 77.624480),
    ('Whitefield, Bangalore', 12.9698, 77.7499),
    ('Electronic City, Bangalore', 12.8399, 77.6770),
    ('Majestic, Bangalore', 12.9779, 77.5724),
    ('Kempegowda Airport, Bangalore', 13.1986, 77.7066),
    ('HSR Layout, Bangalore', 12.9116, 77.6388),
    ('Jayanagar, Bangalore', 12.9298, 77.5833),
    ('MG Road, Bangalore', 12.9733, 77.6117),
    ('Connaught Place, Delhi', 28.6315, 77.2167),
    ('Gurgaon Cyber Hub, Delhi', 28.4950, 77.0890),
    ('Bandra West, Mumbai', 19.0596, 72.8295),
    ('Nariman Point, Mumbai', 18.9256, 72.8242)
]

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
TRAFFIC_CONDITIONS = ['Low', 'Normal', 'Moderate', 'Heavy', 'Severe']
WEATHER_CONDITIONS = ['Clear', 'Clear', 'Clear', 'Rainy', 'Foggy']


def generate_synthetic_historical_dataset(n_samples: int = 12000, seed: int = 42) -> pd.DataFrame:
    """Generates synthetic historical fare dataset matching actual ride distributions."""
    random.seed(seed)
    np.random.seed(seed)

    records = []
    base_date = datetime.now() - timedelta(days=90)

    for i in range(n_samples):
        # Pick city and provider
        city = random.choice(list(PROVIDERS_CONFIG.keys()))
        providers_dict = PROVIDERS_CONFIG[city]
        provider_name = random.choice(list(providers_dict.keys()))
        p_cfg = providers_dict[provider_name]

        # Locations
        loc_a = random.choice(LOCATIONS)
        loc_b = random.choice(LOCATIONS)
        while loc_b[0] == loc_a[0]:
            loc_b = random.choice(LOCATIONS)

        # Distance calculation
        # Realistic distance between 1.0 km to 45 km with log-normal distribution
        distance_km = float(np.clip(np.random.lognormal(mean=2.2, sigma=0.7), 1.0, 48.0))

        # Time & Date
        day_idx = random.randint(0, 6)
        day_of_week = DAYS[day_idx]
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        trip_time = base_date + timedelta(days=random.randint(0, 89), hours=hour, minutes=minute)

        # Determine time of day and surge
        if 7 <= hour < 10:
            time_of_day = 'Morning Peak'
            surge_multiplier = round(random.uniform(1.2, 1.6), 2)
            traffic_condition = random.choice(['Moderate', 'Heavy', 'Severe'])
            avg_speed_kmh = random.uniform(12.0, 22.0)
        elif 17 <= hour < 21:
            time_of_day = 'Evening Peak'
            surge_multiplier = round(random.uniform(1.3, 1.8), 2)
            traffic_condition = random.choice(['Heavy', 'Severe', 'Moderate'])
            avg_speed_kmh = random.uniform(10.0, 18.0)
        elif hour >= 23 or hour < 5:
            time_of_day = 'Night'
            surge_multiplier = 1.25
            traffic_condition = random.choice(['Low', 'Normal'])
            avg_speed_kmh = random.uniform(35.0, 50.0)
        else:
            time_of_day = 'Regular'
            surge_multiplier = 1.0
            traffic_condition = random.choice(['Low', 'Normal', 'Moderate'])
            avg_speed_kmh = random.uniform(22.0, 32.0)

        # Vehicle adjustments
        if p_cfg['vehicleType'] == 'Bike':
            avg_speed_kmh *= 1.25
            surge_multiplier = max(1.0, surge_multiplier * 0.9)
        elif p_cfg['vehicleType'] == 'Auto':
            avg_speed_kmh *= 1.05

        duration_min = max(3.0, round((distance_km / avg_speed_kmh) * 60.0, 1))

        # Weather
        weather_condition = random.choice(WEATHER_CONDITIONS)
        if weather_condition == 'Rainy':
            surge_multiplier = round(surge_multiplier * random.uniform(1.15, 1.35), 2)
            duration_min = round(duration_min * 1.2, 1)

        # Toll estimation (airport routes)
        is_airport = 'airport' in loc_a[0].lower() or 'airport' in loc_b[0].lower()
        toll_fee = 120.0 if (is_airport and distance_km > 15) else 0.0

        # Calculate actual base fare with realistic variations
        base_f = p_cfg['baseFare']
        dist_f = distance_km * p_cfg['perKmRate']
        time_f = duration_min * p_cfg['perMinRate']
        plat_f = p_cfg['platformFee']

        raw_fare = (base_f + dist_f + time_f) * surge_multiplier + plat_f + toll_fee
        
        # Add slight natural noise (+- 4%)
        noise = random.uniform(0.96, 1.04)
        actual_fare = round(raw_fare * noise, 2)

        # Inject ~2% deliberate anomalies (extreme surge or pricing glitch) for testing anomaly detector
        is_synthetic_anomaly = False
        if random.random() < 0.025:
            is_synthetic_anomaly = True
            if random.random() < 0.7:
                # Extreme high surge anomaly
                actual_fare = round(actual_fare * random.uniform(2.2, 3.5), 2)
            else:
                # Extreme low glitch anomaly
                actual_fare = round(max(20.0, actual_fare * random.uniform(0.25, 0.45)), 2)

        records.append({
            'provider': provider_name,
            'vehicle_type': p_cfg['vehicleType'],
            'source': loc_a[0],
            'destination': loc_b[0],
            'source_lat': loc_a[1],
            'source_lng': loc_a[2],
            'dest_lat': loc_b[1],
            'dest_lng': loc_b[2],
            'distance_km': round(distance_km, 2),
            'duration_min': duration_min,
            'actual_fare': actual_fare,
            'base_fare': base_f,
            'surge_multiplier': surge_multiplier,
            'platform_fee': plat_f,
            'toll_fee': toll_fee,
            'traffic_condition': traffic_condition,
            'weather_condition': weather_condition,
            'time_of_day': time_of_day,
            'day_of_week': day_of_week,
            'hour': hour,
            'is_anomaly': is_synthetic_anomaly,
            'created_at': trip_time.strftime('%Y-%m-%d %H:%M:%S')
        })

    df = pd.DataFrame(records)
    return df


if __name__ == '__main__':
    out_dir = os.path.join(os.path.dirname(__file__), 'raw')
    os.makedirs(out_dir, exist_ok=True)
    df = generate_synthetic_historical_dataset(12000)
    out_path = os.path.join(out_dir, 'historical_fares.csv')
    df.to_csv(out_path, index=False)
    print(f"Generated {len(df)} historical fare records saved to {out_path}")
