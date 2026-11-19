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

const CLIENT_CATALOG: MapboxSuggestion[] = [
  {
    mapbox_id: 'cat:lulu_kochi',
    name: 'LuLu International Shopping Mall',
    primaryText: 'LuLu International Shopping Mall',
    secondaryText: 'Edappally, Kochi, Kerala',
    displayName: 'LuLu International Shopping Mall, Edappally, Kochi, Kerala',
    place_formatted: 'Edappally, Kochi, Kerala',
    full_address: '34/1000, Old NH 47, Edappally, Kochi, Kerala 682024',
    latitude: 10.0284,
    longitude: 76.3074,
    city: 'Kochi',
    district: 'Ernakulam',
    state: 'Kerala',
    postcode: '682024',
    country: 'India',
    address: { road: 'Old NH 47', suburb: 'Edappally', city: 'Kochi', state: 'Kerala', country: 'India' },
    provider: 'mapbox'
  },
  {
    mapbox_id: 'cat:kalamassery',
    name: 'Kalamassery',
    primaryText: 'Kalamassery',
    secondaryText: 'Kochi, Kerala, India',
    displayName: 'Kalamassery, Kochi, Kerala, India',
    place_formatted: 'Kochi, Kerala, India',
    full_address: 'Kalamassery, Kochi, Ernakulam, Kerala 682033',
    latitude: 10.0545,
    longitude: 76.3190,
    city: 'Kochi',
    district: 'Ernakulam',
    state: 'Kerala',
    postcode: '682033',
    country: 'India',
    address: { suburb: 'Kalamassery', city: 'Kochi', district: 'Ernakulam', state: 'Kerala', country: 'India' },
    provider: 'mapbox'
  },
  {
    mapbox_id: 'cat:aluva_metro',
    name: 'Aluva Metro Station',
    primaryText: 'Aluva Metro Station',
    secondaryText: 'Aluva, Ernakulam, Kerala',
    displayName: 'Aluva Metro Station, Aluva, Ernakulam, Kerala',
    place_formatted: 'Aluva, Ernakulam, Kerala',
    full_address: 'Aluva Metro Station, Aluva, Ernakulam, Kerala 683101',
    latitude: 10.1098,
    longitude: 76.3533,
    city: 'Kochi',
    district: 'Ernakulam',
    state: 'Kerala',
    country: 'India',
    address: { suburb: 'Aluva', city: 'Kochi', state: 'Kerala', country: 'India' },
    provider: 'mapbox'
  },
  {
    mapbox_id: 'cat:kochi_airport',
    name: 'Cochin International Airport',
    primaryText: 'Cochin International Airport',
    secondaryText: 'Nedumbassery, Kerala',
    displayName: 'Cochin International Airport, Nedumbassery, Kerala',
    place_formatted: 'Nedumbassery, Kerala',
    full_address: 'Airport Road, Nedumbassery, Kerala 683111',
    latitude: 10.1556,
    longitude: 76.3906,
    city: 'Nedumbassery',
    district: 'Ernakulam',
    state: 'Kerala',
    country: 'India',
    address: { road: 'Airport Road', suburb: 'Nedumbassery', city: 'Kochi', state: 'Kerala', country: 'India' },
    provider: 'mapbox'
  },
  {
    mapbox_id: 'cat:ernakulam_south',
    name: 'Ernakulam Junction Railway Station',
    primaryText: 'Ernakulam Junction Railway Station',
    secondaryText: 'Ernakulam South, Kochi, Kerala',
    displayName: 'Ernakulam Junction Railway Station, Ernakulam South, Kochi, Kerala',
    place_formatted: 'Ernakulam South, Kochi, Kerala',
    full_address: 'Station Road, Ernakulam South, Kochi, Kerala 682016',
    latitude: 9.9706,
    longitude: 76.2907,
    city: 'Kochi',
    district: 'Ernakulam',
    state: 'Kerala',
    country: 'India',
    address: { road: 'Station Road', suburb: 'Ernakulam South', city: 'Kochi', state: 'Kerala', country: 'India' },
    provider: 'mapbox'
  },
  {
    mapbox_id: 'cat:marine_drive',
    name: 'Marine Drive Kochi',
    primaryText: 'Marine Drive',
    secondaryText: 'Kochi, Kerala, India',
    displayName: 'Marine Drive, Kochi, Kerala, India',
    place_formatted: 'Kochi, Kerala, India',
    full_address: 'Marine Drive, Ernakulam, Kochi, Kerala 682031',
    latitude: 9.9816,
    longitude: 76.2763,
    city: 'Kochi',
    state: 'Kerala',
    country: 'India',
    address: { suburb: 'Marine Drive', city: 'Kochi', state: 'Kerala', country: 'India' },
    provider: 'mapbox'
  },
  {
    mapbox_id: 'cat:times_square',
    name: 'Times Square',
    primaryText: 'Times Square',
    secondaryText: 'Manhattan, New York, United States',
    displayName: 'Times Square, Manhattan, New York, United States',
    place_formatted: 'Manhattan, New York, United States',
    full_address: 'Broadway & 7th Ave, New York, NY 10036',
    latitude: 40.7580,
    longitude: -73.9855,
    city: 'New York',
    state: 'New York',
    country: 'United States',
    address: { road: 'Broadway', city: 'New York', state: 'New York', country: 'United States' },
    provider: 'mapbox'
  },
  {
    mapbox_id: 'cat:burj_khalifa',
    name: 'Burj Khalifa',
    primaryText: 'Burj Khalifa',
    secondaryText: 'Downtown Dubai, Dubai, United Arab Emirates',
    displayName: 'Burj Khalifa, Downtown Dubai, Dubai, United Arab Emirates',
    place_formatted: 'Downtown Dubai, Dubai, United Arab Emirates',
    full_address: '1 Sheikh Mohammed bin Rashid Blvd, Downtown Dubai, Dubai',
    latitude: 25.1972,
    longitude: 55.2744,
    city: 'Dubai',
    state: 'Dubai',
    country: 'United Arab Emirates',
    address: { road: '1 Sheikh Mohammed bin Rashid Blvd', city: 'Dubai', country: 'United Arab Emirates' },
    provider: 'mapbox'
  },
  {
    mapbox_id: 'cat:london_bridge',
    name: 'London Bridge',
    primaryText: 'London Bridge',
    secondaryText: 'London, Greater London, United Kingdom',
    displayName: 'London Bridge, London, Greater London, United Kingdom',
    place_formatted: 'London, Greater London, United Kingdom',
    full_address: 'London Bridge, London SE1 9RA',
    latitude: 51.5079,
    longitude: -0.0877,
    city: 'London',
    state: 'Greater London',
    country: 'United Kingdom',
    address: { road: 'London Bridge', city: 'London', country: 'United Kingdom' },
    provider: 'mapbox'
  },
  {
    mapbox_id: 'cat:shibuya',
    name: 'Shibuya Station',
    primaryText: 'Shibuya Station',
    secondaryText: 'Shibuya, Tokyo, Japan',
    displayName: 'Shibuya Station, Shibuya, Tokyo, Japan',
    place_formatted: 'Shibuya, Tokyo, Japan',
    full_address: 'Shibuya, Tokyo 150-0002',
    latitude: 35.6580,
    longitude: 139.7016,
    city: 'Tokyo',
    state: 'Tokyo',
    country: 'Japan',
    address: { suburb: 'Shibuya', city: 'Tokyo', country: 'Japan' },
    provider: 'mapbox'
  }
];

async function searchPhotonDirect(query: string, signal?: AbortSignal): Promise<MapboxSuggestion[]> {
  try {
    const res = await fetch(`https://photon.komoot.io/api/?q=${encodeURIComponent(query)}&limit=8`, { signal });
    if (res.ok) {
      const data = await res.json();
      const features = Array.isArray(data?.features) ? data.features : [];
      return features.map((f: { geometry?: { coordinates?: number[] }; properties?: Record<string, string> }) => {
        const coords = f.geometry?.coordinates || [0, 0];
        const props = f.properties || {};
        const primary = (props.name || props.street || props.city || 'Location').trim();
        const secParts = [props.street, props.suburb || props.district, props.city || props.town, props.state, props.country].filter(Boolean);
        const secondary = secParts.slice(0, 3).join(', ');
        const display = secondary ? `${primary}, ${secondary}` : primary;
        return {
          mapbox_id: `photon:${props.osm_type || 'p'}:${props.osm_id || Math.random()}`,
          name: primary,
          primaryText: primary,
          secondaryText: secondary,
          displayName: display,
          display_name: display,
          place_formatted: secondary,
          full_address: display,
          latitude: coords[1],
          longitude: coords[0],
          lat: coords[1],
          lng: coords[0],
          lon: coords[0],
          city: props.city || props.town || '',
          district: props.district || '',
          state: props.state || '',
          country: props.country || '',
          postcode: props.postcode || '',
          address: {
            road: props.street || '',
            suburb: props.suburb || '',
            city: props.city || props.town || '',
            state: props.state || '',
            country: props.country || ''
          },
          provider: 'mapbox',
          source: 'photon'
        };
      });
    }
  } catch {
    return [];
  }
  return [];
}

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
    // Direct Client-Side Photon & Curated Catalog Fallback
    try {
      const qLower = normQuery;
      const catalogMatches = CLIENT_CATALOG.filter(c => {
        const n = normalizeQuery(c.name || '');
        const p = normalizeQuery(c.primaryText || '');
        const s = normalizeQuery(c.secondaryText || '');
        return n.includes(qLower) || p.includes(qLower) || s.includes(qLower);
      });

      const photonMatches = await searchPhotonDirect(trimmed, signal);

      const combined = [
        ...catalogMatches,
        ...photonMatches.filter(pm => !catalogMatches.some(cm => cm.name?.toLowerCase() === pm.name?.toLowerCase()))
      ];

      if (combined.length > 0) {
        suggestions = combined.slice(0, 8);
        for (const item of suggestions) {
          if (item.mapbox_id && Number.isFinite(item.latitude) && Number.isFinite(item.longitude)) {
            retrieveCache.set(`ret:${item.mapbox_id}`, {
              timestamp: Date.now(),
              data: {
                label: item.displayName || item.name || '',
                lat: Number(item.latitude),
                lng: Number(item.longitude),
                address: item.address,
                placeName: item.primaryText || item.name,
                locality: item.secondaryText,
                city: item.city,
                state: item.state,
                country: item.country
              }
            });
          }
        }
      }
    } catch {
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
    try {
      const photonRev = await fetch(`https://photon.komoot.io/reverse?lat=${lat}&lon=${lon}`, { signal });
      if (photonRev.ok) {
        const revData = await photonRev.json();
        const feat = revData?.features?.[0];
        if (feat) {
          const props = feat.properties || {};
          const primary = (props.name || props.street || props.city || 'Location').trim();
          const secParts = [props.street, props.suburb || props.district, props.city || props.town, props.state, props.country].filter(Boolean);
          const secondary = secParts.slice(0, 3).join(', ');
          const display = secondary ? `${primary}, ${secondary}` : primary;
          const loc: LocationInfo = {
            label: display,
            lat,
            lng: lon,
            address: { road: props.street || '', suburb: props.suburb || '', city: props.city || props.town || '', state: props.state || '', country: props.country || '' },
            placeName: primary,
            locality: secondary,
            city: props.city || props.town,
            state: props.state,
            country: props.country
          };
          reverseCache.set(cacheKey, { timestamp: Date.now(), data: loc });
          return loc;
        }
      }
    } catch {
      // Ignore network errors on reverse geocode fallback
    }
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
