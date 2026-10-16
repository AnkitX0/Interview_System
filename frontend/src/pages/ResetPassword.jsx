import { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { apiFetch } from "../utils/api";

const SPECIAL_CHAR_REGEX = /[!@#$%^&*(),.?":{}|<>\-_=+[\]~`/\\';]/;

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";

  // State machine: "CHECKING" | "READY" | "SUBMITTING" | "SUCCESS" | "INVALID" | "ERROR"
  const isTokenMissing = !token || !token.trim();
  const [pageState, setPageState] = useState(isTokenMissing ? "INVALID" : "CHECKING");
  const [stateMessage, setStateMessage] = useState(
    isTokenMissing ? "No password reset token was provided. Please check your reset link or request a new one." : ""
  );

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [formError, setFormError] = useState(null);

  // Validate the token on initial mount
  useEffect(() => {
    if (!token || !token.trim()) {
      return;
    }

    let isMounted = true;

    async function validateToken() {
      try {
        const res = await apiFetch(`/auth/validate-reset-token?token=${encodeURIComponent(token.trim())}`);
        const data = await res.json();

        if (!isMounted) return;

        if (res.ok && data?.valid) {
          setPageState("READY");
        } else {
          setPageState("INVALID");
          setStateMessage(data?.error?.message || data?.detail || "This reset link is invalid, expired, or has already been used.");
        }
      } catch {
        if (!isMounted) return;
        setPageState("ERROR");
        setStateMessage("Could not verify the reset link due to a network connection error. Please try again.");
      }
    }

    validateToken();

    return () => {
      isMounted = false;
    };
  }, [token]);

  // Live password requirements
  const reqLength = newPassword.length >= 8;
  const reqUpper = /[A-Z]/.test(newPassword);
  const reqLower = /[a-z]/.test(newPassword);
  const reqNumber = /[0-9]/.test(newPassword);
  const reqSpecial = SPECIAL_CHAR_REGEX.test(newPassword);
  const allReqsMet = reqLength && reqUpper && reqLower && reqNumber && reqSpecial;

  const passwordsMatch = confirmPassword.length > 0 && newPassword === confirmPassword;
  const passwordsMismatch = confirmPassword.length > 0 && newPassword !== confirmPassword;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError(null);

    if (!allReqsMet) {
      setFormError("Please ensure your new password satisfies all security requirements.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setFormError("Passwords do not match.");
      return;
    }

    setPageState("SUBMITTING");

    try {
      const res = await apiFetch("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({
          token: token.trim(),
          new_password: newPassword,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        const detailMsg = data?.error?.message || data?.detail || "";
        if (
          detailMsg.toLowerCase().includes("valid") ||
          detailMsg.toLowerCase().includes("expired") ||
          detailMsg.toLowerCase().includes("token")
        ) {
          setPageState("INVALID");
          setStateMessage(detailMsg || "This reset link has expired or has already been used.");
          return;
        }
        setPageState("READY");
        setFormError(detailMsg || "Failed to update password. Please try again.");
        return;
      }

      // Atomically remove token from browser address bar to prevent retention
      if (window.history && window.history.replaceState) {
        window.history.replaceState({}, document.title, window.location.pathname);
      }

      setPageState("SUCCESS");
    } catch {
      setPageState("READY");
      setFormError("A network error occurred while updating your password. Please try again.");
    }
  };

  return (
    <div style={pageContainerStyle}>
      <div style={cardStyle}>
        {/* Brand Header */}
        <div style={{ textAlign: "center", marginBottom: "26px" }}>
          <div style={badgeStyle}>AI Interview Intelligence</div>
          <h1 style={{ fontSize: "24px", fontWeight: "700", color: "#f8fafc", margin: "14px 0 6px 0", letterSpacing: "-0.01em" }}>
            {pageState === "SUCCESS"
              ? "Password Updated"
              : pageState === "INVALID"
              ? "Invalid Reset Link"
              : "Choose New Password"}
          </h1>
          <p style={{ fontSize: "14px", color: "#94a3b8", margin: 0, lineHeight: 1.5 }}>
            {pageState === "SUCCESS"
              ? "Your account password has been safely updated."
              : pageState === "INVALID"
              ? "This password reset link is no longer valid."
              : "Create a strong, unique password for your account."}
          </p>
        </div>

        {/* 1. Checking State */}
        {pageState === "CHECKING" && (
          <div style={{ textAlign: "center", padding: "28px 0" }}>
            <div style={spinnerStyle} />
            <p style={{ fontSize: "14px", color: "#94a3b8", marginTop: "16px" }}>
              Verifying your reset link...
            </p>
          </div>
        )}

        {/* 2. Network Error State */}
        {pageState === "ERROR" && (
          <div style={{ textAlign: "center", padding: "12px 0" }}>
            <div style={errorIconContainerStyle}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#f87171" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <p style={{ fontSize: "14px", color: "#cbd5e1", margin: "16px 0 20px 0" }}>
              {stateMessage}
            </p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              style={primaryButtonStyle}
            >
              Retry Connection
            </button>
          </div>
        )}

        {/* 3. Invalid or Expired Token State */}
        {pageState === "INVALID" && (
          <div style={{ textAlign: "center", padding: "8px 0" }}>
            <div style={warningIconContainerStyle}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <div style={errorBannerStyle} role="alert">
              <span>{stateMessage}</span>
            </div>
            <p style={{ fontSize: "13px", color: "#94a3b8", lineHeight: 1.6, margin: "16px 0 24px 0" }}>
              Password reset links expire after 30 minutes and can only be used once for security.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <Link to="/forgot-password" id="request-new-reset-link-btn" style={primaryButtonStyleLink}>
                Request a New Reset Link
              </Link>
              <Link to="/login" style={{ fontSize: "13px", color: "#60a5fa", textDecoration: "none", marginTop: "6px" }}>
                Return to Sign In
              </Link>
            </div>
          </div>
        )}

        {/* 4. Success State */}
        {pageState === "SUCCESS" && (
          <div style={{ textAlign: "center", padding: "8px 0" }}>
            <div style={successIconContainerStyle}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 6 9 17l-5-5" />
              </svg>
            </div>
            <p style={{ fontSize: "14px", color: "#cbd5e1", margin: "16px 0 24px 0" }}>
              Your password has been reset. You can now sign in using your new credentials.
            </p>
            <Link to="/login" id="return-to-login-btn" style={primaryButtonStyleLink}>
              Sign In with New Password
            </Link>
          </div>
        )}

        {/* 5. Ready or Submitting State (Form Display) */}
        {(pageState === "READY" || pageState === "SUBMITTING") && (
          <form onSubmit={handleSubmit} noValidate>
            {formError && (
              <div style={errorBannerStyle} role="alert">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f87171" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: "1px" }}>
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <span>{formError}</span>
              </div>
            )}

            {/* New Password */}
            <div style={{ marginBottom: "18px" }}>
              <label htmlFor="reset-new-password-input" style={labelStyle}>
                New Password
              </label>
              <div style={{ position: "relative" }}>
                <input
                  id="reset-new-password-input"
                  type={showPassword ? "text" : "password"}
                  required
                  autoFocus
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
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

              {/* Security Requirements Checklist */}
              <div style={{ marginTop: "10px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
                <div style={reqItemStyle(reqLength)}>
                  <span>{reqLength ? "✓" : "○"}</span> 8+ characters
                </div>
                <div style={reqItemStyle(reqUpper)}>
                  <span>{reqUpper ? "✓" : "○"}</span> Uppercase letter
                </div>
                <div style={reqItemStyle(reqLower)}>
                  <span>{reqLower ? "✓" : "○"}</span> Lowercase letter
                </div>
                <div style={reqItemStyle(reqNumber)}>
                  <span>{reqNumber ? "✓" : "○"}</span> Number
                </div>
                <div style={{ ...reqItemStyle(reqSpecial), gridColumn: "span 2" }}>
                  <span>{reqSpecial ? "✓" : "○"}</span> Special character (!@#$%^&*...)
                </div>
              </div>
            </div>

            {/* Confirm New Password */}
            <div style={{ marginBottom: "22px" }}>
              <label htmlFor="reset-confirm-password-input" style={labelStyle}>
                Confirm New Password
              </label>
              <div style={{ position: "relative" }}>
                <input
                  id="reset-confirm-password-input"
                  type={showConfirmPassword ? "text" : "password"}
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••••••"
                  style={{
                    ...inputStyle,
                    paddingRight: "42px",
                    borderColor: passwordsMismatch ? "#ef4444" : passwordsMatch ? "#10b981" : "#334155",
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}
                  style={visibilityToggleStyle}
                >
                  {showConfirmPassword ? (
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
              {passwordsMatch && <p style={{ fontSize: "12px", color: "#10b981", marginTop: "4px" }}>✓ Passwords match</p>}
              {passwordsMismatch && <p style={{ fontSize: "12px", color: "#ef4444", marginTop: "4px" }}>Passwords do not match.</p>}
            </div>

            {/* Submit Button */}
            <button
              id="reset-password-submit-btn"
              type="submit"
              disabled={pageState === "SUBMITTING" || !allReqsMet || !passwordsMatch}
              style={{
                ...primaryButtonStyle,
                opacity: pageState === "SUBMITTING" || !allReqsMet || !passwordsMatch ? 0.6 : 1,
                cursor: pageState === "SUBMITTING" || !allReqsMet || !passwordsMatch ? "not-allowed" : "pointer",
              }}
            >
              {pageState === "SUBMITTING" ? "Updating Password..." : "Update Password"}
            </button>
          </form>
        )}

        {/* Return to Sign In link */}
        <div style={{ textAlign: "center", marginTop: "24px", paddingTop: "18px", borderTop: "1px solid #1e293b" }}>
          <Link to="/login" style={{ fontSize: "13px", color: "#60a5fa", textDecoration: "none", fontWeight: "500" }}>
            Return to Sign In
          </Link>
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

const primaryButtonStyleLink = {
  display: "inline-block",
  width: "100%",
  padding: "12px 20px",
  backgroundColor: "#2563eb",
  color: "#ffffff",
  borderRadius: "10px",
  fontSize: "14px",
  fontWeight: "600",
  textAlign: "center",
  textDecoration: "none",
  boxSizing: "border-box",
  boxShadow: "0 4px 6px -1px rgba(37, 99, 235, 0.2)",
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

const spinnerStyle = {
  width: "36px",
  height: "36px",
  borderRadius: "50%",
  border: "3px solid #1e293b",
  borderTopColor: "#3b82f6",
  margin: "0 auto",
  animation: "spin 0.8s linear infinite",
};

const successIconContainerStyle = {
  width: "64px",
  height: "64px",
  borderRadius: "50%",
  backgroundColor: "rgba(34, 197, 94, 0.15)",
  border: "1px solid rgba(34, 197, 94, 0.3)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  margin: "0 auto",
};

const warningIconContainerStyle = {
  width: "64px",
  height: "64px",
  borderRadius: "50%",
  backgroundColor: "rgba(245, 158, 11, 0.15)",
  border: "1px solid rgba(245, 158, 11, 0.3)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  margin: "0 auto",
};

const errorIconContainerStyle = {
  width: "64px",
  height: "64px",
  borderRadius: "50%",
  backgroundColor: "rgba(239, 68, 68, 0.15)",
  border: "1px solid rgba(239, 68, 68, 0.3)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  margin: "0 auto",
};

const reqItemStyle = (met) => ({
  fontSize: "11px",
  color: met ? "#10b981" : "#64748b",
  display: "flex",
  alignItems: "center",
  gap: "4px",
  fontWeight: met ? "500" : "400",
  transition: "color 0.15s ease",
});
