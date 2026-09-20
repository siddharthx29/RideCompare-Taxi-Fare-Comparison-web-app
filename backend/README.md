# RideCompare Backend API 🚖

This is the backend API server for **RideCompare**—the smart cab fare aggregator and route planner. The server is built using Node.js, Express, and TypeScript, interfacing with PostgreSQL for persistent storage and falling back to resilient in-memory stores if the database is offline.

---

## 🛠 Tech Stack & Core Libraries

- **Runtime:** Node.js (v18+)
- **Framework:** Express.js with TypeScript
- **Database:** PostgreSQL (`pg` pool)
- **Security:** `express-rate-limit` for DDoS/abuse protection
- **Routing API:** OpenStreetMap Routing Machine (OSRM)
- **Geocoding API:** Nominatim (OpenStreetMap)

---

## 📦 Directory Structure

```text
backend/
├── src/
│   ├── db/
│   │   ├── pool.ts       # DB connections & connection-retry/in-memory fallback logic
│   │   └── schema.sql    # Database tables schema and initial mock seeds
│   ├── routes/
│   │   └── api.ts        # Express endpoints (geocode, route search, redirect, analytics)
│   ├── services/
│   │   └── pricing.ts    # Fare calculation and recommendation scoring engine
│   └── index.ts          # Express App setup, middleware, and entry point
├── package.json
├── tsconfig.json
└── Dockerfile
```

---

## ⚙️ Environment Variables

The backend loads configuration from an `.env` file in the `backend/` directory.

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `PORT` | Port number the backend server will listen on. | `5000` |
| `DATABASE_URL` | PostgreSQL connection string. | `postgresql://postgres:postgrespassword@localhost:5432/ridecompare` |
| `NODE_ENV` | Development or Production environment mode. | `development` |
| `DATABASE_SSL` | Set to `true` to enable SSL connection in production environments. | `false` |

---

## 🚀 Available Scripts

Run these scripts from the `backend/` directory:

```bash
# Install dependencies
npm install

# Run the server in development mode (live reload via ts-node-dev)
npm run dev

# Compile TypeScript to JavaScript (build for production)
npm run build

# Start the compiled production build
npm run start
```

---

## 🔌 API Endpoints

### 1. Health Check
- **Endpoint:** `GET /health`
- **Description:** Verifies that the API server is online.
- **Response:**
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-06-17T12:00:00.000Z"
  }
  ```

### 2. Geocoding Proxy
- **Endpoint:** `GET /api/geocode`
- **Query Params:** `q` (string query, e.g. `Indiranagar`)
- **Description:** Proxies Nominatim OpenStreetMap API to find geographical coordinates.
- **Response:** Array of matched address objects with bounding boxes, latitudes, and longitudes.

### 3. Route Calculation & Pricing Comparison
- **Endpoint:** `GET /api/route`
- **Query Params:**
  - `start` (`longitude,latitude` e.g. `77.641151,12.971891`)
  - `end` (`longitude,latitude` e.g. `77.624480,12.935192`)
  - `sourceName` (optional, label of start location)
  - `destName` (optional, label of end location)
- **Description:** Queries OSRM for route geometries. On OSRM timeout/failure, it falls back to a straight-line **Haversine formula approximation** (with +25% winding factor). It then calculates fares for all providers (Uber, Ola, Rapido) and records the search to the database (or the in-memory fallback list).
- **Response:**
  ```json
  {
    "searchId": 105,
    "geometry": { "type": "LineString", "coordinates": [...] },
    "comparison": {
      "distanceKm": 5.8,
      "durationMin": 18,
      "providers": [
        { "name": "Uber", "totalFare": 150, "duration": 18, "score": 85, "deepLink": "..." },
        ...
      ],
      "recommendations": {
        "cheapest": "Rapido",
        "fastest": "Uber",
        "bestOverall": "Ola"
      }
    }
  }
  ```

### 4. Booking Redirect Analytics
- **Endpoint:** `POST /api/redirect`
- **Body Params:**
  - `searchId` (number, associated search log ID)
  - `provider` (string, e.g. `'Uber'`)
  - `fare` (number, selected ride cost)
- **Description:** Logs that the user clicked on a cab option. Records click-through counts, redirect rates, and approximate booking revenue.
- **Response:** `{ "success": true }`

### 5. Dashboard Analytics
- **Endpoint:** `GET /api/analytics`
- **Description:** Aggregates search logs and redirects. Used to render charts and key metrics in the frontend Admin/Dashboard panel.
- **Response:**
  ```json
  {
    "totalSearches": 15,
    "avgSavings": 28,
    "popularRoutes": [
      { "source": "A", "destination": "B", "count": 5 }
    ],
    "providerShares": [
      { "provider": "Uber", "clicks": 25, "redirects": 20, "total_fare": 320 }
    ],
    "dailyTrends": [
      { "date": "2026-06-17", "count": 7 }
    ]
  }
  ```

---

## 🛡 Fault Tolerance & Offline Mode

- **Database Fallback:** If PostgreSQL is offline on boot, the server automatically enters **In-Memory Fallback Mode**. All queries will continue to function seamlessly using transient memory stores for searches and analytics.
- **OSRM Fallback:** If the public OSRM API fails or exceeds a 4-second timeout limit, the backend calculates route metrics using a customized **Haversine distance formula** combined with average city driving speeds (25 km/h) to maintain application availability.
