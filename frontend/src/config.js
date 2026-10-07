/**
 * Frontend Application Configuration
 * Resolves API base URL from Vite environment variable with local fallback.
 * Dynamically aligns 127.0.0.1 <-> localhost hostnames to prevent browser SameSite cookie blocking.
 */
function resolveApiBaseUrl() {
  const envUrl = import.meta.env.VITE_API_URL;
  const currentHost = typeof window !== "undefined" ? window.location.hostname : "localhost";

  if (!envUrl) {
    return `http://${currentHost}:8000`;
  }

  try {
    const parsed = new URL(envUrl);
    // Align hostnames between frontend window location and API target so cookies are treated as same-site
    if (
      (currentHost === "localhost" && parsed.hostname === "127.0.0.1") ||
      (currentHost === "127.0.0.1" && parsed.hostname === "localhost")
    ) {
      parsed.hostname = currentHost;
      return parsed.origin;
    }
    return envUrl;
  } catch {
    return envUrl;
  }
}

export const API_BASE_URL = resolveApiBaseUrl();


