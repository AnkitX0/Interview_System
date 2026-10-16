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
  const [unverifiedEmail, setUnverifiedEmail] = useState(null);
  const [resendingVerification, setResendingVerification] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resendSuccessMsg, setResendSuccessMsg] = useState(null);

  const { user, loading: authLoading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || "/dashboard";

  useEffect(() => {
    if (!authLoading && user) {
      navigate(from, { replace: true });
    }
  }, [user, authLoading, navigate, from]);

  // Resend cooldown timer
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
      setResendSuccessMsg("Verification email sent. Please check your inbox.");
      setResendCooldown(60);
    } catch (err) {
      setError(err.message || "Failed to resend verification email.");
    } finally {
      setResendingVerification(false);
    }
  };

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <div style={badgeStyle}>Interview Intelligence</div>
          <h2 style={{ fontSize: "22px", fontWeight: "700", color: "#0f172a", margin: "10px 0 6px 0" }}>
            Sign in to your account
          </h2>
          <p style={{ fontSize: "14px", color: "#64748b", margin: 0 }}>
            Prepare smarter. Interview with confidence.
          </p>
        </div>

        {resendSuccessMsg && (
          <div style={successBannerStyle}>
            <span style={{ fontSize: "13px", fontWeight: "500" }}>{resendSuccessMsg}</span>
          </div>
        )}

        {error && (
          <div style={errorBannerStyle}>
            <span style={{ fontSize: "13px", fontWeight: "500" }}>{error}</span>
          </div>
        )}

        {unverifiedEmail && (
          <div style={{ marginBottom: "18px", padding: "14px 16px", backgroundColor: "#fffbeb", border: "1px solid #fde68a", borderRadius: "8px", textAlign: "center" }}>
            <p style={{ fontSize: "13px", color: "#92400e", margin: "0 0 4px 0", fontWeight: "600" }}>
              Please verify your email address before signing in.
            </p>
            <p style={{ fontSize: "12px", color: "#b45309", margin: "0 0 10px 0", fontFamily: "monospace" }}>
              {maskEmail(unverifiedEmail)}
            </p>
            <button
              id="login-resend-verification-btn"
              type="button"
              onClick={handleResendVerification}
              disabled={resendCooldown > 0 || resendingVerification}
              style={{
                padding: "8px 18px",
                fontSize: "13px",
                fontWeight: "600",
                color: "#92400e",
                backgroundColor: "#fef3c7",
                border: "1px solid #fcd34d",
                borderRadius: "6px",
                cursor: resendCooldown > 0 || resendingVerification ? "not-allowed" : "pointer",
                opacity: resendCooldown > 0 || resendingVerification ? 0.6 : 1,
              }}
            >
              {resendingVerification ? "Sending..." : resendCooldown > 0 ? `Resend in ${resendCooldown}s` : "Resend Verification Email"}
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <div style={{ marginBottom: "18px" }}>
            <label htmlFor="login-email-input" style={labelStyle}>
              Email Address
            </label>
            <input
              id="login-email-input"
              type="email"
              autoComplete="email"
              required
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@gmail.com"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <label htmlFor="login-password-input" style={{ ...labelStyle, marginBottom: 0 }}>
                Password
              </label>
              <Link
                to="/forgot-password"
                id="forgot-password-link"
                style={{ fontSize: "12px", color: "#2563eb", fontWeight: "600", textDecoration: "none" }}
              >
                Forgot password?
              </Link>
            </div>
            <div style={{ position: "relative" }}>
              <input
                id="login-password-input"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                style={{ ...inputStyle, paddingRight: "42px" }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                style={eyeButtonStyle}
              >
                {showPassword ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="m15 18-.722-3.25" />
                    <path d="M2 8a10.645 10.645 0 0 0 20 0" />
                    <path d="m20 15-1.726-2.05" />
                    <path d="m4 15 1.726-2.05" />
                    <path d="m9 18 .722-3.25" />
                  </svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          <button
            id="login-submit-btn"
            type="submit"
            disabled={submitting}
            style={{
              ...buttonStyle,
              opacity: submitting ? 0.7 : 1,
              cursor: submitting ? "not-allowed" : "pointer",
            }}
          >
            {submitting ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <div style={{ textAlign: "center", marginTop: "20px", paddingTop: "16px", borderTop: "1px solid #f1f5f9" }}>
          <p style={{ fontSize: "13px", color: "#64748b", margin: "0 0 8px 0" }}>
            Forgot your password?
          </p>
          <Link
            to="/forgot-password"
            id="reset-password-btn"
            style={{
              display: "inline-block",
              fontSize: "13px",
              color: "#2563eb",
              fontWeight: "600",
              textDecoration: "none",
              padding: "7px 16px",
              borderRadius: "6px",
              backgroundColor: "#eff6ff",
              border: "1px solid #dbeafe",
            }}
          >
            Reset Password
          </Link>
        </div>

        <div style={{ textAlign: "center", marginTop: "16px" }}>
          <p style={{ fontSize: "13px", color: "#64748b", margin: 0 }}>
            Don&apos;t have an account?{" "}
            <Link to="/register" id="create-account-link" style={{ color: "#2563eb", fontWeight: "600", textDecoration: "none" }}>
              Create an account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

const containerStyle = {
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  minHeight: "70vh",
  padding: "20px",
};

const cardStyle = {
  backgroundColor: "#ffffff",
  borderRadius: "12px",
  boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05)",
  border: "1px solid #e2e8f0",
  padding: "36px",
  width: "100%",
  maxWidth: "420px",
};

const labelStyle = {
  display: "block",
  fontSize: "13px",
  fontWeight: "600",
  color: "#334155",
  marginBottom: "6px",
};

const inputStyle = {
  width: "100%",
  boxSizing: "border-box",
  padding: "10px 14px",
  fontSize: "14px",
  borderRadius: "8px",
  border: "1px solid #cbd5e1",
  outline: "none",
  transition: "border-color 0.15s ease",
};

const buttonStyle = {
  width: "100%",
  padding: "11px",
  backgroundColor: "#2563eb",
  color: "#ffffff",
  border: "none",
  borderRadius: "8px",
  fontSize: "14px",
  fontWeight: "600",
  transition: "background-color 0.15s ease",
};

const errorBannerStyle = {
  backgroundColor: "#fef2f2",
  color: "#b91c1c",
  border: "1px solid #fecaca",
  borderRadius: "8px",
  padding: "10px 14px",
  marginBottom: "18px",
};

const successBannerStyle = {
  backgroundColor: "#f0fdf4",
  color: "#166534",
  border: "1px solid #bbf7d0",
  borderRadius: "8px",
  padding: "10px 14px",
  marginBottom: "18px",
};

const badgeStyle = {
  display: "inline-block",
  fontSize: "11px",
  fontWeight: "700",
  letterSpacing: "0.06em",
  textTransform: "uppercase",
  color: "#2563eb",
  backgroundColor: "#eff6ff",
  padding: "3px 10px",
  borderRadius: "100px",
};

const eyeButtonStyle = {
  position: "absolute",
  right: "10px",
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
