-- Migration 03: Create historical_fares table for ML training and analytics
CREATE TABLE IF NOT EXISTS historical_fares (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    vehicle_type VARCHAR(30) NOT NULL,
    source TEXT NOT NULL,
    destination TEXT NOT NULL,
    source_lat DOUBLE PRECISION,
    source_lng DOUBLE PRECISION,
    dest_lat DOUBLE PRECISION,
    dest_lng DOUBLE PRECISION,
    distance_km DOUBLE PRECISION NOT NULL,
    duration_min DOUBLE PRECISION NOT NULL,
    actual_fare DOUBLE PRECISION NOT NULL,
    base_fare DOUBLE PRECISION DEFAULT 0.0,
    surge_multiplier DOUBLE PRECISION DEFAULT 1.0,
    platform_fee DOUBLE PRECISION DEFAULT 0.0,
    toll_fee DOUBLE PRECISION DEFAULT 0.0,
    traffic_condition VARCHAR(30) DEFAULT 'Normal',
    weather_condition VARCHAR(30) DEFAULT 'Clear',
    time_of_day VARCHAR(30) DEFAULT 'Regular',
    day_of_week VARCHAR(20) DEFAULT 'Monday',
    fare_per_km DOUBLE PRECISION,
    fare_per_min DOUBLE PRECISION,
    cluster_id INT,
    cluster_label VARCHAR(50),
    is_anomaly BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_historical_fares_provider ON historical_fares(provider);
CREATE INDEX IF NOT EXISTS idx_historical_fares_created_at ON historical_fares(created_at);
