import { useState, useContext, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { ReportContext } from "../context/ReportContext";
import { apiFetch } from "../utils/api";
import { Card, CardHeader } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";

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
  const [previewTab, setPreviewTab] = useState("document"); // "document" or "raw"

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
    } catch (err) {
      console.error("Resume analysis error:", err);
      setError(err.message || "Failed to analyze document. Please check the file and try again.");
    } finally {
      setLoading(false);
    }
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

        {profile && (
          <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
            <Button variant="secondary" size="md" onClick={handleReset}>
              Analyze Another Document
            </Button>
            <Button variant="primary" size="md" onClick={handleProceedToInterview}>
              Start Interview with this Profile →
            </Button>
          </div>
        )}
      </div>

      {/* DOCUMENT UPLOAD / INPUT CARD (Shown when no profile, or as collapsible edit) */}
      {!profile && (
        <Card style={{ marginBottom: "32px", padding: "28px", border: "1px solid #e2e8f0" }}>
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
                  borderColor: mode === "file" ? "#0f172a" : "#cbd5e1",
                  backgroundColor: mode === "file" ? "#0f172a" : "#f8fafc",
                  color: mode === "file" ? "#ffffff" : "#475569",
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
                  borderColor: mode === "text" ? "#0f172a" : "#cbd5e1",
                  backgroundColor: mode === "text" ? "#0f172a" : "#f8fafc",
                  color: mode === "text" ? "#ffffff" : "#475569",
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
            <div
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: "2px dashed #cbd5e1",
                borderRadius: "10px",
                padding: "40px 20px",
                textAlign: "center",
                backgroundColor: "#f8fafc",
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
              <p style={{ fontWeight: "600", fontSize: "16px", color: "#1e293b", marginBottom: "4px" }}>
                {file ? file.name : "Click to select or drag and drop your resume"}
              </p>
              <p style={{ fontSize: "13px", color: "#64748b" }}>
                Supports PDF or TXT documents (Max 10MB)
              </p>
              {file && (
                <div style={{ marginTop: "12px" }}>
                  <Badge variant="info">Selected: {(file.size / 1024).toFixed(1)} KB</Badge>
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
                  border: "1px solid #cbd5e1",
                  fontFamily: "var(--font-family-sans, inherit)",
                  fontSize: "14px",
                  lineHeight: "1.6",
                  color: "#1e293b",
                  resize: "vertical",
                  backgroundColor: "#ffffff",
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
            <div style={{ marginTop: "24px", padding: "20px", backgroundColor: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
                <span style={{ display: "inline-block", width: "16px", height: "16px", border: "2px solid #2563eb", borderRightColor: "transparent", borderRadius: "50%", animation: "spin 0.6s linear infinite" }} />
                <strong style={{ fontSize: "14px", color: "#0f172a" }}>Analyzing your resume structure...</strong>
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
                Analyze Resume Intelligence →
              </Button>
            </div>
          )}
        </Card>
      )}

      {/* FULL RESUME INTELLIGENCE REPORT VIEW */}
      {profile && (
        <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>

          {/* 1. CANDIDATE SNAPSHOT BAR */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "14px",
            }}
          >
            <div style={snapshotCard}>
              <span style={snapshotLabel}>Candidate</span>
              <div style={snapshotValue}>{profile.candidate_name || "Candidate"}</div>
              <span style={snapshotSub}>
                {profile.role_fit_scores && Object.keys(profile.role_fit_scores).length > 0
                  ? `Best Fit: ${Object.keys(profile.role_fit_scores)[0]}`
                  : "Target Engineering Role"}
              </span>
            </div>

            <div style={snapshotCard}>
              <span style={snapshotLabel}>Technical Stack</span>
              <div style={snapshotValue}>{profile.skills ? `${profile.skills.length} Skills` : "Not available"}</div>
              <span style={snapshotSub}>Extracted from document</span>
            </div>

            <div style={snapshotCard}>
              <span style={snapshotLabel}>Projects Extracted</span>
              <div style={snapshotValue}>{profile.projects ? `${profile.projects.length} Projects` : "Not available"}</div>
              <span style={snapshotSub}>Available for interview defense</span>
            </div>

            <div style={snapshotCard}>
              <span style={snapshotLabel}>Audited Claims</span>
              <div style={snapshotValue}>{profile.claims ? `${profile.claims.length} Claims` : "Not available"}</div>
              <span style={snapshotSub}>Subject to interview verification</span>
            </div>
          </div>

          {/* 2. SPLIT ROW: RESUME PREVIEW (LEFT) + RESUME HEALTH & ANALYSIS (RIGHT) */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(460px, 1fr))",
              gap: "24px",
              alignItems: "stretch",
            }}
          >
            {/* LEFT: RESUME DOCUMENT PREVIEW PANEL */}
            <Card style={{ padding: "20px", display: "flex", flexDirection: "column", minHeight: "560px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", paddingBottom: "12px", borderBottom: "1px solid #e2e8f0" }}>
                <div>
                  <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#0f172a" }}>Resume Document Preview</h3>
                  <p style={{ fontSize: "12px", color: "#64748b" }}>
                    Source document analyzed by the intelligence engine
                  </p>
                </div>

                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
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

                  {pdfBlobUrl && (
                    <a
                      href={pdfBlobUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        padding: "4px 10px",
                        fontSize: "12px",
                        borderRadius: "4px",
                        backgroundColor: "#eff6ff",
                        color: "#1d4ed8",
                        border: "1px solid #bfdbfe",
                        fontWeight: "500",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "4px",
                      }}
                    >
                      Open Full ↗
                    </a>
                  )}
                </div>
              </div>

              {/* VIEWER CONTENT */}
              <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
                {previewTab === "document" && pdfBlobUrl ? (
                  <div style={{ flex: 1, minHeight: "480px", borderRadius: "8px", overflow: "hidden", border: "1px solid #cbd5e1" }}>
                    <object
                      data={pdfBlobUrl}
                      type="application/pdf"
                      width="100%"
                      height="100%"
                      style={{ minHeight: "480px", display: "block" }}
                    >
                      <iframe
                        src={pdfBlobUrl}
                        width="100%"
                        height="480px"
                        title="Resume Preview"
                        style={{ border: "none" }}
                      />
                    </object>
                  </div>
                ) : (
                  <div
                    style={{
                      flex: 1,
                      maxHeight: "500px",
                      overflowY: "auto",
                      backgroundColor: "#f8fafc",
                      padding: "20px",
                      borderRadius: "8px",
                      border: "1px solid #e2e8f0",
                      fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                      fontSize: "13px",
                      lineHeight: "1.6",
                      color: "#334155",
                      whiteSpace: "pre-wrap",
                      boxShadow: "inset 0 1px 3px rgba(0,0,0,0.03)",
                    }}
                  >
                    {profile.raw_text || textInput || "Document text extracted successfully."}
                  </div>
                )}
              </div>
            </Card>

            {/* RIGHT: RESUME HEALTH & ANALYSIS PANEL */}
            <Card style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "20px" }}>
              {/* SCORE HEADER */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: "16px", borderBottom: "1px solid #e2e8f0" }}>
                <div>
                  <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#0f172a" }}>Resume Audit Assessment</h3>
                  <p style={{ fontSize: "12px", color: "#64748b" }}>
                    Synthesized readiness and clarity audit
                  </p>
                </div>

                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "32px", fontWeight: "800", color: getScoreColor(profile.resume_score), lineHeight: "1" }}>
                    {profile.resume_score}
                    <span style={{ fontSize: "16px", color: "#94a3b8", fontWeight: "500" }}> / 100</span>
                  </div>
                  <Badge variant={profile.resume_score >= 80 ? "success" : profile.resume_score >= 65 ? "warning" : "danger"} style={{ marginTop: "4px" }}>
                    {getScoreLabel(profile.resume_score)}
                  </Badge>
                </div>
              </div>

              {/* EXPLAINABLE SCORE BREAKDOWN */}
              <div>
                <h4 style={{ fontSize: "13px", fontWeight: "700", color: "#475569", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "12px" }}>
                  Evaluation Dimensions
                </h4>
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
                    explanation={profile.claims?.some((c) => c.has_metric) ? "Contains measurable throughput/latency gains" : "Limited numerical performance metrics cited"}
                  />
                  <DimensionRow
                    label="Structural Clarity & Specificity"
                    score={Math.max(5, 15 - (profile.flags?.filter((f) => f.severity === "high" || f.severity === "medium").length || 0) * 3)}
                    maxScore={15}
                    explanation={`${profile.flags?.length || 0} audit flags identified for interview probing`}
                  />
                </div>
              </div>

              {/* KEY STRENGTHS */}
              {profile.strengths && profile.strengths.length > 0 && (
                <div style={{ paddingTop: "14px", borderTop: "1px solid #f1f5f9" }}>
                  <h4 style={{ fontSize: "13px", fontWeight: "700", color: "#166534", marginBottom: "8px", display: "flex", alignItems: "center", gap: "6px" }}>
                    <span>✓</span> Key Strengths
                  </h4>
                  <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "6px" }}>
                    {profile.strengths.map((str, idx) => (
                      <li key={idx} style={{ fontSize: "13px", color: "#334155", display: "flex", gap: "8px", lineHeight: "1.4" }}>
                        <span style={{ color: "#16a34a", fontWeight: "bold" }}>•</span> {str}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* AREAS TO IMPROVE */}
              {((profile.weak_areas && profile.weak_areas.length > 0) || (profile.suggested_improvements && profile.suggested_improvements.length > 0)) && (
                <div style={{ paddingTop: "14px", borderTop: "1px solid #f1f5f9" }}>
                  <h4 style={{ fontSize: "13px", fontWeight: "700", color: "#991b1b", marginBottom: "8px", display: "flex", alignItems: "center", gap: "6px" }}>
                    <span>⚠</span> Areas to Strengthen
                  </h4>
                  <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "6px" }}>
                    {profile.weak_areas?.slice(0, 2).map((w, idx) => (
                      <li key={idx} style={{ fontSize: "13px", color: "#7f1d1d", display: "flex", gap: "8px", lineHeight: "1.4" }}>
                        <span style={{ color: "#dc2626", fontWeight: "bold" }}>•</span> {w}
                      </li>
                    ))}
                    {profile.suggested_improvements?.slice(0, 2).map((imp, idx) => (
                      <li key={`imp-${idx}`} style={{ fontSize: "13px", color: "#1e40af", display: "flex", gap: "8px", lineHeight: "1.4" }}>
                        <span style={{ color: "#2563eb", fontWeight: "bold" }}>→</span> {imp}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
          </div>

          {/* 3. SKILLS & TECHNOLOGIES GROUPED BY CATEGORY */}
          <Card style={{ padding: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div>
                <h3 style={{ fontSize: "18px", fontWeight: "700", color: "#0f172a" }}>Skills & Competency Clusters</h3>
                <p style={{ fontSize: "13px", color: "#64748b" }}>
                  Classified against core engineering frameworks and databases
                </p>
              </div>
              <Badge variant="neutral">{profile.skills?.length || 0} Total Skills</Badge>
            </div>

            {profile.categorized_skills && Object.keys(profile.categorized_skills).length > 0 ? (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
                {Object.entries(profile.categorized_skills).map(([category, items]) => (
                  <div key={category} style={{ padding: "16px", backgroundColor: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                    <div style={{ fontSize: "12px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.04em", color: "#475569", marginBottom: "10px" }}>
                      {category}
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                      {items.map((skill, sIdx) => (
                        <span key={sIdx} style={skillPillStyle}>
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : profile.skills && profile.skills.length > 0 ? (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                {profile.skills.map((skill, sIdx) => (
                  <span key={sIdx} style={skillPillStyle}>
                    {skill}
                  </span>
                ))}
              </div>
            ) : (
              <p style={{ color: "#94a3b8", fontSize: "14px" }}>No specific technical skills extracted.</p>
            )}
          </Card>

          {/* 4. EXTRACTED PROJECTS & ARCHITECTURAL ACCOMPLISHMENTS */}
          <Card style={{ padding: "24px" }}>
            <div style={{ marginBottom: "16px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: "700", color: "#0f172a" }}>Extracted Projects</h3>
              <p style={{ fontSize: "13px", color: "#64748b" }}>
                Key technical accomplishments identified for interview defense ladders
              </p>
            </div>

            {profile.projects && profile.projects.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                {profile.projects.map((proj, pIdx) => (
                  <div key={pIdx} style={{ padding: "18px", backgroundColor: "#ffffff", borderRadius: "8px", border: "1px solid #e2e8f0", boxShadow: "0 1px 2px rgba(0,0,0,0.03)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "8px", marginBottom: "8px" }}>
                      <h4 style={{ fontSize: "16px", fontWeight: "700", color: "#0f172a" }}>{proj.title}</h4>
                      {proj.technologies && proj.technologies.length > 0 && (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                          {proj.technologies.map((t, tIdx) => (
                            <Badge key={tIdx} variant="neutral" style={{ fontSize: "11px" }}>{t}</Badge>
                          ))}
                        </div>
                      )}
                    </div>

                    {proj.description && (
                      <p style={{ fontSize: "13px", color: "#475569", marginBottom: "8px" }}>{proj.description}</p>
                    )}

                    {proj.bullets && proj.bullets.length > 0 && (
                      <ul style={{ margin: "8px 0 0 18px", padding: 0, fontSize: "13px", color: "#334155", lineHeight: "1.5" }}>
                        {proj.bullets.map((b, bIdx) => (
                          <li key={bIdx} style={{ marginBottom: "4px" }}>{b}</li>
                        ))}
                      </ul>
                    )}

                    <div style={{ marginTop: "12px", paddingTop: "10px", borderTop: "1px dashed #e2e8f0", fontSize: "12px", color: "#64748b", display: "flex", gap: "14px" }}>
                      <span><strong>Interview Focus:</strong> Architectural Trade-offs & Concurrency</span>
                      <span>•</span>
                      <span><strong>Verification Target:</strong> Deliverable Ownership</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: "#94a3b8", fontSize: "14px" }}>No dedicated projects section parsed from document.</p>
            )}
          </Card>

          {/* 5. EXPERIENCE & EDUCATION */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: "20px" }}>
            <Card style={{ padding: "20px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#0f172a", marginBottom: "12px" }}>Experience Overview</h3>
              <div style={{ fontSize: "13px", color: "#334155", lineHeight: "1.6", whiteSpace: "pre-wrap", backgroundColor: "#f8fafc", padding: "14px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
                {profile.experience || "Experience details extracted from resume."}
              </div>
            </Card>

            <Card style={{ padding: "20px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#0f172a", marginBottom: "12px" }}>Education & Academic Background</h3>
              <div style={{ fontSize: "13px", color: "#334155", lineHeight: "1.6", backgroundColor: "#f8fafc", padding: "14px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
                {profile.education || "Education details extracted from resume."}
              </div>
            </Card>
          </div>

          {/* 6. RESUME CLAIMS & INTERVIEW VERIFICATION STATUS */}
          <Card style={{ padding: "24px" }}>
            <div style={{ marginBottom: "16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                <h3 style={{ fontSize: "18px", fontWeight: "700", color: "#0f172a" }}>Resume Claims & Verification Priorities</h3>
                <Badge variant="warning">{profile.claims?.length || 0} Identified Claims</Badge>
              </div>
              <p style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>
                Statements declared in your resume. Verification is not granted on text alone; each claim enters the interview in a "Needs Verification" state and must be substantiated during questioning.
              </p>
            </div>

            {profile.claims && profile.claims.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {profile.claims.slice(0, 8).map((claim, cIdx) => (
                  <div
                    key={cIdx}
                    style={{
                      padding: "16px",
                      borderRadius: "8px",
                      backgroundColor: "#ffffff",
                      border: "1px solid #e2e8f0",
                      display: "flex",
                      flexDirection: "column",
                      gap: "8px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "8px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <Badge variant="neutral" style={{ textTransform: "capitalize", fontSize: "11px" }}>
                          {claim.claim_type} Claim
                        </Badge>
                        <Badge variant="warning" style={{ fontSize: "11px" }}>
                          Needs Verification
                        </Badge>
                        {claim.has_metric && (
                          <Badge variant="info" style={{ fontSize: "11px" }}>Quantified Metric</Badge>
                        )}
                      </div>

                      <span style={{ fontSize: "12px", fontWeight: "700", color: claim.probe_priority >= 0.75 ? "#c2410c" : "#0369a1" }}>
                        Probe Priority: {Math.round((claim.probe_priority || 0.5) * 100)}%
                      </span>
                    </div>

                    <p style={{ fontSize: "13px", color: "#1e293b", fontWeight: "500", lineHeight: "1.4" }}>
                      "{claim.claim_text}"
                    </p>

                    {claim.reasons && claim.reasons.length > 0 && (
                      <div style={{ fontSize: "12px", color: "#64748b", backgroundColor: "#f8fafc", padding: "8px 12px", borderRadius: "6px" }}>
                        <strong>Interview Reason:</strong> {claim.reasons.join(" • ")}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: "#94a3b8", fontSize: "14px" }}>No specific technical claims extracted.</p>
            )}
          </Card>

          {/* 7. HOW YOUR RESUME WILL SHAPE THE INTERVIEW (PART 6) */}
          <Card style={{ padding: "26px", backgroundColor: "#0f172a", color: "#ffffff", border: "none" }}>
            <div style={{ marginBottom: "18px" }}>
              <span style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.06em", color: "#93c5fd" }}>
                Interview Calibration
              </span>
              <h3 style={{ fontSize: "20px", fontWeight: "800", color: "#ffffff", marginTop: "2px" }}>
                How Your Resume Shapes The Interview Experience
              </h3>
              <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
                Our adaptive interviewer anchors questions directly to your declared experience and projects.
              </p>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
              <div style={shapingCard}>
                <div style={shapingIcon}>🛡️</div>
                <h4 style={shapingTitle}>Project Architecture Defense</h4>
                <p style={shapingDesc}>
                  Questions will examine design choices in your projects, probing concurrency limits, failure recovery, and architectural alternatives.
                </p>
              </div>

              <div style={shapingCard}>
                <div style={shapingIcon}>🔍</div>
                <h4 style={shapingTitle}>Skill Competency Verification</h4>
                <p style={shapingDesc}>
                  Technologies like {profile.skills?.slice(0, 3).join(", ") || "core tools"} will be tested for deep operational understanding beyond surface syntax.
                </p>
              </div>

              <div style={shapingCard}>
                <div style={shapingIcon}>📈</div>
                <h4 style={shapingTitle}>Metric & Scale Probing</h4>
                <p style={shapingDesc}>
                  Quantified gains cited in your claims will trigger follow-ups requesting the profiling methodology and before-and-after benchmarks.
                </p>
              </div>

              <div style={shapingCard}>
                <div style={shapingIcon}>🪜</div>
                <h4 style={shapingTitle}>Adaptive Probe Ladders</h4>
                <p style={shapingDesc}>
                  Strong answers escalate to edge cases; shallow answers trigger targeted probing to help you substantiate technical depth.
                </p>
              </div>
            </div>
          </Card>

          {/* 8. FINAL ACTION BANNER */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "24px 28px",
              backgroundColor: "#ffffff",
              borderRadius: "10px",
              border: "1px solid #e2e8f0",
              boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)",
              flexWrap: "wrap",
              gap: "16px",
            }}
          >
            <div>
              <h4 style={{ fontSize: "17px", fontWeight: "700", color: "#0f172a" }}>
                Ready to practice with this verified resume profile?
              </h4>
              <p style={{ fontSize: "13px", color: "#64748b", marginTop: "2px" }}>
                Configure rounds, select difficulty, and begin your adaptive mock interview.
              </p>
            </div>

            <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
              <Button variant="secondary" size="lg" onClick={handleReset}>
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
  backgroundColor: "#eff6ff",
  color: "#1e40af",
  borderRadius: "16px",
  fontSize: "12px",
  fontWeight: "600",
  border: "1px solid #dbeafe",
  display: "inline-block",
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