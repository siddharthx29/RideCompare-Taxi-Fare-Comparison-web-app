import { apiFetch } from './api';
import type { LocationInfo } from '../types/ride';

export interface GeocodeResult {
  name?: string;
  primaryText?: string;
  secondaryText?: string;
  displayName?: string;
  display_name?: string;
  lat: string | number;
  lng?: string | number;
  lon?: string | number;
  category?: string;
  address?: Record<string, string>;
  source?: string;
}

const CACHE_TTL_MS = 20 * 60 * 1000; // 20 minutes
const clientCache = new Map<string, { timestamp: number; data: GeocodeResult[] }>();

/**
 * Normalizes query string for reliable cache hits and fuzzy matching
 */
export const normalizeQuery = (text: string): string => {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
};

/**
 * Builds regional context from reference location
 */
export const buildLocationContext = (location: LocationInfo | null): string => {
  if (!location) return '';
  const address = location.address || {};
  return [
    address.city || address.town || address.municipality || address.village || address.suburb,
    address.state,
    address.country
  ]
    .filter(Boolean)
    .join(', ');
};

/**
 * Formats a clean primary text, secondary text, and combined display name
 */
export const formatPlaceDisplay = (
  rawName: string,
  rawSecondary?: string,
  rawDisplay?: string,
  address?: Record<string, string>
): { primaryText: string; secondaryText: string; displayName: string } => {
  let primary = (rawName || '').trim();
  if (!primary && rawDisplay) {
    primary = rawDisplay.split(',')[0].trim();
  }
  if (!primary && address) {
    primary = (address.amenity || address.building || address.shop || address.suburb || address.city || 'Location').trim();
  }

  let secondary = (rawSecondary || '').trim();
  if (!secondary && address) {
    const parts = [
      address.suburb || address.neighbourhood || address.quarter,
      address.city || address.town || address.municipality || address.village,
      address.state
    ].filter(Boolean);

    // Remove duplicates or components that already match primary name
    const normPrimary = normalizeQuery(primary);
    const uniqueParts = parts.filter(p => !normPrimary.includes(normalizeQuery(p)));
    secondary = uniqueParts.join(', ');
  }

  const displayName = secondary ? `${primary}, ${secondary}` : primary;
  return { primaryText: primary, secondaryText: secondary, displayName };
};

/**
 * Queries location autocomplete with Geoapify primary, OSM fallback, and instant client caching.
 */
export async function searchLocations(
  query: string,
  nearbyLocation: LocationInfo | null = null,
  signal?: AbortSignal
): Promise<GeocodeResult[]> {
  const trimmed = query.trim();
  if (trimmed.length < 2) {
    return [];
  }

  const normQuery = normalizeQuery(trimmed);
  const context = buildLocationContext(nearbyLocation);
  const nearCoordKey = nearbyLocation
    ? `${nearbyLocation.lat.toFixed(2)},${nearbyLocation.lng.toFixed(2)}`
    : '';
  const cacheKey = `${normQuery}|${nearCoordKey}|${context}`;

  // 1. Check in-memory client cache
  const cached = clientCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
    return cached.data;
  }

  let results: GeocodeResult[] = [];

  // 2. Primary: Query RideCompare backend (proxies to Geoapify with Nominatim fallback)
  try {
    const params = new URLSearchParams({ q: trimmed, limit: '8' });
    if (context) params.set('context', context);
    if (nearbyLocation) {
      params.set('near_lat', String(nearbyLocation.lat));
      params.set('near_lon', String(nearbyLocation.lng));
    }

    const response = await apiFetch(`/api/geocode?${params.toString()}`, { signal });
    if (response.ok) {
      const data = (await response.json()) as GeocodeResult[];
      if (Array.isArray(data) && data.length > 0) {
        results = data.map((item) => {
          const { primaryText, secondaryText, displayName } = formatPlaceDisplay(
            item.primaryText || item.name || '',
            item.secondaryText,
            item.displayName || item.display_name,
            item.address
          );
          return {
            ...item,
            primaryText,
            secondaryText,
            displayName,
            display_name: displayName,
            lat: Number(item.lat),
            lng: Number(item.lng ?? item.lon),
            lon: Number(item.lon ?? item.lng)
          };
        });
      }
    }
  } catch (backendError) {
    // If request was explicitly aborted due to user typing a newer character, propagate abort
    if (signal?.aborted) {
      throw backendError;
    }
    // 3. Fallback: Direct browser query to OpenStreetMap Nominatim if backend is unreachable
    try {
      const directUrl = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(
        trimmed
      )}&format=jsonv2&addressdetails=1&limit=6&accept-language=en`;
      const directRes = await fetch(directUrl, { signal });
      if (directRes.ok) {
        const raw = (await directRes.json()) as Array<{
          name?: string;
          display_name: string;
          lat: string;
          lon: string;
          type?: string;
          address?: Record<string, string>;
        }>;

        results = raw.map((item) => {
          const { primaryText, secondaryText, displayName } = formatPlaceDisplay(
            item.name || '',
            undefined,
            item.display_name,
            item.address
          );
          return {
            name: primaryText,
            primaryText,
            secondaryText,
            displayName,
            display_name: displayName,
            lat: parseFloat(item.lat),
            lng: parseFloat(item.lon),
            lon: parseFloat(item.lon),
            category: item.type,
            address: item.address || {},
            source: 'browser_fallback'
          };
        });
      }
    } catch {
      results = [];
    }
  }

  // 4. Save to client cache
  if (results.length > 0) {
    clientCache.set(cacheKey, { timestamp: Date.now(), data: results });
  }

  return results;
}

/**
 * Reverse geocodes coordinates to a human-readable location
 */
export async function reverseGeocodeLocation(
  lat: number,
  lon: number,
  signal?: AbortSignal
): Promise<GeocodeResult | null> {
  const cacheKey = `rev:${lat.toFixed(5)},${lon.toFixed(5)}`;
  const cached = clientCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS && cached.data.length > 0) {
    return cached.data[0];
  }

  try {
    const response = await apiFetch(`/api/geocode/reverse?lat=${lat}&lon=${lon}`, { signal });
    if (response.ok) {
      const data = (await response.json()) as GeocodeResult;
      if (data && (data.displayName || data.display_name || data.name)) {
        clientCache.set(cacheKey, { timestamp: Date.now(), data: [data] });
        return data;
      }
    }
  } catch {
    // Direct browser reverse fallback
    try {
      const nomUrl = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lon}&zoom=18&addressdetails=1&accept-language=en`;
      const directRes = await fetch(nomUrl, { signal });
      if (directRes.ok) {
        const item = await directRes.json();
        const { primaryText, secondaryText, displayName } = formatPlaceDisplay(
          item.name || '',
          undefined,
          item.display_name,
          item.address
        );
        const res: GeocodeResult = {
          name: primaryText,
          primaryText,
          secondaryText,
          displayName,
          display_name: displayName,
          lat,
          lng: lon,
          lon,
          address: item.address || {},
          source: 'browser_fallback'
        };
        clientCache.set(cacheKey, { timestamp: Date.now(), data: [res] });
        return res;
      }
    } catch {
      // Fallback below
    }
  }

  const fallbackLabel = `Location (${lat.toFixed(4)}, ${lon.toFixed(4)})`;
  return {
    name: fallbackLabel,
    primaryText: fallbackLabel,
    displayName: fallbackLabel,
    display_name: fallbackLabel,
    lat,
    lng: lon,
    lon,
    address: {}
  };
}
