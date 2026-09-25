const getApiBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl) return envUrl;
  
  // In browser, using relative path allows Vite dev proxy or production static serving to handle routing seamlessly
  if (typeof window !== 'undefined') {
    return '';
  }
  
  return 'http://127.0.0.1:5000';
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

const tryFetch = async (url: string, options: RequestInit): Promise<Response | null> => {
  try {
    const response = await fetch(url, options);
    return response.ok ? response : null;
  } catch {
    return null;
  }
};

export async function apiFetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  
  // Primary URL using current origin / proxy
  const primaryUrl = `${API_BASE_URL}${cleanEndpoint}`;

  try {
    const response = await fetch(primaryUrl, options);
    if (response.ok) {
      return response;
    }
    
    // If not OK, parse payload for error message
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

    throw new Error(getErrorMessage(payload, response.status));
  } catch (error: unknown) {
    // If relative fetch failed (e.g. proxy issue), try direct fallback to http://127.0.0.1:5000
    if (primaryUrl.startsWith('/') && typeof window !== 'undefined') {
      const fallbackRes = await tryFetch(`http://127.0.0.1:5000${cleanEndpoint}`, options);
      if (fallbackRes) return fallbackRes;
      const fallbackResLocalhost = await tryFetch(`http://localhost:5000${cleanEndpoint}`, options);
      if (fallbackResLocalhost) return fallbackResLocalhost;
    }

    let finalError = error instanceof Error ? error : new Error('Unknown API request failure.');
    if (error instanceof TypeError && (error.message.includes('Failed to fetch') || error.message.includes('NetworkError'))) {
      finalError = new Error('Network Connection Error: Failed to connect to the backend API server. Please ensure the Python FastAPI backend is running on port 5000 (uvicorn backend.app.main:app --port 5000).');
    }
    console.error('[API Error]', finalError);
    throw finalError;
  }
}
