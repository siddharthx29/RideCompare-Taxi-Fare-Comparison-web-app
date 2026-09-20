# RideCompare Frontend UI 🚖

This is the frontend single-page application (SPA) for **RideCompare**—the smart cab fare aggregator and route planner. It is built using React 19, TypeScript, Vite, Tailwind CSS v4, and Leaflet Maps, offering a modern, dark-mode optimized, fully responsive user interface.

---

## 🛠 Tech Stack & UI Libraries

- **Framework:** React 19
- **Build Tool:** Vite
- **Styling:** Tailwind CSS v4 (configured via `@tailwindcss/vite` plugin)
- **Maps Integration:** Leaflet Maps (`leaflet` & `@types/leaflet`)
- **Icons:** Lucide React
- **Language:** TypeScript

---

## 📦 Component Structure

```text
frontend/src/
├── components/
│   ├── AnalyticsDashboard.tsx # Renders aggregated usage metrics & chart layouts
│   ├── MapView.tsx            # Renders Leaflet Map with route polyline, start & end markers
│   ├── Navbar.tsx             # Responsive header with dark/light mode toggle & views switch
│   ├── RideComparison.tsx     # Comparison grids featuring cheapest/fastest badges and booking deep-links
│   └── SearchPanel.tsx        # Autocomplete search fields fetching address names via geocoding
├── App.tsx                    # Main state manager, layout container, and PWA logic
├── App.css                    # UI theme variables, custom scrollbars, and animations
├── index.css                  # Tailwinds directives and standard base styles
└── main.tsx                   # React DOM render entry point
```

---

## ⚡ Main Features

1. **Address Autocomplete (Geocoding):** Instantly search and lookup locations using OpenStreetMap's Nominatim geocoding engine (proxied through the backend server).
2. **Interactive Route Mapping:** Visualizes routing geometry using custom Leaflet paths. Pins are placed at pickup and drop locations. If OSRM fails, straight-line Haversine fallback paths are rendered.
3. **Advanced Fares Comparison:** Groups results by Cheapest, Fastest, and Best Overall (calculated with a multi-metric scoring engine on the backend).
4. **Mobile Navigation Dock:** Provides app-like, responsive navigation for tablets and mobile devices.
5. **Progressive Web App (PWA) Ready:** Prompts mobile and desktop users to install RideCompare on their home screen for native-like access.
6. **Analytics Admin Panel:** Aggregates database search logs to visualize search volume trends, popular pickup/destination combinations, and click-through market share for Ola, Uber, and Rapido.

---

## 🚀 Available Scripts

Run these commands from the `frontend/` directory:

```bash
# Install dependencies
npm install

# Run the client in development mode (Vite hot-reloading)
npm run dev

# Lint files for TypeScript and React rules
npm run lint

# Build production bundles
npm run build

# Preview the compiled production build locally
npm run preview
```

---

## 🎨 Design Tokens & Custom CSS

RideCompare uses vanilla CSS variables inside `src/App.css` to manage theme transitions seamlessly:

```css
:root {
  --bg-primary: #f8fafc;
  --bg-secondary: #ffffff;
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --border-color: #e2e8f0;
  --glass-bg: rgba(255, 255, 255, 0.7);
  --glass-border: rgba(226, 232, 240, 0.6);
}

.dark {
  --bg-primary: #09090b;
  --bg-secondary: #121214;
  --text-primary: #f4f4f5;
  --text-secondary: #a1a1aa;
  --border-color: #27272a;
  --glass-bg: rgba(18, 18, 20, 0.75);
  --glass-border: rgba(39, 39, 42, 0.6);
}
```

Interactive elements leverage custom glassmorphism styles (`.glass-panel`) for a modern, floating interface look.
