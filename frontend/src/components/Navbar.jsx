import React, { useState, useRef, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { AccountModal } from "./AccountModal";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
import { isInterviewCurrentlyActive, clearInterviewActiveState } from "../utils/interviewLifecycle";

function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [accountModalTab, setAccountModalTab] = useState(null); // 'profile' | 'privacy' | 'data' | null

  // Guarded in-app navigation confirmation modal state
  const [navInterceptModal, setNavInterceptModal] = useState({
    open: false,
    isLogout: false,
    targetPath: null,
  });

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

  const handleGuardedNavigation = (e, targetPath, isLogout = false) => {
    const isActive = isInterviewCurrentlyActive() || (
      location.pathname === "/interview" &&
      sessionStorage.getItem("interviewActive") === "true"
    );
    if (isActive) {
      if (e && e.preventDefault) e.preventDefault();
      setNavInterceptModal({
        open: true,
        isLogout,
        targetPath,
      });
      return false;
    }
    return true;
  };

  const confirmNavIntercept = async () => {
    const { isLogout, targetPath } = navInterceptModal;
    setNavInterceptModal({ open: false, isLogout: false, targetPath: null });

    // Finalize or cleanup active interview session
    const activeSessionId = sessionStorage.getItem("currentSessionId");
    if (activeSessionId) {
      try {
        await fetch(`/interview/${activeSessionId}/complete`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ duration_seconds: 0 }),
        });
      } catch (err) {
        console.warn("Session complete notice:", err);
      }
    }

    clearInterviewActiveState();
    sessionStorage.removeItem("interviewActive");

    if (isLogout) {
      await logout();
      navigate("/login");
    } else if (targetPath) {
      navigate(targetPath);
    }
  };

  const handleLogout = async (e) => {
    if (!handleGuardedNavigation(e, "/login", true)) return;
    await logout();
    navigate("/login");
  };

  const navLinks = [
    { to: "/dashboard", label: "Dashboard" },
    { to: "/practice", label: "Practice" },
    { to: "/resume", label: "Resume" },
    { to: "/progress", label: "Progress" },
    { to: "/history", label: "History" },
    { to: "/profile", label: "Profile" },
  ];

  return (
    <>
      <nav
        style={{
          backgroundColor: "var(--bg-nav)",
          borderBottom: "1px solid var(--border-default)",
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
            onClick={(e) => handleGuardedNavigation(e, user ? "/dashboard" : "/")}
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
                    onClick={(e) => handleGuardedNavigation(e, link.to)}
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

          {/* Desktop Auth / Account & Theme */}
          <div
            className="hide-on-mobile"
            style={{ display: "flex", alignItems: "center", gap: "10px" }}
          >
            {/* Theme Toggle Button */}
            <button
              type="button"
              onClick={toggleTheme}
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: "32px",
                height: "32px",
                borderRadius: "6px",
                background: "rgba(255, 255, 255, 0.08)",
                border: "1px solid #334155",
                color: "#f8fafc",
                cursor: "pointer",
                fontSize: "14px",
                transition: "all var(--transition-fast)",
              }}
            >
              {theme === "dark" ? "☀" : "◐"}
            </button>

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
                      onClick={(e) => {
                        setAccountMenuOpen(false);
                        if (handleGuardedNavigation(e, "/profile")) {
                          navigate("/profile");
                        }
                      }}
                      style={dropdownItemStyle}
                    >
                      Candidate Profile & Biodata
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setAccountMenuOpen(false);
                        setAccountModalTab("profile");
                      }}
                      style={dropdownItemStyle}
                    >
                      Quick Settings & Preferences
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
                    onClick={(e) => {
                      setMobileMenuOpen(false);
                      handleGuardedNavigation(e, link.to);
                    }}
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
                  onClick={toggleTheme}
                  style={{ ...mobileBtnStyle, color: "#93c5fd" }}
                >
                  {theme === "dark" ? "☀ Switch to Light Mode" : "◐ Switch to Dark Mode"}
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

      {/* Active Interview Guard Navigation Intercept Modal */}
      {navInterceptModal.open && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(15, 23, 42, 0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1200,
            padding: "16px",
          }}
        >
          <Card style={{ maxWidth: "440px", width: "100%", padding: "24px", boxShadow: "var(--shadow-xl)" }}>
            <h3 style={{ fontSize: "18px", fontWeight: "700", color: "var(--text-primary)", marginBottom: "8px" }}>
              Your interview is still in progress.
            </h3>
            <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "20px", lineHeight: "1.5" }}>
              {navInterceptModal.isLogout
                ? "Leaving now will end this interview."
                : "Leave the interview and end this session?"}
            </p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <Button
                variant="secondary"
                onClick={() => setNavInterceptModal({ open: false, isLogout: false, targetPath: null })}
              >
                Stay
              </Button>
              <Button
                variant="primary"
                onClick={confirmNavIntercept}
              >
                {navInterceptModal.isLogout ? "End Interview & Log Out" : "End Interview"}
              </Button>
            </div>
          </Card>
        </div>
      )}

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