import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../utils/api";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import {
  calculateProfileCompleteness,
  isValidUrl,
} from "../utils/profileCompletenessLogic";

const DEVELOPER_PLATFORMS = [
  { key: "linkedin", label: "LinkedIn", placeholder: "https://linkedin.com/in/username", icon: "💼" },
  { key: "github", label: "GitHub", placeholder: "https://github.com/username", icon: "🐙" },
  { key: "leetcode", label: "LeetCode", placeholder: "https://leetcode.com/u/username", icon: "⚡" },
  { key: "codeforces", label: "Codeforces", placeholder: "https://codeforces.com/profile/username", icon: "🏆" },
  { key: "hackerrank", label: "HackerRank", placeholder: "https://hackerrank.com/profile/username", icon: "💻" },
  { key: "kaggle", label: "Kaggle", placeholder: "https://kaggle.com/username", icon: "📊" },
  { key: "portfolio", label: "Portfolio", placeholder: "https://yourportfolio.dev", icon: "🌐" },
  { key: "website", label: "Personal Website", placeholder: "https://yourblog.com", icon: "🔗" },
];

export default function Profile() {
  const navigate = useNavigate();
  const { user, updateProfile } = useAuth();

  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState({ type: "", text: "" });
  const [activeSection, setActiveSection] = useState("all"); // 'all' | 'personal' | 'professional' | 'education' | 'skills' | 'links'

  // Resume sync suggestions
  const [resumeData, setResumeData] = useState(null);
  const [showResumeSuggestion, setShowResumeSuggestion] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    full_name: "",
    phone: "",
    location: "",
    bio: "",
    target_role: "Software Engineer",
    experience_level: "Mid-level",
    target_companies: [],
    interview_goal: "",
    weekly_practice_goal: 5,
    university: "",
    degree: "",
    graduation_year: new Date().getFullYear(),
    skills_categorized: {
      languages: [],
      frameworks: [],
      databases: [],
      tools: [],
    },
    professional_links: {},
  });

  // Backup state for cancel
  const [initialData, setInitialData] = useState(null);

  // Load profile on mount
  useEffect(() => {
    async function loadData() {
      try {
        const res = await apiFetch("/auth/profile");
        if (res.ok) {
          const data = await res.json();
          const p = data.profile || {};
          const populated = {
            full_name: p.full_name || user?.full_name || "",
            phone: p.phone || "",
            location: p.location || "",
            bio: p.bio || "",
            target_role: p.target_role || "Software Engineer",
            experience_level: p.experience_level || "Mid-level",
            target_companies: Array.isArray(p.target_companies) ? p.target_companies : [],
            interview_goal: p.interview_goal || "",
            weekly_practice_goal: p.weekly_practice_goal || 5,
            university: p.university || "",
            degree: p.degree || "",
            graduation_year: p.graduation_year || new Date().getFullYear(),
            skills_categorized: p.skills_categorized || {
              languages: ["Python", "JavaScript"],
              frameworks: ["FastAPI", "React"],
              databases: ["PostgreSQL"],
              tools: ["Git", "Docker"],
            },
            professional_links: p.professional_links || {},
          };
          setFormData(populated);
          setInitialData(populated);
        }
      } catch (err) {
        console.warn("Failed to load user profile:", err);
      }

      // Check if resume exists to provide sync suggestions
      try {
        const resRes = await apiFetch("/resume/latest");
        if (resRes.ok) {
          const rData = await resRes.json();
          if (rData && (rData.skills?.length > 0 || rData.target_role)) {
            setResumeData(rData);
            setShowResumeSuggestion(true);
          }
        }
      } catch {}
    }

    loadData();
  }, [user]);

  // Handle Save
  const handleSave = async (e) => {
    if (e) e.preventDefault();
    setIsSaving(true);
    setStatusMessage({ type: "", text: "" });

    try {
      const res = await apiFetch("/auth/profile", {
        method: "PUT",
        body: JSON.stringify(formData),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData?.error?.message || "Failed to update profile.");
      }

      const updated = await res.json();
      setInitialData(formData);
      setIsEditing(false);
      setStatusMessage({ type: "success", text: "Profile updated and persisted successfully." });
    } catch (err) {
      setStatusMessage({ type: "danger", text: err.message || "Failed to save profile." });
    } finally {
      setIsSaving(false);
    }
  };

  // Handle Cancel
  const handleCancel = () => {
    if (initialData) {
      setFormData(initialData);
    }
    setIsEditing(false);
    setStatusMessage({ type: "", text: "" });
  };

  // Sync details from uploaded resume (Part 32)
  const handleApplyResumeDetails = () => {
    if (!resumeData) return;

    setFormData((prev) => {
      const skillsArray = Array.isArray(resumeData.skills) ? resumeData.skills : [];
      const updatedSkills = { ...prev.skills_categorized };

      // Distribute resume skills intelligently if not already present
      skillsArray.forEach((sk) => {
        const lower = sk.toLowerCase();
        if (["python", "java", "c++", "c", "go", "rust", "javascript", "typescript", "ruby"].some((l) => lower.includes(l))) {
          if (!updatedSkills.languages.includes(sk)) updatedSkills.languages.push(sk);
        } else if (["react", "fastapi", "django", "express", "spring", "vue", "next"].some((f) => lower.includes(f))) {
          if (!updatedSkills.frameworks.includes(sk)) updatedSkills.frameworks.push(sk);
        } else if (["sql", "postgres", "mysql", "mongodb", "redis", "dynamodb"].some((d) => lower.includes(d))) {
          if (!updatedSkills.databases.includes(sk)) updatedSkills.databases.push(sk);
        } else {
          if (!updatedSkills.tools.includes(sk)) updatedSkills.tools.push(sk);
        }
      });

      return {
        ...prev,
        target_role: resumeData.target_role || prev.target_role,
        skills_categorized: updatedSkills,
        university: resumeData.education?.[0]?.institution || prev.university,
        degree: resumeData.education?.[0]?.degree || prev.degree,
      };
    });

    setShowResumeSuggestion(false);
    setIsEditing(true);
    setStatusMessage({
      type: "info",
      text: "Extracted resume information populated. Review and click 'Save Changes' to confirm.",
    });
  };

  // Helper for skill addition
  const handleAddSkill = (category, skillName) => {
    if (!skillName || !skillName.trim()) return;
    const clean = skillName.trim();
    setFormData((prev) => {
      const currentList = prev.skills_categorized[category] || [];
      if (currentList.includes(clean)) return prev;
      return {
        ...prev,
        skills_categorized: {
          ...prev.skills_categorized,
          [category]: [...currentList, clean],
        },
      };
    });
  };

  // Helper for skill removal
  const handleRemoveSkill = (category, skillToRemove) => {
    setFormData((prev) => ({
      ...prev,
      skills_categorized: {
        ...prev.skills_categorized,
        [category]: (prev.skills_categorized[category] || []).filter((s) => s !== skillToRemove),
      },
    }));
  };

  // Helper for links update
  const handleLinkChange = (key, val) => {
    setFormData((prev) => ({
      ...prev,
      professional_links: {
        ...prev.professional_links,
        [key]: val,
      },
    }));
  };

  const completeness = calculateProfileCompleteness(formData, { full_name: formData.full_name });

  return (
    <div className="container" style={{ maxWidth: "var(--container-max-w)", padding: "16px 16px 80px 16px" }}>
      {/* Header with Title & Completeness Meter */}
      <div style={{ marginBottom: "28px", display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "flex-end", gap: "16px" }}>
        <div>
          <span style={{ fontSize: "12px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--primary-600)" }}>
            Candidate Profile & Biodata
          </span>
          <h1 style={{ fontSize: "30px", fontWeight: "800", color: "var(--text-primary)", letterSpacing: "-0.02em", marginTop: "2px" }}>
            Professional Profile
          </h1>
          <p style={{ color: "var(--text-secondary)", marginTop: "4px", fontSize: "14px" }}>
            Manage verified biographical data, academic background, technical proficiencies, and developer profile links.
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          {!isEditing ? (
            <Button variant="primary" onClick={() => setIsEditing(true)}>
              ✏️ Edit Profile
            </Button>
          ) : (
            <>
              <Button variant="secondary" onClick={handleCancel} disabled={isSaving}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSave} loading={isSaving}>
                Save Changes
              </Button>
            </>
          )}
        </div>
      </div>

      {statusMessage.text && (
        <div
          className={`alert alert-${statusMessage.type === "danger" ? "warning" : "success"}`}
          style={{ marginBottom: "20px" }}
        >
          {statusMessage.text}
        </div>
      )}

      {/* Suggestion from Parsed Resume Banner (Part 32) */}
      {showResumeSuggestion && (
        <Card
          style={{
            marginBottom: "24px",
            backgroundColor: "var(--primary-50)",
            border: "1px solid var(--primary-200)",
            padding: "16px 20px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
            <div>
              <div style={{ fontWeight: "700", fontSize: "14px", color: "var(--primary-900)" }}>
                📄 Information detected in your uploaded resume
              </div>
              <p style={{ fontSize: "13px", color: "var(--primary-800)", marginTop: "2px" }}>
                We extracted verified skills ({resumeData?.skills?.length || 0} technologies) and role details ({resumeData?.target_role || "Engineering"}).
              </p>
            </div>
            <div style={{ display: "flex", gap: "10px" }}>
              <Button size="sm" variant="secondary" onClick={() => setShowResumeSuggestion(false)}>
                Dismiss
              </Button>
              <Button size="sm" variant="primary" onClick={handleApplyResumeDetails}>
                Use Extracted Details
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Profile Overview Card & Completeness Gauge */}
      <Card style={{ padding: "24px", marginBottom: "24px" }}>
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "18px" }}>
            <div
              style={{
                width: "68px",
                height: "68px",
                borderRadius: "50%",
                backgroundColor: "var(--primary-600)",
                color: "#ffffff",
                fontSize: "26px",
                fontWeight: "700",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: "var(--font-family-serif)",
              }}
            >
              {(formData.full_name || user?.email || "U").slice(0, 1).toUpperCase()}
            </div>
            <div>
              <div style={{ fontSize: "20px", fontWeight: "700", color: "var(--text-primary)" }}>
                {formData.full_name || "Candidate Name"}
              </div>
              <div style={{ fontSize: "14px", color: "var(--text-secondary)", marginTop: "2px" }}>
                {formData.target_role} · {formData.experience_level}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                {user?.email} {formData.location && `· ${formData.location}`}
              </div>
            </div>
          </div>

          {/* Deterministic Completeness Meter (Part 30) */}
          <div style={{ minWidth: "220px", textAlign: "right" }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", fontWeight: "700", marginBottom: "6px" }}>
              <span style={{ color: "var(--text-secondary)" }}>Profile Completeness</span>
              <span style={{ color: completeness >= 80 ? "var(--success-text)" : "var(--primary-600)" }}>
                {completeness}%
              </span>
            </div>
            <div style={{ width: "100%", height: "8px", backgroundColor: "var(--bg-muted)", borderRadius: "4px", overflow: "hidden" }}>
              <div
                style={{
                  width: `${completeness}%`,
                  height: "100%",
                  backgroundColor: completeness >= 80 ? "var(--success-text)" : "var(--primary-600)",
                  transition: "width 0.4s ease",
                }}
              />
            </div>
            <span style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px", display: "inline-block" }}>
              {completeness === 100 ? "Complete profile" : "Add links and education to reach 100%"}
            </span>
          </div>
        </div>
      </Card>

      {/* Section Navigation Tabs */}
      <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid var(--border-default)", marginBottom: "24px", overflowX: "auto" }}>
        {[
          { key: "all", label: "Overview" },
          { key: "personal", label: "Personal" },
          { key: "professional", label: "Professional" },
          { key: "education", label: "Education" },
          { key: "skills", label: "Technical Skills" },
          { key: "links", label: "Developer Profiles" },
        ].map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveSection(tab.key)}
            style={{
              padding: "10px 16px",
              background: "none",
              border: "none",
              borderBottom: activeSection === tab.key ? "2px solid var(--primary-600)" : "2px solid transparent",
              fontWeight: activeSection === tab.key ? "700" : "500",
              color: activeSection === tab.key ? "var(--text-primary)" : "var(--text-muted)",
              fontSize: "14px",
              cursor: "pointer",
              whiteSpace: "nowrap",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        {/* SECTION 1: PERSONAL INFORMATION */}
        {(activeSection === "all" || activeSection === "personal") && (
          <Card style={{ padding: "24px" }}>
            <h3 style={{ fontSize: "18px", fontWeight: "700", marginBottom: "16px", color: "var(--text-primary)" }}>
              1. Personal Information
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "var(--text-secondary)", marginBottom: "6px" }}>
                  Full Name
                </label>
                {isEditing ? (
                  <input
                    type="text"
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                    className="form-input"
                    style={{ width: "100%", padding: "10px", borderRadius: "6px", border: "1px solid var(--border-default)", backgroundColor: "var(--bg-app)", color: "var(--text-primary)" }}
                  />
                ) : (
                  <div style={{ fontSize: "14px", color: "var(--text-primary)", fontWeight: "500" }}>{formData.full_name || "—"}</div>
                )}
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "var(--text-secondary)", marginBottom: "6px" }}>
                  Email Address
                </label>
                <div style={{ fontSize: "14px", color: "var(--text-muted)" }}>{user?.email} (Account ID)</div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "var(--text-secondary)", marginBottom: "6px" }}>
                  Phone Number
                </label>
                {isEditing ? (
                  <input
                    type="text"
                    placeholder="+1 (555) 000-0000"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="form-input"
                    style={{ width: "100%", padding: "10px", borderRadius: "6px", border: "1px solid var(--border-default)", backgroundColor: "var(--bg-app)", color: "var(--text-primary)" }}
                  />
                ) : (
                  <div style={{ fontSize: "14px", color: "var(--text-primary)" }}>{formData.phone || "Not added"}</div>
                )}
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "var(--text-secondary)", marginBottom: "6px" }}>
                  Location
                </label>
                {isEditing ? (
                  <input
                    type="text"
                    placeholder="City, Country"
                    value={formData.location}
                    onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                    className="form-input"
                    style={{ width: "100%", padding: "10px", borderRadius: "6px", border: "1px solid var(--border-default)", backgroundColor: "var(--bg-app)", color: "var(--text-primary)" }}
                  />
                ) : (
                  <div style={{ fontSize: "14px", color: "var(--text-primary)" }}>{formData.location || "Not added"}</div>
                )}
              </div>
            </div>

            <div style={{ marginTop: "16px" }}>
              <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "var(--text-secondary)", marginBottom: "6px" }}>
                Bio & Career Summary
              </label>
              {isEditing ? (
                <textarea
                  rows={3}
                  value={formData.bio}
                  onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                  placeholder="Concise overview of your engineering domain and technical passions..."
                  className="form-textarea"
                  style={{ width: "100%", padding: "10px", borderRadius: "6px", border: "1px solid var(--border-default)", backgroundColor: "var(--bg-app)", color: "var(--text-primary)", fontSize: "13px" }}
                />
              ) : (
                <p style={{ fontSize: "13px", color: "var(--text-primary)", lineHeight: "1.6" }}>
                  {formData.bio || "No summary provided yet."}
                </p>
              )}
            </div>
          </Card>
        )}

        {/* SECTION 2: PROFESSIONAL & CAREER */}
        {(activeSection === "all" || activeSection === "professional") && (
          <Card style={{ padding: "24px" }}>
            <h3 style={{ fontSize: "18px", fontWeight: "700", marginBottom: "16px", color: "var(--text-primary)" }}>
              2. Professional & Career Focus
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "var(--text-secondary)", marginBottom: "6px" }}>
                  Target Role
                </label>
                {isEditing ? (
                  <input
                    type="text"
                    value={formData.target_role}
                    onChange={(e) => setFormData({ ...formData, target_role: e.target.value })}
                    className="form-input"
                    style={{ width: "100%", padding: "10px", borderRadius: "6px", border: "1px solid var(--border-default)", backgroundColor: "var(--bg-app)", color: "var(--text-primary)" }}
                  />
                ) : (
                  <div style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-primary)" }}>{formData.target_role}</div>
                )}
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "var(--text-secondary)", marginBottom: "6px" }}>
                  Experience Level
                </label>
                {isEditing ? (
                  <select
                    value={formData.experience_level}
                    onChange={(e) => setFormData({ ...formData, experience_level: e.target.value })}
                    style={{ width: "100%", padding: "10px", borderRadius: "6px", border: "1px solid var(--border-default)", backgroundColor: "var(--bg-app)", color: "var(--text-primary)" }}
                  >
                    <option value="Intern / New Grad">Intern / New Grad</option>
                    <option value="Junior (1-2 yrs)">Junior (1-2 yrs)</option>
                    <option value="Mid-level (3-5 yrs)">Mid-level (3-5 yrs)</option>
                    <option value="Senior (5+ yrs)">Senior (5+ yrs)</option>
                    <option value="Staff / Lead">Staff / Lead</option>
                  </select>
                ) : (
                  <div style={{ fontSize: "14px", color: "var(--text-primary)" }}>{formData.experience_level}</div>
                )}
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "var(--text-secondary)", marginBottom: "6px" }}>
                  Weekly Practice Goal (Sessions)
                </label>
                {isEditing ? (
                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={formData.weekly_practice_goal}
                    onChange={(e) => setFormData({ ...formData, weekly_practice_goal: parseInt(e.target.value, 10) || 5 })}
                    className="form-input"
                    style={{ width: "100%", padding: "10px", borderRadius: "6px", border: "1px solid var(--border-default)", backgroundColor: "var(--bg-app)", color: "var(--text-primary)" }}
                  />
                ) : (
                  <div style={{ fontSize: "14px", color: "var(--text-primary)" }}>{formData.weekly_practice_goal} mock sessions / week</div>
                )}
              </div>
            </div>
          </Card>
        )}

        {/* SECTION 3: EDUCATION */}
        {(activeSection === "all" || activeSection === "education") && (
          <Card style={{ padding: "24px" }}>
            <h3 style={{ fontSize: "18px", fontWeight: "700", marginBottom: "16px", color: "var(--text-primary)" }}>
              3. Education & Credentials
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "var(--text-secondary)", marginBottom: "6px" }}>
                  College / University
                </label>
                {isEditing ? (
                  <input
                    type="text"
                    placeholder="e.g. Stanford University / IIT Delhi"
                    value={formData.university}
                    onChange={(e) => setFormData({ ...formData, university: e.target.value })}
                    className="form-input"
                    style={{ width: "100%", padding: "10px", borderRadius: "6px", border: "1px solid var(--border-default)", backgroundColor: "var(--bg-app)", color: "var(--text-primary)" }}
                  />
                ) : (
                  <div style={{ fontSize: "14px", color: "var(--text-primary)" }}>{formData.university || "Not added"}</div>
                )}
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "var(--text-secondary)", marginBottom: "6px" }}>
                  Degree & Major
                </label>
                {isEditing ? (
                  <input
                    type="text"
                    placeholder="e.g. B.S. in Computer Science"
                    value={formData.degree}
                    onChange={(e) => setFormData({ ...formData, degree: e.target.value })}
                    className="form-input"
                    style={{ width: "100%", padding: "10px", borderRadius: "6px", border: "1px solid var(--border-default)", backgroundColor: "var(--bg-app)", color: "var(--text-primary)" }}
                  />
                ) : (
                  <div style={{ fontSize: "14px", color: "var(--text-primary)" }}>{formData.degree || "Not added"}</div>
                )}
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "var(--text-secondary)", marginBottom: "6px" }}>
                  Graduation Year
                </label>
                {isEditing ? (
                  <input
                    type="number"
                    value={formData.graduation_year}
                    onChange={(e) => setFormData({ ...formData, graduation_year: parseInt(e.target.value, 10) || 2026 })}
                    className="form-input"
                    style={{ width: "100%", padding: "10px", borderRadius: "6px", border: "1px solid var(--border-default)", backgroundColor: "var(--bg-app)", color: "var(--text-primary)" }}
                  />
                ) : (
                  <div style={{ fontSize: "14px", color: "var(--text-primary)" }}>{formData.graduation_year || "—"}</div>
                )}
              </div>
            </div>
          </Card>
        )}

        {/* SECTION 4: TECHNICAL SKILLS */}
        {(activeSection === "all" || activeSection === "skills") && (
          <Card style={{ padding: "24px" }}>
            <h3 style={{ fontSize: "18px", fontWeight: "700", marginBottom: "16px", color: "var(--text-primary)" }}>
              4. Technical Skills & Proficiencies
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
              {[
                { cat: "languages", label: "Programming Languages" },
                { cat: "frameworks", label: "Frameworks & Libraries" },
                { cat: "databases", label: "Databases & Storage" },
                { cat: "tools", label: "Tools, DevOps & Cloud" },
              ].map(({ cat, label }) => {
                const list = formData.skills_categorized[cat] || [];
                return (
                  <div key={cat} style={{ borderBottom: "1px solid var(--border-subtle)", paddingBottom: "12px" }}>
                    <div style={{ fontSize: "13px", fontWeight: "700", color: "var(--text-secondary)", marginBottom: "8px" }}>
                      {label} ({list.length})
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
                      {list.length === 0 && <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>None added</span>}
                      {list.map((skill) => (
                        <span
                          key={skill}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "6px",
                            padding: "4px 10px",
                            borderRadius: "6px",
                            backgroundColor: "var(--bg-subtle)",
                            border: "1px solid var(--border-default)",
                            fontSize: "12px",
                            color: "var(--text-primary)",
                          }}
                        >
                          <span>{skill}</span>
                          {isEditing && (
                            <button
                              type="button"
                              onClick={() => handleRemoveSkill(cat, skill)}
                              style={{ background: "none", border: "none", cursor: "pointer", color: "var(--danger-text)", fontWeight: "700" }}
                            >
                              ×
                            </button>
                          )}
                        </span>
                      ))}

                      {isEditing && (
                        <input
                          type="text"
                          placeholder="+ Add..."
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              handleAddSkill(cat, e.target.value);
                              e.target.value = "";
                            }
                          }}
                          style={{
                            padding: "3px 8px",
                            borderRadius: "4px",
                            border: "1px dashed var(--border-strong)",
                            fontSize: "12px",
                            width: "100px",
                            backgroundColor: "transparent",
                            color: "var(--text-primary)",
                          }}
                        />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        )}

        {/* SECTION 5: DEVELOPER PROFILES & PROFESSIONAL LINKS (Part 29) */}
        {(activeSection === "all" || activeSection === "links") && (
          <Card style={{ padding: "24px" }}>
            <h3 style={{ fontSize: "18px", fontWeight: "700", marginBottom: "16px", color: "var(--text-primary)" }}>
              5. Developer Profiles & External Verification
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
              {DEVELOPER_PLATFORMS.map(({ key, label, placeholder, icon }) => {
                const currentUrl = formData.professional_links[key] || "";
                const hasValid = isValidUrl(currentUrl);

                return (
                  <div
                    key={key}
                    style={{
                      padding: "14px",
                      borderRadius: "8px",
                      border: "1px solid var(--border-default)",
                      backgroundColor: "var(--bg-subtle)",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", fontWeight: "700", color: "var(--text-primary)" }}>
                        <span>{icon}</span>
                        <span>{label}</span>
                      </div>
                      {hasValid && !isEditing && (
                        <a
                          href={currentUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            fontSize: "11px",
                            fontWeight: "700",
                            color: "var(--primary-600)",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "2px",
                          }}
                        >
                          Open ↗
                        </a>
                      )}
                    </div>

                    {isEditing ? (
                      <input
                        type="url"
                        placeholder={placeholder}
                        value={currentUrl}
                        onChange={(e) => handleLinkChange(key, e.target.value)}
                        className="form-input"
                        style={{
                          width: "100%",
                          padding: "8px 10px",
                          borderRadius: "6px",
                          border: `1px solid ${currentUrl && !hasValid ? "var(--danger-text)" : "var(--border-default)"}`,
                          backgroundColor: "var(--bg-app)",
                          color: "var(--text-primary)",
                          fontSize: "12px",
                        }}
                      />
                    ) : (
                      <div style={{ fontSize: "13px", color: currentUrl ? "var(--text-primary)" : "var(--text-muted)", wordBreak: "break-all" }}>
                        {currentUrl || "Not added"}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
