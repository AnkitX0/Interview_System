import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { apiFetch } from "../utils/api";

const SPECIAL_CHAR_REGEX = /[!@#$%^&*(),.?":{}|<>\-_=+[\]~`/\\';]/;

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [resetSuccess, setResetSuccess] = useState(false);
  const [tokenInvalid, setTokenInvalid] = useState(!token);
  const [errorMessage, setErrorMessage] = useState(null);

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
    setErrorMessage(null);

    if (!token) {
      setTokenInvalid(true);
      return;
    }

    if (!allReqsMet) {
      setErrorMessage("Please ensure all password requirements are satisfied.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setErrorMessage("Passwords do not match.");
      return;
    }

    setSubmitting(true);

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
          setTokenInvalid(true);
          return;
        }
        throw new Error(detailMsg || "Failed to update password. Please try again.");
      }

      setResetSuccess(true);
    } catch (err) {
      setErrorMessage(err.message || "An unexpected error occurred. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  // 1. Invalid or Expired Token State
  if (tokenInvalid) {
    return (
      <div style={containerStyle}>
        <div style={cardStyle}>
          <div style={{ textAlign: "center", marginBottom: "20px" }}>
            <div style={badgeStyle}>Interview Intelligence</div>
            <div style={warningCircleStyle}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#d97706" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <h2 style={{ fontSize: "22px", fontWeight: "700", color: "#0f172a", margin: "14px 0 8px 0" }}>
              Invalid Reset Link
            </h2>
            <p style={{ fontSize: "14px", color: "#64748b", margin: 0, lineHeight: 1.5 }}>
              This password reset link is no longer valid.
            </p>
          </div>

          <div style={{ fontSize: "13px", color: "#64748b", textAlign: "center", marginBottom: "24px", lineHeight: 1.5 }}>
            Reset links expire after 30 minutes and can only be used once. Please request a new link to continue.
          </div>

          <div style={{ textAlign: "center" }}>
            <Link
              to="/forgot-password"
              id="request-new-reset-link-btn"
              style={{
                display: "inline-block",
                width: "100%",
                boxSizing: "border-box",
                padding: "11px",
                backgroundColor: "#2563eb",
                color: "#ffffff",
                textAlign: "center",
                borderRadius: "8px",
                fontSize: "14px",
                fontWeight: "600",
                textDecoration: "none",
              }}
            >
              Request a new reset link
            </Link>
          </div>

          <div style={{ textAlign: "center", marginTop: "18px" }}>
            <Link to="/login" style={{ fontSize: "13px", color: "#64748b", textDecoration: "none" }}>
              Back to Sign In
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // 2. Success State
  if (resetSuccess) {
    return (
      <div style={containerStyle}>
        <div style={cardStyle}>
          <div style={{ textAlign: "center", marginBottom: "24px" }}>
            <div style={badgeStyle}>Interview Intelligence</div>
            <div style={successCircleStyle}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            </div>
            <h2 style={{ fontSize: "22px", fontWeight: "700", color: "#0f172a", margin: "14px 0 8px 0" }}>
              Password Updated
            </h2>
            <p style={{ fontSize: "14px", color: "#16a34a", fontWeight: "600", margin: 0 }}>
              Your password has been updated.
            </p>
          </div>

          <p style={{ fontSize: "13px", color: "#64748b", textAlign: "center", marginBottom: "24px", lineHeight: 1.5 }}>
            You can now sign in to your Interview Intelligence account using your new password.
          </p>

          <div style={{ textAlign: "center" }}>
            <Link
              to="/login"
              id="return-to-login-btn"
              style={{
                display: "inline-block",
                width: "100%",
                boxSizing: "border-box",
                padding: "11px",
                backgroundColor: "#2563eb",
                color: "#ffffff",
                textAlign: "center",
                borderRadius: "8px",
                fontSize: "14px",
                fontWeight: "600",
                textDecoration: "none",
              }}
            >
              Sign In
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // 3. Password Reset Form State
  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <div style={{ textAlign: "center", marginBottom: "24px" }}>
          <div style={badgeStyle}>Interview Intelligence</div>
          <h2 style={{ fontSize: "22px", fontWeight: "700", color: "#0f172a", margin: "10px 0 6px 0" }}>
            Reset your password
          </h2>
          <p style={{ fontSize: "14px", color: "#64748b", margin: 0 }}>
            Choose a new, secure password for your account.
          </p>
        </div>

        {errorMessage && (
          <div style={errorBannerStyle}>
            <span style={{ fontSize: "13px", fontWeight: "500" }}>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* New Password */}
          <div style={{ marginBottom: "16px" }}>
            <label style={labelStyle}>New Password</label>
            <div style={{ position: "relative" }}>
              <input
                id="reset-new-password"
                type={showPassword ? "text" : "password"}
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="••••••••••••"
                style={{ ...inputStyle, paddingRight: "40px" }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={eyeToggleStyle}
                tabIndex="-1"
                aria-label="Toggle password visibility"
              >
                {showPassword ? "🙈" : "👁"}
              </button>
            </div>
          </div>

          {/* Confirm Password */}
          <div style={{ marginBottom: "18px" }}>
            <label style={labelStyle}>Confirm Password</label>
            <div style={{ position: "relative" }}>
              <input
                id="reset-confirm-password"
                type={showConfirmPassword ? "text" : "password"}
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••••••"
                style={{
                  ...inputStyle,
                  paddingRight: "40px",
                  borderColor: passwordsMismatch ? "#ef4444" : passwordsMatch ? "#10b981" : "#cbd5e1",
                }}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                style={eyeToggleStyle}
                tabIndex="-1"
                aria-label="Toggle confirm password visibility"
              >
                {showConfirmPassword ? "🙈" : "👁"}
              </button>
            </div>
            {passwordsMismatch && (
              <div style={{ fontSize: "12px", color: "#ef4444", marginTop: "4px" }}>
                Passwords do not match.
              </div>
            )}
          </div>

          {/* Password Requirements Checklist */}
          <div style={requirementsCardStyle}>
            <div style={{ fontSize: "12px", fontWeight: "700", color: "#334155", marginBottom: "8px" }}>
              Password requirements:
            </div>
            <div style={reqItemStyle(reqLength)}>
              {reqLength ? "✓" : "○"} At least 8 characters
            </div>
            <div style={reqItemStyle(reqUpper)}>
              {reqUpper ? "✓" : "○"} Uppercase letter
            </div>
            <div style={reqItemStyle(reqLower)}>
              {reqLower ? "✓" : "○"} Lowercase letter
            </div>
            <div style={reqItemStyle(reqNumber)}>
              {reqNumber ? "✓" : "○"} Number
            </div>
            <div style={reqItemStyle(reqSpecial)}>
              {reqSpecial ? "✓" : "○"} Special character
            </div>
          </div>

          <button
            id="reset-password-submit-btn"
            type="submit"
            disabled={submitting || !allReqsMet || newPassword !== confirmPassword}
            style={{
              ...buttonStyle,
              opacity: submitting || !allReqsMet || newPassword !== confirmPassword ? 0.6 : 1,
              cursor: submitting || !allReqsMet || newPassword !== confirmPassword ? "not-allowed" : "pointer",
            }}
          >
            {submitting ? "Updating Password..." : "Reset Password"}
          </button>

          <div style={{ textAlign: "center", marginTop: "20px" }}>
            <Link to="/login" style={{ fontSize: "13px", color: "#64748b", textDecoration: "none" }}>
              Back to Sign In
            </Link>
          </div>
        </form>
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
  maxWidth: "440px",
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

const warningCircleStyle = {
  width: "56px",
  height: "56px",
  borderRadius: "50%",
  backgroundColor: "#fef3c7",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  margin: "0 auto 12px auto",
};

const successCircleStyle = {
  width: "56px",
  height: "56px",
  borderRadius: "50%",
  backgroundColor: "#dcfce7",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  margin: "0 auto 12px auto",
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

const eyeToggleStyle = {
  position: "absolute",
  right: "10px",
  top: "50%",
  transform: "translateY(-50%)",
  background: "none",
  border: "none",
  cursor: "pointer",
  fontSize: "16px",
  padding: 0,
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

const requirementsCardStyle = {
  backgroundColor: "#f8fafc",
  border: "1px solid #e2e8f0",
  borderRadius: "8px",
  padding: "12px 14px",
  marginBottom: "20px",
};

const reqItemStyle = (passed) => ({
  fontSize: "12px",
  color: passed ? "#059669" : "#64748b",
  fontWeight: passed ? "600" : "400",
  marginBottom: "4px",
  display: "flex",
  alignItems: "center",
  gap: "6px",
});
