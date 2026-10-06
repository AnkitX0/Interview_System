import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const authenticatedLinks = [
    { to: "/resume", label: "Resume Analysis" },
    { to: "/setup", label: "Mock Interview" },
    { to: "/dashboard", label: "Report" },
    { to: "/fix-answer", label: "Fix My Answer" },
    { to: "/progress", label: "Progress" },
  ];

  return (
    <nav style={navStyle}>
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <div style={logoBadge}>AI</div>
        <div>
          <Link to="/" style={{ textDecoration: "none" }}>
            <h2 style={{ margin: 0, fontSize: "18px", fontWeight: "700", color: "#f8fafc", letterSpacing: "-0.02em" }}>
              Interview Intelligence
            </h2>
          </Link>
          <span style={{ fontSize: "11px", color: "#94a3b8" }}>Enterprise Mock Assessment</span>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <Link
          to="/"
          style={{
            ...linkStyle,
            backgroundColor: location.pathname === "/" ? "rgba(255, 255, 255, 0.12)" : "transparent",
            color: location.pathname === "/" ? "#ffffff" : "#cbd5e1",
            fontWeight: location.pathname === "/" ? "600" : "500",
          }}
        >
          Home
        </Link>

        {user && authenticatedLinks.map((link) => {
          const isActive = location.pathname === link.to;
          return (
            <Link
              key={link.to}
              to={link.to}
              style={{
                ...linkStyle,
                backgroundColor: isActive ? "rgba(255, 255, 255, 0.12)" : "transparent",
                color: isActive ? "#ffffff" : "#cbd5e1",
                fontWeight: isActive ? "600" : "500",
              }}
            >
              {link.label}
            </Link>
          );
        })}

        {user ? (
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginLeft: "12px", borderLeft: "1px solid #334155", paddingLeft: "14px" }}>
            <span style={{ fontSize: "12px", color: "#94a3b8" }}>
              {user.full_name || user.email}
            </span>
            <button
              onClick={handleLogout}
              style={{
                padding: "6px 12px",
                backgroundColor: "rgba(239, 68, 68, 0.15)",
                color: "#fca5a5",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                borderRadius: "6px",
                fontSize: "12px",
                fontWeight: "600",
                cursor: "pointer",
              }}
            >
              Sign Out
            </button>
          </div>
        ) : (
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginLeft: "8px" }}>
            <Link
              to="/login"
              style={{
                ...linkStyle,
                color: "#cbd5e1",
              }}
            >
              Sign In
            </Link>
            <Link
              to="/register"
              style={{
                padding: "7px 14px",
                backgroundColor: "#2563eb",
                color: "#ffffff",
                borderRadius: "6px",
                textDecoration: "none",
                fontSize: "13px",
                fontWeight: "600",
              }}
            >
              Create Account
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
}

const navStyle = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "14px 40px",
  backgroundColor: "#0f172a",
  color: "white",
  borderBottom: "1px solid #1e293b",
  boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
  position: "sticky",
  top: 0,
  zIndex: 50,
};

const logoBadge = {
  backgroundColor: "#3b82f6",
  color: "white",
  fontWeight: "800",
  fontSize: "14px",
  padding: "4px 8px",
  borderRadius: "6px",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

const linkStyle = {
  padding: "8px 14px",
  borderRadius: "6px",
  textDecoration: "none",
  fontSize: "13px",
  transition: "all 0.15s ease",
};

export default Navbar;