import { useState, useEffect, useRef, useCallback } from "react";
import { Link, useSearchParams, useNavigate, useLocation } from "react-router-dom";
import { apiFetch } from "../utils/api";
import { maskEmail } from "../utils/maskEmail";

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();

  // Query and navigation state
  const paramEmail = searchParams.get("email") || "";
  const paramOtp = searchParams.get("otp") || "";
  const paramToken = searchParams.get("token") || "";
  const stateEmail = location.state?.email || "";
  const initialEmail = (stateEmail || paramEmail || "").trim().toLowerCase();

  const [email, setEmail] = useState(initialEmail);
  const [otpDigits, setOtpDigits] = useState(["", "", "", "", "", ""]);
  const inputRefs = useRef([]);

  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);
  const [resendSuccess, setResendSuccess] = useState(null);
  const [resending, setResending] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(location.state?.email ? 60 : 0);

  const autoVerifyAttemptedRef = useRef(false);

  // Focus the first input on initial render
  useEffect(() => {
    if (!success && inputRefs.current[0] && !paramOtp && !paramToken) {
      inputRefs.current[0].focus();
    }
  }, [success, paramOtp, paramToken]);

  // Resend cooldown countdown timer
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const interval = setInterval(() => {
      setResendCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [resendCooldown]);

  // Submission handler
  const performVerification = useCallback(
    async (codeToVerify, tokenToVerify) => {
      setError(null);
      setResendSuccess(null);
      setLoading(true);

      try {
        const payload = {};
        if (codeToVerify) {
          payload.otp = codeToVerify;
          payload.email = email.trim().toLowerCase();
        } else if (tokenToVerify) {
          payload.token = tokenToVerify;
          if (email) payload.email = email.trim().toLowerCase();
        }

        const res = await apiFetch("/auth/verify-email", {
          method: "POST",
          body: JSON.stringify(payload),
        });

        const data = await res.json();

        if (res.ok) {
          setSuccess(true);
        } else {
          const detail = data?.error?.message || data?.detail || "Verification failed. Please check the code and try again.";
          setError(detail);
        }
      } catch {
        setError("Network error connecting to verification service. Please try again.");
      } finally {
        setLoading(false);
      }
    },
    [email]
  );

  // Auto-verify if link contains complete OTP or token
  useEffect(() => {
    if (autoVerifyAttemptedRef.current) return;

    if (paramOtp && paramOtp.trim().length === 6 && /^\d+$/.test(paramOtp.trim())) {
      autoVerifyAttemptedRef.current = true;
      const digits = paramOtp.trim().split("");
      setOtpDigits(digits);
      performVerification(paramOtp.trim(), null);
    } else if (paramToken && paramToken.trim()) {
      autoVerifyAttemptedRef.current = true;
      performVerification(null, paramToken.trim());
    }
  }, [paramOtp, paramToken, performVerification]);

  // Handle single digit input
  const handleDigitChange = (index, value) => {
    const cleaned = value.replace(/\D/g, "");
    if (!cleaned) {
      const next = [...otpDigits];
      next[index] = "";
      setOtpDigits(next);
      return;
    }

    const digit = cleaned.slice(-1);
    const next = [...otpDigits];
    next[index] = digit;
    setOtpDigits(next);

    // Auto-advance to next input
    if (index < 5 && inputRefs.current[index + 1]) {
      inputRefs.current[index + 1].focus();
    }
  };

  // Handle Backspace and arrow navigation
  const handleKeyDown = (index, e) => {
    if (e.key === "Backspace" && !otpDigits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === "ArrowLeft" && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === "ArrowRight" && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  // Handle paste for full 6-digit code
  const handlePaste = (e) => {
    e.preventDefault();
    const pasteData = e.clipboardData.getData("text").trim();
    const digitsOnly = pasteData.replace(/\D/g, "").slice(0, 6);
    if (!digitsOnly) return;

    const next = ["", "", "", "", "", ""];
    for (let i = 0; i < digitsOnly.length; i++) {
      next[i] = digitsOnly[i];
    }
    setOtpDigits(next);

    const targetFocus = Math.min(digitsOnly.length, 5);
    inputRefs.current[targetFocus]?.focus();

    if (digitsOnly.length === 6) {
      performVerification(digitsOnly, null);
    }
  };

  const fullCode = otpDigits.join("");
  const isCodeComplete = fullCode.length === 6;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!isCodeComplete || loading) return;
    performVerification(fullCode, null);
  };

  // Resend OTP
  const handleResend = async () => {
    if (!email || resendCooldown > 0 || resending) return;

    setResending(true);
    setError(null);
    setResendSuccess(null);

    try {
      const res = await apiFetch("/auth/resend-verification", {
        method: "POST",
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      const data = await res.json();

      if (res.ok) {
        setResendSuccess("A new 6-digit verification code has been sent.");
        setResendCooldown(60);
        setOtpDigits(["", "", "", "", "", ""]);
        inputRefs.current[0]?.focus();
      } else {
        const detail = data?.error?.message || data?.detail || "Could not resend code. Please try again.";
        setError(detail);
      }
    } catch {
      setError("Failed to connect to server. Please try again.");
    } finally {
      setResending(false);
    }
  };

  return (
    <div style={pageContainerStyle}>
      <div style={cardStyle}>
        {/* Brand Header */}
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <div style={badgeStyle}>AI Interview Intelligence</div>
          <h1 style={{ fontSize: "24px", fontWeight: "700", color: "#f8fafc", margin: "14px 0 6px 0", letterSpacing: "-0.01em" }}>
            {success ? "Account Verified" : "Verify Your Email"}
          </h1>
          <p style={{ fontSize: "14px", color: "#94a3b8", margin: 0, lineHeight: 1.5 }}>
            {success
              ? "Your account is activated and ready for interview preparation."
              : "Enter the 6-digit verification code sent to your inbox."}
          </p>
        </div>

        {/* Destination Email Display or Input */}
        {!success && (
          email ? (
            <div style={emailCardStyle}>
              <span style={{ fontSize: "12px", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: "600" }}>
                Sent to
              </span>
              <div id="verify-masked-email" style={{ fontSize: "15px", fontWeight: "600", color: "#e2e8f0", fontFamily: "monospace", marginTop: "2px" }}>
                {maskEmail(email)}
              </div>
            </div>
          ) : (
            <div style={{ marginBottom: "18px" }}>
              <label htmlFor="verify-email-input" style={{ display: "block", fontSize: "13px", fontWeight: "600", color: "#cbd5e1", marginBottom: "6px" }}>
                Account Email
              </label>
              <input
                id="verify-email-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@gmail.com"
                style={{
                  width: "100%",
                  padding: "11px 14px",
                  backgroundColor: "#0b0f19",
                  border: "1px solid #334155",
                  borderRadius: "10px",
                  color: "#f8fafc",
                  fontSize: "14px",
                  outline: "none",
                  boxSizing: "border-box",
                }}
              />
            </div>
          )
        )}

        {/* Success State */}
        {success ? (
          <div style={{ textAlign: "center", paddingTop: "8px" }}>
            <div style={successIconContainerStyle}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 6 9 17l-5-5" />
              </svg>
            </div>
            <p style={{ fontSize: "14px", color: "#cbd5e1", margin: "16px 0 24px 0" }}>
              Thank you for verifying your email address. You now have full access to your interview intelligence workspace.
            </p>
            <button
              id="continue-to-login-btn"
              type="button"
              onClick={() => navigate("/login", { state: { verifiedEmail: email } })}
              style={primaryButtonStyle}
            >
              Sign In to Your Account
            </button>
          </div>
        ) : (
          /* Verification Form */
          <form onSubmit={handleSubmit}>
            {/* Feedback Banners */}
            {resendSuccess && (
              <div style={successBannerStyle} role="status">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4ade80" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>{resendSuccess}</span>
              </div>
            )}

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

            {/* 6-Digit OTP Input Container */}
            <div style={{ margin: "24px 0 16px 0" }}>
              <label style={{ display: "block", fontSize: "13px", fontWeight: "600", color: "#cbd5e1", marginBottom: "10px", textAlign: "center" }}>
                6-Digit Verification Code
              </label>
              <div style={otpRowStyle} onPaste={handlePaste}>
                {otpDigits.map((digit, idx) => (
                  <input
                    key={idx}
                    ref={(el) => (inputRefs.current[idx] = el)}
                    id={`otp-digit-${idx}`}
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    maxLength={1}
                    value={digit}
                    autoComplete="one-time-code"
                    aria-label={`Digit ${idx + 1} of verification code`}
                    onChange={(e) => handleDigitChange(idx, e.target.value)}
                    onKeyDown={(e) => handleKeyDown(idx, e)}
                    style={{
                      ...otpInputStyle,
                      borderColor: digit ? "#3b82f6" : "#334155",
                      backgroundColor: digit ? "#0f172a" : "#0b0f19",
                    }}
                  />
                ))}
              </div>
            </div>

            {/* Expiry Notice & Attempts Info */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "12px", color: "#64748b", marginBottom: "24px", padding: "0 4px" }}>
              <span>Expires in 5 minutes</span>
              <span>Max 5 attempts</span>
            </div>

            {/* Action Button */}
            <button
              id="verify-otp-submit-btn"
              type="submit"
              disabled={!isCodeComplete || loading}
              style={{
                ...primaryButtonStyle,
                opacity: !isCodeComplete || loading ? 0.6 : 1,
                cursor: !isCodeComplete || loading ? "not-allowed" : "pointer",
              }}
            >
              {loading ? "Verifying Code..." : "Verify & Activate Account"}
            </button>

            {/* Resend OTP Section */}
            <div style={{ textAlign: "center", marginTop: "20px", paddingTop: "16px", borderTop: "1px solid #1e293b" }}>
              <p style={{ fontSize: "13px", color: "#64748b", margin: "0 0 10px 0" }}>
                Didn't receive the email?
              </p>
              <button
                id="verify-resend-btn"
                type="button"
                onClick={handleResend}
                disabled={resendCooldown > 0 || resending || !email}
                style={{
                  ...secondaryButtonStyle,
                  opacity: resendCooldown > 0 || resending || !email ? 0.5 : 1,
                  cursor: resendCooldown > 0 || resending || !email ? "not-allowed" : "pointer",
                }}
              >
                {resending ? "Sending..." : resendCooldown > 0 ? `Resend Code (${resendCooldown}s)` : "Resend Code"}
              </button>
            </div>
          </form>
        )}

        {/* Footer Navigation */}
        <div style={{ textAlign: "center", marginTop: "24px", paddingTop: "16px", borderTop: "1px solid #1e293b", display: "flex", justifyContent: "center", gap: "20px" }}>
          <Link to="/login" style={{ fontSize: "13px", color: "#60a5fa", textDecoration: "none", fontWeight: "500" }}>
            Return to Sign In
          </Link>
          <span style={{ color: "#334155" }}>•</span>
          <Link to="/register" style={{ fontSize: "13px", color: "#94a3b8", textDecoration: "none" }}>
            Create New Account
          </Link>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Styles: Polished SaaS Dark Navy Palette
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

const emailCardStyle = {
  backgroundColor: "#0b0f19",
  borderRadius: "10px",
  border: "1px solid #1e293b",
  padding: "12px 16px",
  marginBottom: "20px",
  textAlign: "center",
};

const otpRowStyle = {
  display: "flex",
  justifyContent: "center",
  gap: "10px",
};

const otpInputStyle = {
  width: "48px",
  height: "56px",
  borderRadius: "10px",
  border: "1px solid #334155",
  textAlign: "center",
  fontSize: "24px",
  fontWeight: "700",
  color: "#f8fafc",
  fontFamily: "ui-monospace, monospace",
  outline: "none",
  transition: "all 0.15s ease",
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

const secondaryButtonStyle = {
  padding: "8px 18px",
  backgroundColor: "#1e293b",
  color: "#cbd5e1",
  border: "1px solid #334155",
  borderRadius: "8px",
  fontSize: "13px",
  fontWeight: "500",
  cursor: "pointer",
  transition: "all 0.15s ease",
};

const successBannerStyle = {
  display: "flex",
  alignItems: "center",
  gap: "10px",
  backgroundColor: "rgba(34, 197, 94, 0.1)",
  border: "1px solid rgba(34, 197, 94, 0.3)",
  color: "#4ade80",
  padding: "12px 14px",
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
