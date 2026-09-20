import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

interface MapViewProps {
  sourceCoords: [number, number] | null;
  destCoords: [number, number] | null;
  routeGeometry: any | null; // GeoJSON from OSRM
  distanceKm?: number;
  durationMins?: number;
}

export const MapView: React.FC<MapViewProps> = ({
  sourceCoords,
  destCoords,
  routeGeometry,
  distanceKm,
  durationMins
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const routeLayerRef = useRef<L.Polyline | null>(null);
  const markersRef = useRef<L.Marker[]>([]);

  // Custom SVG Markers
  const createCustomIcon = (color: string, label: string) => {
    return L.divIcon({
      html: `
        <div class="relative flex flex-col items-center">
          <div class="px-2.5 py-1 bg-slate-900 text-white dark:bg-white dark:text-slate-900 text-[10px] font-extrabold rounded-md shadow-md mb-1 whitespace-nowrap border border-slate-700 dark:border-slate-200">
            ${label}
          </div>
          <div class="w-6 h-6 flex items-center justify-center rounded-full shadow-lg border-2 border-white dark:border-slate-800" style="background-color: ${color}">
            <div class="w-2.5 h-2.5 bg-white rounded-full"></div>
          </div>
          <div class="w-1 h-2 -mt-0.5" style="background-color: ${color}"></div>
        </div>
      `,
      className: 'custom-div-icon',
      iconSize: [60, 42],
      iconAnchor: [30, 42]
    });
  };

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    // Default center at Bengaluru if no coordinates provided
    const defaultCenter: L.LatLngExpression = [12.9716, 77.5946];
    
    const map = L.map(mapContainerRef.current, {
      zoomControl: false, // will add in custom position below
      zoomSnap: 0.5,
      zoomDelta: 1
    }).setView(defaultCenter, 12);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19
    }).addTo(map);

    // Add zoom control at bottom-right
    L.control.zoom({
      position: 'bottomright'
    }).addTo(map);

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update Markers and Polyline
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Force Leaflet recalculation to scale layout boundaries correctly
    map.invalidateSize();

    // Clear old markers
    markersRef.current.forEach(marker => marker.remove());
    markersRef.current = [];

    // Clear old route
    if (routeLayerRef.current) {
      routeLayerRef.current.remove();
      routeLayerRef.current = null;
    }

    const bounds: L.LatLngBounds = L.latLngBounds([]);

    // Add source marker
    if (sourceCoords) {
      const sourceIcon = createCustomIcon('#22c55e', 'Start'); // Green
      const sourceMarker = L.marker(sourceCoords, { icon: sourceIcon }).addTo(map);
      markersRef.current.push(sourceMarker);
      bounds.extend(sourceCoords);
    }

    // Add dest marker
    if (destCoords) {
      const destIcon = createCustomIcon('#6366f1', 'Dropoff'); // Indigo
      const destMarker = L.marker(destCoords, { icon: destIcon }).addTo(map);
      markersRef.current.push(destMarker);
      bounds.extend(destCoords);
    }

    // Draw routing polyline
    if (routeGeometry) {
      // routeGeometry.coordinates is in GeoJSON format: array of [lng, lat]
      // Leaflet expects coordinates in [lat, lng] format
      const leafletCoords = routeGeometry.coordinates.map((coord: [number, number]) => [
        coord[1],
        coord[0]
      ]);

      const polyline = L.polyline(leafletCoords, {
        color: '#4f46e5', // Indigo color for polyline
        weight: 5,
        opacity: 0.85,
        lineJoin: 'round'
      }).addTo(map);

      routeLayerRef.current = polyline;
      bounds.extend(polyline.getBounds());

      // Bind a nice popup showing summary details
      if (distanceKm && durationMins) {
        polyline.bindPopup(`
          <div class="p-1.5 text-xs text-slate-800 dark:text-slate-100 bg-white dark:bg-slate-900 font-semibold rounded">
            <p class="font-bold text-indigo-600 dark:text-indigo-400 mb-0.5">Route Summary</p>
            <p>Distance: ${distanceKm.toFixed(1)} km</p>
            <p>Est. Time: ${Math.round(durationMins)} mins</p>
          </div>
        `, { closeButton: false }).openPopup(polyline.getCenter());
      }
    }

    // Fit map bounds to show full route
    if (bounds.isValid()) {
      map.fitBounds(bounds, {
        padding: [50, 50],
        maxZoom: 15,
        animate: true,
        duration: 1.2
      });
    }
  }, [sourceCoords, destCoords, routeGeometry, distanceKm, durationMins]);

  return (
    <div className="relative w-full h-[240px] md:h-full min-h-[220px] border border-[var(--border-color)] rounded-2xl overflow-hidden shadow-md transition-all">
      {/* Visual Overlay badges when routing is loaded */}
      {distanceKm && durationMins && (
        <div className="absolute top-4 left-4 z-40 bg-[var(--bg-secondary)] border border-[var(--border-color)] px-4 py-2 rounded-xl shadow-lg flex gap-4 text-xs font-bold divide-x divide-[var(--border-color)]">
          <div className="flex flex-col">
            <span className="text-[10px] text-[var(--text-secondary)] uppercase font-semibold">Distance</span>
            <span className="text-indigo-600 dark:text-indigo-400 text-sm font-extrabold">{distanceKm.toFixed(1)} km</span>
          </div>
          <div className="flex flex-col pl-4">
            <span className="text-[10px] text-[var(--text-secondary)] uppercase font-semibold">ETA</span>
            <span className="text-indigo-600 dark:text-indigo-400 text-sm font-extrabold">{Math.round(durationMins)} mins</span>
          </div>
        </div>
      )}
      {/* Map DOM target */}
      <div ref={mapContainerRef} className="w-full h-full z-10" />
    </div>
  );
};
export default MapView;
