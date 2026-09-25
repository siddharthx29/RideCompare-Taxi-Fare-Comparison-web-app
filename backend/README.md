# Backend

FastAPI provides route calculation, fare comparison, platform analytics, geocoding, and public fare history. SQLAlchemy uses SQLite by default for local development; PostgreSQL is supported through `DATABASE_URL`.

## Run

From the repository root:

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 5000 --reload
```

Local API documentation is available at `/docs` and `/redoc`. Both are disabled when `ENVIRONMENT=production`.

## Configuration

Copy `backend/.env.example` to a local `.env` only when environment-file loading is configured by your runner. Otherwise, set variables in the shell or deployment environment:

- `DATABASE_URL`: optional SQLAlchemy URL; defaults to local SQLite.
- `ENVIRONMENT`: `development` or `production`.
- `CORS_ORIGINS`: comma-separated exact browser origins. Development has localhost defaults; production does not.
- `PORT`: HTTP port, default `5000`.

Production does not silently fall back to SQLite when PostgreSQL is unavailable. Do not put real credentials in tracked files.

## Provider Coverage

`app/config/service_coverage.json` is the central allowlist. Both route endpoints must resolve to the same configured region before any provider adapter or tariff fallback can produce a quote. Unknown regions fail closed.

## Tests

```powershell
python -m pytest backend/tests -q
```