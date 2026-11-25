# RideCompare — Real-Time Dynamic Pricing & Demand Intelligence System

## 1. Architecture Overview

RideCompare's **Dynamic Pricing & Demand Intelligence** engine provides real-time, independent estimation of current market demand pressure across ride providers (Uber, Ola, Rapido, Local Taxis, etc.) without calculating or displaying fabricated exact prices.

```
                    +------------------------------------------+
                    |           Client / Frontend              |
                    | (React 19 + TypeScript + Vite + Tailwind)|
                    +--------------------+---------------------+
                                         |
                       GET /api/pricing-pressure
                       POST /api/route (enriched comparison)
                                         v
                    +------------------------------------------+
                    |          FastAPI Backend Service         |
                    +--------------------+---------------------+
                                         |
     +-----------------------------------+-----------------------------------+
     |                                   |                                   |
     v                                   v                                   v
+------------------+           +--------------------+              +--------------------+
|  Geo-Spatial H3  |           | Dynamic Pricing    |              |  Time-Decayed DB   |
|  Discretization  |           | Demand Engine      |              |  Observations      |
| (Uber H3 Res 7/8)|           | (5-Level Fallback) |              | (SQLite/PostgreSQL)|
+------------------+           +---------+----------+              +--------------------+
                                         |
                         +---------------+---------------+
                         |                               |
                         v                               v
              +----------------------+       +----------------------+
              | Level 1: Provider    |       | Level 2: ML Model    |
              | Authorized Signals   |       | Gradient Boosting /  |
              | (When API Authorized)|       | Random Forest (0-4)  |
              +----------------------+       +----------------------+
                         |                               |
                         +---------------+---------------+
                                         |
                         +---------------+---------------+
                         |                               |
                         v                               v
              +----------------------+       +----------------------+
              | Level 3: Statistical |       | Level 4: Heuristic   |
              | Time-Decayed Model   |       | Time/Traffic Model   |
              +----------------------+       +----------------------+
                                         |
                                         v
                             +-----------------------+
                             | Level 5: Insufficient |
                             | Data ("Limited data") |
                             +-----------------------+
```

### Core Design Principles:
1. **No Fabricated Fares**: The system does NOT output exact prices like `Uber = ₹245` for demand estimation. When legitimate provider APIs supply an authorized quote, that fare is displayed alongside the demand intelligence indicator.
2. **Standardized Pricing Pressure Scale**: Normalized to a 0–4 continuous scale converted to 5 human-readable levels: `LOW`, `NORMAL`, `SLIGHTLY HIGH`, `HIGH`, `VERY HIGH`.
3. **Transparent Methodology**: Discloses that RideCompare estimates pricing pressure independently using available geographic, traffic, and multi-horizon request signals, without claiming to know internal proprietary surge algorithms.
4. **Geo-Spatial Discretization**: Partitioned using Uber H3 hexagon cells (resolution 7, ~1.2 km edge length) so adjacent zones can have distinct demand conditions simultaneously.
5. **Continuous Learning**: Ingests route queries and pricing snapshots asynchronously into `demand_observations` table for scheduled retraining.

---

## 2. Standardized Pricing Pressure Scale

Thresholds are configurable in [`DEFAULT_PRESSURE_THRESHOLDS`](file:///c:/Users/HP/Desktop/Taxi-Fare-Comparison-web-app-master/Taxi-Fare-Comparison-web-app-master/backend/app/services/demand_intelligence.py):

| Internal Score Range | Demand Level | Indicator | Human-Readable Condition Wording |
|---|---|---|---|
| `0.0 – 0.5` | **LOW** | 🟡 Yellow / Sky | *"Low demand conditions detected. Pricing likely at baseline."* |
| `0.5 – 1.5` | **NORMAL** | 🟢 Green | *"Demand currently appears normal. Standard market conditions."* |
| `1.5 – 2.5` | **SLIGHTLY HIGH** | 🟠 Orange / Amber | *"Moderate demand detected. Pricing may be slightly elevated."* |
| `2.5 – 3.5` | **HIGH** | 🔴 Red | *"High demand conditions detected. Pricing may be elevated."* |
| `3.5 – 4.0` | **VERY HIGH** | 🔴 Dark Red / Rose | *"Very high demand conditions detected. High pricing pressure across zone."* |

---

## 3. Database Schema

The database model is defined in [`DemandObservation`](file:///c:/Users/HP/Desktop/Taxi-Fare-Comparison-web-app-master/Taxi-Fare-Comparison-web-app-master/backend/app/models/db_models.py):

```sql
CREATE TABLE demand_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    provider VARCHAR(50) NOT NULL,
    pickup_zone VARCHAR(64) NOT NULL,
    destination_zone VARCHAR(64),
    ride_category VARCHAR(30) DEFAULT 'Cab',
    observed_fare_if_available FLOAT,
    observed_demand_signal FLOAT,
    observed_supply_signal FLOAT,
    traffic_level FLOAT DEFAULT 1.0,
    distance_km FLOAT DEFAULT 0.0,
    duration_min FLOAT DEFAULT 0.0,
    pricing_pressure_score FLOAT DEFAULT 1.0,
    demand_level VARCHAR(20) DEFAULT 'NORMAL',
    confidence FLOAT DEFAULT 0.8,
    source_type VARCHAR(50) DEFAULT 'ml_estimate',
    reason TEXT,
    actual_observation_when_available FLOAT
);

CREATE INDEX ix_demand_obs_timestamp ON demand_observations (timestamp);
CREATE INDEX ix_demand_obs_provider ON demand_observations (provider);
CREATE INDEX ix_demand_obs_pickup_zone ON demand_observations (pickup_zone);
```

### Privacy Guarantee:
- No PII (personally identifiable information), IP addresses, user IDs, or names are ever recorded in `demand_observations`.
- Observations operate solely at H3 hexagon zone resolution and aggregated request velocity.

---

## 4. API Endpoints

### 4.1. Single Provider Real-Time Demand Estimation
`GET /api/pricing-pressure?pickup_lat=10.0284&pickup_lng=76.3074&provider=Uber&ride_category=Cab`

**Response (`200 OK`):**
```json
{
  "provider": "Uber",
  "pricing_pressure_score": 2.8,
  "demand_level": "HIGH",
  "pricing_pressure": "HIGH",
  "confidence": 0.84,
  "confidence_text": "84% confidence",
  "confidence_score": 84,
  "reason": "Current demand is above the historical baseline for this area and time.",
  "condition_wording": "High demand conditions detected. Pricing may be elevated.",
  "source_type": "ml_estimate",
  "pickup_zone": "876004da6ffffff",
  "destination_zone": "zone_destination_unknown",
  "ride_category": "Cab",
  "updated_at": "2026-09-27T10:30:00Z",
  "last_updated": "2026-09-27T10:30:00Z"
}
```

### 4.2. Multi-Provider Market Summary
`GET /api/pricing-pressure?pickup_lat=10.0284&pickup_lng=76.3074`

**Response (`200 OK`):**
```json
{
  "success": true,
  "pickup_zone": "876004da6ffffff",
  "destination_zone": "zone_destination_unknown",
  "market_summary": [
    {
      "provider": "Uber",
      "demand_level": "HIGH",
      "pricing_pressure": "HIGH",
      "confidence": 0.84,
      "confidence_text": "84% confidence",
      "reason": "High request activity relative to historical baseline in this zone.",
      "source_type": "ml_estimate",
      "last_updated": "2026-09-27T10:30:00Z"
    },
    {
      "provider": "Ola",
      "demand_level": "NORMAL",
      "pricing_pressure": "NORMAL",
      "confidence": 0.76,
      "confidence_text": "76% confidence",
      "reason": "Demand currently aligns with normal historical baseline.",
      "source_type": "ml_estimate",
      "last_updated": "2026-09-27T10:30:00Z"
    },
    {
      "provider": "Rapido",
      "demand_level": "VERY HIGH",
      "pricing_pressure": "VERY HIGH",
      "confidence": 0.88,
      "confidence_text": "88% confidence",
      "reason": "High request activity relative to historical availability.",
      "source_type": "ml_estimate",
      "last_updated": "2026-09-27T10:30:00Z"
    }
  ],
  "disclaimer": "Demand indicators are RideCompare independent estimates based on available market signals. They do not represent proprietary provider surge multipliers."
}
```

### 4.3. Market Conditions Point Overview
`GET /api/market-conditions?lat=12.9716&lng=77.5946`

### 4.4. Internal Telemetry & Performance Metrics
`GET /api/admin/demand-model/metrics` (Requires `X-Admin-Key` in production)

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_name": "Gradient Boosting Regressor",
  "version": "v20260927.0529",
  "total_training_records": 12000,
  "validation_metrics": {
    "mae": 0.0859,
    "rmse": 0.1170,
    "r2": 0.9918,
    "mape": 9.21
  },
  "database_observations_collected": 80
}
```

### 4.5. Retrain Model Endpoint
`POST /api/admin/demand-model/retrain?sample_size=12000` (Requires `X-Admin-Key` in production)

---

## 5. Machine Learning Features & Engineering

Target variable: `pricing_pressure_score` $\in [0.0, 4.0]$.

### 5.1. Numerical Features:
- `hour_of_day`: Integer (0–23)
- `hour_sin`: Cyclical sine encoding $\sin(2\pi \cdot hour / 24)$
- `hour_cos`: Cyclical cosine encoding $\cos(2\pi \cdot hour / 24)$
- `day_of_week`: Integer (0=Monday, 6=Sunday)
- `is_weekend`: Binary flag (1 if Sat/Sun)
- `is_holiday`: Binary flag for public holidays
- `latitude`, `longitude`: Geospatial pickup location
- `route_distance`: Distance in km
- `estimated_duration`: Duration in minutes
- `traffic_level`: Detour / speed traffic factor (1.0 to 2.5)
- `recent_request_count_5m`: Request count in past 5 minutes
- `recent_request_count_15m`: Request count in past 15 minutes
- `recent_request_count_30m`: Request count in past 30 minutes
- `recent_request_count_1h`: Request count in past 1 hour
- `recent_request_count_24h`: Request count in past 24 hours
- `request_rate`: Requests per minute over last 15 minutes
- `historical_request_average`: Zone-specific historical baseline for the current hour and day
- `historical_demand_deviation`: $(request\_rate - historical\_avg) / \max(historical\_avg, 0.01)$
- `historical_provider_pressure`: Time-decayed provider observation average
- `time_since_last_observation`: Delta in seconds since previous observation in the zone

### 5.2. Categorical Features:
- `provider`: One-hot encoded (e.g. `Uber Go`, `Uber Premier`, `Ola Mini`, `Ola Prime`, `Rapido Bike`, `Rapido Auto`, `Local Taxi`)
- `ride_category`: One-hot encoded (`Cab`, `Bike`, `Auto`)

### 5.3. Exponential Time-Decay Weighting:
For past observations $\Delta t$ seconds ago:
$$w(\Delta t) = 2^{-\Delta t / \tau}$$
- $\tau = 300\text{s}$ (5m rolling window)
- $\tau = 1800\text{s}$ (30m rolling window)
- $\tau = 86400\text{s}$ (24h window)

---

## 6. Fallback Hierarchy (5 Levels)

When determining pricing pressure, the engine traverses five sequential levels:

```
[LEVEL 1] Provider-Authorized Live Signal
   ├── Checks if official provider API returns authorized demand pressure
   └── If present: source_type = "provider_signal", confidence >= 0.90

[LEVEL 2] ML Prediction Pipeline
   ├── Scikit-learn Gradient Boosting Regressor Pipeline
   ├── Standardized features & one-hot encoding
   └── If loaded: source_type = "ml_estimate", confidence ~ 0.80 - 0.90

[LEVEL 3] Statistical / Historical Demand Model
   ├── Computes exponential time-decay over historical zone observations
   └── Used if ML model is unavailable and zone has >= 3 samples:
       source_type = "statistical_baseline", confidence ~ 0.70 - 0.80

[LEVEL 4] Time / Location Heuristic Fallback
   ├── Peak hours (8-10 AM, 5-8 PM, weekend nightlife)
   ├── Route distance, airport keyword detection, traffic level
   └── source_type = "heuristic_fallback", confidence ~ 0.60 - 0.70

[LEVEL 5] Insufficient Data
   ├── Triggered if coordinates are invalid or out of range
   └── source_type = "insufficient_data", confidence = 0.25 ("Limited data")
```

---

## 7. Caching & Performance

To prevent computational latency during concurrent peak search traffic:
- **Cache**: Thread-safe in-memory cache [`PricingPressureCache`](file:///c:/Users/HP/Desktop/Taxi-Fare-Comparison-web-app-master/Taxi-Fare-Comparison-web-app-master/backend/app/services/demand_intelligence.py).
- **Key**: `provider:pickup_zone:ride_category`
- **TTL**: 60 seconds (configurable).
- **Asynchronous Persistence**: All database logging occurs via background tasks, ensuring 0ms addition to the user response latency.

---

## 8. Testing Instructions

Run the dedicated test suite:
```bash
# In the project root with virtual environment active:
.venv\Scripts\python.exe -m pytest backend/tests/test_demand_intelligence.py -v
```

Run the entire platform test suite (32 tests):
```bash
.venv\Scripts\python.exe -m pytest backend/tests/test_backend_api.py backend/tests/test_demand_intelligence.py -v
```

---

## 9. How to Retrain the Model

### Option A: Via Terminal Script
```bash
.venv\Scripts\python.exe ml/training/train_demand_model.py
```
This will:
1. Load historical observations from database augmented with multi-city scenario data.
2. Split train/test sets (80/20) strictly before fitting transformers.
3. Train `GradientBoostingRegressor` and `RandomForestRegressor`.
4. Validate MAE, RMSE, R2, and MAPE.
5. Save winning model to `ml/models/saved/demand_intelligence_model.joblib`.
6. Write telemetry to `ml/models/saved/demand_metadata.json`.

### Option B: Via HTTP API Endpoint
```bash
curl -X POST "http://localhost:5000/api/admin/demand-model/retrain?sample_size=15000" \
     -H "X-Admin-Key: <YOUR_ADMIN_KEY>"
```

---

## 10. How to Add Another Ride Provider

To add a new provider (e.g. `BluSmart`, `inDrive`):

1. **Add Provider Tariff / Centroid Configuration**:
   In `backend/app/config/fares.json`, add the provider entry under the target city's `providers`:
   ```json
   "BluSmart EV": {
     "baseFare": 60,
     "perKmRate": 16.0,
     "perMinRate": 2.0,
     "platformFee": 15,
     "vehicleType": "EV",
     "etaMultiplier": 1.05,
     "categoryTag": "100% Pure Electric Fleet",
     "rating": 4.7
   }
   ```

2. **Add Adapter (Optional for Live API)**:
   In `backend/app/services/adapters/provider_adapters.py`, create `BluSmartAdapter(ProviderAdapter)`.

3. **Demand Intelligence Integration**:
   The engine automatically detects any new provider name passed in `GET /api/pricing-pressure?provider=BluSmart+EV`.
   The model's categorical encoder uses `handle_unknown="ignore"`, allowing novel providers to be safely evaluated with baseline market characteristics immediately.

4. **Retrain Model**:
   Run `train_demand_model.py` to include the new provider in future training cycles.
