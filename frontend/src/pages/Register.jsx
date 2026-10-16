import { useState, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const SECURITY_QUESTIONS = [
  "What is your favorite movie?",
  "What was your childhood nickname?",
  "What was the name of your first pet?",
  "What was the first concert you attended?",
  "What was the name of your childhood best friend?",
];

const SPECIAL_CHAR_REGEX = /[!@#$%^&*(),.?":{}|<>\-_=+[\]~`/\\';]/;

export default function Register() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [securityQuestion, setSecurityQuestion] = useState(SECURITY_QUESTIONS[0]);
  const [securityAnswer, setSecurityAnswer] = useState("");
  const [savedAnswerAck, setSavedAnswerAck] = useState(false);

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

  // Live password requirements
  const reqLength = password.length >= 8;
  const reqUpper = /[A-Z]/.test(password);
  const reqLower = /[a-z]/.test(password);
  const reqNumber = /[0-9]/.test(password);
  const reqSpecial = SPECIAL_CHAR_REGEX.test(password);

  const validateForm = () => {
    const errors = {};
    const trimmedName = fullName.trim();
    if (!trimmedName || trimmedName.length < 2) {
      errors.fullName = "Please enter your full name.";
    }

    const trimmedEmail = email.trim().toLowerCase();
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!trimmedEmail || !emailRegex.test(trimmedEmail)) {
      errors.email = "Please enter a valid email address.";
    }

    if (!reqLength || !reqUpper || !reqLower || !reqNumber || !reqSpecial) {
      errors.password = "Password must meet all 5 security criteria.";
    }

    if (password !== confirmPassword) {
      errors.confirmPassword = "Passwords do not match.";
    }

    if (!SECURITY_QUESTIONS.includes(securityQuestion)) {
      errors.securityQuestion = "Please choose a valid security question from the list.";
    }

    const trimmedAnswer = securityAnswer.trim();
    if (!trimmedAnswer || trimmedAnswer.length < 2) {
      errors.securityAnswer = "Security answer must be at least 2 characters.";
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
      await register(
        email.trim(),
        password,
        fullName.trim(),
        securityQuestion,
        securityAnswer.trim()
      );
      // Immediately authenticated without OTP/email verification
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || "Registration failed. Please check your details and try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        {/* Header */}
        <div style={{ marginBottom: "26px", textAlign: "left" }}>
          <span style={badgeStyle}>AI Interview Intelligence</span>
          <h1 style={titleStyle}>Create your account</h1>
          <p style={subtitleStyle}>Start practicing realistic, AI-evaluated interviews today.</p>
        </div>

        {/* Global Error Banner */}
        {error && (
          <div style={errorBannerStyle} role="alert" id="register-error-alert">
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
          {/* Full Name */}
          <div style={formGroupStyle}>
            <label htmlFor="register-full-name" style={labelStyle}>
              Full name
            </label>
            <input
              id="register-full-name"
              type="text"
              autoComplete="name"
              required
              value={fullName}
              onChange={(e) => {
                setFullName(e.target.value);
                if (fieldErrors.fullName) setFieldErrors((prev) => ({ ...prev, fullName: null }));
              }}
              placeholder="e.g. Alex Morgan"
              style={fieldErrors.fullName ? { ...inputStyle, borderColor: "var(--danger-border)" } : inputStyle}
              disabled={submitting}
            />
            {fieldErrors.fullName && <p style={fieldErrorStyle}>{fieldErrors.fullName}</p>}
          </div>

          {/* Email Address */}
          <div style={formGroupStyle}>
            <label htmlFor="register-email" style={labelStyle}>
              Email address
            </label>
            <input
              id="register-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (fieldErrors.email) setFieldErrors((prev) => ({ ...prev, email: null }));
              }}
              placeholder="name@example.com"
              style={fieldErrors.email ? { ...inputStyle, borderColor: "var(--danger-border)" } : inputStyle}
              disabled={submitting}
            />
            {fieldErrors.email && <p style={fieldErrorStyle}>{fieldErrors.email}</p>}
          </div>

          {/* Password */}
          <div style={formGroupStyle}>
            <label htmlFor="register-password" style={labelStyle}>
              Password
            </label>
            <div style={{ position: "relative" }}>
              <input
                id="register-password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (fieldErrors.password) setFieldErrors((prev) => ({ ...prev, password: null }));
                }}
                placeholder="••••••••"
                style={{
                  ...inputStyle,
                  paddingRight: "44px",
                  borderColor: fieldErrors.password ? "var(--danger-border)" : "var(--border-default)",
                }}
                disabled={submitting}
              />
              <button
                type="button"
                id="register-show-password-btn"
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

            {/* Password Criteria Checklist */}
            {password.length > 0 && (
              <div style={criteriaBoxStyle}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px 12px" }}>
                  <CriterionMet met={reqLength} text="At least 8 characters" />
                  <CriterionMet met={reqUpper} text="Uppercase letter (A-Z)" />
                  <CriterionMet met={reqLower} text="Lowercase letter (a-z)" />
                  <CriterionMet met={reqNumber} text="Number (0-9)" />
                  <CriterionMet met={reqSpecial} text="Special character (!@#...)" />
                </div>
              </div>
            )}
            {fieldErrors.password && <p style={fieldErrorStyle}>{fieldErrors.password}</p>}
          </div>

          {/* Confirm Password */}
          <div style={formGroupStyle}>
            <label htmlFor="register-confirm-password" style={labelStyle}>
              Confirm password
            </label>
            <div style={{ position: "relative" }}>
              <input
                id="register-confirm-password"
                type={showConfirmPassword ? "text" : "password"}
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => {
                  setConfirmPassword(e.target.value);
                  if (fieldErrors.confirmPassword) setFieldErrors((prev) => ({ ...prev, confirmPassword: null }));
                }}
                placeholder="••••••••"
                style={{
                  ...inputStyle,
                  paddingRight: "44px",
                  borderColor: fieldErrors.confirmPassword ? "var(--danger-border)" : "var(--border-default)",
                }}
                disabled={submitting}
              />
              <button
                type="button"
                id="register-show-confirm-password-btn"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                style={showPasswordBtnStyle}
                aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}
                tabIndex="-1"
              >
                {showConfirmPassword ? (
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
            {fieldErrors.confirmPassword && <p style={fieldErrorStyle}>{fieldErrors.confirmPassword}</p>}
          </div>

          {/* Section Divider: Security Recovery */}
          <div style={sectionDividerStyle}>
            <span style={sectionLabelStyle}>Account Recovery Setup</span>
            <p style={sectionHintStyle}>
              Choose a security question to recover your account if you forget your password. We store your answer as a secure hash.
            </p>
          </div>

          {/* Security Question Selection */}
          <div style={formGroupStyle}>
            <label htmlFor="register-security-question" style={labelStyle}>
              Security question
            </label>
            <select
              id="register-security-question"
              value={securityQuestion}
              onChange={(e) => {
                setSecurityQuestion(e.target.value);
                if (fieldErrors.securityQuestion) setFieldErrors((prev) => ({ ...prev, securityQuestion: null }));
              }}
              style={selectStyle}
              disabled={submitting}
            >
              {SECURITY_QUESTIONS.map((q) => (
                <option key={q} value={q}>
                  {q}
                </option>
              ))}
            </select>
            {fieldErrors.securityQuestion && <p style={fieldErrorStyle}>{fieldErrors.securityQuestion}</p>}
          </div>

          {/* Security Answer */}
          <div style={formGroupStyle}>
            <label htmlFor="register-security-answer" style={labelStyle}>
              Security answer
            </label>
            <input
              id="register-security-answer"
              type="text"
              autoComplete="off"
              required
              value={securityAnswer}
              onChange={(e) => {
                setSecurityAnswer(e.target.value);
                if (fieldErrors.securityAnswer) setFieldErrors((prev) => ({ ...prev, securityAnswer: null }));
              }}
              placeholder="Enter your answer and remember it for account recovery"
              style={fieldErrors.securityAnswer ? { ...inputStyle, borderColor: "var(--danger-border)" } : inputStyle}
              disabled={submitting}
            />
            {fieldErrors.securityAnswer && <p style={fieldErrorStyle}>{fieldErrors.securityAnswer}</p>}
          </div>

          {/* Saved Answer Acknowledgement Checkbox */}
          <div style={{ display: "flex", alignItems: "flex-start", marginBottom: "22px" }}>
            <input
              id="register-saved-answer-ack"
              type="checkbox"
              checked={savedAnswerAck}
              onChange={(e) => setSavedAnswerAck(e.target.checked)}
              style={{ ...checkboxStyle, marginTop: "2px" }}
              disabled={submitting}
            />
            <label htmlFor="register-saved-answer-ack" style={checkboxLabelStyle}>
              I've saved my security answer somewhere safe
            </label>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            id="register-submit-btn"
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
                Creating account...
              </span>
            ) : (
              "Create account"
            )}
          </button>
        </form>

        {/* Sign In Footer */}
        <div style={footerStyle}>
          <span style={{ color: "var(--text-muted)", fontSize: "14px" }}>
            Already have an account?{" "}
          </span>
          <Link
            to="/login"
            id="register-login-link"
            style={loginLinkStyle}
          >
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}

function CriterionMet({ met, text }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}>
      {met ? (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--success-text)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
          <polyline points="20 6 9 17 4 12" />
        </svg>
      ) : (
        <span style={{ width: "6px", height: "6px", borderRadius: "50%", backgroundColor: "var(--text-disabled)", display: "inline-block", margin: "4px" }} />
      )}
      <span style={{ color: met ? "var(--success-text)" : "var(--text-muted)" }}>{text}</span>
    </div>
  );
}

// ==============================================================================
// Styles
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
  maxWidth: "480px",
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
  marginBottom: "16px",
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

const selectStyle = {
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
  cursor: "pointer",
};

const fieldErrorStyle = {
  fontSize: "12px",
  color: "var(--danger-text)",
  margin: "4px 0 0 0",
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

const criteriaBoxStyle = {
  marginTop: "10px",
  padding: "10px 12px",
  backgroundColor: "var(--bg-app)",
  border: "1px solid var(--border-subtle)",
  borderRadius: "6px",
};

const sectionDividerStyle = {
  margin: "24px 0 16px 0",
  paddingTop: "16px",
  borderTop: "1px solid var(--border-subtle)",
};

const sectionLabelStyle = {
  display: "block",
  fontSize: "13px",
  fontWeight: "600",
  letterSpacing: "0.02em",
  color: "var(--text-primary)",
  marginBottom: "4px",
};

const sectionHintStyle = {
  fontSize: "12px",
  color: "var(--text-muted)",
  margin: 0,
  lineHeight: 1.45,
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
  lineHeight: 1.4,
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

const loginLinkStyle = {
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
