import { useState, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../utils/api";

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

  // Verification Pending State
  const [verificationPending, setVerificationPending] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState("");
  const [emailDeliveryStatus, setEmailDeliveryStatus] = useState("EMAIL_SENT");
  const [resending, setResending] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resendMessage, setResendMessage] = useState(null);

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

  // Resend cooldown timer countdown
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

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
      setRegisteredEmail(normalizedEmail);
      setEmailDeliveryStatus(res?.email_status || "EMAIL_SENT");
      setVerificationPending(true);
      setResendCooldown(60); // 60s initial cooldown
    } catch (err) {
      const msg = err.message || "Something went wrong while creating your account. Please try again.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    if (resendCooldown > 0 || resending) return;
    setResending(true);
    setResendMessage(null);
    setError(null);

    try {
      const res = await apiFetch("/auth/resend-verification", {
        method: "POST",
        body: JSON.stringify({ email: registeredEmail }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error?.message || data?.detail || "We couldn't resend the email. Please try again.");
      }
      setEmailDeliveryStatus("EMAIL_SENT");
      setResendMessage("Verification email sent. Please check your inbox.");
      setResendCooldown(60);
    } catch (err) {
      setError(err.message || "We couldn't resend the email. Please try again.");
    } finally {
      setResending(false);
    }
  };

  // Render Verification Pending Screen
  if (verificationPending) {
    const isEmailSent = emailDeliveryStatus === "EMAIL_SENT";

    return (
      <div style={containerStyle}>
        <div style={cardStyle}>
          {/* Header */}
          <div style={{ textAlign: "center", marginBottom: "24px" }}>
            <div style={badgeStyle}>Interview Intelligence</div>
            <div style={isEmailSent ? iconCircleStyle : warningCircleStyle}>
              {isEmailSent ? (
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect width="20" height="16" x="2" y="4" rx="2" />
                  <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                </svg>
              ) : (
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#d97706" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              )}
            </div>
            <h2 style={{ fontSize: "22px", fontWeight: "700", color: "#0f172a", margin: "14px 0 6px 0" }}>
              {isEmailSent ? "Check your email" : "Email delivery issue"}
            </h2>
            <p style={{ fontSize: "14px", color: isEmailSent ? "#64748b" : "#b45309", margin: 0 }}>
              {isEmailSent
                ? "Verify your email address to activate your account."
                : "Your account is created, but the verification email could not be sent."}
            </p>
          </div>

          {resendMessage && (
            <div style={successBannerStyle}>
              <span>{resendMessage}</span>
            </div>
          )}

          {error && (
            <div style={errorBannerStyle}>
              <span>{error}</span>
            </div>
          )}

          {!isEmailSent && !error && (
            <div style={warningBannerStyle}>
              <span>We couldn't send the verification email right now. Please try again.</span>
            </div>
          )}

          <div style={{ backgroundColor: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0", padding: "14px 16px", marginBottom: "20px", textAlign: "center" }}>
            <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "4px" }}>
              {isEmailSent ? "We sent a verification link to:" : "Registered email address:"}
            </div>
            <div style={{ fontSize: "14px", fontWeight: "600", color: "#0f172a", wordBreak: "break-all" }}>
              {registeredEmail}
            </div>
          </div>

          <div style={{ fontSize: "13px", color: "#475569", lineHeight: "1.5", marginBottom: "24px", textAlign: "center" }}>
            {isEmailSent ? (
              <>
                Click the link in the email to activate your account.<br />
                <span style={{ color: "#64748b", fontSize: "12px" }}>This link expires in 30 minutes.</span>
              </>
            ) : (
              <span style={{ color: "#64748b" }}>
                Use the button below to resend the verification email when your email service is configured.
              </span>
            )}
          </div>

          <div style={{ textAlign: "center", paddingTop: "18px", borderTop: "1px solid #f1f5f9" }}>
            <p style={{ fontSize: "13px", color: "#64748b", margin: "0 0 10px 0" }}>
              Didn't receive the email?
            </p>
            <button
              id="resend-verification-btn"
              type="button"
              onClick={handleResend}
              disabled={resendCooldown > 0 || resending}
              style={{
                ...secondaryButtonStyle,
                opacity: resendCooldown > 0 || resending ? 0.6 : 1,
                cursor: resendCooldown > 0 || resending ? "not-allowed" : "pointer",
              }}
            >
              {resending ? "Sending..." : resendCooldown > 0 ? `Resend in ${resendCooldown}s` : "Resend verification email"}
            </button>
          </div>

          <div style={{ textAlign: "center", marginTop: "20px" }}>
            <Link to="/login" style={{ fontSize: "13px", color: "#2563eb", fontWeight: "600", textDecoration: "none" }}>
              Return to Sign In
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Render Registration Form
  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <div style={{ textAlign: "center", marginBottom: "24px" }}>
          <div style={badgeStyle}>Interview Intelligence</div>
          <h2 style={{ fontSize: "22px", fontWeight: "700", color: "#0f172a", margin: "10px 0 6px 0" }}>
            Create your account
          </h2>
          <p style={{ fontSize: "14px", color: "#64748b", margin: 0 }}>
            Prepare smarter. Interview with confidence.
          </p>
        </div>

        {error && (
          <div style={errorBannerStyle}>
            <span style={{ fontSize: "13px", fontWeight: "500" }}>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          {/* Full Name */}
          <div style={{ marginBottom: "16px" }}>
            <label htmlFor="register-fullname" style={labelStyle}>
              Full Name
            </label>
            <input
              id="register-fullname"
              name="fullName"
              type="text"
              autoComplete="name"
              required
              autoFocus
              value={fullName}
              onChange={(e) => {
                setFullName(e.target.value);
                if (fieldErrors.fullName) {
                  setFieldErrors((prev) => ({ ...prev, fullName: null }));
                }
              }}
              placeholder="Alex Morgan"
              style={{
                ...inputStyle,
                borderColor: fieldErrors.fullName ? "#ef4444" : "#cbd5e1",
              }}
            />
            {fieldErrors.fullName && (
              <span style={fieldErrorStyle}>{fieldErrors.fullName}</span>
            )}
          </div>

          {/* Gmail Address */}
          <div style={{ marginBottom: "16px" }}>
            <label htmlFor="register-email" style={labelStyle}>
              Gmail Address
            </label>
            <input
              id="register-email"
              name="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (fieldErrors.email) {
                  setFieldErrors((prev) => ({ ...prev, email: null }));
                }
              }}
              placeholder="you@gmail.com"
              style={{
                ...inputStyle,
                borderColor: fieldErrors.email ? "#ef4444" : "#cbd5e1",
              }}
            />
            <span style={{ display: "block", fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
              Gmail addresses only.
            </span>
            {fieldErrors.email && (
              <span style={fieldErrorStyle}>{fieldErrors.email}</span>
            )}
          </div>

          {/* Password */}
          <div style={{ marginBottom: "16px" }}>
            <label htmlFor="register-password" style={labelStyle}>
              Password
            </label>
            <div style={{ position: "relative" }}>
              <input
                id="register-password"
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (fieldErrors.password) {
                    setFieldErrors((prev) => ({ ...prev, password: null }));
                  }
                }}
                placeholder="••••••••••••"
                style={{
                  ...inputStyle,
                  paddingRight: "42px",
                  borderColor: fieldErrors.password ? "#ef4444" : "#cbd5e1",
                }}
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

            {/* Password Strength Indicator */}
            {password.length > 0 && (
              <div style={{ marginTop: "8px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                  <span style={{ fontSize: "11px", color: "#64748b", fontWeight: "500" }}>Password strength</span>
                  <span style={{ fontSize: "11px", fontWeight: "600", color: strengthColor }}>{passwordStrength}</span>
                </div>
                <div style={{ height: "4px", width: "100%", backgroundColor: "#e2e8f0", borderRadius: "2px", overflow: "hidden" }}>
                  <div
                    style={{
                      height: "100%",
                      width: `${strengthPercent}%`,
                      backgroundColor: strengthColor,
                      transition: "all 0.2s ease",
                    }}
                  />
                </div>
              </div>
            )}

            {/* Live Requirements Checklist */}
            <div style={{ marginTop: "10px", padding: "10px 12px", backgroundColor: "#f8fafc", borderRadius: "6px", border: "1px solid #f1f5f9" }}>
              <div style={{ fontSize: "11px", fontWeight: "600", color: "#475569", marginBottom: "6px" }}>
                Password requirements
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px" }}>
                <RequirementItem satisfied={reqLength} text="8+ characters" />
                <RequirementItem satisfied={reqUpper} text="Uppercase" />
                <RequirementItem satisfied={reqLower} text="Lowercase" />
                <RequirementItem satisfied={reqNumber} text="Number" />
                <RequirementItem satisfied={reqSpecial} text="Special character" />
              </div>
            </div>

            {fieldErrors.password && (
              <span style={fieldErrorStyle}>{fieldErrors.password}</span>
            )}
          </div>

          {/* Confirm Password */}
          <div style={{ marginBottom: "22px" }}>
            <label htmlFor="register-confirm-password" style={labelStyle}>
              Confirm Password
            </label>
            <div style={{ position: "relative" }}>
              <input
                id="register-confirm-password"
                name="confirmPassword"
                type={showConfirmPassword ? "text" : "password"}
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => {
                  setConfirmPassword(e.target.value);
                  if (fieldErrors.confirmPassword) {
                    setFieldErrors((prev) => ({ ...prev, confirmPassword: null }));
                  }
                }}
                placeholder="••••••••••••"
                style={{
                  ...inputStyle,
                  paddingRight: "42px",
                  borderColor: passwordsMismatch || fieldErrors.confirmPassword ? "#ef4444" : passwordsMatch ? "#10b981" : "#cbd5e1",
                }}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                style={eyeButtonStyle}
              >
                {showConfirmPassword ? (
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
            {passwordsMismatch && (
              <span style={fieldErrorStyle}>Passwords do not match.</span>
            )}
            {fieldErrors.confirmPassword && !passwordsMismatch && (
              <span style={fieldErrorStyle}>{fieldErrors.confirmPassword}</span>
            )}
          </div>

          {/* Submit Button */}
          <button
            id="register-submit-btn"
            type="submit"
            disabled={submitting}
            style={{
              ...buttonStyle,
              opacity: submitting ? 0.7 : 1,
              cursor: submitting ? "not-allowed" : "pointer",
            }}
          >
            {submitting ? "Creating account..." : "Create Account"}
          </button>
        </form>

        {/* Trust Information */}
        <div style={{ textAlign: "center", marginTop: "16px" }}>
          <p style={{ fontSize: "12px", color: "#94a3b8", margin: 0 }}>
            Your account credentials are securely protected.
          </p>
        </div>

        {/* Sign In Link */}
        <div style={{ textAlign: "center", marginTop: "22px", paddingTop: "18px", borderTop: "1px solid #f1f5f9" }}>
          <p style={{ fontSize: "13px", color: "#64748b", margin: 0 }}>
            Already have an account?{" "}
            <Link to="/login" style={{ color: "#2563eb", fontWeight: "600", textDecoration: "none" }}>
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

function RequirementItem({ satisfied, text }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", color: satisfied ? "#166534" : "#94a3b8" }}>
      <span style={{ fontWeight: "bold" }}>{satisfied ? "✓" : "○"}</span>
      <span>{text}</span>
    </div>
  );
}

// Visual styles consistent with Login.jsx
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

const iconCircleStyle = {
  width: "56px",
  height: "56px",
  borderRadius: "28px",
  backgroundColor: "#eff6ff",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  margin: "16px auto 0 auto",
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
  padding: "9px 18px",
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
  marginBottom: "18px",
  border: "1px solid #fecaca",
  fontSize: "13px",
};

const successBannerStyle = {
  backgroundColor: "#f0fdf4",
  color: "#166534",
  padding: "10px 14px",
  borderRadius: "8px",
  marginBottom: "18px",
  border: "1px solid #bbf7d0",
  fontSize: "13px",
  textAlign: "center",
};

const fieldErrorStyle = {
  display: "block",
  fontSize: "12px",
  color: "#ef4444",
  marginTop: "4px",
  fontWeight: "500",
};

const warningBannerStyle = {
  backgroundColor: "#fffbeb",
  color: "#b45309",
  padding: "12px 14px",
  borderRadius: "8px",
  marginBottom: "18px",
  border: "1px solid #fde68a",
  fontSize: "13px",
  textAlign: "center",
  fontWeight: "500",
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

