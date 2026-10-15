/**
 * Frontend Application Configuration
 * Resolves API base URL from Vite environment variable with smart fallback.
 * Prioritizes VITE_API_BASE_URL with backward-compatibility for VITE_API_URL.
 * Normalizes trailing slashes and ensures valid URL formatting.
 */
function resolveApiBaseUrl() {
  const envUrl = (
    import.meta.env.VITE_API_BASE_URL ||
    import.meta.env.VITE_API_URL ||
    ""
  ).trim();

  const currentHost = typeof window !== "undefined" ? window.location.hostname : "localhost";

  // If environment variable is provided, validate and normalize it
  if (envUrl) {
    try {
      const parsed = new URL(envUrl);
      // For local development, align 127.0.0.1 <-> localhost hostnames so cookies are treated as same-site
      if (
        (currentHost === "localhost" && parsed.hostname === "127.0.0.1") ||
        (currentHost === "127.0.0.1" && parsed.hostname === "localhost")
      ) {
        parsed.hostname = currentHost;
        return parsed.origin.replace(/\/+$/, "");
      }
      // Return origin + clean pathname without trailing slash
      const cleanPath = parsed.pathname.replace(/\/+$/, "");
      return `${parsed.origin}${cleanPath}`;
    } catch (err) {
      console.warn("Invalid VITE_API_BASE_URL format provided:", envUrl, err);
      return envUrl.replace(/\/+$/, "");
    }
  }

  // If in production build on Vercel without env var, default to production Render backend
  if (import.meta.env.PROD) {
    return "https://interview-intelligence-api-rla6.onrender.com";
  }

  // Local development default fallback
  return `http://${currentHost}:8001`;
}

export const API_BASE_URL = resolveApiBaseUrl();


