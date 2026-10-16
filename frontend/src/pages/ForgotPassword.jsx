import { useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../utils/api";

const SPECIAL_CHAR_REGEX = /[!@#$%^&*(),.?":{}|<>\-_=+[\]~`/\\';]/;

const ALLOWED_SECURITY_QUESTIONS = [
  "What is your favorite movie?",
  "What was your childhood nickname?",
  "What was the name of your first pet?",
  "What was the first concert you attended?",
  "What was the name of your childhood best friend?",
];

export default function ForgotPassword() {
  // Step machine: "EMAIL" | "QUESTION" | "PASSWORD" | "SUCCESS"
  const [step, setStep] = useState("EMAIL");

  // Step 1: Email Challenge
  const [email, setEmail] = useState("");
  const [maskedEmail, setMaskedEmail] = useState("");
  const [securityQuestion, setSecurityQuestion] = useState(ALLOWED_SECURITY_QUESTIONS[0]);

  // Step 2: Answer Verification
  const [securityAnswer, setSecurityAnswer] = useState("");
  const [recoveryToken, setRecoveryToken] = useState("");

  // Step 3: New Password
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Status & Errors
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // Live password validation
  const reqLength = newPassword.length >= 8;
  const reqUpper = /[A-Z]/.test(newPassword);
  const reqLower = /[a-z]/.test(newPassword);
  const reqNumber = /[0-9]/.test(newPassword);
  const reqSpecial = SPECIAL_CHAR_REGEX.test(newPassword);

  // ==============================================================================
  // Step 1: Submit Email for Security Question
  // ==============================================================================
  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      setError("Please enter your account email address.");
      return;
    }

    setSubmitting(true);

    try {
      const res = await apiFetch("/auth/recovery/challenge", {
        method: "POST",
        body: JSON.stringify({ email: cleanEmail }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error?.message || data?.detail || "Could not find account recovery information.");
      }

      const returnedQuestion = data?.security_question || data?.question || "";
      if (returnedQuestion) {
        setSecurityQuestion(returnedQuestion);
      }
      setMaskedEmail(data?.masked_email || cleanEmail);
      setStep("QUESTION");
    } catch (err) {
      setError(err.message || "Could not find account recovery information.");
    } finally {
      setSubmitting(false);
    }
  };

  // ==============================================================================
  // Step 2: Submit Security Answer for Recovery Token
  // ==============================================================================
  const handleAnswerSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const cleanAnswer = securityAnswer.trim();
    if (!cleanAnswer) {
      setError("Please enter your security answer.");
      return;
    }

    setSubmitting(true);

    try {
      const res = await apiFetch("/auth/recovery/verify-answer", {
        method: "POST",
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          answer: cleanAnswer,
          security_answer: cleanAnswer,
          security_question: securityQuestion,
          question: securityQuestion,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error?.message || data?.detail || "Incorrect security answer.");
      }

      setRecoveryToken(data.recovery_token);
      setStep("PASSWORD");
    } catch (err) {
      setError(err.message || "Incorrect security answer. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  // ==============================================================================
  // Step 3: Set New Password
  // ==============================================================================
  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!reqLength || !reqUpper || !reqLower || !reqNumber || !reqSpecial) {
      setError("Password must meet all 5 security criteria.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);

    try {
      const res = await apiFetch("/auth/recovery/reset-password", {
        method: "POST",
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          recovery_token: recoveryToken,
          new_password: newPassword,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error?.message || data?.detail || "Could not update password.");
      }

      setStep("SUCCESS");
    } catch (err) {
      setError(err.message || "Could not reset password. Your session may have expired.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        {/* Header */}
        <div style={{ marginBottom: "26px", textAlign: "left" }}>
          <span style={badgeStyle}>Account Recovery</span>
          <h1 style={titleStyle}>
            {step === "SUCCESS"
              ? "Password updated"
              : step === "PASSWORD"
              ? "Create new password"
              : step === "QUESTION"
              ? "Security verification"
              : "Recover your account"}
          </h1>
          <p style={subtitleStyle}>
            {step === "SUCCESS"
              ? "Your password has been securely reset. You can now log in."
              : step === "PASSWORD"
              ? "Choose a strong password to protect your account."
              : step === "QUESTION"
              ? "Answer the question you selected during registration."
              : "Enter your registered email address to begin."}
          </p>
        </div>

        {/* Global Error Banner */}
        {error && (
          <div style={errorBannerStyle} role="alert" id="recovery-error-alert">
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

        {/* ==================================================================== */}
        {/* Step 1: Email Form */}
        {/* ==================================================================== */}
        {step === "EMAIL" && (
          <form onSubmit={handleEmailSubmit} noValidate>
            <div style={formGroupStyle}>
              <label htmlFor="recovery-email" style={labelStyle}>
                Account email address
              </label>
              <input
                id="recovery-email"
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

            <button
              type="submit"
              id="recovery-continue-email-btn"
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
                  Finding account...
                </span>
              ) : (
                "Continue"
              )}
            </button>
          </form>
        )}

        {/* ==================================================================== */}
        {/* Step 2: Security Question Form */}
        {/* ==================================================================== */}
        {step === "QUESTION" && (
          <form onSubmit={handleAnswerSubmit} noValidate>
            <div style={accountBadgeBoxStyle}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)", display: "block", marginBottom: "2px" }}>
                Recovering account:
              </span>
              <strong style={{ fontSize: "14px", color: "var(--text-primary)" }}>{maskedEmail}</strong>
            </div>

            <div style={formGroupStyle}>
              <label htmlFor="recovery-security-question-select" style={{ ...labelStyle, fontSize: "14px", marginBottom: "6px" }}>
                Security question
              </label>
              <select
                id="recovery-security-question-select"
                value={securityQuestion}
                onChange={(e) => {
                  setSecurityQuestion(e.target.value);
                  if (error) setError(null);
                }}
                style={selectStyle}
                disabled={submitting}
              >
                {ALLOWED_SECURITY_QUESTIONS.map((q) => (
                  <option key={q} value={q}>
                    {q}
                  </option>
                ))}
              </select>
              <span style={{ ...hintStyle, color: "var(--primary-600)", fontWeight: "500", marginTop: "6px" }}>
                ✓ Loaded from your account records. Ensure it matches your registered question.
              </span>
            </div>

            <div style={formGroupStyle}>
              <label htmlFor="recovery-security-answer" style={labelStyle}>
                Your answer
              </label>
              <input
                id="recovery-security-answer"
                type="text"
                autoComplete="off"
                required
                value={securityAnswer}
                onChange={(e) => {
                  setSecurityAnswer(e.target.value);
                  if (error) setError(null);
                }}
                placeholder="Enter your security answer"
                style={inputStyle}
                disabled={submitting}
              />
              <span style={hintStyle}>
                Answers are case-insensitive. Extra spaces are trimmed automatically.
              </span>
            </div>

            <button
              type="submit"
              id="recovery-verify-answer-btn"
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
                  Verifying answer...
                </span>
              ) : (
                "Verify answer"
              )}
            </button>

            <button
              type="button"
              id="recovery-back-to-email-btn"
              onClick={() => {
                setError(null);
                setStep("EMAIL");
              }}
              style={secondaryLinkBtnStyle}
            >
              Use a different email
            </button>
          </form>
        )}

        {/* ==================================================================== */}
        {/* Step 3: New Password Form */}
        {/* ==================================================================== */}
        {step === "PASSWORD" && (
          <form onSubmit={handlePasswordSubmit} noValidate>
            <div style={formGroupStyle}>
              <label htmlFor="recovery-new-password" style={labelStyle}>
                New password
              </label>
              <div style={{ position: "relative" }}>
                <input
                  id="recovery-new-password"
                  type={showNewPassword ? "text" : "password"}
                  autoComplete="new-password"
                  required
                  value={newPassword}
                  onChange={(e) => {
                    setNewPassword(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder="••••••••"
                  style={{ ...inputStyle, paddingRight: "44px" }}
                  disabled={submitting}
                />
                <button
                  type="button"
                  id="recovery-show-new-password-btn"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  style={showPasswordBtnStyle}
                  aria-label={showNewPassword ? "Hide password" : "Show password"}
                  tabIndex="-1"
                >
                  {showNewPassword ? (
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

              {/* Password criteria */}
              {newPassword.length > 0 && (
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
            </div>

            <div style={formGroupStyle}>
              <label htmlFor="recovery-confirm-password" style={labelStyle}>
                Confirm new password
              </label>
              <div style={{ position: "relative" }}>
                <input
                  id="recovery-confirm-password"
                  type={showConfirmPassword ? "text" : "password"}
                  autoComplete="new-password"
                  required
                  value={confirmPassword}
                  onChange={(e) => {
                    setConfirmPassword(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder="••••••••"
                  style={{ ...inputStyle, paddingRight: "44px" }}
                  disabled={submitting}
                />
                <button
                  type="button"
                  id="recovery-show-confirm-password-btn"
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
            </div>

            <button
              type="submit"
              id="recovery-reset-password-btn"
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
                  Saving new password...
                </span>
              ) : (
                "Update password"
              )}
            </button>
          </form>
        )}

        {/* ==================================================================== */}
        {/* Step 4: Success Screen */}
        {/* ==================================================================== */}
        {step === "SUCCESS" && (
          <div>
            <div style={successBannerStyle} role="status">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
              <div>
                <p style={{ margin: "0 0 4px 0", fontWeight: "600", color: "var(--success-text)", fontSize: "14px" }}>
                  Password updated successfully
                </p>
                <p style={{ margin: 0, fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.4 }}>
                  All previous sessions have been invalidated. You can now sign in with your new password.
                </p>
              </div>
            </div>

            <Link
              to="/login"
              state={{ email }}
              id="recovery-return-login-btn"
              style={{
                ...primaryBtnStyle,
                display: "block",
                textAlign: "center",
                textDecoration: "none",
                boxSizing: "border-box",
                marginTop: "20px",
              }}
            >
              Return to sign in
            </Link>
          </div>
        )}

        {/* Return to Sign In Link */}
        {step !== "SUCCESS" && (
          <div style={footerStyle}>
            <Link
              to="/login"
              id="recovery-cancel-link"
              style={returnLinkStyle}
            >
              ← Back to sign in
            </Link>
          </div>
        )}
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
  maxWidth: "440px",
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

const successBannerStyle = {
  display: "flex",
  alignItems: "flex-start",
  gap: "12px",
  backgroundColor: "var(--success-bg)",
  color: "var(--success-text)",
  border: "1px solid var(--success-border)",
  borderRadius: "8px",
  padding: "14px 16px",
};

const accountBadgeBoxStyle = {
  padding: "10px 14px",
  backgroundColor: "var(--bg-app)",
  border: "1px solid var(--border-subtle)",
  borderRadius: "8px",
  marginBottom: "18px",
};

const questionHighlightBoxStyle = {
  padding: "12px 14px",
  backgroundColor: "var(--bg-app)",
  border: "1px solid var(--border-default)",
  borderRadius: "8px",
  lineHeight: 1.45,
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

const hintStyle = {
  display: "block",
  fontSize: "12px",
  color: "var(--text-muted)",
  marginTop: "6px",
  lineHeight: 1.4,
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

const secondaryLinkBtnStyle = {
  width: "100%",
  marginTop: "12px",
  padding: "8px",
  background: "none",
  border: "none",
  fontSize: "13px",
  color: "var(--text-muted)",
  cursor: "pointer",
  textAlign: "center",
};

const footerStyle = {
  marginTop: "24px",
  paddingTop: "20px",
  borderTop: "1px solid var(--border-subtle)",
  textAlign: "center",
};

const returnLinkStyle = {
  fontSize: "13px",
  fontWeight: "500",
  color: "var(--text-muted)",
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
