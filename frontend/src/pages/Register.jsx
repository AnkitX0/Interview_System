import { useState, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const SPECIAL_CHAR_REGEX = /[!@#$%^&*(),.?":{}|<>\-_=+[\]~`/\\';]/;

export default function Register() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const { user, loading: authLoading, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || "/dashboard";

  // Redirect if already authenticated
  useEffect(() => {
    if (!authLoading && user) {
      navigate(from, { replace: true });
    }
  }, [user, authLoading, navigate, from]);

  // Live Password Requirements
  const reqLength = password.length >= 8;
  const reqUpper = /[A-Z]/.test(password);
  const reqLower = /[a-z]/.test(password);
  const reqNumber = /[0-9]/.test(password);
  const reqSpecial = SPECIAL_CHAR_REGEX.test(password);

  const passedRequirementsCount = [reqLength, reqUpper, reqLower, reqNumber, reqSpecial].filter(Boolean).length;

  let passwordStrength = "Weak";
  let strengthColor = "#ef4444";
  let strengthPercent = 20;

  if (passedRequirementsCount >= 5) {
    passwordStrength = "Strong";
    strengthColor = "#10b981";
    strengthPercent = 100;
  } else if (passedRequirementsCount >= 3) {
    passwordStrength = "Fair";
    strengthColor = "#f59e0b";
    strengthPercent = 60;
  } else if (password.length > 0) {
    passwordStrength = "Weak";
    strengthColor = "#ef4444";
    strengthPercent = 30;
  }

  // Live confirm password check
  const passwordsMatch = confirmPassword.length > 0 && password === confirmPassword;
  const passwordsMismatch = confirmPassword.length > 0 && password !== confirmPassword;

  // Client-side validation
  const validateForm = () => {
    const errors = {};
    const trimmedName = fullName.trim();
    if (!trimmedName || trimmedName.length < 2 || !/[a-zA-Z]/.test(trimmedName)) {
      errors.fullName = "Please enter your name.";
    }

    const trimmedEmail = email.trim().toLowerCase();
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!trimmedEmail || !emailRegex.test(trimmedEmail)) {
      errors.email = "Please use a Gmail address.";
    } else {
      const parts = trimmedEmail.split("@");
      if (parts.length !== 2 || parts[1] !== "gmail.com") {
        errors.email = "Please use a Gmail address.";
      }
    }

    if (!reqLength || !reqUpper || !reqLower || !reqNumber || !reqSpecial) {
      errors.password = "Password must be at least 8 characters and include uppercase, lowercase, number, and special character.";
    }

    if (password !== confirmPassword) {
      errors.confirmPassword = "Passwords do not match.";
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!validateForm()) {
      return;
    }

    setSubmitting(true);

    try {
      const normalizedEmail = email.trim().toLowerCase();
      const res = await register(normalizedEmail, password, fullName.trim());

      if (res?.verification_required) {
        if (res?.email_status === "FAILED") {
          setError("We created your pending registration, but could not deliver the verification email right now. Please try resending from the verification page or try again in a moment.");
          return;
        }
        // Direct transition to the 6-digit OTP verification screen
        navigate("/verify-email", {
          state: {
            email: normalizedEmail,
            emailStatus: res?.email_status || "EMAIL_SENT",
          },
        });
      } else {
        // Direct transition to dashboard if verification disabled
        navigate(from, { replace: true });
      }
    } catch (err) {
      const msg = err.message || "Something went wrong while creating your account. Please try again.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={pageContainerStyle}>
      <div style={cardStyle}>
        {/* Brand Header */}
        <div style={{ textAlign: "center", marginBottom: "26px" }}>
          <div style={badgeStyle}>AI Interview Intelligence</div>
          <h1 style={{ fontSize: "24px", fontWeight: "700", color: "#f8fafc", margin: "14px 0 6px 0", letterSpacing: "-0.01em" }}>
            Create Your Account
          </h1>
          <p style={{ fontSize: "14px", color: "#94a3b8", margin: 0, lineHeight: 1.5 }}>
            Master technical interviews with evidence-based intelligence.
          </p>
        </div>

        {/* Global Error Banner */}
        {error && (
          <div style={errorBannerStyle} role="alert">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f87171" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: "1px" }}>
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div>
              <span>{error}</span>
              {error.toLowerCase().includes("already exists") && (
                <div style={{ marginTop: "6px" }}>
                  <Link to="/login" style={{ color: "#93c5fd", textDecoration: "underline", fontWeight: "600" }}>
                    Sign in here
                  </Link>
                  {" or "}
                  <Link to="/forgot-password" style={{ color: "#93c5fd", textDecoration: "underline", fontWeight: "600" }}>
                    reset your password
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} noValidate>
          {/* Full Name */}
          <div style={{ marginBottom: "18px" }}>
            <label htmlFor="register-fullname-input" style={labelStyle}>
              Full Name
            </label>
            <input
              id="register-fullname-input"
              type="text"
              required
              value={fullName}
              onChange={(e) => {
                setFullName(e.target.value);
                if (fieldErrors.fullName) setFieldErrors((prev) => ({ ...prev, fullName: null }));
              }}
              placeholder="e.g. Alex Chen"
              style={{
                ...inputStyle,
                borderColor: fieldErrors.fullName ? "#ef4444" : "#334155",
              }}
            />
            {fieldErrors.fullName && <p style={fieldErrorStyle}>{fieldErrors.fullName}</p>}
          </div>

          {/* Email Address */}
          <div style={{ marginBottom: "18px" }}>
            <label htmlFor="register-email-input" style={labelStyle}>
              Gmail Address
            </label>
            <input
              id="register-email-input"
              type="email"
              required
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (fieldErrors.email) setFieldErrors((prev) => ({ ...prev, email: null }));
              }}
              placeholder="name@gmail.com"
              style={{
                ...inputStyle,
                borderColor: fieldErrors.email ? "#ef4444" : "#334155",
              }}
            />
            {fieldErrors.email && <p style={fieldErrorStyle}>{fieldErrors.email}</p>}
          </div>

          {/* Password */}
          <div style={{ marginBottom: "18px" }}>
            <label htmlFor="register-password-input" style={labelStyle}>
              Password
            </label>
            <div style={{ position: "relative" }}>
              <input
                id="register-password-input"
                type={showPassword ? "text" : "password"}
                required
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (fieldErrors.password) setFieldErrors((prev) => ({ ...prev, password: null }));
                }}
                placeholder="••••••••••••"
                style={{
                  ...inputStyle,
                  paddingRight: "42px",
                  borderColor: fieldErrors.password ? "#ef4444" : "#334155",
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
            {fieldErrors.password && <p style={fieldErrorStyle}>{fieldErrors.password}</p>}

            {/* Password Strength Meter */}
            {password.length > 0 && (
              <div style={{ marginTop: "8px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                  <span style={{ fontSize: "11px", color: "#64748b" }}>Strength</span>
                  <span style={{ fontSize: "11px", fontWeight: "600", color: strengthColor }}>{passwordStrength}</span>
                </div>
                <div style={{ height: "4px", backgroundColor: "#1e293b", borderRadius: "2px", overflow: "hidden" }}>
                  <div
                    style={{
                      width: `${strengthPercent}%`,
                      height: "100%",
                      backgroundColor: strengthColor,
                      transition: "all 0.2s ease",
                    }}
                  />
                </div>
              </div>
            )}

            {/* Password Requirements Checklist */}
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

          {/* Confirm Password */}
          <div style={{ marginBottom: "22px" }}>
            <label htmlFor="register-confirm-password-input" style={labelStyle}>
              Confirm Password
            </label>
            <div style={{ position: "relative" }}>
              <input
                id="register-confirm-password-input"
                type={showConfirmPassword ? "text" : "password"}
                required
                value={confirmPassword}
                onChange={(e) => {
                  setConfirmPassword(e.target.value);
                  if (fieldErrors.confirmPassword) setFieldErrors((prev) => ({ ...prev, confirmPassword: null }));
                }}
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
            {fieldErrors.confirmPassword && <p style={fieldErrorStyle}>{fieldErrors.confirmPassword}</p>}
            {passwordsMatch && <p style={{ fontSize: "12px", color: "#10b981", marginTop: "4px" }}>✓ Passwords match</p>}
          </div>

          {/* Submit Button */}
          <button
            id="register-submit-btn"
            type="submit"
            disabled={submitting}
            style={{
              ...primaryButtonStyle,
              opacity: submitting ? 0.7 : 1,
              cursor: submitting ? "not-allowed" : "pointer",
            }}
          >
            {submitting ? "Creating Account..." : "Create Account & Verify"}
          </button>
        </form>

        {/* Existing User Login Link */}
        <div style={{ textAlign: "center", marginTop: "24px", paddingTop: "18px", borderTop: "1px solid #1e293b" }}>
          <p style={{ fontSize: "13px", color: "#94a3b8", margin: 0 }}>
            Already have an account?{" "}
            <Link to="/login" id="register-login-link" style={{ color: "#60a5fa", fontWeight: "600", textDecoration: "none" }}>
              Sign In
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Styles: Dark Navy SaaS Design
// ============================================================================
const pageContainerStyle = {
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  minHeight: "85vh",
  padding: "32px 16px",
};

const cardStyle = {
  backgroundColor: "#111827",
  border: "1px solid #1f2937",
  borderRadius: "16px",
  boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.4)",
  padding: "36px 32px",
  width: "100%",
  maxWidth: "480px",
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

const fieldErrorStyle = {
  fontSize: "12px",
  color: "#f87171",
  marginTop: "4px",
  marginBottom: 0,
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
  marginBottom: "20px",
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
