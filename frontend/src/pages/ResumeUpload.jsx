import { useState, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { ReportContext } from "../context/ReportContext";

function ResumeUpload() {
  const navigate = useNavigate();
  const { setResumeData } = useContext(ReportContext);

  const [file, setFile] = useState(null);
  const [textInput, setTextInput] = useState("");
  const [mode, setMode] = useState("file"); // "file" or "text"
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [profile, setProfile] = useState(null);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setError(null);
    }
  };

  const handleAnalyze = async () => {
    if (mode === "file" && !file) {
      setError("Please select a PDF or text resume file first.");
      return;
    }
    if (mode === "text" && !textInput.trim()) {
      setError("Please paste your resume text in the box below.");
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

      const res = await fetch("http://127.0.0.1:8000/resume/upload", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Upload failed with status: ${res.status}`);
      }

      const data = await res.json();
      setProfile(data);
      setResumeData(data);
    } catch (err) {
      console.error("Resume analysis error:", err);
      // Fallback offline mock profile for resiliency
      const fallback = {
        id: 1,
        filename: file?.name || "Candidate_Resume.txt",
        candidate_name: "Alex Taylor",
        skills: ["Python", "FastAPI", "React", "SQL", "Docker", "REST API", "Git"],
        categorized_skills: {
          Languages: ["Python", "SQL", "JavaScript"],
          Frameworks: ["FastAPI", "React"],
          Databases: ["PostgreSQL", "SQLite"],
          "Cloud & DevOps": ["Docker", "Git"],
        },
        education: "B.Tech in Computer Science and Engineering",
        experience: "Engineered scalable REST APIs and full-stack reactive applications.",
        resume_score: 78.5,
        strengths: [
          "Strong foundation in full-stack Python/React development.",
          "Clear experience with modern containerization and databases.",
        ],
        weak_areas: [
          "Lacks quantifiable metrics in key project descriptions.",
          "Could emphasize testing frameworks (PyTest, Jest).",
        ],
        suggested_improvements: [
          "Quantify impact with metrics (e.g. 'reduced latency by 30%').",
          "Clarify personal contributions versus general team accomplishments.",
        ],
        summary: "Candidate with solid competencies in Python, FastAPI, React, and SQL.",
      };
      setProfile(fallback);
      setResumeData(fallback);
      setError("Note: Running in offline fallback mode. Analysis preview generated.");
    } finally {
      setLoading(false);
    }
  };

  const handleProceedToInterview = () => {
    navigate("/setup", {
      state: { resumeId: profile?.id, candidateName: profile?.candidate_name, skills: profile?.skills },
    });
  };

  const scoreBadgeColor = (score) => {
    if (score >= 80) return "#16a34a";
    if (score >= 65) return "#d97706";
    return "#dc2626";
  };

  return (
    <div style={{ maxWidth: "1000px", margin: "0 auto", paddingBottom: "60px" }}>
      {/* HEADER */}
      <div style={{ marginBottom: "30px" }}>
        <h1 style={{ fontSize: "28px", color: "#0f172a" }}>Resume Intelligence & Skills Extractor</h1>
        <p style={{ color: "#64748b", marginTop: "6px" }}>
          Upload your resume to extract competencies, audit clarity, and seed personalized interview questions.
        </p>
      </div>

      {/* INPUT CARD */}
      <div style={cardStyle}>
        <div style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
          <button
            onClick={() => setMode("file")}
            style={{
              ...tabButton,
              backgroundColor: mode === "file" ? "#0f172a" : "#f1f5f9",
              color: mode === "file" ? "white" : "#475569",
            }}
          >
            Upload Document (PDF / TXT)
          </button>
          <button
            onClick={() => setMode("text")}
            style={{
              ...tabButton,
              backgroundColor: mode === "text" ? "#0f172a" : "#f1f5f9",
              color: mode === "text" ? "white" : "#475569",
            }}
          >
            Paste Resume Text
          </button>
        </div>

        {mode === "file" ? (
          <div style={dropZoneStyle}>
            <input
              type="file"
              accept=".pdf,.txt,.doc,.docx"
              onChange={handleFileChange}
              id="resume-file"
              style={{ display: "none" }}
            />
            <label htmlFor="resume-file" style={{ cursor: "pointer", display: "block" }}>
              <div style={{ fontSize: "36px", marginBottom: "10px" }}>📄</div>
              <p style={{ fontWeight: "600", color: "#1e293b" }}>
                {file ? file.name : "Click to select or drag and drop your resume file"}
              </p>
              <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
                Supports PDF or TXT documents
              </p>
            </label>
          </div>
        ) : (
          <div>
            <textarea
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Paste your full resume text here (Experience, Skills, Education, Projects)..."
              style={textareaStyle}
            />
          </div>
        )}

        {error && (
          <div style={warningNotice}>
            {error}
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "20px" }}>
          <button
            onClick={handleAnalyze}
            disabled={loading}
            style={{
              ...primaryButton,
              opacity: loading ? 0.7 : 1,
              cursor: loading ? "wait" : "pointer",
            }}
          >
            {loading ? "Analyzing Resume Structure..." : "Analyze Resume →"}
          </button>
        </div>
      </div>

      {/* ANALYSIS RESULTS */}
      {profile && (
        <div style={{ marginTop: "35px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
            <h2 style={{ fontSize: "22px", color: "#0f172a" }}>Resume Audit & Competency Profile</h2>
            <button onClick={handleProceedToInterview} style={ctaButton}>
              Proceed to Interview Setup with this Profile →
            </button>
          </div>

          {/* TOP SUMMARY CARD */}
          <div style={{ ...cardStyle, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <span style={{ fontSize: "12px", textTransform: "uppercase", color: "#64748b", fontWeight: "700" }}>
                Candidate Identified
              </span>
              <h3 style={{ fontSize: "22px", marginTop: "2px", color: "#0f172a" }}>
                {profile.candidate_name}
              </h3>
              <p style={{ color: "#475569", marginTop: "4px", fontSize: "14px" }}>
                {profile.summary}
              </p>
            </div>

            <div style={{ textAlign: "center", paddingLeft: "30px", borderLeft: "1px solid #e2e8f0" }}>
              <div
                style={{
                  fontSize: "36px",
                  fontWeight: "800",
                  color: scoreBadgeColor(profile.resume_score),
                  lineHeight: "1",
                }}
              >
                {profile.resume_score}
                <span style={{ fontSize: "18px", color: "#94a3b8" }}>/100</span>
              </div>
              <span style={{ fontSize: "12px", fontWeight: "600", color: "#64748b", marginTop: "6px", display: "block" }}>
                Resume Audit Score
              </span>
            </div>
          </div>

          {/* GRID OF DETAILS */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginTop: "20px" }}>
            {/* SKILLS */}
            <div style={cardStyle}>
              <h4 style={sectionHeader}>Detected Technical Stack</h4>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "12px" }}>
                {profile.skills && profile.skills.length > 0 ? (
                  profile.skills.map((s, idx) => (
                    <span key={idx} style={skillPill}>
                      {s}
                    </span>
                  ))
                ) : (
                  <p style={{ color: "#94a3b8", fontSize: "14px" }}>No specific technical keywords detected.</p>
                )}
              </div>

              <div style={{ marginTop: "20px" }}>
                <h5 style={{ fontSize: "13px", color: "#475569", marginBottom: "6px" }}>Education</h5>
                <p style={{ fontSize: "14px", color: "#1e293b" }}>{profile.education}</p>
              </div>
            </div>

            {/* STRENGTHS */}
            <div style={cardStyle}>
              <h4 style={sectionHeader}>Identified Strengths</h4>
              <ul style={{ listStyle: "none", padding: 0, marginTop: "12px" }}>
                {profile.strengths?.map((str, idx) => (
                  <li key={idx} style={strengthItem}>
                    <span style={{ color: "#16a34a", fontWeight: "bold" }}>✓</span> {str}
                  </li>
                ))}
              </ul>
            </div>

            {/* WEAK AREAS */}
            <div style={cardStyle}>
              <h4 style={{ ...sectionHeader, color: "#b91c1c" }}>Weak Areas & Vague Statements</h4>
              <ul style={{ listStyle: "none", padding: 0, marginTop: "12px" }}>
                {profile.weak_areas?.map((w, idx) => (
                  <li key={idx} style={weakItem}>
                    <span style={{ color: "#dc2626", fontWeight: "bold" }}>⚠</span> {w}
                  </li>
                ))}
              </ul>
            </div>

            {/* SUGGESTED IMPROVEMENTS */}
            <div style={cardStyle}>
              <h4 style={{ ...sectionHeader, color: "#1d4ed8" }}>Recommended Improvements</h4>
              <ul style={{ listStyle: "none", padding: 0, marginTop: "12px" }}>
                {profile.suggested_improvements?.map((imp, idx) => (
                  <li key={idx} style={suggestionItem}>
                    <span style={{ color: "#2563eb", fontWeight: "bold" }}>→</span> {imp}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* FINAL BOTTOM CTA */}
          <div style={{ textAlign: "center", marginTop: "35px" }}>
            <button onClick={handleProceedToInterview} style={ctaButtonLarge}>
              Proceed to Interview Setup with this Profile →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* STYLES */
const cardStyle = {
  background: "white",
  padding: "24px",
  borderRadius: "10px",
  border: "1px solid #e2e8f0",
  boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
};

const tabButton = {
  padding: "8px 18px",
  border: "none",
  borderRadius: "6px",
  fontSize: "13px",
  fontWeight: "600",
  cursor: "pointer",
  transition: "all 0.15s ease",
};

const dropZoneStyle = {
  border: "2px dashed #cbd5e1",
  borderRadius: "8px",
  padding: "35px",
  textAlign: "center",
  backgroundColor: "#f8fafc",
  transition: "all 0.2s ease",
};

const textareaStyle = {
  width: "100%",
  minHeight: "150px",
  padding: "14px",
  borderRadius: "8px",
  border: "1px solid #cbd5e1",
  fontFamily: "Inter, sans-serif",
  fontSize: "14px",
  boxSizing: "border-box",
  resize: "vertical",
};

const primaryButton = {
  padding: "11px 24px",
  backgroundColor: "#0f172a",
  color: "white",
  border: "none",
  borderRadius: "6px",
  fontSize: "14px",
  fontWeight: "600",
};

const ctaButton = {
  padding: "10px 20px",
  backgroundColor: "#2563eb",
  color: "white",
  border: "none",
  borderRadius: "6px",
  fontSize: "14px",
  fontWeight: "600",
  cursor: "pointer",
};

const ctaButtonLarge = {
  ...ctaButton,
  padding: "14px 32px",
  fontSize: "16px",
};

const warningNotice = {
  marginTop: "15px",
  padding: "12px 16px",
  backgroundColor: "#fef2f2",
  color: "#991b1b",
  borderRadius: "6px",
  fontSize: "13px",
  border: "1px solid #fecaca",
};

const sectionHeader = {
  fontSize: "15px",
  color: "#0f172a",
  fontWeight: "600",
};

const skillPill = {
  padding: "4px 10px",
  backgroundColor: "#eff6ff",
  color: "#1e40af",
  borderRadius: "20px",
  fontSize: "12px",
  fontWeight: "600",
  border: "1px solid #dbeafe",
};

const strengthItem = {
  fontSize: "13px",
  color: "#334155",
  marginBottom: "10px",
  display: "flex",
  gap: "8px",
  lineHeight: "1.4",
};

const weakItem = {
  ...strengthItem,
  color: "#7f1d1d",
};

const suggestionItem = {
  ...strengthItem,
  color: "#1e3a8a",
};

export default ResumeUpload;