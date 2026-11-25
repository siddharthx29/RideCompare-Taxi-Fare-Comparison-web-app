# RideCompare 🚕⚡

**RideCompare** is an urban ride-fare comparison platform. It calculates estimated fare ranges across all ride services available at the user's location (Uber, Ola, Rapido, inDrive, Namma Yatri, Bolt, Grab, DiDi, Lyft, etc.), sorted cheapest first, using internal statutory rate card models and point-in-polygon geofencing.

> 📖 **Read the Complete Management Guide**: [RATE_CARDS_GUIDE.md](file:///c:/Users/HP/Downloads/RideCompare-Taxi-Fare-Comparison-web-app-main%20%281%29/RideCompare-Taxi-Fare-Comparison-web-app-main/RATE_CARDS_GUIDE.md) — How to add a city, update rate cards, and flip aggregator regulatory statuses.

---

## 🏛️ Core Principles & Hard Rules

1. **Zero Scraping**: No scraping of Uber/Ola/Rapido or any other ride app. No unofficial or reverse-engineered APIs. All prices come from internal statutory rate cards and verified routing algorithms.
2. **Ranges Only (Labeled "Estimate")**: Every price is labeled **"Estimate"** and presented as a range (`low – high`), never a single exact number. Includes mandatory legal footer: *"Actual fare is shown in the app and may differ due to live demand, traffic, tolls and taxes."*
3. **Official App Deep Links**: Each result card features an **"Open in app"** deep link (`uber://`, `ola://`, `rapido://`, `nammayatri://`, `bolt://`, etc.) with browser web fallback.
4. **4-Case Availability Gating**:
   - **Case A (Intra-city with active apps)**: Both points inside geofence with $\ge 1$ active app service $\rightarrow$ show comparisons sorted cheapest first.
   - **Case B (Metered-only)**: In region, 0 active app services, but metered autos/taxis exist $\rightarrow$ show "Normal auto / local taxi" card with government minimum meter estimate (range) and message: *"No ride-hailing apps operate here. Typical metered auto fare estimate:"*.
   - **Case C (Unsupported area)**: Outside all geofences or no services $\rightarrow$ disable "Compare" button, show *"Ride services are not available in this area."*, and block API with HTTP 422 (`OUT_OF_COVERAGE`).
   - **Case D (Intercity)**: Pickup and drop in different cities/regions $\rightarrow$ show intercity notice banner: *"Standard city-ride fares do not apply for intercity/outstation trips."*

---

## 🏗️ System Architecture

```
                                 ROUTE SEARCH
                          (Origin & Destination Coords)
                                      │
            ┌─────────────────────────┴─────────────────────────┐
            ▼                                                   ▼
   REAL-TIME PROVIDER                                 MACHINE LEARNING
      INTEGRATIONS                                   PRICING INTELLIGENCE
 (Uber, Ola, Rapido, etc.)                   (Gradient Boosting, K-Means, IF)
            │                                                   │
     Live Quoted Fare                                 Historical Baseline
   (e.g., ₹287 ● LIVE)                                 (e.g., ₹250–₹265)
   Timestamped & Verified                                       │
            │                                                   ▼
            │                                       Comparison & Anomaly Engine
            │                                         (+14.8% above typical)
            │                                         (Demand: High | Trend: Stable)
            │                                                   │
            └─────────────────────────┬─────────────────────────┘
                                      ▼
                           UNIFIED CONSUMER CARD
           ┌─────────────────────────────────────────────────────┐
           │ Uber Go                                             │
           │ ₹287  ● LIVE PRICE   [Updated just now]             │
           │ ETA: 4 min · Distance: 14.2 km                      │
           │ ─────────────────────────────────────────────────── │
           │ 🧠 AI/ML PRICING INSIGHT                            │
           │ Typical Fare:       ₹250–₹265                       │
           │ Current vs Typical: +14.8% above typical           │
           │ Demand Level:       High                            │
           │ Price Trend:        Stable / Increasing             │
           │ "14.8% above historical average for this route"     │
           └─────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

- **Real-Time Dynamic Pricing & Demand Intelligence**:
  - Independent estimation of current pricing pressure on a standardized 0–4 scale (`LOW`, `NORMAL`, `SLIGHTLY HIGH`, `HIGH`, `VERY HIGH`).
  - Never fabricates exact fares or proprietary surge algorithms.
  - Geo-spatial zone discretization using **Uber H3** hexagonal cells (resolution 7).
  - Multi-horizon rolling request windows (5m, 15m, 30m, 1h, 24h, 7d) with exponential time-decay weighting.
  - 5-level transparent fallback hierarchy with data-grounded confidence scores (`84% confidence`, `Limited data`).
  - Interactive demand indicator and top-level **Market Conditions Summary** (`Uber 🔴 HIGH`, `Ola 🟢 NORMAL`, `Rapido 🟠 SLIGHTLY HIGH`).
  - Read complete architecture in [DEMAND_INTELLIGENCE_DOCUMENTATION.md](file:///c:/Users/HP/Desktop/Taxi-Fare-Comparison-web-app-master/Taxi-Fare-Comparison-web-app-master/DEMAND_INTELLIGENCE_DOCUMENTATION.md).
- **Authoritative Live Fares**: Real-time provider pricing with pulsing live indicators and quote age timestamps.
- **Fail-Safe Fallbacks**: If a provider API is unreachable, RideCompare explicitly labels the estimate as:
  *`"Historical/ML estimate — not a live provider price."`* (No fabricated live data).
- **ML Pricing Intelligence**:
  - **Supervised Regression**: Gradient Boosting Regressor ($R^2 = 0.9918$, $\text{MAE} = 0.086$ pricing pressure score).
  - **K-Means Route Regimes**: Dynamically clusters transit into distinct operating regimes.
  - **Isolation Forest Anomaly Detection**: Flags unusual price spikes or deviations against historical distributions.
  - **Demand & Volatility Trends**: Real-time evaluation of surge multipliers, traffic density, and time-of-day dynamics.
- **Segregated Internal Diagnostics**: Production-hardened internal telemetry console displaying model metrics, confusion matrix benchmarks, and feature engineering breakdowns away from standard consumer flows.
- **Strict Service Coverage**: Centralized allowlist (`backend/app/config/service_coverage.json`) protecting against cross-regional service mismatches.

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 20+** / **npm 10+**

### 1. Clone & Set Up Backend

```bash
# Clone the repository
git clone https://github.com/siddharthx29/RideCompare-Taxi-Fare-Comparison-web-app.git
cd RideCompare-Taxi-Fare-Comparison-web-app

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Run the FastAPI server (runs on port 5000)
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 5000 --reload
```

Backend health check is accessible at `http://127.0.0.1:5000/health`.

### 2. Set Up Frontend

In a separate terminal:

```bash
cd frontend

# Install dependencies
npm ci

# Start the Vite development server
npm run dev
```

Open `http://localhost:5173/` in your browser. Vite proxies `/api` and `/health` requests to the backend server.

---

## 🔒 Security & Production Best Practices

- **Zero Tracked Secrets**: All `.env` files are ignored by git. Use `.env.example` templates to configure production environments.
- **Protected Admin Telemetry**: The internal ML dashboard is protected and hidden by default. In production environments (`ENVIRONMENT=production`), internal diagnostic endpoints require an `X-Admin-Key` header or `?key=` query matching `ADMIN_KEY`.
- **CORS Hardening**: Strict origin whitelist configured via `CORS_ORIGINS`. Production mode disables open wildcard origins.
- **Defensive API Headers**: Middleware applies `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, and strict `Permissions-Policy`.
- **Database Fail-Safe**: SQLite is used for lightweight local development; PostgreSQL is activated via `DATABASE_URL` with connection pooling and health checks.

---

## 🐳 Docker Deployment

To launch the full containerized stack (FastAPI backend + Nginx frontend + PostgreSQL):

```bash
# Prepare environment variables
cp .env.example .env
# Edit .env with your production credentials

# Build and start containers
docker compose up --build
```

The application is served at `http://localhost:8080/`.

---

## 🧪 Test Suite

Run the full automated test suite (backend API, provider adapters, serviceability, ML pipeline, and security):

```bash
# Run all Python unit & integration tests
python -m pytest backend/tests ml/tests -v

# Run frontend production build & TypeScript validation
cd frontend
npm run build
```

---

## 📁 Repository Structure

```
├── backend/
│   ├── app/
│   │   ├── config/              # Tariffs, coverage registries & settings
│   │   ├── models/              # SQLAlchemy database models
│   │   ├── routers/             # API routes (route, geocode, analytics, ml)
│   │   └── services/            # Provider adapters & quote orchestrator
│   └── tests/                   # Backend & adapter test suite
├── frontend/
│   ├── src/
│   │   ├── components/          # MapView, RideComparison, Analytics, ML Dashboard
│   │   ├── types/               # TypeScript data models
│   │   └── utils/               # Fetch API & geocoding helpers
│   └── package.json
├── ml/
│   ├── data/                    # Dataset generation & feature schemas
│   ├── inference/               # Normalizer & fare prediction engine
│   ├── models/saved/            # Trained scikit-learn models & metadata
│   ├── tests/                   # ML pipeline verification tests
│   └── training/                # Training pipelines (regression, clustering)
├── .env.example                 # Root environment template
├── .gitignore                   # Multi-stage security ignore rules
├── docker-compose.yml           # Production Docker Compose orchestration
└── README.md
```

---

## 🌐 Live App, Route Guides & SEO

- **Live App**: [https://ridecompare.world](https://ridecompare.world)
- **Route Fare Guides**: [https://ridecompare.world/routes](https://ridecompare.world/routes) — Indexable static + SPA pages for popular corridors (e.g., [Kochi Airport to Alappuzha Taxi Fare](https://ridecompare.world/routes/kochi-airport-to-alappuzha-taxi-fare), [Bangalore Airport to Koramangala](https://ridecompare.world/routes/bangalore-airport-to-koramangala-taxi-fare), [Goa Dabolim Airport to Baga Beach](https://ridecompare.world/routes/dabolim-airport-to-baga-beach-taxi-fare)).
- **Travel & Pricing Guides**: [https://ridecompare.world/blog](https://ridecompare.world/blog) — Helpful articles including [Uber vs Ola vs Rapido in Kerala](https://ridecompare.world/blog/uber-vs-ola-vs-rapido-in-kerala) and [How Surge Pricing Works](https://ridecompare.world/blog/how-surge-pricing-works).
- **Sitemap & Structured Data**: Auto-generated `sitemap.xml`, `robots.txt`, and Schema.org JSON-LD (`WebApplication`, `Service`, `FAQPage`, `BlogPosting`, `BreadcrumbList`) on every route and guide page.

---

## 📄 License

This project is licensed under the MIT License.