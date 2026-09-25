# RideCompare Frontend UI 🚖

The frontend application for **RideCompare** — an intelligent multi-provider taxi fare aggregator and route planner. Built with **React 19**, **TypeScript**, **Vite**, **Tailwind CSS**, and **Leaflet Maps**, offering an interactive, dark-mode optimized, and responsive user experience.

---

## Tech Stack

- **Framework:** React 19
- **Build Tool:** Vite
- **Styling:** Tailwind CSS
- **Maps:** Leaflet & OpenStreetMap tiles
- **Icons:** Lucide React
- **Language:** TypeScript

---

## Component Structure

```text
frontend/src/
├── components/
│   ├── AnalyticsDashboard.tsx # Usage metrics, 7-day search trends & ML model hub
│   ├── MapView.tsx            # Leaflet Map with interactive route polyline & markers
│   ├── Navbar.tsx             # Responsive header with dark/light mode toggle
│   ├── PriceHistoryGraph.tsx  # Sparkline visualization of price volatility
│   ├── RideComparison.tsx     # Provider comparison cards, ML insights & deep links
│   └── SearchPanel.tsx        # Autocomplete search with Nominatim geocoding
├── types/
│   └── ride.ts                # TypeScript domain models & interfaces
├── utils/
│   └── api.ts                 # API client wrapper
├── App.tsx                    # Main state manager & view orchestrator
├── App.css                    # Theme variables & glassmorphism styling
├── index.css                  # Tailwind directives & global rules
└── main.tsx                   # React root mount
```

---

## Main Features

1. **Address Autocomplete (Geocoding):** Instant location lookups using OpenStreetMap Nominatim.
2. **Interactive Route Mapping:** Visualizes OSRM routing paths with pickup and drop markers.
3. **Multi-Provider Fare Breakdown:** Side-by-side comparison across Uber, Ola, Rapido, and Local Taxi with itemized base fares, distance fees, time rates, and platform fees.
4. **ML Expected Fare Baseline:** Displays Gradient Boosting regression predictions and Isolation Forest anomaly flags for price transparency.
5. **Real-time Price Volatility:** Historical sparkline graphs showing recent price movements per corridor.
6. **Progressive Web App (PWA) Ready:** Installable on mobile and desktop devices.
7. **Intelligence & Analytics Hub:** Comprehensive dashboard with ML validation metrics, K-Means pricing clusters, and user booking ledger.

---

## Available Scripts

```bash
# Install dependencies
npm install

# Start Vite dev server
npm run dev

# Build production bundle
npm run build

# Preview production build
npm run preview
```
