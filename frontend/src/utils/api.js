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
  const fullUrl = url.startsWith("http") ? url : `${API_BASE_URL}${url.startsWith("/") ? "" : "/"}${url}`;

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
  } catch (networkErr) {
    // fetch() throws a TypeError when the backend is unreachable (wrong port,
    // server not started, DNS failure, or CORS preflight hard-blocked).
    throw new Error(
      `Unable to connect to the server at ${API_BASE_URL}. Make sure the backend server is running.`
    );
  }

  if (
    response.status === 401 &&
    !fullUrl.includes("/auth/login") &&
    !fullUrl.includes("/auth/register") &&
    !fullUrl.includes("/auth/verify-email") &&
    !fullUrl.includes("/auth/resend-verification")
  ) {
    window.dispatchEvent(new CustomEvent("auth:unauthorized"));
  }

  return response;
}
