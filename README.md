# RideCompare 🚕⚡

**RideCompare** is an intelligent urban mobility aggregator and route pricing intelligence platform. It solves a core consumer challenge: **"What are ride providers charging right now, and how does that price compare with expected historical behavior?"**

The platform operates on a dual-engine architecture:
1. **Real-Time Authoritative Provider Pricing**: Captures and displays live provider rates (e.g. `₹287 ● LIVE PRICE`) with timestamped validation. Live provider quotes are always authoritative and never overwritten by artificial approximations.
2. **AI/Machine Learning Pricing Intelligence**: Analyzes live observations alongside 12,000+ historical trip records to predict typical fare baselines, demand levels, price anomalies, and expected fare ranges.

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

- **Authoritative Live Fares**: Real-time provider pricing with pulsing live indicators and quote age timestamps.
- **Fail-Safe Fallbacks**: If a provider API is unreachable, RideCompare explicitly labels the estimate as:
  *`"Historical/ML estimate — not a live provider price."`* (No fabricated live data).
- **ML Pricing Intelligence**:
  - **Supervised Regression**: Gradient Boosting Regressor ($R^2 = 0.9803$, $\text{MAE} = ₹20.66$, $\text{MAPE} = 5.96\%$).
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

## 📄 License

This project is licensed under the MIT License.