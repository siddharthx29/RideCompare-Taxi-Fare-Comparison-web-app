# RideCompare Backend API 🚖

The backend API service for **RideCompare** — an intelligent taxi and cab fare comparison platform. Built with **FastAPI**, **SQLAlchemy**, and **Scikit-Learn**, it provides real-time multi-provider fare calculation, route planning, time-series volatility tracking, and machine learning price intelligence.

---

## Tech Stack & Architecture

- **Framework:** FastAPI (Python 3.11+)
- **Server:** Uvicorn ASGI
- **ORM & Database:** SQLAlchemy with PostgreSQL (auto-falls back to SQLite for local development)
- **Machine Learning:** Scikit-Learn (Gradient Boosting Regressor, K-Means Clustering, Isolation Forest)
- **Routing & Geocoding:** OpenStreetMap Nominatim and OSRM with Haversine fallback
- **Validation:** Pydantic v2

---

## Directory Structure

```text
backend/
├── app/
│   ├── config/
│   │   └── fares.json           # City tariff configurations and rate models
│   ├── models/
│   │   └── db_models.py         # SQLAlchemy relational database models
│   ├── routers/
│   │   ├── geocode.py           # Nominatim place search & caching
│   │   ├── route.py             # OSRM routing & fare calculation
│   │   ├── analytics.py         # Aggregated metrics & click tracking
│   │   └── ml_endpoints.py      # ML inference & retraining endpoints
│   ├── services/
│   │   ├── adapters/
│   │   │   ├── base_adapter.py      # ProviderAdapter & QuoteObject abstractions
│   │   │   └── provider_adapters.py # Uber, Ola, Rapido, and Local Taxi adapters
│   │   ├── quote_orchestrator.py    # Parallel quote fetcher & volatility tracker
│   │   └── pricing.py               # Fare calculation & multi-factor scoring
│   ├── config.py                # Pydantic Settings & environment variables
│   ├── database.py              # Database engine & session management
│   └── main.py                  # FastAPI application entrypoint
├── tests/
│   ├── test_adapters.py
│   ├── test_backend_api.py
│   └── test_quote_orchestrator.py
├── requirements.txt
└── Dockerfile
```

---

## Configuration & Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `PORT` | Listening port for FastAPI server | `5000` |
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql://postgres:postgrespassword@localhost:5432/ridecompare` |
| `ENVIRONMENT` | Runtime environment mode | `development` |
| `CORS_ORIGINS` | Comma-separated list of allowed origins | `http://localhost:5173,http://localhost:3000` |

---

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start backend server with auto-reload
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 5000 --reload
```

Interactive API documentation is automatically available at:
- Swagger UI: `http://127.0.0.1:5000/docs`
- ReDoc: `http://127.0.0.1:5000/redoc`

---

## Running Tests

```bash
python -m pytest backend/tests/ -v
```
