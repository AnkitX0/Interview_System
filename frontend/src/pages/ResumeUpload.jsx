import { useState, useContext, useEffect, useRef, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { ReportContext } from "../context/ReportContext";
import { apiFetch } from "../utils/api";
import { Card, CardHeader } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { TechIcon } from "../components/TechIcon";

const SAMPLE_BENCHMARK_RESUME = `Jane Doe
Email: jane.doe@example.com | Phone: 555-0199 | San Francisco, CA

PROFESSIONAL SUMMARY
Senior Backend Engineer with 5+ years of experience architecting distributed microservices, optimizing database throughput, and designing resilient REST APIs.

TECHNICAL SKILLS
Languages: Python, Java, SQL, TypeScript, Bash
Frameworks & Libraries: FastAPI, Django, React, Pandas
Databases & Storage: PostgreSQL, Redis, MongoDB
Cloud & DevOps: Docker, Kubernetes, AWS, CI/CD, Git
Core Concepts: REST API, Microservices, Distributed Systems, Concurrency, System Design

EXPERIENCE
Senior Software Engineer - CloudTech Solutions (2021 - Present)
- Architected high-throughput REST APIs using FastAPI and PostgreSQL, serving 25,000 requests per second with 99.95% uptime.
- Implemented Redis caching with a cache-aside pattern, reducing p99 API query latency by 45%.
- Deployed containerized microservices to AWS EKS with automated GitHub Actions CI/CD pipelines.

Software Developer - FinTech Systems (2019 - 2021)
- Developed transaction validation service handling 10,000 daily financial transfers.
- Integrated PostgreSQL read replicas and connection pooling via PgBouncer to eliminate database lock contention.

PROJECTS
High-Concurrency Order Processing Engine
- Built distributed order event processing pipeline using Python, Redis Streams, and Docker.
- Handled simulated order surges of 5,000 requests/sec with zero message drop.

Real-Time Telemetry Analytics Service
- Engineered time-series log aggregator using FastAPI, MongoDB, and React dashboard.
- Reduced ingestion latency from 800ms to 120ms through asynchronous batching.

EDUCATION
B.Tech in Computer Science and Engineering, Tech University (2015 - 2019)
GPA: 3.8 / 4.0`;

/**
 * Classifies resume claims into priority tiers:
 * HIGH VALUE (quantified performance metrics, technical architecture, models)
 * MEDIUM VALUE (operational implementation, frameworks, tools)
 * SUPPORTING (education credentials, general background)
 */
export function scoreClaimPriority(claim) {
  let score = 0;
  const text = (claim.claim_text || "").toLowerCase();

  // Metrics, numbers, percentages or latency/throughput
  if (claim.has_metric || /\d+(\.\d+)?%|\d+\+?\s*(requests|users|rps|ms|qps|problems|accuracy)/i.test(text)) {
    score += 50;
  }
  // ML / System architecture keywords
  if (/random forest|mediapipe|pytorch|fastapi|cnn|mlp|postgresql|redis|kubernetes|microservices|distributed/i.test(text)) {
    score += 30;
  }
  // Probe priority multiplier
  if (claim.probe_priority) {
    score += claim.probe_priority * 20;
  }
  // Penalize generic / links / certificates
  if (/github|certificate|course|hackathon|b\.tech|gpa|cgpa/i.test(text)) {
    score -= 40;
  }

  if (score >= 45) return { tier: "HIGH VALUE", score, color: "#16a34a", bg: "#f0fdf4", border: "#bbf7d0" };
  if (score >= 20) return { tier: "MEDIUM VALUE", score, color: "#0284c7", bg: "#f0f9ff", border: "#bae6fd" };
  return { tier: "SUPPORTING", score, color: "#64748b", bg: "#f8fafc", border: "#e2e8f0" };
}

export default function ResumeUpload() {
  const navigate = useNavigate();
  const { resumeData, setResumeData } = useContext(ReportContext);

  const [file, setFile] = useState(null);
  const [pdfBlobUrl, setPdfBlobUrl] = useState(null);
  const [textInput, setTextInput] = useState("");
  const [mode, setMode] = useState("file"); // "file" or "text"
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState(0);
  const [error, setError] = useState(null);
  const [profile, setProfile] = useState(resumeData || null);
  const [step, setStep] = useState(resumeData ? "complete" : "upload"); // "upload" | "review" | "complete"
  const [reviewForm, setReviewForm] = useState({
    candidate_name: "",
    target_role: "",
    education: "",
    experience: "",
    skills: [],
    projects: [],
    claims: [],
  });
  const [newSkillInput, setNewSkillInput] = useState("");
  const [savingReview, setSavingReview] = useState(false);
  const [previewTab, setPreviewTab] = useState("document"); // "document" or "raw"
  const [showAllClaimsModal, setShowAllClaimsModal] = useState(false);
  const [claimSearchFilter, setClaimSearchFilter] = useState("");
  const [claimTierFilter, setClaimTierFilter] = useState("ALL");
  const [collapsedSections, setCollapsedSections] = useState({
    skills: true,
    projects: true,
    experience: true,
    education: true,
    scoring: true,
    sourceDoc: true,
  });

  const toggleSection = (sec) => {
    setCollapsedSections((prev) => ({ ...prev, [sec]: !prev[sec] }));
  };

  const sortedClaims = useMemo(() => {
    if (!profile?.claims) return [];
    return [...profile.claims].map((c) => ({
      ...c,
      _priority: scoreClaimPriority(c),
    })).sort((a, b) => b._priority.score - a._priority.score);
  }, [profile?.claims]);

  const topClaims = useMemo(() => {
    return sortedClaims.slice(0, 4);
  }, [sortedClaims]);

  const filteredModalClaims = useMemo(() => {
    return sortedClaims.filter((c) => {
      const matchesSearch = !claimSearchFilter ||
        (c.claim_text || "").toLowerCase().includes(claimSearchFilter.toLowerCase()) ||
        (c.claim_type || "").toLowerCase().includes(claimSearchFilter.toLowerCase());
      if (!matchesSearch) return false;
      if (claimTierFilter === "HIGH") return c._priority.tier === "HIGH VALUE";
      if (claimTierFilter === "METRIC") return Boolean(c.has_metric);
      return true;
    });
  }, [sortedClaims, claimSearchFilter, claimTierFilter]);

  const interviewFocusItems = useMemo(() => {
    const items = [];
    if (profile?.projects && profile.projects.length > 0) {
      items.push({
        title: `Project Architecture: ${profile.projects[0].title}`,
        desc: `Defense of architectural choices, concurrency limits, and data pipeline design.`,
        badge: "Architecture Defense",
      });
      if (profile.projects.length > 1) {
        items.push({
          title: `Implementation Probing: ${profile.projects[1].title}`,
          desc: `Technical trade-offs, technology selection rationale, and failure isolation.`,
          badge: "Technical Depth",
        });
      }
    }
    const topMetricClaim = sortedClaims.find((c) => c.has_metric);
    if (topMetricClaim) {
      items.push({
        title: "Quantified Metrics Validation",
        desc: `Evaluation of benchmark methodology behind: "${(topMetricClaim.claim_text || '').slice(0, 90)}..."`,
        badge: "Metric Verification",
      });
    }
    if (profile?.skills && profile.skills.length > 0) {
      const topSkills = profile.skills.slice(0, 4).join(", ");
      items.push({
        title: `Core Technology Probing: ${topSkills}`,
        desc: `Operational depth, internal execution model, and edge-case handling.`,
        badge: "Tech Competency",
      });
    }
    items.push({
      title: "Problem Solving & Algorithmic Trade-offs",
      desc: "Live reasoning on time/space complexity, distributed state, and system bottlenecks.",
      badge: "Problem Solving",
    });
    return items.slice(0, 5);
  }, [profile, sortedClaims]);

  const fileInputRef = useRef(null);

  // Generate blob URL for PDF preview when file changes
  useEffect(() => {
    if (file && (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf"))) {
      const url = URL.createObjectURL(file);
      setPdfBlobUrl(url);
      return () => {
        URL.revokeObjectURL(url);
      };
    } else {
      setPdfBlobUrl(null);
    }
  }, [file]);

  // Staged loading feedback
  useEffect(() => {
    let interval;
    if (loading) {
      setLoadingStage(0);
      interval = setInterval(() => {
        setLoadingStage((prev) => (prev < 3 ? prev + 1 : prev));
      }, 700);
    } else {
      setLoadingStage(0);
    }
    return () => clearInterval(interval);
  }, [loading]);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setError(null);
    }
  };

  const handleLoadSample = () => {
    setMode("text");
    setTextInput(SAMPLE_BENCHMARK_RESUME);
    setError(null);
  };

  const handleAnalyze = async () => {
    if (mode === "file" && !file) {
      setError("Please select a PDF or text resume file first.");
      return;
    }
    if (mode === "text" && !textInput.trim()) {
      setError("Please paste your resume text in the box below or load the sample resume.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      if (mode === "file" && file) {
        formData.append("file", file);
      } else {
        formData.append("raw_text", textInput);
      }

      const res = await apiFetch("/resume/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        const errorMsg =
          data?.error?.message ||
          data?.detail ||
          "Document validation failed. Please ensure file contains valid resume content.";
        setError(errorMsg);
        return;
      }

      setProfile(data);
      setResumeData(data);

      // Populate review stage for candidate audit
      setReviewForm({
        candidate_name: data.candidate_name || "Candidate",
        target_role: (data.role_fit_scores && Object.keys(data.role_fit_scores)[0]) || "Software Engineer",
        education: data.education || "",
        experience: data.experience || "",
        skills: Array.isArray(data.skills) ? [...data.skills] : [],
        projects: Array.isArray(data.projects) ? data.projects.map((p) => ({ ...p, accepted: true })) : [],
        claims: Array.isArray(data.claims) ? [...data.claims] : [],
      });
      setStep("review");
    } catch (err) {
      console.error("Resume analysis error:", err);
      setError(err.message || "Failed to analyze document. Please check the file and try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleSaveReview = async () => {
    setSavingReview(true);
    try {
      const acceptedProjects = reviewForm.projects.filter((p) => p.accepted);
      const updatePayload = {
        candidate_name: reviewForm.candidate_name,
        skills: reviewForm.skills,
        education: reviewForm.education,
        experience: reviewForm.experience,
      };

      if (profile?.id) {
        const res = await apiFetch(`/resume/${profile.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(updatePayload),
        });
        if (res.ok) {
          const updated = await res.json();
          setProfile(updated);
          setResumeData(updated);
        } else {
          const merged = { ...profile, ...updatePayload, projects: acceptedProjects };
          setProfile(merged);
          setResumeData(merged);
        }
      } else {
        const merged = { ...profile, ...updatePayload, projects: acceptedProjects };
        setProfile(merged);
        setResumeData(merged);
      }
      setStep("complete");
    } catch (err) {
      console.warn("Save review error:", err);
      setStep("complete");
    } finally {
      setSavingReview(false);
    }
  };

  const handleRemoveSkill = (skillToRemove) => {
    setReviewForm((prev) => ({
      ...prev,
      skills: prev.skills.filter((s) => s !== skillToRemove),
    }));
  };

  const handleAddSkill = () => {
    const trimmed = newSkillInput.trim();
    if (trimmed && !reviewForm.skills.includes(trimmed)) {
      setReviewForm((prev) => ({
        ...prev,
        skills: [...prev.skills, trimmed],
      }));
      setNewSkillInput("");
    }
  };

  const handleToggleProject = (idx) => {
    setReviewForm((prev) => {
      const nextProjects = [...prev.projects];
      if (nextProjects[idx]) {
        nextProjects[idx] = { ...nextProjects[idx], accepted: !nextProjects[idx].accepted };
      }
      return { ...prev, projects: nextProjects };
    });
  };

  const handleProceedToInterview = () => {
    navigate("/setup", {
      state: {
        resumeId: profile?.id,
        candidateName: profile?.candidate_name,
        skills: profile?.skills,
      },
    });
  };

  const handleReset = () => {
    setProfile(null);
    setFile(null);
    setPdfBlobUrl(null);
    setTextInput("");
    setError(null);
    setStep("upload");
  };

  // Helper for score badge colors
  const getScoreColor = (score) => {
    if (score >= 80) return "#16a34a";
    if (score >= 65) return "#d97706";
    return "#dc2626";
  };

  const getScoreLabel = (score) => {
    if (score >= 85) return "Strong Profile";
    if (score >= 70) return "Solid Baseline";
    if (score >= 55) return "Moderate Depth";
    return "Needs Refinement";
  };

  return (
    <div style={{ maxWidth: "1140px", margin: "0 auto", padding: "0 16px 80px 16px" }}>
      {/* PAGE HEADER */}
      <div style={{ marginBottom: "28px", display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
            <span style={{ fontSize: "12px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--primary-700)" }}>
              Career Intelligence
            </span>
            <Badge variant="info">Resume Intelligence Engine</Badge>
          </div>
          <h1 style={{ fontSize: "28px", fontWeight: "800", color: "#0f172a", letterSpacing: "-0.02em" }}>
            Resume Intelligence & Competency Audit
          </h1>
          <p style={{ color: "#64748b", marginTop: "4px", fontSize: "14px", maxWidth: "680px" }}>
            Analyze your resume to extract verifiable skills, audit accomplishment claims, calibrate role relevance, and ground your mock interview in authentic career evidence.
          </p>
        </div>

        {step === "complete" && profile && (
          <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
            <Button variant="secondary" size="md" onClick={() => setStep("review")}>
              ✏️ Edit Extracted Review
            </Button>
            <Button variant="subtle" size="md" onClick={handleReset}>
              Analyze Another Document
            </Button>
            <Button variant="primary" size="md" onClick={handleProceedToInterview}>
              Start Interview with this Profile →
            </Button>
          </div>
        )}
      </div>

      {/* STEP 1: DOCUMENT UPLOAD / INPUT CARD */}
      {step === "upload" && (
        <Card style={{ marginBottom: "32px", padding: "28px", border: "1px solid var(--border-default)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                type="button"
                onClick={() => setMode("file")}
                style={{
                  padding: "8px 18px",
                  borderRadius: "6px",
                  fontSize: "13px",
                  fontWeight: "600",
                  cursor: "pointer",
                  border: "1px solid",
                  borderColor: mode === "file" ? "var(--primary-700)" : "var(--border-default)",
                  backgroundColor: mode === "file" ? "var(--primary-700)" : "var(--bg-card)",
                  color: mode === "file" ? "#ffffff" : "var(--text-secondary)",
                  transition: "all 0.15s ease",
                }}
              >
                Upload File (PDF / TXT)
              </button>
              <button
                type="button"
                onClick={() => setMode("text")}
                style={{
                  padding: "8px 18px",
                  borderRadius: "6px",
                  fontSize: "13px",
                  fontWeight: "600",
                  cursor: "pointer",
                  border: "1px solid",
                  borderColor: mode === "text" ? "var(--primary-700)" : "var(--border-default)",
                  backgroundColor: mode === "text" ? "var(--primary-700)" : "var(--bg-card)",
                  color: mode === "text" ? "#ffffff" : "var(--text-secondary)",
                  transition: "all 0.15s ease",
                }}
              >
                Paste Resume Text
              </button>
            </div>

            <Button variant="subtle" size="sm" onClick={handleLoadSample}>
              Load Sample Benchmark Resume
            </Button>
          </div>

          {mode === "file" ? (
            <div>
              <div
                onClick={() => fileInputRef.current?.click()}
                style={{
                  border: "2px dashed var(--border-default)",
                  borderRadius: "10px",
                  padding: "36px 20px",
                  textAlign: "center",
                  backgroundColor: "var(--bg-app)",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.txt,.doc,.docx"
                  onChange={handleFileChange}
                  style={{ display: "none" }}
                />
                <div style={{ fontSize: "40px", marginBottom: "12px" }}>📄</div>
                <p style={{ fontWeight: "600", fontSize: "16px", color: "var(--text-primary)", marginBottom: "4px" }}>
                  {file ? file.name : "Click to select or drag and drop your resume"}
                </p>
                <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                  Supports PDF or TXT documents (Max 10MB)
                </p>
              </div>

              {/* Dedicated File Information & Primary CTA Card (Bug #1 Fix) */}
              {file && (
                <div
                  style={{
                    marginTop: "16px",
                    padding: "16px 20px",
                    backgroundColor: "var(--bg-card)",
                    borderRadius: "8px",
                    border: "1px solid var(--border-default)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: "14px",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <div style={{ fontSize: "28px" }}>📄</div>
                    <div>
                      <div style={{ fontWeight: "700", color: "var(--text-primary)", fontSize: "15px" }}>
                        {file.name}
                      </div>
                      <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
                        {(file.size / 1024).toFixed(1)} KB • PDF Document • Ready for Intelligence Review
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <Button
                      variant="subtle"
                      size="sm"
                      onClick={() => {
                        setFile(null);
                        if (fileInputRef.current) fileInputRef.current.value = "";
                      }}
                    >
                      Remove
                    </Button>
                    <Button
                      variant="primary"
                      size="md"
                      onClick={handleAnalyze}
                      loading={loading}
                    >
                      Review Resume →
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div>
              <textarea
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Paste your full resume text here (Summary, Skills, Experience, Projects, Education)..."
                rows={12}
                style={{
                  width: "100%",
                  padding: "16px",
                  borderRadius: "8px",
                  border: "1px solid var(--border-default)",
                  fontFamily: "var(--font-family-sans, inherit)",
                  fontSize: "14px",
                  lineHeight: "1.6",
                  color: "var(--text-primary)",
                  resize: "vertical",
                  backgroundColor: "var(--bg-card)",
                }}
              />
            </div>
          )}

          {error && (
            <div style={{ marginTop: "18px", padding: "14px 18px", backgroundColor: "#fef2f2", border: "1px solid #fecaca", borderRadius: "8px", color: "#991b1b", fontSize: "14px" }}>
              <strong>Validation Notice:</strong> {error}
            </div>
          )}

          {/* LOADING STATE FEEDBACK */}
          {loading ? (
            <div style={{ marginTop: "24px", padding: "20px", backgroundColor: "var(--bg-app)", borderRadius: "8px", border: "1px solid var(--border-default)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
                <span style={{ display: "inline-block", width: "16px", height: "16px", border: "2px solid var(--primary-600)", borderRightColor: "transparent", borderRadius: "50%", animation: "spin 0.6s linear infinite" }} />
                <strong style={{ fontSize: "14px", color: "var(--text-primary)" }}>Extracting and auditing resume intelligence...</strong>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "10px", fontSize: "13px" }}>
                <div style={{ color: loadingStage >= 0 ? "#16a34a" : "#94a3b8", display: "flex", alignItems: "center", gap: "6px" }}>
                  <span>{loadingStage >= 0 ? "✓" : "○"}</span> Parsing document text
                </div>
                <div style={{ color: loadingStage >= 1 ? "#16a34a" : "#94a3b8", display: "flex", alignItems: "center", gap: "6px" }}>
                  <span>{loadingStage >= 1 ? "✓" : "○"}</span> Extracting skills & stack
                </div>
                <div style={{ color: loadingStage >= 2 ? "#16a34a" : "#94a3b8", display: "flex", alignItems: "center", gap: "6px" }}>
                  <span>{loadingStage >= 2 ? "✓" : "○"}</span> Auditing claims & metrics
                </div>
                <div style={{ color: loadingStage >= 3 ? "#16a34a" : "#94a3b8", display: "flex", alignItems: "center", gap: "6px" }}>
                  <span>{loadingStage >= 3 ? "✓" : "○"}</span> Calibrating interview context
                </div>
              </div>
            </div>
          ) : (
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "24px" }}>
              <Button
                variant="primary"
                size="lg"
                onClick={handleAnalyze}
                disabled={loading || (mode === "file" && !file) || (mode === "text" && !textInput.trim())}
              >
                Review Resume →
              </Button>
            </div>
          )}
        </Card>
      )}

      {/* STEP 2: RESUME REVIEW & CONFIRMATION SCREEN (Bug #1 & Review Flow) */}
      {step === "review" && (
        <Card style={{ marginBottom: "32px", padding: "28px", border: "1px solid var(--border-default)" }}>
          {/* Header */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "24px", borderBottom: "1px solid var(--border-default)", paddingBottom: "16px", flexWrap: "wrap", gap: "14px" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                <Badge variant="info">Step 2: Candidate Verification & Audit</Badge>
                <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Inspect before committing</span>
              </div>
              <h2 style={{ fontSize: "22px", fontWeight: "800", color: "var(--text-primary)" }}>
                Review Extracted Resume Profile
              </h2>
              <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "2px" }}>
                Verify, edit, or adjust extracted details. Fields labeled &quot;Found in resume&quot; were grounded from your document.
              </p>
            </div>

            <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              <Button variant="secondary" size="md" onClick={() => setStep("upload")}>
                ← Back to Upload
              </Button>
              <Button variant="primary" size="md" onClick={handleSaveReview} loading={savingReview}>
                Save Resume Analysis & Continue →
              </Button>
            </div>
          </div>

          {/* Form Fields */}
          <div style={{ display: "flex", flexDirection: "column", gap: "22px" }}>
            {/* Row 1: Candidate Name & Target Role */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "18px" }}>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                  <label style={{ fontSize: "13px", fontWeight: "700", color: "var(--text-primary)" }}>
                    Candidate Name
                  </label>
                  <span style={{ fontSize: "11px", color: "#16a34a", fontWeight: "600" }}>✓ Found in resume</span>
                </div>
                <input
                  type="text"
                  value={reviewForm.candidate_name}
                  onChange={(e) => setReviewForm({ ...reviewForm, candidate_name: e.target.value })}
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    borderRadius: "6px",
                    border: "1px solid var(--border-default)",
                    backgroundColor: "var(--bg-app)",
                    color: "var(--text-primary)",
                    fontSize: "14px",
                  }}
                />
              </div>

              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                  <label style={{ fontSize: "13px", fontWeight: "700", color: "var(--text-primary)" }}>
                    Target Role
                  </label>
                  <span style={{ fontSize: "11px", color: "#2563eb", fontWeight: "600" }}>Calibrated by Role Fit</span>
                </div>
                <input
                  type="text"
                  value={reviewForm.target_role}
                  onChange={(e) => setReviewForm({ ...reviewForm, target_role: e.target.value })}
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    borderRadius: "6px",
                    border: "1px solid var(--border-default)",
                    backgroundColor: "var(--bg-app)",
                    color: "var(--text-primary)",
                    fontSize: "14px",
                  }}
                />
              </div>
            </div>

            {/* Row 2: Education */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                <label style={{ fontSize: "13px", fontWeight: "700", color: "var(--text-primary)" }}>
                  Education & Academic Credentials
                </label>
                <span style={{ fontSize: "11px", color: "#16a34a", fontWeight: "600" }}>✓ Found in resume</span>
              </div>
              <textarea
                rows={2}
                value={reviewForm.education}
                onChange={(e) => setReviewForm({ ...reviewForm, education: e.target.value })}
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "6px",
                  border: "1px solid var(--border-default)",
                  backgroundColor: "var(--bg-app)",
                  color: "var(--text-primary)",
                  fontSize: "13px",
                  lineHeight: "1.5",
                }}
              />
            </div>

            {/* Row 3: Skills with Interactive Tags */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                <label style={{ fontSize: "13px", fontWeight: "700", color: "var(--text-primary)" }}>
                  Extracted Technical Skills ({reviewForm.skills.length})
                </label>
                <span style={{ fontSize: "11px", color: "#16a34a", fontWeight: "600" }}>✓ Found in resume</span>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", padding: "12px", backgroundColor: "var(--bg-app)", borderRadius: "8px", border: "1px solid var(--border-default)", minHeight: "48px" }}>
                {reviewForm.skills.map((skill) => (
                  <span
                    key={skill}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      padding: "4px 10px",
                      backgroundColor: "var(--bg-card)",
                      borderRadius: "4px",
                      border: "1px solid var(--border-default)",
                      fontSize: "12px",
                      fontWeight: "600",
                      color: "var(--text-primary)",
                    }}
                  >
                    {skill}
                    <button
                      type="button"
                      onClick={() => handleRemoveSkill(skill)}
                      style={{
                        background: "none",
                        border: "none",
                        color: "var(--danger-text)",
                        cursor: "pointer",
                        fontWeight: "700",
                        fontSize: "13px",
                        lineHeight: "1",
                        padding: 0,
                      }}
                      title="Remove skill"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
                <input
                  type="text"
                  placeholder="Add another verified technical competency..."
                  value={newSkillInput}
                  onChange={(e) => setNewSkillInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddSkill();
                    }
                  }}
                  style={{
                    flex: 1,
                    padding: "8px 12px",
                    borderRadius: "6px",
                    border: "1px solid var(--border-default)",
                    backgroundColor: "var(--bg-app)",
                    color: "var(--text-primary)",
                    fontSize: "13px",
                  }}
                />
                <Button variant="secondary" size="sm" onClick={handleAddSkill}>
                  + Add Skill
                </Button>
              </div>
            </div>

            {/* Row 4: Projects with Accept / Ignore */}
            {reviewForm.projects.length > 0 && (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <label style={{ fontSize: "13px", fontWeight: "700", color: "var(--text-primary)" }}>
                    Extracted Projects ({reviewForm.projects.length})
                  </label>
                  <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                    Click &quot;Accept&quot; or &quot;Ignore&quot; to calibrate interview defense topics
                  </span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {reviewForm.projects.map((proj, pIdx) => (
                    <div
                      key={pIdx}
                      style={{
                        padding: "14px 16px",
                        backgroundColor: proj.accepted ? "var(--bg-card)" : "var(--bg-app)",
                        opacity: proj.accepted ? 1 : 0.6,
                        borderRadius: "8px",
                        border: "1px solid",
                        borderColor: proj.accepted ? "var(--border-default)" : "transparent",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "flex-start",
                        gap: "14px",
                      }}
                    >
                      <div style={{ flex: 1 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                          <span style={{ fontWeight: "700", fontSize: "14px", color: "var(--text-primary)" }}>
                            {proj.title}
                          </span>
                          <span style={{ fontSize: "11px", color: "#16a34a", fontWeight: "600" }}>
                            Found in resume
                          </span>
                        </div>
                        {proj.description && (
                          <p style={{ fontSize: "12px", color: "var(--text-secondary)", margin: "0 0 6px 0" }}>
                            {proj.description}
                          </p>
                        )}
                        {proj.technologies && proj.technologies.length > 0 && (
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                            {proj.technologies.map((t, tIdx) => (
                              <span key={tIdx} style={{ fontSize: "11px", padding: "2px 6px", backgroundColor: "var(--bg-app)", borderRadius: "3px", color: "var(--text-secondary)" }}>
                                {t}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      <Button
                        variant={proj.accepted ? "secondary" : "subtle"}
                        size="sm"
                        onClick={() => handleToggleProject(pIdx)}
                      >
                        {proj.accepted ? "✓ Accepted" : "Ignored"}
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Row 5: Audited Metrics & Claims */}
            {reviewForm.claims.length > 0 && (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <label style={{ fontSize: "13px", fontWeight: "700", color: "var(--text-primary)" }}>
                    Audited Claims & Quantified Metrics ({reviewForm.claims.length})
                  </label>
                  <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                    Audited for interview probe questions
                  </span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "10px" }}>
                  {reviewForm.claims.map((claim, cIdx) => (
                    <div
                      key={cIdx}
                      style={{
                        padding: "12px 14px",
                        backgroundColor: "var(--bg-app)",
                        borderRadius: "6px",
                        border: "1px solid var(--border-default)",
                        fontSize: "12px",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                        <span style={{ fontWeight: "700", color: "var(--text-primary)" }}>
                          {claim.claim_type ? claim.claim_type.toUpperCase() : "TECHNICAL CLAIM"}
                        </span>
                        <span
                          style={{
                            fontSize: "10px",
                            padding: "2px 6px",
                            borderRadius: "4px",
                            backgroundColor: claim.has_metric ? "#dcfce7" : "#fef3c7",
                            color: claim.has_metric ? "#166534" : "#92400e",
                            fontWeight: "700",
                          }}
                        >
                          {claim.has_metric ? "Found in resume" : "Needs confirmation"}
                        </span>
                      </div>
                      <p style={{ margin: "0 0 4px 0", color: "var(--text-secondary)", lineHeight: "1.4" }}>
                        &quot;{claim.claim_text}&quot;
                      </p>
                      {claim.metric && (
                        <div style={{ color: "#2563eb", fontWeight: "600", fontSize: "11px" }}>
                          Metric: {claim.metric}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Bottom Actions */}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "12px", paddingTop: "16px", borderTop: "1px solid var(--border-default)" }}>
              <Button variant="secondary" size="md" onClick={() => setStep("upload")}>
                ← Back to Upload
              </Button>
              <Button variant="primary" size="lg" onClick={handleSaveReview} loading={savingReview}>
                Save Resume Analysis & Continue →
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* STEP 3: PROGRESSIVE DISCLOSURE RESUME INTELLIGENCE DOSSIER */}
      {step === "complete" && profile && (
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>

          {/* 1. DOSSIER HEADER */}
          <Card style={{ padding: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
              <div>
                <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "4px 10px", borderRadius: "12px", backgroundColor: "#f1f5f9", color: "#475569", fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px" }}>
                  <span>📋</span> Resume Intelligence Dossier
                </div>
                <h2 style={{ fontSize: "24px", fontWeight: "800", color: "#0f172a", margin: 0 }}>
                  {profile.candidate_name || "Engineering Candidate"}
                </h2>
                <div style={{ display: "flex", alignItems: "center", gap: "12px", marginTop: "6px", flexWrap: "wrap" }}>
                  <span style={{ fontSize: "14px", color: "#475569", fontWeight: "500" }}>
                    🎯 Target Role: <strong>{profile.target_role || (profile.role_fit_scores && Object.keys(profile.role_fit_scores)[0]) || "Software Engineer"}</strong>
                  </span>
                  <span style={{ color: "#cbd5e1" }}>•</span>
                  <span style={{ fontSize: "13px", color: "#64748b" }}>
                    Status: <strong style={{ color: "#16a34a" }}>Audited & Ready</strong>
                  </span>
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "28px", fontWeight: "800", color: getScoreColor(profile.resume_score), lineHeight: "1" }}>
                    {profile.resume_score}
                    <span style={{ fontSize: "14px", color: "#94a3b8", fontWeight: "500" }}> / 100</span>
                  </div>
                  <Badge variant={profile.resume_score >= 80 ? "success" : profile.resume_score >= 65 ? "warning" : "danger"} style={{ marginTop: "4px" }}>
                    {getScoreLabel(profile.resume_score)}
                  </Badge>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  <Button variant="primary" size="md" onClick={handleProceedToInterview}>
                    Start Interview Now →
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => setStep("review")}>
                    ✏️ Edit Information
                  </Button>
                </div>
              </div>
            </div>
          </Card>

          {/* 2. AT A GLANCE (Compact Dossier Grid) */}
          <Card style={{ padding: "20px" }}>
            <h3 style={{ fontSize: "12px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "0.06em", color: "#64748b", marginBottom: "14px" }}>
              At A Glance
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "14px" }}>
              <div style={glanceCard}>
                <span style={snapshotLabel}>Skills Extracted</span>
                <div style={glanceValue}>{profile.skills?.length || 0} Skills</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "6px" }}>
                  {(profile.skills || []).slice(0, 4).map((s, idx) => (
                    <span key={idx} style={{ fontSize: "11px", padding: "2px 6px", backgroundColor: "#f1f5f9", borderRadius: "4px", color: "#334155" }}>
                      {s}
                    </span>
                  ))}
                  {(profile.skills?.length || 0) > 4 && (
                    <span style={{ fontSize: "11px", color: "#64748b", alignSelf: "center" }}>
                      +{profile.skills.length - 4} more
                    </span>
                  )}
                </div>
              </div>

              <div style={glanceCard}>
                <span style={snapshotLabel}>Projects Identified</span>
                <div style={glanceValue}>{profile.projects?.length || 0} Projects</div>
                <span style={snapshotSub}>
                  {profile.projects?.length > 0
                    ? profile.projects.map((p) => p.title).slice(0, 2).join(", ")
                    : "No projects parsed"}
                </span>
              </div>

              <div style={glanceCard}>
                <span style={snapshotLabel}>Experience Track</span>
                <div style={glanceValue}>{profile.experience ? "Documented" : "Entry Level"}</div>
                <span style={snapshotSub}>
                  {profile.experience ? profile.experience.slice(0, 50) + "..." : "Academic / Project background"}
                </span>
              </div>

              <div style={glanceCard}>
                <span style={snapshotLabel}>Education Credential</span>
                <div style={glanceValue}>{profile.education ? "Verified" : "Not Specified"}</div>
                <span style={snapshotSub}>
                  {profile.education ? profile.education.slice(0, 45) + "..." : "Standard Curriculum"}
                </span>
              </div>

              <div style={glanceCard}>
                <span style={snapshotLabel}>Audited Claims</span>
                <div style={glanceValue}>{profile.claims?.length || 0} Claims</div>
                <span style={snapshotSub}>
                  {sortedClaims.filter((c) => c._priority.tier === "HIGH VALUE").length} High-Value Probes
                </span>
              </div>
            </div>
          </Card>

          {/* 3. INTERVIEW FOCUS (3–5 Most Important Areas) */}
          <Card style={{ padding: "22px", borderLeft: "4px solid #ea580c", backgroundColor: "#fffaf7" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <div>
                <h3 style={{ fontSize: "16px", fontWeight: "800", color: "#9a3412", display: "flex", alignItems: "center", gap: "8px" }}>
                  <span>🎯</span> Interview Focus: Calibrated Exploration Areas
                </h3>
                <p style={{ fontSize: "12px", color: "#7c2d12", margin: "2px 0 0 0" }}>
                  Based on your resume, the interviewer is programmed to explore these critical technical dimensions:
                </p>
              </div>
              <Badge variant="warning">Prioritized Engine Targets</Badge>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "10px", marginTop: "12px" }}>
              {interviewFocusItems.map((item, idx) => (
                <div key={idx} style={{ backgroundColor: "#ffffff", padding: "12px 14px", borderRadius: "6px", border: "1px solid #fed7aa", boxShadow: "0 1px 2px rgba(0,0,0,0.02)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                    <span style={{ fontSize: "11px", fontWeight: "700", color: "#ea580c", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                      {idx + 1}. {item.badge}
                    </span>
                  </div>
                  <div style={{ fontSize: "13px", fontWeight: "700", color: "#1e293b", marginBottom: "3px" }}>
                    {item.title}
                  </div>
                  <div style={{ fontSize: "12px", color: "#64748b", lineHeight: "1.4" }}>
                    {item.desc}
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* 4. AUDITED CLAIMS & METRICS (Top High-Value Probes with "View All" Button) */}
          <Card style={{ padding: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px", marginBottom: "16px" }}>
              <div>
                <h3 style={{ fontSize: "17px", fontWeight: "800", color: "#0f172a", display: "flex", alignItems: "center", gap: "8px" }}>
                  <span>🛡️</span> Prioritized High-Value Claims & Metrics
                </h3>
                <p style={{ fontSize: "12px", color: "#64748b", margin: "2px 0 0 0" }}>
                  Top technical claims selected for deep probing during the interview. Full set contains {profile.claims?.length || 0} claims.
                </p>
              </div>

              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowAllClaimsModal(true)}
                style={{ fontWeight: "600", borderColor: "#0284c7", color: "#0369a1" }}
              >
                View All {profile.claims?.length || 0} Claims & Probes →
              </Button>
            </div>

            {topClaims.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {topClaims.map((claim, cIdx) => (
                  <div
                    key={cIdx}
                    style={{
                      padding: "14px 16px",
                      borderRadius: "8px",
                      backgroundColor: "#ffffff",
                      border: "1px solid",
                      borderColor: claim._priority.border,
                      boxShadow: "0 1px 2px rgba(0,0,0,0.02)",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px", marginBottom: "6px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span style={{ fontSize: "11px", fontWeight: "800", color: claim._priority.color, backgroundColor: claim._priority.bg, padding: "2px 8px", borderRadius: "4px", border: `1px solid ${claim._priority.border}` }}>
                          {claim._priority.tier}
                        </span>
                        <Badge variant="neutral" style={{ textTransform: "capitalize", fontSize: "11px" }}>
                          {claim.claim_type}
                        </Badge>
                        {claim.has_metric && (
                          <Badge variant="info" style={{ fontSize: "11px" }}>Quantified Metric</Badge>
                        )}
                        <Badge variant="warning" style={{ fontSize: "11px" }}>Needs Verification</Badge>
                      </div>

                      <span style={{ fontSize: "11px", fontWeight: "700", color: "#64748b" }}>
                        Interview Priority: {Math.round((claim.probe_priority || 0.6) * 100)}%
                      </span>
                    </div>

                    <p style={{ fontSize: "13px", color: "#0f172a", fontWeight: "600", lineHeight: "1.4", margin: "4px 0" }}>
                      "{claim.claim_text}"
                    </p>

                    {claim.reasons && claim.reasons.length > 0 && (
                      <div style={{ fontSize: "11px", color: "#475569", backgroundColor: "#f8fafc", padding: "6px 10px", borderRadius: "4px", marginTop: "4px" }}>
                        <strong>Interview Probe Target:</strong> {claim.reasons.join(" • ")}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: "#94a3b8", fontSize: "13px" }}>No specific technical claims extracted.</p>
            )}

            <div style={{ marginTop: "12px", textAlign: "center" }}>
              <button
                type="button"
                onClick={() => setShowAllClaimsModal(true)}
                style={{
                  background: "none",
                  border: "none",
                  color: "#0284c7",
                  fontSize: "13px",
                  fontWeight: "700",
                  cursor: "pointer",
                  textDecoration: "underline",
                }}
              >
                Expand full catalog ({profile.claims?.length || 0} claims audited)
              </button>
            </div>
          </Card>

          {/* 5. DETAILED ANALYSIS (PROGRESSIVE DISCLOSURE COLLAPSIBLE ACCORDIONS) */}
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <h3 style={{ fontSize: "13px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "0.06em", color: "#64748b", margin: "8px 0 4px 0" }}>
              Detailed Analysis (Progressive Disclosure)
            </h3>

            {/* SECTION A: SKILLS */}
            <Card style={{ padding: "16px 20px" }}>
              <div
                onClick={() => toggleSection("skills")}
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span style={{ fontSize: "16px" }}>⚡</span>
                  <div>
                    <h4 style={{ fontSize: "15px", fontWeight: "700", color: "#0f172a", margin: 0 }}>
                      Extracted Technical Stack & Skills ({profile.skills?.length || 0})
                    </h4>
                    <p style={{ fontSize: "12px", color: "#64748b", margin: "2px 0 0 0" }}>
                      Categorized languages, frameworks, databases, and engineering competencies
                    </p>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "12px", color: "#0284c7", fontWeight: "600" }}>
                    {collapsedSections.skills ? "Show details ▾" : "Hide details ▴"}
                  </span>
                </div>
              </div>

              {!collapsedSections.skills && (
                <div style={{ marginTop: "16px", paddingTop: "14px", borderTop: "1px solid #f1f5f9" }}>
                  {profile.categorized_skills && Object.keys(profile.categorized_skills).length > 0 ? (
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "12px" }}>
                      {Object.entries(profile.categorized_skills).map(([category, items]) => (
                        <div key={category} style={{ padding: "12px", backgroundColor: "#f8fafc", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
                          <div style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", color: "#475569", marginBottom: "8px" }}>
                            {category}
                          </div>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                            {items.map((skill, sIdx) => (
                              <span key={sIdx} style={skillPillStyle}>
                                <TechIcon name={skill} size={14} />
                                {skill}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                      {(profile.skills || []).map((skill, sIdx) => (
                        <span key={sIdx} style={skillPillStyle}>
                          <TechIcon name={skill} size={14} />
                          {skill}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </Card>

            {/* SECTION B: PROJECTS */}
            <Card style={{ padding: "16px 20px" }}>
              <div
                onClick={() => toggleSection("projects")}
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span style={{ fontSize: "16px" }}>🛠️</span>
                  <div>
                    <h4 style={{ fontSize: "15px", fontWeight: "700", color: "#0f172a", margin: 0 }}>
                      Extracted Projects ({profile.projects?.length || 0})
                    </h4>
                    <p style={{ fontSize: "12px", color: "#64748b", margin: "2px 0 0 0" }}>
                      Key technical projects parsed with architecture details and bullet accomplishments
                    </p>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "12px", color: "#0284c7", fontWeight: "600" }}>
                    {collapsedSections.projects ? "Show details ▾" : "Hide details ▴"}
                  </span>
                </div>
              </div>

              {!collapsedSections.projects && (
                <div style={{ marginTop: "16px", paddingTop: "14px", borderTop: "1px solid #f1f5f9", display: "flex", flexDirection: "column", gap: "12px" }}>
                  {profile.projects && profile.projects.length > 0 ? (
                    profile.projects.map((proj, pIdx) => (
                      <div key={pIdx} style={{ padding: "14px", backgroundColor: "#ffffff", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "6px", marginBottom: "6px" }}>
                          <h5 style={{ fontSize: "14px", fontWeight: "700", color: "#0f172a", margin: 0 }}>{proj.title}</h5>
                          {proj.technologies && (
                            <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                              {proj.technologies.map((t, tIdx) => (
                                <Badge key={tIdx} variant="neutral" style={{ fontSize: "10px" }}>{t}</Badge>
                              ))}
                            </div>
                          )}
                        </div>
                        {proj.description && (
                          <p style={{ fontSize: "12px", color: "#475569", margin: "4px 0" }}>{proj.description}</p>
                        )}
                        {proj.bullets && proj.bullets.length > 0 && (
                          <ul style={{ margin: "6px 0 0 16px", padding: 0, fontSize: "12px", color: "#334155" }}>
                            {proj.bullets.map((b, bIdx) => (
                              <li key={bIdx} style={{ marginBottom: "3px" }}>{b}</li>
                            ))}
                          </ul>
                        )}
                        <div style={{ marginTop: "8px", paddingTop: "6px", borderTop: "1px dashed #e2e8f0", fontSize: "11px", color: "#64748b" }}>
                          <strong>Interview Anchor:</strong> Architectural trade-offs, concurrency design, and scalability limits.
                        </div>
                      </div>
                    ))
                  ) : (
                    <p style={{ color: "#94a3b8", fontSize: "13px" }}>No projects section found.</p>
                  )}
                </div>
              )}
            </Card>

            {/* SECTION C: EXPERIENCE */}
            <Card style={{ padding: "16px 20px" }}>
              <div
                onClick={() => toggleSection("experience")}
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span style={{ fontSize: "16px" }}>💼</span>
                  <div>
                    <h4 style={{ fontSize: "15px", fontWeight: "700", color: "#0f172a", margin: 0 }}>
                      Professional Experience
                    </h4>
                    <p style={{ fontSize: "12px", color: "#64748b", margin: "2px 0 0 0" }}>
                      Roles, tenure, company domains, and technical leadership
                    </p>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "12px", color: "#0284c7", fontWeight: "600" }}>
                    {collapsedSections.experience ? "Show details ▾" : "Hide details ▴"}
                  </span>
                </div>
              </div>

              {!collapsedSections.experience && (
                <div style={{ marginTop: "14px", paddingTop: "14px", borderTop: "1px solid #f1f5f9" }}>
                  <div style={{ fontSize: "13px", color: "#334155", lineHeight: "1.6", whiteSpace: "pre-wrap", backgroundColor: "#f8fafc", padding: "12px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
                    {profile.experience || "Experience details extracted from resume."}
                  </div>
                </div>
              )}
            </Card>

            {/* SECTION D: EDUCATION */}
            <Card style={{ padding: "16px 20px" }}>
              <div
                onClick={() => toggleSection("education")}
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span style={{ fontSize: "16px" }}>🎓</span>
                  <div>
                    <h4 style={{ fontSize: "15px", fontWeight: "700", color: "#0f172a", margin: 0 }}>
                      Education & Academic Background
                    </h4>
                    <p style={{ fontSize: "12px", color: "#64748b", margin: "2px 0 0 0" }}>
                      Degrees, institutions, honors, and coursework
                    </p>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "12px", color: "#0284c7", fontWeight: "600" }}>
                    {collapsedSections.education ? "Show details ▾" : "Hide details ▴"}
                  </span>
                </div>
              </div>

              {!collapsedSections.education && (
                <div style={{ marginTop: "14px", paddingTop: "14px", borderTop: "1px solid #f1f5f9" }}>
                  <div style={{ fontSize: "13px", color: "#334155", lineHeight: "1.6", backgroundColor: "#f8fafc", padding: "12px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
                    {profile.education || "Education details extracted from resume."}
                  </div>
                </div>
              )}
            </Card>

            {/* SECTION E: EVALUATION DIMENSIONS & SCORING AUDIT */}
            <Card style={{ padding: "16px 20px" }}>
              <div
                onClick={() => toggleSection("scoring")}
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span style={{ fontSize: "16px" }}>📊</span>
                  <div>
                    <h4 style={{ fontSize: "15px", fontWeight: "700", color: "#0f172a", margin: 0 }}>
                      Evaluation Dimensions & Scoring Audit ({profile.resume_score}/100)
                    </h4>
                    <p style={{ fontSize: "12px", color: "#64748b", margin: "2px 0 0 0" }}>
                      Breakdown of stack coverage, project depth, metrics impact, strengths, and weaknesses
                    </p>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "12px", color: "#0284c7", fontWeight: "600" }}>
                    {collapsedSections.scoring ? "Show details ▾" : "Hide details ▴"}
                  </span>
                </div>
              </div>

              {!collapsedSections.scoring && (
                <div style={{ marginTop: "16px", paddingTop: "14px", borderTop: "1px solid #f1f5f9", display: "flex", flexDirection: "column", gap: "14px" }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    <DimensionRow
                      label="Technical Stack Coverage"
                      score={Math.min(35, Math.round((profile.skills?.length || 0) * 3.5))}
                      maxScore={35}
                      explanation={`${profile.skills?.length || 0} recognized engineering skills identified`}
                    />
                    <DimensionRow
                      label="Experience & Project Depth"
                      score={Math.min(30, 15 + Math.round((profile.claims?.length || 0) * 2.5))}
                      maxScore={30}
                      explanation={`${profile.projects?.length || 0} projects with practical implementation evidence`}
                    />
                    <DimensionRow
                      label="Quantified Impact & Metrics"
                      score={profile.claims?.some((c) => c.has_metric) ? 15 : 5}
                      maxScore={15}
                      explanation={profile.claims?.some((c) => c.has_metric) ? "Contains measurable throughput/accuracy gains" : "Limited numerical performance metrics cited"}
                    />
                    <DimensionRow
                      label="Structural Clarity & Specificity"
                      score={Math.max(5, 15 - (profile.flags?.filter((f) => f.severity === "high" || f.severity === "medium").length || 0) * 3)}
                      maxScore={15}
                      explanation={`${profile.flags?.length || 0} audit flags identified for interview probing`}
                    />
                  </div>

                  {/* STRENGTHS & WEAKNESSES */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "12px", marginTop: "8px" }}>
                    {profile.strengths && profile.strengths.length > 0 && (
                      <div style={{ backgroundColor: "#f0fdf4", padding: "12px", borderRadius: "6px", border: "1px solid #bbf7d0" }}>
                        <div style={{ fontSize: "12px", fontWeight: "700", color: "#166534", marginBottom: "6px" }}>
                          ✓ Key Strengths
                        </div>
                        <ul style={{ listStyle: "none", padding: 0, margin: 0, fontSize: "12px", color: "#166534", display: "flex", flexDirection: "column", gap: "4px" }}>
                          {profile.strengths.map((str, idx) => (
                            <li key={idx}>• {str}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {((profile.weak_areas && profile.weak_areas.length > 0) || (profile.suggested_improvements && profile.suggested_improvements.length > 0)) && (
                      <div style={{ backgroundColor: "#fef2f2", padding: "12px", borderRadius: "6px", border: "1px solid #fecaca" }}>
                        <div style={{ fontSize: "12px", fontWeight: "700", color: "#991b1b", marginBottom: "6px" }}>
                          ⚠ Areas to Strengthen in Interview
                        </div>
                        <ul style={{ listStyle: "none", padding: 0, margin: 0, fontSize: "12px", color: "#991b1b", display: "flex", flexDirection: "column", gap: "4px" }}>
                          {profile.weak_areas?.slice(0, 2).map((w, idx) => (
                            <li key={idx}>• {w}</li>
                          ))}
                          {profile.suggested_improvements?.slice(0, 2).map((imp, idx) => (
                            <li key={`imp-${idx}`}>→ {imp}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </Card>

            {/* SECTION F: SOURCE DOCUMENT PREVIEW */}
            <Card style={{ padding: "16px 20px" }}>
              <div
                onClick={() => toggleSection("sourceDoc")}
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span style={{ fontSize: "16px" }}>📄</span>
                  <div>
                    <h4 style={{ fontSize: "15px", fontWeight: "700", color: "#0f172a", margin: 0 }}>
                      Original Document & Extracted Source
                    </h4>
                    <p style={{ fontSize: "12px", color: "#64748b", margin: "2px 0 0 0" }}>
                      PDF viewer and raw extracted text representation
                    </p>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "12px", color: "#0284c7", fontWeight: "600" }}>
                    {collapsedSections.sourceDoc ? "Show details ▾" : "Hide details ▴"}
                  </span>
                </div>
              </div>

              {!collapsedSections.sourceDoc && (
                <div style={{ marginTop: "14px", paddingTop: "14px", borderTop: "1px solid #f1f5f9" }}>
                  <div style={{ display: "flex", gap: "8px", marginBottom: "10px" }}>
                    <button
                      type="button"
                      onClick={() => setPreviewTab("document")}
                      style={{
                        padding: "4px 10px",
                        fontSize: "12px",
                        borderRadius: "4px",
                        border: "1px solid",
                        borderColor: previewTab === "document" ? "#0f172a" : "#cbd5e1",
                        backgroundColor: previewTab === "document" ? "#0f172a" : "#f8fafc",
                        color: previewTab === "document" ? "#ffffff" : "#475569",
                        cursor: "pointer",
                      }}
                    >
                      Document View
                    </button>
                    <button
                      type="button"
                      onClick={() => setPreviewTab("raw")}
                      style={{
                        padding: "4px 10px",
                        fontSize: "12px",
                        borderRadius: "4px",
                        border: "1px solid",
                        borderColor: previewTab === "raw" ? "#0f172a" : "#cbd5e1",
                        backgroundColor: previewTab === "raw" ? "#0f172a" : "#f8fafc",
                        color: previewTab === "raw" ? "#ffffff" : "#475569",
                        cursor: "pointer",
                      }}
                    >
                      Extracted Text
                    </button>
                  </div>

                  {previewTab === "document" ? (
                    pdfBlobUrl ? (
                      <div style={{ width: "100%", height: "450px", border: "1px solid #cbd5e1", borderRadius: "6px", overflow: "hidden" }}>
                        <iframe src={pdfBlobUrl} title="Resume PDF Preview" style={{ width: "100%", height: "100%", border: "none" }} />
                      </div>
                    ) : (
                      <p style={{ color: "#94a3b8", fontSize: "12px" }}>No PDF binary attached. Text parsing mode active.</p>
                    )
                  ) : (
                    <div style={{ height: "450px", overflowY: "auto", padding: "12px", backgroundColor: "#f8fafc", borderRadius: "6px", border: "1px solid #e2e8f0", fontSize: "12px", fontFamily: "monospace", whiteSpace: "pre-wrap" }}>
                      {profile.raw_text || textInput || "No raw text available."}
                    </div>
                  )}
                </div>
              )}
            </Card>
          </div>

          {/* 6. MODAL: ALL AUDITED CLAIMS & METRICS */}
          {showAllClaimsModal && (
            <div
              style={{
                position: "fixed",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: "rgba(15, 23, 42, 0.65)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 9999,
                padding: "20px",
              }}
              onClick={() => setShowAllClaimsModal(false)}
            >
              <div
                style={{
                  backgroundColor: "#ffffff",
                  borderRadius: "12px",
                  maxWidth: "800px",
                  width: "100%",
                  maxHeight: "85vh",
                  display: "flex",
                  flexDirection: "column",
                  overflow: "hidden",
                  boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
                }}
                onClick={(e) => e.stopPropagation()}
              >
                {/* MODAL HEADER */}
                <div style={{ padding: "18px 22px", borderBottom: "1px solid #e2e8f0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <h3 style={{ fontSize: "18px", fontWeight: "800", color: "#0f172a", margin: 0 }}>
                      All Audited Claims & Metrics ({profile.claims?.length || 0})
                    </h3>
                    <p style={{ fontSize: "12px", color: "#64748b", margin: "2px 0 0 0" }}>
                      Search and filter through the complete catalog of extracted claims
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowAllClaimsModal(false)}
                    style={{ background: "none", border: "none", fontSize: "20px", color: "#94a3b8", cursor: "pointer", padding: "4px 8px" }}
                  >
                    ✕
                  </button>
                </div>

                {/* MODAL FILTER BAR */}
                <div style={{ padding: "12px 22px", backgroundColor: "#f8fafc", borderBottom: "1px solid #e2e8f0", display: "flex", gap: "10px", flexWrap: "wrap", alignItems: "center" }}>
                  <input
                    type="text"
                    placeholder="Search claims or technologies..."
                    value={claimSearchFilter}
                    onChange={(e) => setClaimSearchFilter(e.target.value)}
                    style={{
                      flex: "1",
                      minWidth: "220px",
                      padding: "8px 12px",
                      fontSize: "13px",
                      borderRadius: "6px",
                      border: "1px solid #cbd5e1",
                      outline: "none",
                    }}
                  />
                  <div style={{ display: "flex", gap: "6px" }}>
                    <button
                      type="button"
                      onClick={() => setClaimTierFilter("ALL")}
                      style={{
                        padding: "6px 12px",
                        fontSize: "12px",
                        fontWeight: "600",
                        borderRadius: "6px",
                        border: "1px solid",
                        borderColor: claimTierFilter === "ALL" ? "#0f172a" : "#cbd5e1",
                        backgroundColor: claimTierFilter === "ALL" ? "#0f172a" : "#ffffff",
                        color: claimTierFilter === "ALL" ? "#ffffff" : "#475569",
                        cursor: "pointer",
                      }}
                    >
                      All ({sortedClaims.length})
                    </button>
                    <button
                      type="button"
                      onClick={() => setClaimTierFilter("HIGH")}
                      style={{
                        padding: "6px 12px",
                        fontSize: "12px",
                        fontWeight: "600",
                        borderRadius: "6px",
                        border: "1px solid",
                        borderColor: claimTierFilter === "HIGH" ? "#16a34a" : "#cbd5e1",
                        backgroundColor: claimTierFilter === "HIGH" ? "#16a34a" : "#ffffff",
                        color: claimTierFilter === "HIGH" ? "#ffffff" : "#16a34a",
                        cursor: "pointer",
                      }}
                    >
                      High Value ({sortedClaims.filter((c) => c._priority.tier === "HIGH VALUE").length})
                    </button>
                    <button
                      type="button"
                      onClick={() => setClaimTierFilter("METRIC")}
                      style={{
                        padding: "6px 12px",
                        fontSize: "12px",
                        fontWeight: "600",
                        borderRadius: "6px",
                        border: "1px solid",
                        borderColor: claimTierFilter === "METRIC" ? "#0284c7" : "#cbd5e1",
                        backgroundColor: claimTierFilter === "METRIC" ? "#0284c7" : "#ffffff",
                        color: claimTierFilter === "METRIC" ? "#ffffff" : "#0284c7",
                        cursor: "pointer",
                      }}
                    >
                      With Metrics ({sortedClaims.filter((c) => c.has_metric).length})
                    </button>
                  </div>
                </div>

                {/* MODAL CLAIMS LIST */}
                <div style={{ flex: "1", overflowY: "auto", padding: "16px 22px", display: "flex", flexDirection: "column", gap: "10px" }}>
                  {filteredModalClaims.length > 0 ? (
                    filteredModalClaims.map((claim, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: "12px 14px",
                          borderRadius: "8px",
                          backgroundColor: "#ffffff",
                          border: `1px solid ${claim._priority.border}`,
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <span style={{ fontSize: "10px", fontWeight: "800", color: claim._priority.color, backgroundColor: claim._priority.bg, padding: "2px 6px", borderRadius: "3px" }}>
                              {claim._priority.tier}
                            </span>
                            <Badge variant="neutral" style={{ fontSize: "10px", textTransform: "capitalize" }}>
                              {claim.claim_type}
                            </Badge>
                            {claim.has_metric && <Badge variant="info" style={{ fontSize: "10px" }}>Metric</Badge>}
                          </div>
                          <span style={{ fontSize: "11px", color: "#64748b" }}>
                            Priority: {Math.round((claim.probe_priority || 0.5) * 100)}%
                          </span>
                        </div>
                        <p style={{ fontSize: "13px", color: "#1e293b", margin: "4px 0", lineHeight: "1.4" }}>
                          "{claim.claim_text}"
                        </p>
                        {claim.reasons && claim.reasons.length > 0 && (
                          <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
                            <strong>Probe:</strong> {claim.reasons.join(" • ")}
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div style={{ textAlign: "center", padding: "40px 20px", color: "#94a3b8" }}>
                      No claims match current filter criteria.
                    </div>
                  )}
                </div>

                {/* MODAL FOOTER */}
                <div style={{ padding: "12px 22px", borderTop: "1px solid #e2e8f0", display: "flex", justifyContent: "flex-end" }}>
                  <Button variant="secondary" size="sm" onClick={() => setShowAllClaimsModal(false)}>
                    Close
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* 7. FINAL ACTION BANNER */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "20px 24px",
              backgroundColor: "#ffffff",
              borderRadius: "10px",
              border: "1px solid #e2e8f0",
              boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)",
              flexWrap: "wrap",
              gap: "16px",
            }}
          >
            <div>
              <h4 style={{ fontSize: "16px", fontWeight: "700", color: "#0f172a", margin: 0 }}>
                Ready to practice with this verified resume profile?
              </h4>
              <p style={{ fontSize: "12px", color: "#64748b", margin: "2px 0 0 0" }}>
                Begin your adaptive interview session anchored directly to your projects and claims.
              </p>
            </div>

            <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              <Button variant="secondary" size="md" onClick={handleReset}>
                Upload Different Resume
              </Button>
              <Button variant="primary" size="lg" onClick={handleProceedToInterview}>
                Start Interview Now →
              </Button>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}

// Subcomponent for Explainable Score Rows
function DimensionRow({ label, score, maxScore, explanation }) {
  const pct = Math.round((score / maxScore) * 100);
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", marginBottom: "4px" }}>
        <span style={{ fontWeight: "600", color: "#1e293b" }}>{label}</span>
        <span style={{ fontWeight: "700", color: "#475569" }}>{score} / {maxScore}</span>
      </div>
      <div style={{ width: "100%", height: "6px", backgroundColor: "#e2e8f0", borderRadius: "3px", overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", backgroundColor: pct >= 75 ? "#16a34a" : pct >= 50 ? "#d97706" : "#dc2626", borderRadius: "3px" }} />
      </div>
      <span style={{ fontSize: "11px", color: "#64748b", marginTop: "2px", display: "block" }}>
        {explanation}
      </span>
    </div>
  );
}

// STYLES
const snapshotCard = {
  backgroundColor: "#ffffff",
  padding: "16px 20px",
  borderRadius: "8px",
  border: "1px solid #e2e8f0",
  boxShadow: "0 1px 2px rgba(0,0,0,0.03)",
};

const snapshotLabel = {
  fontSize: "11px",
  fontWeight: "700",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  color: "#64748b",
  display: "block",
  marginBottom: "4px",
};

const snapshotValue = {
  fontSize: "18px",
  fontWeight: "800",
  color: "#0f172a",
};

const snapshotSub = {
  fontSize: "12px",
  color: "#94a3b8",
  marginTop: "2px",
  display: "block",
};

const skillPillStyle = {
  padding: "4px 10px",
  backgroundColor: "var(--bg-subtle, #eff6ff)",
  color: "var(--text-primary, #1e40af)",
  borderRadius: "16px",
  fontSize: "12px",
  fontWeight: "600",
  border: "1px solid var(--border-default, #dbeafe)",
  display: "inline-flex",
  alignItems: "center",
  gap: "6px",
};

const shapingCard = {
  backgroundColor: "#1e293b",
  padding: "16px",
  borderRadius: "8px",
  border: "1px solid #334155",
};

const shapingIcon = {
  fontSize: "20px",
  marginBottom: "8px",
};

const shapingTitle = {
  fontSize: "14px",
  fontWeight: "700",
  color: "#f8fafc",
  marginBottom: "4px",
};

const shapingDesc = {
  fontSize: "12px",
  color: "#cbd5e1",
  lineHeight: "1.5",
};
const glanceCard = {
  backgroundColor: "#f8fafc",
  padding: "14px 16px",
  borderRadius: "8px",
  border: "1px solid #e2e8f0",
};

const glanceValue = {
  fontSize: "16px",
  fontWeight: "800",
  color: "#0f172a",
};
