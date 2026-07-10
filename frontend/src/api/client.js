import axios from "axios";

// Single axios instance for the whole workspace. The base URL is relative so
// the Vite dev proxy (and any production reverse proxy) forwards `/api/v1`
// to the FastAPI backend — the frontend never hardcodes a host.
export const apiClient = axios.create({
  baseURL: "/api/v1",
  timeout: 60000,
  headers: { "Content-Type": "application/json" },
});

const MAX_RETRIES = 2;
const RETRY_BASE_MS = 400;
const isRetryable = (error) => {
  if (error.code === "ECONNABORTED" || error.message === "Network Error") return true;
  const status = error.response?.status;
  return status === 502 || status === 503 || status === 504;
};

// Transient-failure retry with linear backoff. Only idempotent GETs are
// retried automatically; POSTs (comparisons) are left to the caller.
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config || {};
    const method = (config.method || "get").toLowerCase();
    config.__retryCount = config.__retryCount || 0;
    if (method === "get" && isRetryable(error) && config.__retryCount < MAX_RETRIES) {
      config.__retryCount += 1;
      await new Promise((r) => setTimeout(r, RETRY_BASE_MS * config.__retryCount));
      return apiClient(config);
    }
    return Promise.reject(normalizeError(error));
  }
);

/**
 * Normalize any axios failure into the platform's error shape so the whole
 * UI handles errors identically. Mirrors the backend's error envelope
 * ({ error: { type, message, status_code } }) when present.
 */
export function normalizeError(error) {
  const envelope = error.response?.data?.error;
  return {
    status: error.response?.status ?? 0,
    type: envelope?.type ?? (error.response ? "http_error" : "network_error"),
    message:
      envelope?.message ??
      (error.response
        ? `Request failed with status ${error.response.status}`
        : "Unable to reach the intelligence platform. Is the backend running?"),
    details: envelope?.details ?? null,
  };
}

/** Drop null/undefined/empty query params so URLs stay clean. */
export function cleanParams(params = {}) {
  const out = {};
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== "") out[k] = v;
  }
  return out;
}
