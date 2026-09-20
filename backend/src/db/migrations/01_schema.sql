-- Migration 01: Setup initial tables

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS searches (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    destination TEXT NOT NULL,
    source_lat DOUBLE PRECISION,
    source_lng DOUBLE PRECISION,
    dest_lat DOUBLE PRECISION,
    dest_lng DOUBLE PRECISION,
    distance_km DOUBLE PRECISION,
    duration_min DOUBLE PRECISION,
    cheapest_provider VARCHAR(50),
    fastest_provider VARCHAR(50),
    best_provider VARCHAR(50),
    selected_provider VARCHAR(50), -- Nullable, set when clicked
    savings DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analytics (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    clicks INT DEFAULT 0,
    redirects INT DEFAULT 0,
    fare DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
