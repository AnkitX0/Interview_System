import { API_BASE_URL } from "../config";

/**
 * Enhanced fetch client that automatically attaches `credentials: "include"`
 * for httpOnly cookie management and dispatches global auth:unauthorized on 401.
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

  const response = await fetch(fullUrl, config);

  if (
    response.status === 401 &&
    !fullUrl.includes("/auth/login") &&
    !fullUrl.includes("/auth/register")
  ) {
    window.dispatchEvent(new CustomEvent("auth:unauthorized"));
  }

  return response;
}
