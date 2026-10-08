import { useState, useEffect } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { apiFetch } from "../utils/api";

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  useEffect(() => {
    if (!token || !token.trim()) {
      setLoading(false);
      setErrorMessage("This verification link is no longer valid.");
      return;
    }

    let isMounted = true;

    async function performVerification() {
      try {
        const res = await apiFetch("/auth/verify-email", {
          method: "POST",
          body: JSON.stringify({ token: token.trim() }),
        });

        const data = await res.json();

        if (!isMounted) return;

        if (res.ok) {
          setSuccess(true);
        } else {
          const detail = data?.error?.message || data?.detail || "This verification link is no longer valid.";
          setErrorMessage(detail);
        }
      } catch (err) {
        if (!isMounted) return;
        setErrorMessage("Something went wrong while verifying your email. Please try again.");
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    performVerification();

    return () => {
      isMounted = false;
    };
  }, [token]);

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <div style={{ textAlign: "center", marginBottom: "24px" }}>
          <div style={badgeStyle}>Interview Intelligence</div>
        </div>

        {/* Loading State */}
        {loading && (
          <div style={{ textAlign: "center", padding: "24px 0" }}>
            <div style={spinnerStyle} />
            <h3 style={{ fontSize: "18px", fontWeight: "600", color: "#0f172a", marginTop: "16px", marginBottom: "6px" }}>
              Verifying your email...
            </h3>
            <p style={{ fontSize: "14px", color: "#64748b", margin: 0 }}>
              Please wait while we activate your account.
            </p>
          </div>
        )}

        {/* Success State */}
        {!loading && success && (
          <div style={{ textAlign: "center", padding: "10px 0" }}>
            <div style={successIconCircleStyle}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 6 9 17l-5-5" />
              </svg>
            </div>

            <h2 style={{ fontSize: "22px", fontWeight: "700", color: "#0f172a", margin: "16px 0 6px 0" }}>
              Email verified
            </h2>
            <p style={{ fontSize: "14px", color: "#64748b", margin: "0 0 24px 0" }}>
              Your account is ready.
            </p>

            <button
              id="continue-to-signin-btn"
              type="button"
              onClick={() => navigate("/login")}
              style={buttonStyle}
            >
              Continue to Sign In
            </button>
          </div>
        )}

        {/* Error / Failure State */}
        {!loading && !success && (
          <div style={{ textAlign: "center", padding: "10px 0" }}>
            <div style={errorIconCircleStyle}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>

            <h2 style={{ fontSize: "20px", fontWeight: "700", color: "#0f172a", margin: "16px 0 8px 0" }}>
              Verification Failed
            </h2>

            <div style={errorBannerStyle}>
              <span>{errorMessage}</span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "20px" }}>
              <button
                type="button"
                onClick={() => navigate("/login")}
                style={buttonStyle}
              >
                Go to Sign In
              </button>
              <button
                type="button"
                onClick={() => navigate("/register")}
                style={secondaryButtonStyle}
              >
                Create an Account
              </button>
            </div>
          </div>
        )}

        {/* Footer */}
        <div style={{ textAlign: "center", marginTop: "24px", paddingTop: "18px", borderTop: "1px solid #f1f5f9" }}>
          <p style={{ fontSize: "12px", color: "#94a3b8", margin: 0 }}>
            Interview Intelligence Preparation System
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
  minHeight: "75vh",
  padding: "24px 16px",
};

const cardStyle = {
  backgroundColor: "#ffffff",
  borderRadius: "12px",
  boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05)",
  border: "1px solid #e2e8f0",
  padding: "36px",
  width: "100%",
  maxWidth: "420px",
  boxSizing: "border-box",
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

const successIconCircleStyle = {
  width: "56px",
  height: "56px",
  borderRadius: "28px",
  backgroundColor: "#f0fdf4",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  margin: "0 auto",
  border: "1px solid #bbf7d0",
};

const errorIconCircleStyle = {
  width: "56px",
  height: "56px",
  borderRadius: "28px",
  backgroundColor: "#fef2f2",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  margin: "0 auto",
  border: "1px solid #fecaca",
};

const spinnerStyle = {
  width: "36px",
  height: "36px",
  borderRadius: "50%",
  border: "3px solid #e2e8f0",
  borderTopColor: "#2563eb",
  margin: "0 auto",
  animation: "spin 0.8s linear infinite",
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
  cursor: "pointer",
  transition: "background-color 0.15s ease",
};

const secondaryButtonStyle = {
  width: "100%",
  padding: "10px",
  backgroundColor: "#ffffff",
  color: "#334155",
  border: "1px solid #cbd5e1",
  borderRadius: "8px",
  fontSize: "13px",
  fontWeight: "600",
  cursor: "pointer",
  transition: "all 0.15s ease",
};

const errorBannerStyle = {
  backgroundColor: "#fef2f2",
  color: "#b91c1c",
  padding: "10px 14px",
  borderRadius: "8px",
  marginTop: "12px",
  border: "1px solid #fecaca",
  fontSize: "13px",
  lineHeight: "1.4",
};
