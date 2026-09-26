import { apiFetch } from './api';
import type { LocationInfo } from '../types/ride';

export type GeocodeAddress = Record<string, string>;

export interface GeocodeResult {
  id?: number | string;
  name?: string;
  primaryText?: string;
  secondaryText?: string;
  displayName?: string;
  display_name?: string;
  latitude?: number;
  longitude?: number;
  lat: string | number;
  lng?: string | number;
  lon?: string | number;
  category?: string;
  address?: Record<string, string>;
  source?: string;
  provider?: string;
  importance?: number;
}

const CACHE_TTL_MS = 30 * 60 * 1000; // 30 minutes in-memory cache
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
  address?: GeocodeAddress
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
      address.road,
      address.suburb || address.neighbourhood || address.quarter,
      address.city || address.town || address.municipality || address.village,
      address.district,
      address.state
    ].filter(Boolean) as string[];

    // Remove duplicates or components that already match primary name
    const normPrimary = normalizeQuery(primary);
    const uniqueParts = parts.filter(p => !normPrimary.includes(normalizeQuery(p)));
    secondary = uniqueParts.slice(0, 3).join(', ');
  }

  const displayName = secondary ? `${primary}, ${secondary}` : primary;
  return { primaryText: primary, secondaryText: secondary, displayName };
};

/**
 * Queries location autocomplete via backend location service:
 * Photon primary -> Cache -> Fallbacks with local client caching.
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

  // 2. Primary: Query RideCompare backend location service
  try {
    const params = new URLSearchParams({ q: trimmed, limit: '8' });
    if (context) params.set('context', context);
    if (nearbyLocation) {
      params.set('near_lat', String(nearbyLocation.lat));
      params.set('near_lon', String(nearbyLocation.lng));
    }

    // Try dedicated /api/location/search endpoint first
    let response = await apiFetch(`/api/location/search?${params.toString()}`, { signal });
    if (!response.ok) {
      // Fallback to /api/geocode endpoint
      response = await apiFetch(`/api/geocode?${params.toString()}`, { signal });
    }

    if (response.ok) {
      const rawData = await response.json();
      const rawList: GeocodeResult[] = Array.isArray(rawData)
        ? rawData
        : Array.isArray(rawData?.results)
        ? rawData.results
        : [];

      if (rawList.length > 0) {
        results = rawList.map((item) => {
          const lat = Number(item.latitude ?? item.lat);
          const lng = Number(item.longitude ?? item.lng ?? item.lon);
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
            latitude: lat,
            longitude: lng,
            lat,
            lng,
            lon: lng
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
          const lat = parseFloat(item.lat);
          const lng = parseFloat(item.lon);
          return {
            name: primaryText,
            primaryText,
            secondaryText,
            displayName,
            display_name: displayName,
            latitude: lat,
            longitude: lng,
            lat,
            lng,
            lon: lng,
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
 * Reverse geocodes coordinates to a detailed human-readable local address
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
    let response = await apiFetch(`/api/location/reverse?lat=${lat}&lon=${lon}`, { signal });
    if (!response.ok) {
      response = await apiFetch(`/api/geocode/reverse?lat=${lat}&lon=${lon}`, { signal });
    }

    if (response.ok) {
      const data = (await response.json()) as GeocodeResult;
      if (data && (data.displayName || data.display_name || data.name)) {
        const { primaryText, secondaryText, displayName } = formatPlaceDisplay(
          data.primaryText || data.name || '',
          data.secondaryText,
          data.displayName || data.display_name,
          data.address
        );
        const enriched: GeocodeResult = {
          ...data,
          primaryText,
          secondaryText,
          displayName,
          display_name: displayName,
          latitude: lat,
          longitude: lon,
          lat,
          lng: lon,
          lon
        };
        clientCache.set(cacheKey, { timestamp: Date.now(), data: [enriched] });
        return enriched;
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
          latitude: lat,
          longitude: lon,
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
    latitude: lat,
    longitude: lon,
    lat,
    lng: lon,
    lon,
    address: {}
  };
}
