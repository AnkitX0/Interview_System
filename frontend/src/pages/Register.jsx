import { useState, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const { user, loading: authLoading, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || "/dashboard";

  useEffect(() => {
    if (!authLoading && user) {
      navigate(from, { replace: true });
    }
  }, [user, authLoading, navigate, from]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (password.length < 10) {
      setError("Password must be at least 10 characters long.");
      return;
    }

    setSubmitting(true);

    try {
      await register(email, password, fullName);
      navigate(from, { replace: true });
    } catch (err) {
      if (err.message?.includes("Email is already registered")) {
        setError("An account with this email already exists.");
      } else {
        setError(err.message || "Registration failed");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <h2 style={{ fontSize: "22px", fontWeight: "700", color: "#0f172a", margin: "0 0 6px 0" }}>
            Create your account
          </h2>
          <p style={{ fontSize: "14px", color: "#64748b", margin: 0 }}>
            Start structured, verifiable interview preparation
          </p>
        </div>

        {error && (
          <div style={errorBannerStyle}>
            <span style={{ fontSize: "13px", fontWeight: "500" }}>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "16px" }}>
            <label style={labelStyle}>Full Name (Optional)</label>
            <input
              type="text"
              autoFocus
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Alex Smith"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: "16px" }}>
            <label style={labelStyle}>Email Address</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: "24px" }}>
            <label style={labelStyle}>Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 10 characters"
              style={inputStyle}
            />
            <span style={{ display: "block", fontSize: "12px", color: "#64748b", marginTop: "5px" }}>
              Must be at least 10 characters. Avoid easily guessable phrases.
            </span>
          </div>

          <button
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

        <div style={{ textAlign: "center", marginTop: "24px", paddingTop: "18px", borderTop: "1px solid #f1f5f9" }}>
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
