const DEFAULT_RENDER_URL = 'https://taxi-fare-comparison-web-app.onrender.com';

const isBrowser = typeof window !== 'undefined';

const isLocalHost = (): boolean => {
  if (!isBrowser) return false;
  const host = window.location.hostname;
  return host === 'localhost' || host === '127.0.0.1' || host === '0.0.0.0';
};

const getApiBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && envUrl.trim()) {
    return envUrl.trim().replace(/\/+$/, '');
  }

  // When deployed on Vercel or external domain:
  // If vercel.json is present, relative path '' is proxied to Render.
  // Otherwise, direct requests to Render backend will be attempted as fallback.
  return '';
};

const API_BASE_URL = getApiBaseUrl();

const getErrorMessage = (payload: unknown, status: number): string => {
  const fallback = `HTTP error! status: ${status}`;
  if (typeof payload === 'string' && payload.trim()) return payload;
  if (typeof payload !== 'object' || payload === null) return fallback;

  const record = payload as Record<string, unknown>;
  const message = [record.error, record.message, record.detail].find(
    (value): value is string => typeof value === 'string' && value.trim().length > 0
  );
  return message || fallback;
};

const tryFetch = async (url: string, options: RequestInit, timeoutMs = 6000): Promise<Response | null> => {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    const response = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(timeoutId);
    return response.ok ? response : null;
  } catch {
    return null;
  }
};

export async function apiFetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;

  // 1. Primary Attempt: uses configured VITE_API_URL or relative path (handled by Vercel rewrites / Vite proxy)
  const primaryUrl = `${API_BASE_URL}${cleanEndpoint}`;

  try {
    const response = await fetch(primaryUrl, options);
    if (response.ok) {
      return response;
    }

    // If HTTP error code returned (400, 404, 500, etc.)
    let payload: unknown = null;
    try {
      payload = await response.clone().json();
    } catch {
      try {
        payload = await response.clone().text();
      } catch {
        payload = null;
      }
    }

    // In production on Vercel: if relative path returns 404 (e.g. vercel.json rewrite pending),
    // fallback directly to the Render backend over HTTPS
    if (!isLocalHost() && response.status === 404 && primaryUrl.startsWith('/')) {
      const renderFallback = await tryFetch(`${DEFAULT_RENDER_URL}${cleanEndpoint}`, options);
      if (renderFallback) return renderFallback;
    }

    throw new Error(getErrorMessage(payload, response.status));
  } catch (error: unknown) {
    // 2. Fallback handling when network fetch fails
    if (isLocalHost()) {
      // Local development fallback to port 5000
      const localRes = await tryFetch(`http://127.0.0.1:5000${cleanEndpoint}`, options, 5000);
      if (localRes) return localRes;
      const localhostRes = await tryFetch(`http://localhost:5000${cleanEndpoint}`, options, 5000);
      if (localhostRes) return localhostRes;
    } else {
      // Remote production fallback (Vercel -> Render)
      const renderFallback = await tryFetch(`${DEFAULT_RENDER_URL}${cleanEndpoint}`, options);
      if (renderFallback) return renderFallback;
    }

    let finalError = error instanceof Error ? error : new Error('Unknown API request failure.');

    if (error instanceof TypeError && (error.message.includes('Failed to fetch') || error.message.includes('NetworkError'))) {
      if (isLocalHost()) {
        finalError = new Error(
          'Network Connection Error: Failed to connect to the backend API server. ' +
          'Please ensure the Python FastAPI backend is running on port 5000 (uvicorn backend.app.main:app --port 5000).'
        );
      } else {
        finalError = new Error(
          'Network Connection Error: Unable to reach the backend API server. ' +
          'If the backend is hosted on Render (free tier), the server may be spinning up from sleep mode (takes ~30–50 seconds). ' +
          'Please wait a few seconds and try your search again.'
        );
      }
    }

    console.error('[API Error]', finalError);
    throw finalError;
  }
}
