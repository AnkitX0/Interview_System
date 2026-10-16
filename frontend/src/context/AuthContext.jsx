import { createContext, useContext, useState, useEffect } from "react";
import { apiFetch } from "../utils/api";
import { ReportContext } from "./ReportContext";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const reportCtx = useContext(ReportContext);

  // Check current session on application mount
  useEffect(() => {
    async function checkAuth() {
      try {
        const res = await apiFetch("/auth/me");
        if (res.ok) {
          const data = await res.json();
          setUser(data);
        } else {
          setUser(null);
        }
      } catch (err) {
        console.error("Auth initialization failed:", err);
        setUser(null);
      } finally {
        setLoading(false);
      }
    }
    checkAuth();

    // Listen for global 401 unauthorized events from apiFetch
    const handleUnauthorized = () => {
      setUser(null);
      if (reportCtx?.clearReportContext) {
        reportCtx.clearReportContext();
      }
      try {
        sessionStorage.clear();
      } catch {
        // ignore
      }
    };

    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", handleUnauthorized);
  }, []);

  const login = async (email, password, rememberMe = false) => {
    const res = await apiFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password, remember_me: rememberMe }),
    });

    const data = await res.json();
    if (!res.ok) {
      const errorMsg = data?.error?.message || data?.detail || "Invalid email or password";
      throw new Error(errorMsg);
    }

    try {
      const meRes = await apiFetch("/auth/me");
      if (meRes.ok) {
        const meData = await meRes.json();
        setUser(meData);
        return meData;
      }
    } catch {
      // Fallback to data.user if /auth/me check encounters network glitch
    }

    setUser(data.user);
    return data.user;
  };

  const register = async (email, password, fullName = "", securityQuestion = "", securityAnswer = "") => {
    const res = await apiFetch("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        full_name: fullName,
        security_question: securityQuestion,
        security_answer: securityAnswer,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      const errorMsg = data?.error?.message || data?.detail || "Registration failed";
      throw new Error(errorMsg);
    }

    // Account is active immediately; set authenticated user
    if (data?.user) {
      setUser(data.user);
    }

    return data;
  };

  const logout = async () => {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } catch (e) {
      console.error("Logout request error:", e);
    } finally {
      setUser(null);
      if (reportCtx?.clearReportContext) {
        reportCtx.clearReportContext();
      }
      try {
        sessionStorage.clear();
      } catch {
        // ignore
      }
    }
  };

  const updateProfile = async (profileData) => {
    const res = await apiFetch("/profile", {
      method: "PUT",
      body: JSON.stringify(profileData),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data?.error?.message || "Failed to update profile");
    }

    setUser((prev) => (prev ? { ...prev, profile: data.profile } : prev));
    return data.profile;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        updateProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
