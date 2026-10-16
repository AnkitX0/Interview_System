import { useState, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const { user, loading: authLoading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || "/dashboard";

  // Pre-fill email if passed via navigation
  useEffect(() => {
    if (location.state?.email) {
      setEmail(location.state.email);
    }
  }, [location.state]);

  // Redirect if already authenticated
  useEffect(() => {
    if (!authLoading && user) {
      navigate(from, { replace: true });
    }
  }, [user, authLoading, navigate, from]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

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
      await login(trimmedEmail, password, rememberMe);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || "Invalid email or password.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        {/* Header */}
        <div style={{ marginBottom: "28px", textAlign: "left" }}>
          <span style={badgeStyle}>AI Interview Intelligence</span>
          <h1 style={titleStyle}>Welcome back</h1>
          <p style={subtitleStyle}>Continue preparing for your next interview.</p>
        </div>

        {/* Error Alert */}
        {error && (
          <div style={errorBannerStyle} role="alert" id="login-error-alert">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ flexShrink: 0, marginTop: "2px" }}
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span style={{ fontSize: "14px", lineHeight: 1.4 }}>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          {/* Email Field */}
          <div style={formGroupStyle}>
            <label htmlFor="login-email" style={labelStyle}>
              Email address
            </label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (error) setError(null);
              }}
              placeholder="name@example.com"
              style={inputStyle}
              disabled={submitting}
            />
          </div>

          {/* Password Field */}
          <div style={formGroupStyle}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <label htmlFor="login-password" style={labelStyle}>
                Password
              </label>
              <Link
                to="/forgot-password"
                id="login-forgot-password-link"
                style={forgotLinkStyle}
              >
                Forgot password?
              </Link>
            </div>
            <div style={{ position: "relative" }}>
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (error) setError(null);
                }}
                placeholder="••••••••"
                style={{ ...inputStyle, paddingRight: "44px" }}
                disabled={submitting}
              />
              <button
                type="button"
                id="login-show-password-btn"
                onClick={() => setShowPassword(!showPassword)}
                style={showPasswordBtnStyle}
                aria-label={showPassword ? "Hide password" : "Show password"}
                tabIndex="-1"
              >
                {showPassword ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* Remember Me Option */}
          <div style={{ display: "flex", alignItems: "center", marginBottom: "22px" }}>
            <input
              id="login-remember-me"
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              style={checkboxStyle}
              disabled={submitting}
            />
            <label htmlFor="login-remember-me" style={checkboxLabelStyle}>
              Remember me for 30 days
            </label>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            id="login-submit-btn"
            disabled={submitting}
            style={{
              ...primaryBtnStyle,
              opacity: submitting ? 0.75 : 1,
              cursor: submitting ? "not-allowed" : "pointer",
            }}
          >
            {submitting ? (
              <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
                <span style={spinnerStyle} />
                Signing in...
              </span>
            ) : (
              "Sign in"
            )}
          </button>
        </form>

        {/* Create Account Footer */}
        <div style={footerStyle}>
          <span style={{ color: "var(--text-muted)", fontSize: "14px" }}>
            Don't have an account?{" "}
          </span>
          <Link
            to="/register"
            id="login-register-link"
            style={createAccountLinkStyle}
          >
            Create an account
          </Link>
        </div>
      </div>
    </div>
  );
}

// ==============================================================================
// Styles (Clean, Restrained, Editorial & Responsive)
// ==============================================================================
const containerStyle = {
  minHeight: "calc(100vh - 80px)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "32px 16px",
  backgroundColor: "var(--bg-app)",
};

const cardStyle = {
  width: "100%",
  maxWidth: "420px",
  backgroundColor: "var(--bg-surface)",
  border: "1px solid var(--border-default)",
  borderRadius: "12px",
  padding: "36px 32px",
  boxShadow: "var(--shadow-sm)",
  boxSizing: "border-box",
};

const badgeStyle = {
  display: "inline-block",
  fontSize: "12px",
  fontWeight: "600",
  letterSpacing: "0.04em",
  textTransform: "uppercase",
  color: "var(--primary-600)",
  marginBottom: "8px",
};

const titleStyle = {
  fontSize: "26px",
  fontWeight: "700",
  letterSpacing: "-0.02em",
  color: "var(--text-primary)",
  margin: "0 0 6px 0",
};

const subtitleStyle = {
  fontSize: "14px",
  color: "var(--text-secondary)",
  margin: 0,
  lineHeight: 1.5,
};

const errorBannerStyle = {
  display: "flex",
  alignItems: "flex-start",
  gap: "10px",
  backgroundColor: "var(--danger-bg)",
  color: "var(--danger-text)",
  border: "1px solid var(--danger-border)",
  borderRadius: "8px",
  padding: "12px 14px",
  marginBottom: "20px",
};

const formGroupStyle = {
  marginBottom: "18px",
};

const labelStyle = {
  display: "block",
  fontSize: "13px",
  fontWeight: "600",
  color: "var(--text-primary)",
  marginBottom: "6px",
};

const inputStyle = {
  width: "100%",
  boxSizing: "border-box",
  padding: "10px 14px",
  fontSize: "14px",
  fontFamily: "inherit",
  color: "var(--text-primary)",
  backgroundColor: "var(--bg-app)",
  border: "1px solid var(--border-default)",
  borderRadius: "8px",
  outline: "none",
  transition: "border-color 150ms ease, box-shadow 150ms ease",
};

const showPasswordBtnStyle = {
  position: "absolute",
  right: "10px",
  top: "50%",
  transform: "translateY(-50%)",
  background: "none",
  border: "none",
  padding: "4px",
  color: "var(--text-muted)",
  cursor: "pointer",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

const checkboxStyle = {
  width: "16px",
  height: "16px",
  accentColor: "var(--primary-600)",
  cursor: "pointer",
  margin: "0 8px 0 0",
};

const checkboxLabelStyle = {
  fontSize: "13px",
  color: "var(--text-secondary)",
  cursor: "pointer",
  userSelect: "none",
};

const forgotLinkStyle = {
  fontSize: "12px",
  fontWeight: "500",
  color: "var(--primary-600)",
  textDecoration: "none",
};

const primaryBtnStyle = {
  width: "100%",
  padding: "11px 16px",
  fontSize: "14px",
  fontWeight: "600",
  fontFamily: "inherit",
  color: "#FFFFFF",
  backgroundColor: "var(--primary-600)",
  border: "none",
  borderRadius: "8px",
  cursor: "pointer",
  transition: "background-color 150ms ease",
};

const footerStyle = {
  marginTop: "24px",
  paddingTop: "20px",
  borderTop: "1px solid var(--border-subtle)",
  textAlign: "center",
};

const createAccountLinkStyle = {
  fontSize: "14px",
  fontWeight: "600",
  color: "var(--primary-600)",
  textDecoration: "none",
};

const spinnerStyle = {
  width: "14px",
  height: "14px",
  border: "2px solid #FFFFFF",
  borderTopColor: "transparent",
  borderRadius: "50%",
  display: "inline-block",
  animation: "spin 0.7s linear infinite",
};
