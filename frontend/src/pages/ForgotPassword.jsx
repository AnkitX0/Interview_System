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
      setError("Please enter your Gmail address.");
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
    <div style={containerStyle}>
      <div style={cardStyle}>
        <div style={{ textAlign: "center", marginBottom: "24px" }}>
          <div style={badgeStyle}>Interview Intelligence</div>
          <h2 style={{ fontSize: "22px", fontWeight: "700", color: "#0f172a", margin: "10px 0 6px 0" }}>
            Reset your password
          </h2>
          <p style={{ fontSize: "14px", color: "#64748b", margin: 0, lineHeight: 1.5 }}>
            Enter the Gmail address associated with your account.
          </p>
        </div>

        {error && (
          <div style={errorBannerStyle}>
            <span style={{ fontSize: "13px", fontWeight: "500" }}>{error}</span>
          </div>
        )}

        {submitted ? (
          <div>
            <div style={successBannerStyle}>
              <div style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: "2px" }}>
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
                <div style={{ fontSize: "14px", color: "#065f46", lineHeight: 1.5 }}>
                  If an account exists for this email, we'll send a password reset link.
                </div>
              </div>
            </div>

            <p style={{ fontSize: "13px", color: "#64748b", lineHeight: 1.6, textAlign: "center", margin: "20px 0" }}>
              Please check your inbox and spam folder. Reset links expire in 30 minutes.
            </p>

            <div style={{ textAlign: "center", marginTop: "24px", paddingTop: "18px", borderTop: "1px solid #f1f5f9" }}>
              <Link to="/login" style={{ fontSize: "14px", color: "#2563eb", fontWeight: "600", textDecoration: "none" }}>
                Back to Sign In
              </Link>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: "20px" }}>
              <label style={labelStyle}>Gmail Address</label>
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
                ...buttonStyle,
                opacity: submitting ? 0.7 : 1,
                cursor: submitting ? "not-allowed" : "pointer",
              }}
            >
              {submitting ? "Sending Reset Link..." : "Send Reset Link"}
            </button>

            <div style={{ textAlign: "center", marginTop: "24px", paddingTop: "18px", borderTop: "1px solid #f1f5f9" }}>
              <Link to="/login" style={{ fontSize: "13px", color: "#64748b", textDecoration: "none", fontWeight: "500" }}>
                ← Back to Sign In
              </Link>
            </div>
          </form>
        )}
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

const badgeStyle = {
  display: "inline-block",
  fontSize: "11px",
  fontWeight: "700",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#2563eb",
  backgroundColor: "#eff6ff",
  padding: "4px 10px",
  borderRadius: "9999px",
  marginBottom: "10px",
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
  border: "1px solid #bbf7d0",
  borderRadius: "8px",
  padding: "14px 16px",
  marginBottom: "18px",
};
