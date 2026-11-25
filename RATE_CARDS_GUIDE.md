# Statutory Rate Cards & Coverage Management Guide 🚕📋

This guide details how to add a city, update statutory rate cards, flip aggregator regulatory statuses, and understand what is estimated versus verified in **RideCompare**.

---

## 🏛️ 1. Architecture Overview & Hard Rules

1. **Zero Scraping / No Unofficial APIs**:
   - Prices come purely from internal statutory rate cards and mathematical routing calculations.
   - We never scrape Uber, Ola, Rapido, or use reverse-engineered endpoints.
2. **Strict Estimate Ranges Only**:
   - Every price is labeled **"Estimate"** and presented as a range (`low – high`), never as a single exact number.
   - Mandatory legal footer:
     > *"Actual fare is shown in the app and may differ due to live demand, traffic, tolls and taxes."*
3. **Official App Deep Links**:
   - Every result card includes an **"Open in app"** deep link (`uber://`, `ola://`, `rapido://`, `nammayatri://`, `bolt://`, etc.) with browser web fallback.
4. **4-Case Availability Gating**:
   - **Case A (Intra-city with active apps)**: Both points inside geofence with $\ge 1$ active app service $\rightarrow$ show comparisons sorted cheapest first.
   - **Case B (Metered-only)**: In region, 0 active app services, but metered autos/taxis exist $\rightarrow$ show "Normal auto / local taxi" card with government minimum meter estimate (range) and message: *"No ride-hailing apps operate here. Typical metered auto fare estimate:"*.
   - **Case C (Unsupported area)**: Outside all geofences or no services $\rightarrow$ disable "Compare" button, show *"Ride services are not available in this area."*, and block API with HTTP 422 (`OUT_OF_COVERAGE`).
   - **Case D (Intercity)**: Pickup and drop in different cities/regions $\rightarrow$ show intercity notice banner: *"Standard city-ride fares do not apply for intercity/outstation trips."*

---

## 🌍 2. How to Add a New City

### Step 1: Add Region Data to Seed Script
Open `backend/app/services/seed_rate_cards.py` and append your city to `REGIONS_DATA`:

```python
{
    "region_id": "hyderabad",
    "name": "Hyderabad",
    "state": "Telangana",
    "country": "India",
    "polygon_geojson": {
        "type": "Polygon",
        "coordinates": [[
            [78.20, 17.20],
            [78.65, 17.20],
            [78.65, 17.60],
            [78.20, 17.60],
            [78.20, 17.20]
        ]]
    },
    "legal_surge_cap": 2.0,  # Motor Vehicle Aggregator Guidelines 2025
    "auto_rickshaw_metered_available": True,
    "metered_auto_fare": {
        "min_fare": 30.0,
        "free_km": 1.6,
        "per_km": 15.0,
        "night_multiplier": 1.25,
        "currency": "INR",
        "currency_symbol": "₹"
    }
}
```

### Step 2: Add Rate Cards for the City
In `RATE_CARDS_DATA` in `backend/app/services/seed_rate_cards.py`:

```python
{
    "city": "Hyderabad",
    "service": "Uber",
    "ride_type": "UberGo",
    "vehicle_category": "Cab",
    "currency": "INR",
    "base_fare": 45.0,
    "per_km": 15.0,
    "per_min": 1.2,
    "booking_fee": 15.0,
    "min_fare": 75.0,
    "free_km": 0.0,
    "long_distance_threshold": 25.0,
    "long_distance_rate": 20.0,
    "night_multiplier": 1.25,
    "tax_pct": 5.0,
    "source_url": "https://transport.telangana.gov.in",
    "last_verified_date": "2026-03-01",
    "is_verified": False,  # Marked unverified until confirmed by admin
}
```

### Step 3: Add Service Statuses
In `SERVICE_STATUS_DATA` in `backend/app/services/seed_rate_cards.py`:

```python
{"region_id": "hyderabad", "service_name": "Uber", "status": "active", "status_reason": "Licensed aggregator"},
{"region_id": "hyderabad", "service_name": "Ola", "status": "active", "status_reason": "Licensed aggregator"},
{"region_id": "hyderabad", "service_name": "Rapido", "status": "active", "status_reason": "Bike and Auto aggregation permitted"},
```

Then re-run:
```bash
python -c "from backend.app.database import SessionLocal, init_db; from backend.app.services.seed_rate_cards import seed_coverage_and_rate_cards; init_db(); db = SessionLocal(); seed_coverage_and_rate_cards(db); db.close()"
```

---

## ✏️ 3. How to Update a Rate Card

### Option A: Using the Web Admin Screen
1. Open RideCompare and click **Admin** in the navigation bar.
2. Under the **Statutory Rate Cards** sub-tab:
   - Filter by City (e.g. `Bengaluru`, `Mumbai`, `Kochi`).
   - Click the **Edit** icon on any rate card row.
   - Adjust `base_fare`, `per_km`, `per_min`, `min_fare`, `booking_fee`, `night_multiplier`, or `tax_pct`.
   - Update `source_url` (gazette notification URL) and `last_verified_date`.
   - Check the **"Mark as Verified by Admin"** checkbox.
   - Click **Save Changes**.

### Option B: Using the REST API
Send a `PUT /api/admin/rate-cards/{id}` request:

```bash
curl -X PUT "http://127.0.0.1:5000/api/admin/rate-cards/1" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ridecompare_admin_secret" \
  -d '{
    "base_fare": 55.0,
    "per_km": 17.0,
    "per_min": 1.5,
    "min_fare": 85.0,
    "is_verified": true,
    "last_verified_date": "2026-03-01",
    "source_url": "https://transport.karnataka.gov.in/gazette-2026.pdf"
  }'
```

### Option C: Bulk JSON Import
1. Navigate to **Admin $\rightarrow$ JSON / CSV Import**.
2. Paste a JSON array of rate cards and click **Import Rate Cards**.
3. Existing cards matching `(city, service, ride_type)` are updated; new cards are inserted.

---

## 🚫 4. How to Flip an Aggregator's Status (Active / Suspended)

When regulators suspend aggregators (e.g. licence reviews in Indian municipal zones):

### Option A: Using the Admin Screen
1. Open **Admin $\rightarrow$ Service Statuses**.
2. Locate the aggregator in that region (e.g. `Uber` in `Goa` or `Ola` in `Bengaluru`).
3. Click **Suspend** and enter the regulatory reason (e.g. *"Licence suspended by State Transport Authority"*).
4. Or click **Active** to restore normal operation.

### Option B: Using the REST API
Send a `PUT /api/admin/service-status` request:

```bash
curl -X PUT "http://127.0.0.1:5000/api/admin/service-status" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ridecompare_admin_secret" \
  -d '{
    "region_id": "bengaluru",
    "service_name": "Uber",
    "status": "suspended",
    "status_reason": "Temporary licence inspection by Karnataka Transport Dept"
  }'
```

When suspended, the service is immediately excluded from Case A comparison and moved to the excluded/suspended audit drawer.

---

## ⚖️ 5. What is Estimated vs What is Verified

| Feature | Classification | Source & Logic |
| :--- | :--- | :--- |
| **Statutory Base Fare & Min Fare** | ✅ **Verified** | Official gazetted transport tariffs (e.g. Karnataka RTO, Maharashtra Khatua Committee, Delhi Aggregator Policy). |
| **Legal Surge Caps** | ✅ **Verified** | Strictly capped by state policy: **2.0x** under India MV Aggregator Guidelines 2025; **1.5x** in Maharashtra draft rules; **1.5x** in London/NY/Singapore. |
| **Geofence Boundaries** | ✅ **Verified** | GeoJSON polygons bounding official municipal operating jurisdictions. |
| **Aggregator Operating Status** | ✅ **Verified** | Admin-controlled status (`active`, `suspended`, `unavailable`) with timestamp and suspension reason. |
| **Rate Card Verification Date** | ✅ **Verified** | Admin-audited `last_verified_date` with `✓ Verified` / `⚠ Unverified` badge in cards. |
| **Deep Links & App Schemes** | ✅ **Verified** | Verified URL schemes (`uber://`, `ola://`, `rapido://`, `nammayatri://`, `bolt://`, etc.) with official web fallbacks. |
| **Route Distance & Duration** | 📊 **Estimated** | Real driving path computed via OSRM / Google Directions routing engine. |
| **Surge Multiplier Window** | 📊 **Estimated** | Diurnal and weekend rush-hour demand window (e.g. 1.1x–1.4x morning peak, 1.2x–1.6x evening peak), strictly constrained by the legal cap. |
| **Consumer Fare Range** | 📊 **Estimated** | Low (off-peak, 1.0x surge) to High (peak surge window). Displayed strictly as a range (`low – high`), never an exact single number. |
