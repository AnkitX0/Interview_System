import { API_BASE_URL } from "../config";

/**
 * Enhanced fetch client that automatically attaches `credentials: "include"`
 * for httpOnly cookie management and dispatches global auth:unauthorized on 401.
 *
 * Network-level failures (backend unreachable, wrong port, CORS preflight error)
 * are caught and re-thrown with a descriptive message instead of the raw browser
 * "Failed to fetch" string.
 */
export async function apiFetch(url, options = {}) {
  const cleanBase = (API_BASE_URL || "").replace(/\/+$/, "");
  const isAbsolute = url.startsWith("http://") || url.startsWith("https://");

  if (!cleanBase && !isAbsolute) {
    throw new Error(
      "Configuration Error: API base URL is missing. Please ensure VITE_API_BASE_URL is configured."
    );
  }

  const cleanPath = url.startsWith("/") ? url : `/${url}`;
  const fullUrl = isAbsolute ? url : `${cleanBase}${cleanPath}`;

  const headers = { ...options.headers };
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (!headers["X-Requested-With"]) {
    headers["X-Requested-With"] = "XMLHttpRequest";
  }

  const config = {
    ...options,
    headers,
    credentials: "include",
  };

  let response;
  try {
    response = await fetch(fullUrl, config);
  } catch {
    const isRenderBackend = cleanBase.includes("onrender.com");
    const coldStartHint = isRenderBackend
      ? " The server may be waking up from sleep (Render free instances take ~30-40s on first request). Please wait a moment and retry."
      : "";

    throw new Error(
      `Unable to connect to the server at ${cleanBase}.${coldStartHint}`
    );
  }

  if (
    response.status === 401 &&
    !fullUrl.includes("/auth/login") &&
    !fullUrl.includes("/auth/register") &&
    !fullUrl.includes("/auth/recovery")
  ) {
    window.dispatchEvent(new CustomEvent("auth:unauthorized"));
  }

  return response;
}
