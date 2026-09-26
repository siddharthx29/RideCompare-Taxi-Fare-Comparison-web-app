import { apiFetch } from './api';
import type { LocationInfo } from '../types/ride';

export type GeocodeAddress = Record<string, string>;

export interface GeocodeResult {
  id?: number | string;
  mapbox_id?: string;
  name?: string;
  primaryText?: string;
  secondaryText?: string;
  displayName?: string;
  display_name?: string;
  place_formatted?: string;
  full_address?: string;
  feature_type?: string;
  formatted_address?: string;
  latitude?: number;
  longitude?: number;
  lat?: string | number;
  lng?: string | number;
  lon?: string | number;
  city?: string;
  district?: string;
  suburb?: string;
  state?: string;
  postcode?: string;
  country?: string;
  category?: string;
  address?: Record<string, string>;
  source?: string;
  provider?: string;
  importance?: number;
}

export type MapboxSuggestion = GeocodeResult;

const CACHE_TTL_MS = 30 * 60 * 1000; // 30 minutes in-memory cache
const suggestCache = new Map<string, { timestamp: number; data: MapboxSuggestion[] }>();
const retrieveCache = new Map<string, { timestamp: number; data: LocationInfo }>();
const reverseCache = new Map<string, { timestamp: number; data: LocationInfo }>();

/**
 * Generates a unique UUIDv4 session token for Mapbox Search Box interactive sessions.
 */
export const generateSessionToken = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

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
    address.city || address.town || address.municipality || address.village || address.suburb || location.city,
    address.state || location.state,
    address.country || location.country
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
      address.suburb || address.neighbourhood,
      address.city || address.town,
      address.district,
      address.state,
      address.country
    ].filter(Boolean) as string[];

    const normPrimary = normalizeQuery(primary);
    const uniqueParts = parts.filter(p => !normPrimary.includes(normalizeQuery(p)));
    secondary = uniqueParts.slice(0, 3).join(', ');
  }

  const displayName = secondary ? `${primary}, ${secondary}` : primary;
  return { primaryText: primary, secondaryText: secondary, displayName };
};

/**
 * Primary Mapbox Search Box /suggest:
 * - Debounced interactive search-as-you-type
 * - Sends session token for search sessions
 * - Applies proximity biasing from nearbyLocation if available
 * - Worldwide place discovery (not restricted to India)
 */
export async function suggestLocations(
  query: string,
  sessionToken: string,
  nearbyLocation: LocationInfo | null = null,
  signal?: AbortSignal
): Promise<MapboxSuggestion[]> {
  const trimmed = query.trim();
  if (trimmed.length < 2) {
    return [];
  }

  const normQuery = normalizeQuery(trimmed);
  const nearKey = nearbyLocation
    ? `${nearbyLocation.lat.toFixed(2)},${nearbyLocation.lng.toFixed(2)}`
    : '';
  const cacheKey = `sug:${normQuery}|${nearKey}`;

  // 1. Check client memory cache
  const cached = suggestCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
    return cached.data;
  }

  const params = new URLSearchParams({
    q: trimmed,
    session_token: sessionToken,
    limit: '8'
  });

  if (nearbyLocation && Number.isFinite(nearbyLocation.lat) && Number.isFinite(nearbyLocation.lng)) {
    params.set('near_lat', String(nearbyLocation.lat));
    params.set('near_lon', String(nearbyLocation.lng));
    params.set('proximity', `${nearbyLocation.lng.toFixed(5)},${nearbyLocation.lat.toFixed(5)}`);
  }

  let suggestions: MapboxSuggestion[] = [];

  try {
    let response = await apiFetch(`/api/location/suggest?${params.toString()}`, { signal });
    if (!response.ok) {
      response = await apiFetch(`/location/suggest?${params.toString()}`, { signal });
    }

    if (response.ok) {
      const data = await response.json();
      const rawList: MapboxSuggestion[] = Array.isArray(data?.suggestions)
        ? data.suggestions
        : Array.isArray(data)
        ? data
        : [];

      suggestions = rawList.map((item) => {
        const { primaryText, secondaryText, displayName } = formatPlaceDisplay(
          item.primaryText || item.name || '',
          item.secondaryText || item.place_formatted,
          item.displayName || item.display_name,
          item.address
        );
        return {
          ...item,
          mapbox_id: item.mapbox_id || String(item.id || ''),
          primaryText,
          secondaryText,
          displayName,
          display_name: displayName,
        };
      });
    }
  } catch (error) {
    if (signal?.aborted) {
      throw error;
    }
    // Backward-compatibility fallback to /api/location/search
    try {
      const fallbackRes = await apiFetch(`/api/location/search?q=${encodeURIComponent(trimmed)}&limit=8`, { signal });
      if (fallbackRes.ok) {
        const fbData = await fallbackRes.json();
        const list: MapboxSuggestion[] = Array.isArray(fbData?.results) ? fbData.results : [];
        suggestions = list.map((item) => {
          const { primaryText, secondaryText, displayName } = formatPlaceDisplay(
            item.primaryText || item.name || '',
            item.secondaryText,
            item.displayName || item.display_name,
            item.address
          );
          return {
            ...item,
            mapbox_id: item.mapbox_id || String(item.id || ''),
            primaryText,
            secondaryText,
            displayName,
            display_name: displayName,
          };
        });
      }
    } catch (fallbackError) {
      if (signal?.aborted) {
        throw fallbackError;
      }
      // If it's a network connection error (e.g. backend offline), re-throw so the UI can inform the user
      if (
        fallbackError instanceof Error &&
        (fallbackError.message.includes('Network Connection Error') ||
          fallbackError.message.includes('Failed to fetch') ||
          fallbackError.message.includes('NetworkError'))
      ) {
        throw fallbackError;
      }
      suggestions = [];
    }
  }

  if (suggestions.length > 0) {
    suggestCache.set(cacheKey, { timestamp: Date.now(), data: suggestions });
  }

  return suggestions;
}

/**
 * Mapbox Search Box /retrieve:
 * - Triggered ONLY upon user selecting a suggestion
 * - Retrieves authoritative coordinates (latitude, longitude) and normalized address
 * - Completes session billing cycle
 */
export async function retrieveLocation(
  mapboxId: string,
  sessionToken: string,
  signal?: AbortSignal
): Promise<LocationInfo | null> {
  if (!mapboxId) return null;

  const cacheKey = `ret:${mapboxId}`;
  const cached = retrieveCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
    return cached.data;
  }

  try {
    const params = new URLSearchParams({
      id: mapboxId,
      session_token: sessionToken
    });

    let response = await apiFetch(`/api/location/retrieve?${params.toString()}`, { signal });
    if (!response.ok) {
      response = await apiFetch(`/location/retrieve?${params.toString()}`, { signal });
    }

    if (response.ok) {
      const item = await response.json();
      const lat = Number(item.latitude ?? item.lat);
      const lng = Number(item.longitude ?? item.lng ?? item.lon);

      if (Number.isFinite(lat) && Number.isFinite(lng)) {
        const chosenLabel = item.displayName || item.display_name || item.formatted_address || item.primaryText || item.name || 'Selected Location';
        const loc: LocationInfo = {
          label: chosenLabel,
          lat,
          lng,
          address: item.address,
          placeName: item.primaryText || item.name,
          locality: item.secondaryText || item.suburb || item.locality,
          city: item.city || item.address?.city || item.address?.town,
          state: item.state || item.address?.state,
          country: item.country || item.address?.country
        };
        retrieveCache.set(cacheKey, { timestamp: Date.now(), data: loc });
        return loc;
      }
    }
  } catch (error) {
    if (signal?.aborted) throw error;
    console.warn('[Retrieve Location Error]', error);
  }

  return null;
}

/**
 * Reverse geocodes coordinates to a clean structured local address
 */
export async function reverseGeocodeLocation(
  lat: number,
  lon: number,
  signal?: AbortSignal
): Promise<LocationInfo | null> {
  const cacheKey = `rev:${lat.toFixed(5)},${lon.toFixed(5)}`;
  const cached = reverseCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
    return cached.data;
  }

  try {
    let response = await apiFetch(`/api/location/reverse?lat=${lat}&lon=${lon}`, { signal });
    if (!response.ok) {
      response = await apiFetch(`/location/reverse?lat=${lat}&lon=${lon}`, { signal });
    }

    if (response.ok) {
      const data = await response.json();
      if (data && (data.displayName || data.display_name || data.name || data.formatted_address)) {
        const { primaryText, secondaryText, displayName } = formatPlaceDisplay(
          data.primaryText || data.name || '',
          data.secondaryText,
          data.displayName || data.display_name || data.formatted_address,
          data.address
        );

        const loc: LocationInfo = {
          label: displayName,
          lat,
          lng: lon,
          address: data.address,
          placeName: primaryText,
          locality: secondaryText || data.suburb,
          city: data.city || data.address?.city || data.address?.town,
          state: data.state || data.address?.state,
          country: data.country || data.address?.country
        };

        reverseCache.set(cacheKey, { timestamp: Date.now(), data: loc });
        return loc;
      }
    }
  } catch (error) {
    if (signal?.aborted) throw error;
    console.warn('[Reverse Geocode Error]', error);
  }

  const fallbackLabel = `Location (${lat.toFixed(4)}, ${lon.toFixed(4)})`;
  return {
    label: fallbackLabel,
    lat,
    lng: lon,
    address: {}
  };
}

/**
 * Backward-compatible searchLocations helper (for any callers expecting GeocodeResult[])
 */
export async function searchLocations(
  query: string,
  nearbyLocation: LocationInfo | null = null,
  signal?: AbortSignal
): Promise<GeocodeResult[]> {
  const sessionToken = generateSessionToken();
  return suggestLocations(query, sessionToken, nearbyLocation, signal);
}
