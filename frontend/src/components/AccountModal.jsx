import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../utils/api";
import { Button } from "./ui/Button";

export function AccountModal({ isOpen, onClose, initialTab = "profile" }) {
  const navigate = useNavigate();
  const { user, updateProfile, logout } = useAuth();
  const [activeTab, setActiveTab] = useState(initialTab);
  const [profileForm, setProfileForm] = useState({
    target_role: "",
    years_experience: 0,
    preferred_difficulty: "medium",
  });
  const [statusMessage, setStatusMessage] = useState({ type: "", text: "" });
  const [isSaving, setIsSaving] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  // Account deletion state
  const [deletePassword, setDeletePassword] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    if (user?.profile) {
      setProfileForm({
        target_role: user.profile.target_role || "Software Engineer",
        years_experience: user.profile.years_experience || 0,
        preferred_difficulty: user.profile.preferred_difficulty || "medium",
      });
    }
    setActiveTab(initialTab);
  }, [user, initialTab, isOpen]);

  if (!isOpen) return null;

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    setStatusMessage({ type: "", text: "" });
    try {
      await updateProfile(profileForm);
      setStatusMessage({ type: "success", text: "Profile updated successfully." });
    } catch (err) {
      setStatusMessage({ type: "danger", text: err.message || "Failed to update profile." });
    } finally {
      setIsSaving(false);
    }
  };

  const handleExportData = async () => {
    setIsExporting(true);
    setStatusMessage({ type: "", text: "" });
    try {
      const res = await apiFetch("/auth/export");
      if (!res.ok) throw new Error("Export failed");
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `interview-data-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setStatusMessage({ type: "success", text: "Data export downloaded." });
    } catch (err) {
      setStatusMessage({ type: "danger", text: "Failed to export data: " + err.message });
    } finally {
      setIsExporting(false);
    }
  };

  const handleDeleteAccount = async (e) => {
    e.preventDefault();
    if (!deletePassword) {
      setStatusMessage({ type: "danger", text: "Please enter your password to confirm deletion." });
      return;
    }
    setIsDeleting(true);
    try {
      const res = await apiFetch("/auth/account", {
        method: "DELETE",
        body: JSON.stringify({ password: deletePassword }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error?.message || "Failed to delete account");
      }
      await logout();
      onClose();
      window.location.href = "/";
    } catch (err) {
      setStatusMessage({ type: "danger", text: err.message });
      setIsDeleting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(15, 23, 42, 0.6)",
        backdropFilter: "blur(2px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
        padding: "16px",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          backgroundColor: "#ffffff",
          borderRadius: "var(--radius-lg)",
          width: "100%",
          maxWidth: "560px",
          boxShadow: "var(--shadow-lg)",
          overflow: "hidden",
          border: "1px solid var(--border-default)",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "18px 24px",
            borderBottom: "1px solid var(--border-default)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            backgroundColor: "var(--slate-50)",
          }}
        >
          <div>
            <h3 style={{ fontSize: "16px", fontWeight: "600", margin: 0, color: "var(--text-primary)" }}>
              Account & Privacy Settings
            </h3>
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              {user?.email}
            </span>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            style={{
              background: "none",
              border: "none",
              fontSize: "20px",
              cursor: "pointer",
              color: "var(--text-muted)",
              padding: "4px 8px",
            }}
          >
            ×
          </button>
        </div>

        {/* Tab Navigation */}
        <div
          style={{
            display: "flex",
            borderBottom: "1px solid var(--border-default)",
            backgroundColor: "#ffffff",
          }}
        >
          <button
            type="button"
            onClick={() => setActiveTab("profile")}
            style={{
              flex: 1,
              padding: "12px",
              background: "none",
              border: "none",
              borderBottom: activeTab === "profile" ? "2px solid var(--slate-900)" : "2px solid transparent",
              fontWeight: activeTab === "profile" ? "600" : "500",
              color: activeTab === "profile" ? "var(--text-primary)" : "var(--text-secondary)",
              fontSize: "13px",
              cursor: "pointer",
            }}
          >
            Profile
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("privacy")}
            style={{
              flex: 1,
              padding: "12px",
              background: "none",
              border: "none",
              borderBottom: activeTab === "privacy" ? "2px solid var(--slate-900)" : "2px solid transparent",
              fontWeight: activeTab === "privacy" ? "600" : "500",
              color: activeTab === "privacy" ? "var(--text-primary)" : "var(--text-secondary)",
              fontSize: "13px",
              cursor: "pointer",
            }}
          >
            Privacy & Trust
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("data")}
            style={{
              flex: 1,
              padding: "12px",
              background: "none",
              border: "none",
              borderBottom: activeTab === "data" ? "2px solid var(--slate-900)" : "2px solid transparent",
              fontWeight: activeTab === "data" ? "600" : "500",
              color: activeTab === "data" ? "var(--text-primary)" : "var(--text-secondary)",
              fontSize: "13px",
              cursor: "pointer",
            }}
          >
            Data Control
          </button>
        </div>

        {/* Body Content */}
        <div style={{ padding: "24px", maxHeight: "65vh", overflowY: "auto" }}>
          {statusMessage.text && (
            <div
              className={`alert alert-${statusMessage.type}`}
              style={{ marginBottom: "16px", padding: "10px 14px", fontSize: "13px" }}
            >
              {statusMessage.text}
            </div>
          )}

          {activeTab === "profile" && (
            <div>
              <div
                style={{
                  marginBottom: "16px",
                  padding: "10px 14px",
                  backgroundColor: "var(--primary-50)",
                  border: "1px solid var(--primary-200)",
                  borderRadius: "6px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span style={{ fontSize: "12px", color: "var(--primary-900)" }}>
                  Manage verified biodata, education & developer links
                </span>
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    navigate("/profile");
                  }}
                  style={{
                    fontSize: "12px",
                    fontWeight: "700",
                    color: "var(--primary-700)",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                  }}
                >
                  Open Full Profile →
                </button>
              </div>

              <form onSubmit={handleProfileSubmit}>
              <div className="form-group">
                <label className="form-label">Full Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={user?.full_name || ""}
                  disabled
                  style={{ backgroundColor: "var(--slate-100)", color: "var(--text-secondary)" }}
                />
                <span className="form-hint">Registered name on file.</span>
              </div>

              <div className="form-group">
                <label className="form-label">Target Role</label>
                <input
                  type="text"
                  className="form-input"
                  value={profileForm.target_role}
                  onChange={(e) => setProfileForm({ ...profileForm, target_role: e.target.value })}
                  placeholder="e.g. Backend Engineer, Frontend Developer"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Preferred Difficulty</label>
                <select
                  className="form-select"
                  value={profileForm.preferred_difficulty}
                  onChange={(e) => setProfileForm({ ...profileForm, preferred_difficulty: e.target.value })}
                >
                  <option value="easy">Introductory</option>
                  <option value="medium">Standard (Mid-Level)</option>
                  <option value="hard">Advanced (Senior / Principal)</option>
                </select>
              </div>

              <div style={{ marginTop: "24px", display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <Button variant="secondary" onClick={onClose}>Close</Button>
                <Button type="submit" variant="primary" loading={isSaving}>Save Changes</Button>
              </div>
            </form>
          </div>
          )}

          {activeTab === "privacy" && (
            <div style={{ fontSize: "13px", lineHeight: "1.6", color: "var(--text-secondary)" }}>
              <h4 style={{ fontSize: "14px", color: "var(--text-primary)", marginBottom: "8px" }}>
                Data Privacy & Sensor Policies
              </h4>
              <p style={{ marginBottom: "12px" }}>
                This platform is designed to give you realistic interview practice while respecting your privacy:
              </p>
              <ul style={{ paddingLeft: "20px", marginBottom: "16px", display: "flex", flexDirection: "column", gap: "8px" }}>
                <li>
                  <strong style={{ color: "var(--text-primary)" }}>Local Video Analysis:</strong> Webcam frames are analyzed locally in your browser for camera positioning and head alignment. Video frames are never recorded, uploaded, or transmitted to any server.
                </li>
                <li>
                  <strong style={{ color: "var(--text-primary)" }}>Speech Recognition:</strong> Speech transcription uses your browser’s native speech engine. Only the final transcribed text and cadence intervals are sent to the server for evaluation.
                </li>
                <li>
                  <strong style={{ color: "var(--text-primary)" }}>Text-Only Alternative:</strong> You can practice entirely in Text-Only mode with cameras and microphones completely disabled.
                </li>
                <li>
                  <strong style={{ color: "var(--text-primary)" }}>Data Retention:</strong> Your interview responses, scores, and recommendations are kept strictly until you delete them.
                </li>
              </ul>
              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <Button variant="secondary" onClick={onClose}>Done</Button>
              </div>
            </div>
          )}

          {activeTab === "data" && (
            <div>
              <div style={{ marginBottom: "24px", paddingBottom: "20px", borderBottom: "1px solid var(--border-default)" }}>
                <h4 style={{ fontSize: "14px", color: "var(--text-primary)", marginBottom: "4px" }}>
                  Export Your Data
                </h4>
                <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "12px" }}>
                  Download a complete JSON export of all your interview sessions, questions, scores, and practice history.
                </p>
                <Button variant="secondary" onClick={handleExportData} loading={isExporting}>
                  Export Data (JSON)
                </Button>
              </div>

              <div>
                <h4 style={{ fontSize: "14px", color: "var(--danger-text)", marginBottom: "4px" }}>
                  Delete Account
                </h4>
                <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "12px" }}>
                  Permanently delete your account, past interviews, resume uploads, and readiness scores. This action cannot be undone.
                </p>

                {!showDeleteConfirm ? (
                  <Button variant="danger" size="sm" onClick={() => setShowDeleteConfirm(true)}>
                    Delete Account...
                  </Button>
                ) : (
                  <div style={{ backgroundColor: "var(--danger-bg)", padding: "14px", borderRadius: "var(--radius-md)", border: "1px solid var(--danger-border)" }}>
                    <p style={{ fontSize: "12px", color: "var(--danger-text)", fontWeight: "600", marginBottom: "8px" }}>
                      Enter your password to permanently delete all your data:
                    </p>
                    <input
                      type="password"
                      className="form-input"
                      placeholder="Your current password"
                      value={deletePassword}
                      onChange={(e) => setDeletePassword(e.target.value)}
                      style={{ marginBottom: "10px" }}
                    />
                    <div style={{ display: "flex", gap: "8px" }}>
                      <Button variant="danger" size="sm" onClick={handleDeleteAccount} loading={isDeleting}>
                        Confirm Permanent Deletion
                      </Button>
                      <Button variant="subtle" size="sm" onClick={() => setShowDeleteConfirm(false)}>
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

