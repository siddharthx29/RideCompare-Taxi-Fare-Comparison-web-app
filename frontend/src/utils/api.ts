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
    let payload: any = null;
    try {
      const clone = response.clone();
      payload = await clone.json();
    } catch {
      try {
        const clone = response.clone();
        payload = await clone.text();
      } catch {}
    }

    let errMsg = `HTTP error! status: ${response.status}`;
    if (payload) {
      if (typeof payload === 'object') {
        errMsg = payload.error || payload.message || payload.detail || errMsg;
      } else if (typeof payload === 'string' && payload.trim().length > 0) {
        errMsg = payload;
      }
    }
    throw new Error(errMsg);
  } catch (error: any) {
    // If relative fetch failed (e.g. proxy issue), try direct fallback to http://127.0.0.1:5000
    if (primaryUrl.startsWith('/') && typeof window !== 'undefined') {
      try {
        const directUrl = `http://127.0.0.1:5000${cleanEndpoint}`;
        const fallbackRes = await fetch(directUrl, options);
        if (fallbackRes.ok) {
          return fallbackRes;
        }
      } catch {}
      try {
        const directUrl2 = `http://localhost:5000${cleanEndpoint}`;
        const fallbackRes2 = await fetch(directUrl2, options);
        if (fallbackRes2.ok) {
          return fallbackRes2;
        }
      } catch {}
    }

    let finalError = error;
    if (error instanceof TypeError && (error.message.includes('Failed to fetch') || error.message.includes('NetworkError'))) {
      finalError = new Error('Network Connection Error: Failed to connect to the backend API server. Please ensure the Python FastAPI backend is running on port 5000 (uvicorn backend.app.main:app --port 5000).');
    }
    console.error(`[API Error] Endpoint: ${cleanEndpoint} | Error:`, finalError);
    throw finalError;
  }
}
