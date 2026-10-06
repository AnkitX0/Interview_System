/**
 * Frontend Application Configuration
 * Resolves API base URL from Vite environment variable with local fallback.
 */
export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

