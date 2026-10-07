import React, { useState, useRef, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { AccountModal } from "./AccountModal";

function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [accountModalTab, setAccountModalTab] = useState(null); // 'profile' | 'privacy' | 'data' | null

  const accountMenuRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (accountMenuRef.current && !accountMenuRef.current.contains(event.target)) {
        setAccountMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false);
    setAccountMenuOpen(false);
  }, [location.pathname]);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const navLinks = [
    { to: "/dashboard", label: "Dashboard" },
    { to: "/practice", label: "Practice" },
    { to: "/resume", label: "Resume" },
    { to: "/progress", label: "Progress" },
    { to: "/history", label: "History" },
  ];

  return (
    <>
      <nav
        style={{
          backgroundColor: "#0f172a",
          borderBottom: "1px solid #1e293b",
          position: "sticky",
          top: 0,
          zIndex: 40,
        }}
      >
        <div
          style={{
            maxWidth: "var(--container-max-w)",
            margin: "0 auto",
            padding: "0 16px",
            height: "64px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          {/* Brand Mark */}
          <Link
            to={user ? "/dashboard" : "/"}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              textDecoration: "none",
            }}
          >
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "8px",
                backgroundColor: "#2563eb",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#ffffff",
                fontWeight: "700",
                fontSize: "14px",
                letterSpacing: "-0.02em",
              }}
            >
              II
            </div>
            <div>
              <div
                style={{
                  color: "#f8fafc",
                  fontSize: "16px",
                  fontWeight: "700",
                  letterSpacing: "-0.015em",
                  lineHeight: 1.15,
                }}
              >
                Interview Intelligence
              </div>
              <div
                style={{
                  color: "#94a3b8",
                  fontSize: "11px",
                  letterSpacing: "0.02em",
                  textTransform: "uppercase",
                }}
              >
                Preparation System
              </div>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <div
            className="hide-on-mobile"
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            {user &&
              navLinks.map((link) => {
                const isActive =
                  location.pathname === link.to ||
                  (link.to === "/dashboard" && location.pathname.startsWith("/report"));
                return (
                  <Link
                    key={link.to}
                    to={link.to}
                    style={{
                      padding: "7px 12px",
                      borderRadius: "6px",
                      fontSize: "13px",
                      fontWeight: isActive ? "600" : "500",
                      color: isActive ? "#ffffff" : "#cbd5e1",
                      backgroundColor: isActive ? "rgba(255, 255, 255, 0.1)" : "transparent",
                      textDecoration: "none",
                      transition: "all 0.15s ease",
                    }}
                  >
                    {link.label}
                  </Link>
                );
              })}
          </div>

          {/* Desktop Auth / Account */}
          <div
            className="hide-on-mobile"
            style={{ display: "flex", alignItems: "center", gap: "12px" }}
          >
            {user ? (
              <div ref={accountMenuRef} style={{ position: "relative" }}>
                <button
                  type="button"
                  onClick={() => setAccountMenuOpen(!accountMenuOpen)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    background: "rgba(255, 255, 255, 0.06)",
                    border: "1px solid #334155",
                    borderRadius: "6px",
                    padding: "6px 12px",
                    cursor: "pointer",
                    color: "#f8fafc",
                    fontSize: "13px",
                    fontWeight: "500",
                  }}
                  aria-expanded={accountMenuOpen}
                >
                  <span
                    style={{
                      width: "22px",
                      height: "22px",
                      borderRadius: "50%",
                      backgroundColor: "#3b82f6",
                      color: "#ffffff",
                      fontSize: "11px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontWeight: "700",
                    }}
                  >
                    {(user.full_name || user.email || "U").slice(0, 1).toUpperCase()}
                  </span>
                  <span>{user.full_name || user.email.split("@")[0]}</span>
                  <span style={{ fontSize: "10px", color: "#94a3b8" }}>▾</span>
                </button>

                {accountMenuOpen && (
                  <div
                    style={{
                      position: "absolute",
                      right: 0,
                      top: "calc(100% + 6px)",
                      backgroundColor: "#ffffff",
                      border: "1px solid var(--border-default)",
                      borderRadius: "8px",
                      boxShadow: "var(--shadow-md)",
                      minWidth: "200px",
                      padding: "6px 0",
                      zIndex: 50,
                    }}
                  >
                    <div
                      style={{
                        padding: "8px 14px",
                        borderBottom: "1px solid var(--border-default)",
                        fontSize: "12px",
                      }}
                    >
                      <div style={{ fontWeight: "600", color: "var(--text-primary)" }}>
                        {user.full_name || "Account"}
                      </div>
                      <div style={{ color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {user.email}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => {
                        setAccountMenuOpen(false);
                        setAccountModalTab("profile");
                      }}
                      style={dropdownItemStyle}
                    >
                      Profile & Target Role
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setAccountMenuOpen(false);
                        setAccountModalTab("privacy");
                      }}
                      style={dropdownItemStyle}
                    >
                      Privacy & Sensors
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setAccountMenuOpen(false);
                        setAccountModalTab("data");
                      }}
                      style={dropdownItemStyle}
                    >
                      Export or Delete Data
                    </button>

                    <div style={{ borderTop: "1px solid var(--border-default)", margin: "4px 0" }} />

                    <button
                      type="button"
                      onClick={handleLogout}
                      style={{
                        ...dropdownItemStyle,
                        color: "var(--danger-text)",
                      }}
                    >
                      Sign Out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Link
                  to="/login"
                  style={{
                    color: "#cbd5e1",
                    fontSize: "13px",
                    fontWeight: "500",
                    textDecoration: "none",
                    padding: "6px 12px",
                  }}
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  style={{
                    backgroundColor: "#2563eb",
                    color: "#ffffff",
                    fontSize: "13px",
                    fontWeight: "600",
                    padding: "7px 14px",
                    borderRadius: "6px",
                    textDecoration: "none",
                  }}
                >
                  Get Started
                </Link>
              </div>
            )}
          </div>

          {/* Mobile Hamburger Toggle */}
          <button
            type="button"
            className="hide-on-desktop"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle navigation menu"
            style={{
              background: "none",
              border: "none",
              color: "#ffffff",
              fontSize: "22px",
              cursor: "pointer",
              padding: "6px",
            }}
          >
            {mobileMenuOpen ? "✕" : "☰"}
          </button>
        </div>

        {/* Mobile Nav Drawer */}
        {mobileMenuOpen && (
          <div
            className="hide-on-desktop"
            style={{
              backgroundColor: "#0f172a",
              borderTop: "1px solid #1e293b",
              padding: "16px",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
            }}
          >
            {user ? (
              <>
                <div style={{ padding: "6px 10px", fontSize: "12px", color: "#94a3b8", borderBottom: "1px solid #1e293b" }}>
                  Signed in as <strong style={{ color: "#ffffff" }}>{user.email}</strong>
                </div>
                {navLinks.map((link) => (
                  <Link
                    key={link.to}
                    to={link.to}
                    style={{
                      padding: "10px 12px",
                      borderRadius: "6px",
                      fontSize: "14px",
                      fontWeight: location.pathname === link.to ? "600" : "500",
                      color: location.pathname === link.to ? "#ffffff" : "#cbd5e1",
                      backgroundColor: location.pathname === link.to ? "rgba(255, 255, 255, 0.1)" : "transparent",
                      textDecoration: "none",
                    }}
                  >
                    {link.label}
                  </Link>
                ))}
                <div style={{ borderTop: "1px solid #1e293b", margin: "6px 0" }} />
                <button
                  type="button"
                  onClick={() => setAccountModalTab("profile")}
                  style={{ ...mobileBtnStyle, color: "#cbd5e1" }}
                >
                  Profile & Settings
                </button>
                <button
                  type="button"
                  onClick={() => setAccountModalTab("privacy")}
                  style={{ ...mobileBtnStyle, color: "#cbd5e1" }}
                >
                  Privacy & Data Control
                </button>
                <button
                  type="button"
                  onClick={handleLogout}
                  style={{ ...mobileBtnStyle, color: "#fca5a5" }}
                >
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  style={{
                    padding: "10px 12px",
                    color: "#cbd5e1",
                    fontSize: "14px",
                    textDecoration: "none",
                  }}
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  style={{
                    padding: "10px 12px",
                    backgroundColor: "#2563eb",
                    color: "#ffffff",
                    borderRadius: "6px",
                    fontSize: "14px",
                    fontWeight: "600",
                    textAlign: "center",
                    textDecoration: "none",
                  }}
                >
                  Get Started
                </Link>
              </>
            )}
          </div>
        )}
      </nav>

      {/* Account Modal */}
      <AccountModal
        isOpen={Boolean(accountModalTab)}
        initialTab={accountModalTab || "profile"}
        onClose={() => setAccountModalTab(null)}
      />
    </>
  );
}

const dropdownItemStyle = {
  width: "100%",
  textAlign: "left",
  padding: "8px 14px",
  background: "none",
  border: "none",
  fontSize: "13px",
  color: "var(--text-secondary)",
  cursor: "pointer",
  transition: "background 0.15s ease",
  display: "block",
};

const mobileBtnStyle = {
  width: "100%",
  textAlign: "left",
  padding: "10px 12px",
  background: "none",
  border: "none",
  fontSize: "14px",
  cursor: "pointer",
};

export default Navbar;