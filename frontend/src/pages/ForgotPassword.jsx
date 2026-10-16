import { useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../utils/api";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      setError("Please enter your email address.");
      return;
    }

    const parts = cleanEmail.split("@");
    if (parts.length !== 2 || parts[1] !== "gmail.com") {
      setError("Please use a Gmail address.");
      return;
    }

    setSubmitting(true);

    try {
      const res = await apiFetch("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email: cleanEmail }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error?.message || data?.detail || "Could not process password reset request.");
      }

      setSubmitted(true);
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={pageContainerStyle}>
      <div style={cardStyle}>
        {/* Brand Header */}
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <div style={badgeStyle}>AI Interview Intelligence</div>
          <h1 style={{ fontSize: "24px", fontWeight: "700", color: "#f8fafc", margin: "14px 0 6px 0", letterSpacing: "-0.01em" }}>
            Reset Password
          </h1>
          <p style={{ fontSize: "14px", color: "#94a3b8", margin: 0, lineHeight: 1.5 }}>
            Enter your account email to receive reset instructions.
          </p>
        </div>

        {error && (
          <div style={errorBannerStyle} role="alert">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f87171" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: "1px" }}>
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{error}</span>
          </div>
        )}

        {submitted ? (
          <div>
            <div style={successBannerStyle} role="status">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4ade80" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
              <div>
                <p style={{ margin: "0 0 4px 0", fontWeight: "600", color: "#4ade80" }}>
                  Instructions Dispatched
                </p>
                <p style={{ margin: 0, fontSize: "13px", color: "#86efac", lineHeight: 1.4 }}>
                  If an account matches that email address, we'll send instructions to reset the password.
                </p>
              </div>
            </div>

            <p style={{ fontSize: "13px", color: "#94a3b8", lineHeight: 1.6, textAlign: "center", margin: "20px 0" }}>
              Please check your inbox and spam folder. Reset links expire in 30 minutes and are single-use.
            </p>

            <div style={{ textAlign: "center", marginTop: "24px", paddingTop: "18px", borderTop: "1px solid #1e293b" }}>
              <Link to="/login" id="back-to-login-link" style={primaryButtonStyleLink}>
                Return to Sign In
              </Link>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} noValidate>
            <div style={{ marginBottom: "22px" }}>
              <label htmlFor="forgot-password-email-input" style={labelStyle}>
                Gmail Address
              </label>
              <input
                id="forgot-password-email-input"
                type="email"
                required
                autoFocus
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@gmail.com"
                style={inputStyle}
              />
            </div>

            <button
              id="send-reset-link-btn"
              type="submit"
              disabled={submitting}
              style={{
                ...primaryButtonStyle,
                opacity: submitting ? 0.7 : 1,
                cursor: submitting ? "not-allowed" : "pointer",
              }}
            >
              {submitting ? "Sending Reset Link..." : "Send Reset Instructions"}
            </button>

            <div style={{ textAlign: "center", marginTop: "24px", paddingTop: "18px", borderTop: "1px solid #1e293b" }}>
              <Link to="/login" style={{ fontSize: "13px", color: "#60a5fa", textDecoration: "none", fontWeight: "500" }}>
                Return to Sign In
              </Link>
            </div>
          </form>
        )}
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
  minHeight: "75vh",
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

const primaryButtonStyleLink = {
  display: "inline-block",
  width: "100%",
  padding: "12px 20px",
  backgroundColor: "#2563eb",
  color: "#ffffff",
  borderRadius: "10px",
  fontSize: "14px",
  fontWeight: "600",
  textDecoration: "none",
  boxSizing: "border-box",
  boxShadow: "0 4px 6px -1px rgba(37, 99, 235, 0.2)",
};

const successBannerStyle = {
  display: "flex",
  alignItems: "flex-start",
  gap: "12px",
  backgroundColor: "rgba(34, 197, 94, 0.1)",
  border: "1px solid rgba(34, 197, 94, 0.3)",
  color: "#4ade80",
  padding: "14px 16px",
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
