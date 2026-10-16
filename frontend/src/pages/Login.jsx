import { useState, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../utils/api";
import { maskEmail } from "../utils/maskEmail";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // Unverified account state
  const [unverifiedEmail, setUnverifiedEmail] = useState(null);
  const [resendingVerification, setResendingVerification] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resendSuccessMsg, setResendSuccessMsg] = useState(null);

  const { user, loading: authLoading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || "/dashboard";

  // Pre-fill email if passed via navigation
  useEffect(() => {
    if (location.state?.verifiedEmail) {
      setEmail(location.state.verifiedEmail);
    }
  }, [location.state]);

  // Redirect if already authenticated
  useEffect(() => {
    if (!authLoading && user) {
      navigate(from, { replace: true });
    }
  }, [user, authLoading, navigate, from]);

  // Resend cooldown countdown timer
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setResendSuccessMsg(null);

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setError("Please enter your email address.");
      return;
    }
    if (!password) {
      setError("Please enter your password.");
      return;
    }

    setSubmitting(true);

    try {
      await login(trimmedEmail, password);
      navigate(from, { replace: true });
    } catch (err) {
      const msg = err.message || "Invalid email or password.";
      setError(msg);

      if (
        msg.toLowerCase().includes("verify your email") ||
        msg.toLowerCase().includes("verification") ||
        msg.toLowerCase().includes("unverified")
      ) {
        setUnverifiedEmail(trimmedEmail.toLowerCase());
      } else {
        setUnverifiedEmail(null);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleResendVerification = async () => {
    if (!unverifiedEmail || resendCooldown > 0 || resendingVerification) return;
    setResendingVerification(true);
    setResendSuccessMsg(null);
    setError(null);

    try {
      const res = await apiFetch("/auth/resend-verification", {
        method: "POST",
        body: JSON.stringify({ email: unverifiedEmail }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error?.message || data?.detail || "Could not resend verification email.");
      }
      setResendSuccessMsg("A new verification code has been sent. Please check your inbox.");
      setResendCooldown(60);
    } catch (err) {
      setError(err.message || "Failed to resend verification email.");
    } finally {
      setResendingVerification(false);
    }
  };

  const isUnregistered = error && (
    error.toLowerCase().includes("no account found") ||
    error.toLowerCase().includes("please register first")
  );

  return (
    <div style={pageContainerStyle}>
      <div style={cardStyle}>
        {/* Brand Header */}
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <div style={badgeStyle}>AI Interview Intelligence</div>
          <h1 style={{ fontSize: "24px", fontWeight: "700", color: "#f8fafc", margin: "14px 0 6px 0", letterSpacing: "-0.01em" }}>
            Welcome Back
          </h1>
          <p style={{ fontSize: "14px", color: "#94a3b8", margin: 0, lineHeight: 1.5 }}>
            Sign in to access your interview sessions and diagnostic reports.
          </p>
        </div>

        {/* Resend Success Banner */}
        {resendSuccessMsg && (
          <div style={successBannerStyle} role="status">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4ade80" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
              <polyline points="20 6 9 17 4 12" />
            </svg>
            <span>{resendSuccessMsg}</span>
          </div>
        )}

        {/* Error Banner */}
        {error && (
          <div style={errorBannerStyle} role="alert">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f87171" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: "1px" }}>
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div>
              <span>{error}</span>
              {isUnregistered && (
                <div style={{ marginTop: "6px" }}>
                  <Link to="/register" style={{ color: "#93c5fd", textDecoration: "underline", fontWeight: "600" }}>
                    Create an account here
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Unverified Account Banner & Action Panel */}
        {unverifiedEmail && (
          <div style={warningPanelStyle}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span style={{ fontSize: "13px", fontWeight: "600", color: "#fef3c7" }}>
                Account Verification Required
              </span>
            </div>
            <p style={{ fontSize: "12px", color: "#fde68a", margin: "0 0 10px 0", fontFamily: "monospace" }}>
              {maskEmail(unverifiedEmail)}
            </p>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={() => navigate("/verify-email", { state: { email: unverifiedEmail } })}
                style={warningActionBtnStyle}
              >
                Enter Code
              </button>
              <button
                id="login-resend-verification-btn"
                type="button"
                onClick={handleResendVerification}
                disabled={resendCooldown > 0 || resendingVerification}
                style={{
                  ...warningSecondaryBtnStyle,
                  opacity: resendCooldown > 0 || resendingVerification ? 0.6 : 1,
                  cursor: resendCooldown > 0 || resendingVerification ? "not-allowed" : "pointer",
                }}
              >
                {resendingVerification ? "Sending..." : resendCooldown > 0 ? `Resend (${resendCooldown}s)` : "Resend Code"}
              </button>
            </div>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} noValidate>
          {/* Email */}
          <div style={{ marginBottom: "18px" }}>
            <label htmlFor="login-email-input" style={labelStyle}>
              Email Address
            </label>
            <input
              id="login-email-input"
              type="email"
              required
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@gmail.com"
              style={inputStyle}
            />
          </div>

          {/* Password */}
          <div style={{ marginBottom: "14px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <label htmlFor="login-password-input" style={{ ...labelStyle, marginBottom: 0 }}>
                Password
              </label>
              <Link to="/forgot-password" id="login-forgot-password-link" style={linkStyle}>
                Forgot password?
              </Link>
            </div>
            <div style={{ position: "relative" }}>
              <input
                id="login-password-input"
                type={showPassword ? "text" : "password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                style={{
                  ...inputStyle,
                  paddingRight: "42px",
                }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                style={visibilityToggleStyle}
              >
                {showPassword ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* Submit Button */}
          <button
            id="login-submit-btn"
            type="submit"
            disabled={submitting}
            style={{
              ...primaryButtonStyle,
              opacity: submitting ? 0.7 : 1,
              cursor: submitting ? "not-allowed" : "pointer",
              marginTop: "10px",
            }}
          >
            {submitting ? "Signing In..." : "Sign In"}
          </button>
        </form>

        {/* Registration Link */}
        <div style={{ textAlign: "center", marginTop: "24px", paddingTop: "18px", borderTop: "1px solid #1e293b" }}>
          <p style={{ fontSize: "13px", color: "#94a3b8", margin: 0 }}>
            Don't have an account?{" "}
            <Link to="/register" id="login-register-link" style={{ color: "#60a5fa", fontWeight: "600", textDecoration: "none" }}>
              Create an Account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Styles: Dark Navy SaaS Palette
// ============================================================================
const pageContainerStyle = {
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  minHeight: "80vh",
  padding: "32px 16px",
};

const cardStyle = {
  backgroundColor: "#111827",
  border: "1px solid #1f2937",
  borderRadius: "16px",
  boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.4)",
  padding: "36px 32px",
  width: "100%",
  maxWidth: "460px",
  boxSizing: "border-box",
};

const badgeStyle = {
  display: "inline-block",
  fontSize: "11px",
  fontWeight: "700",
  letterSpacing: "0.06em",
  textTransform: "uppercase",
  color: "#60a5fa",
  backgroundColor: "rgba(37, 99, 235, 0.15)",
  border: "1px solid rgba(59, 130, 246, 0.3)",
  padding: "4px 12px",
  borderRadius: "9999px",
};

const labelStyle = {
  display: "block",
  fontSize: "13px",
  fontWeight: "600",
  color: "#cbd5e1",
  marginBottom: "6px",
};

const linkStyle = {
  fontSize: "12px",
  color: "#60a5fa",
  textDecoration: "none",
  fontWeight: "500",
};

const inputStyle = {
  width: "100%",
  padding: "11px 14px",
  backgroundColor: "#0b0f19",
  border: "1px solid #334155",
  borderRadius: "10px",
  color: "#f8fafc",
  fontSize: "14px",
  outline: "none",
  boxSizing: "border-box",
  transition: "border-color 0.15s ease",
};

const visibilityToggleStyle = {
  position: "absolute",
  right: "12px",
  top: "50%",
  transform: "translateY(-50%)",
  background: "none",
  border: "none",
  cursor: "pointer",
  padding: "4px",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

const primaryButtonStyle = {
  width: "100%",
  padding: "12px 20px",
  backgroundColor: "#2563eb",
  color: "#ffffff",
  border: "none",
  borderRadius: "10px",
  fontSize: "14px",
  fontWeight: "600",
  cursor: "pointer",
  transition: "all 0.15s ease",
  boxShadow: "0 4px 6px -1px rgba(37, 99, 235, 0.2)",
};

const successBannerStyle = {
  display: "flex",
  alignItems: "center",
  gap: "10px",
  backgroundColor: "rgba(34, 197, 94, 0.1)",
  border: "1px solid rgba(34, 197, 94, 0.3)",
  color: "#4ade80",
  padding: "12px 14px",
  borderRadius: "10px",
  fontSize: "13px",
  marginBottom: "18px",
};

const errorBannerStyle = {
  display: "flex",
  alignItems: "flex-start",
  gap: "10px",
  backgroundColor: "rgba(239, 68, 68, 0.1)",
  border: "1px solid rgba(239, 68, 68, 0.3)",
  color: "#f87171",
  padding: "12px 14px",
  borderRadius: "10px",
  fontSize: "13px",
  lineHeight: "1.4",
  marginBottom: "18px",
};

const warningPanelStyle = {
  backgroundColor: "rgba(245, 158, 11, 0.1)",
  border: "1px solid rgba(245, 158, 11, 0.3)",
  borderRadius: "10px",
  padding: "12px 14px",
  marginBottom: "18px",
};

const warningActionBtnStyle = {
  padding: "6px 14px",
  backgroundColor: "#d97706",
  color: "#ffffff",
  border: "none",
  borderRadius: "6px",
  fontSize: "12px",
  fontWeight: "600",
  cursor: "pointer",
};

const warningSecondaryBtnStyle = {
  padding: "6px 14px",
  backgroundColor: "#1e293b",
  color: "#fbbf24",
  border: "1px solid rgba(245, 158, 11, 0.4)",
  borderRadius: "6px",
  fontSize: "12px",
  fontWeight: "500",
};
