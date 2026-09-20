const getApiBaseUrl = (): string => {
  // If there's an environment variable injected
  const envUrl = import.meta.env.VITE_API_URL;
  
  if (typeof window !== 'undefined' && window.location) {
    const hostname = window.location.hostname;
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      // If the envUrl is present and does not point to localhost, use it.
      if (envUrl && !envUrl.includes('localhost') && !envUrl.includes('127.0.0.1')) {
        return envUrl;
      }
      // Since the backend serves the frontend static build from the same server,
      // we default to the current domain origin to prevent CORS/cross-origin network errors.
      return window.location.origin;
    }
  }
  
  return envUrl || 'http://localhost:5000';
};

const API_BASE_URL = getApiBaseUrl();

export async function apiFetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
  const baseUrl = API_BASE_URL.endsWith('/') ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const fullUrl = `${baseUrl}${cleanEndpoint}`;

  // Log Request URL, Method, and Payload
  console.log(`[API Request] URL: ${fullUrl}`);
  console.log(`[API Request] Method: ${options.method || 'GET'}`);
  if (options.body) {
    console.log(`[API Request Payload]`, options.body);
  }

  try {
    const response = await fetch(fullUrl, options);
    
    // Log response status
    console.log(`[API Response] URL: ${fullUrl} | Status: ${response.status} ${response.statusText}`);

    // Clone response to parse and log payload safely without locking the body stream
    const responseClone = response.clone();
    let payload: any = null;
    try {
      const contentType = responseClone.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        payload = await responseClone.json();
      } else {
        payload = await responseClone.text();
      }
      console.log(`[API Response Body] URL: ${fullUrl} | Body:`, payload);
    } catch (logErr) {
      console.warn(`[API Response Body Log Error] URL: ${fullUrl} | Could not read body:`, logErr);
    }

    if (!response.ok) {
      let errMsg = `HTTP error! status: ${response.status}`;
      if (payload) {
        if (typeof payload === 'object') {
          errMsg = payload.error || payload.message || errMsg;
        } else if (typeof payload === 'string' && payload.trim().length > 0) {
          errMsg = payload;
        }
      }
      throw new Error(errMsg);
    }

    return response;
  } catch (error: any) {
    let finalError = error;
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      finalError = new Error('Network Connection Error: Failed to connect to the backend API server. Please check your network connection or backend service status.');
    }
    console.error(`[API Error Details] URL: ${fullUrl} | Error:`, finalError);
    throw finalError;
  }
}

