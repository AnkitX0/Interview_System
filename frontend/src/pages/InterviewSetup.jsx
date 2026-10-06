import { useState, useContext, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { ReportContext } from "../context/ReportContext";
import { API_BASE_URL } from "../config";

function InterviewSetup() {
  const navigate = useNavigate();
  const location = useLocation();
  const { resumeData, setCurrentSessionId } = useContext(ReportContext);

  const [mode, setMode] = useState("technical");
  const [difficulty, setDifficulty] = useState("medium");
  const [questionCount, setQuestionCount] = useState(3);
  const [targetRole, setTargetRole] = useState("Software Engineer");
  const [systemReady, setSystemReady] = useState(false);
  const [isCheckingMedia, setIsCheckingMedia] = useState(false);
  const [loadingStart, setLoadingStart] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  // Resume profile if passed from Resume page or context
  const activeResume = location.state?.resumeId
    ? {
        id: location.state.resumeId,
        candidate_name: location.state.candidateName,
        skills: location.state.skills,
      }
    : resumeData;

  const modes = [
    {
      id: "practice",
      title: "Practice Mode",
      desc: "Balanced feedback across technical, communication, and behavioral dimensions.",
    },
    {
      id: "technical",
      title: "Technical Round",
      desc: "Architecture, engineering tradeoffs, database design, and concepts.",
    },
    {
      id: "hr",
      title: "HR & Behavioral",
      desc: "STAR-driven behavioral questions, leadership scenarios, and team culture.",
    },
    {
      id: "pressure",
      title: "Pressure & Incident",
      desc: "Challenging live scenarios, production failure postmortems, and tough tradeoffs.",
    },
  ];

  const difficulties = ["easy", "medium", "hard"];

  const handleSystemCheck = async () => {
    setIsCheckingMedia(true);
    setErrorMessage(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      // Release tracks right away
      stream.getTracks().forEach((track) => track.stop());
      setSystemReady(true);
    } catch (err) {
      console.warn("Media permissions not granted:", err);
      setErrorMessage("Camera/mic access was not granted. You can still proceed in text/standard mode!");
      // Allow proceeding regardless
      setSystemReady(true);
    } finally {
      setIsCheckingMedia(false);
    }
  };

  const handleStart = async () => {
    setLoadingStart(true);
    setErrorMessage(null);

    try {
      const payload = {
        mode,
        difficulty,
        number_of_questions: questionCount,
        resume_id: activeResume?.id || null,
        target_role: targetRole,
      };

      const res = await fetch(`${API_BASE_URL}/interview/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`Failed to initialize session: status ${res.status}`);
      }

      const session = await res.json();
      setCurrentSessionId(session.session_id);

      // Save state in sessionStorage for page refreshes
      sessionStorage.setItem("interviewCompleted", "false");
      sessionStorage.setItem("interviewSetupState", JSON.stringify({
        sessionId: session.session_id,
        mode,
        difficulty,
        targetRole,
        questions: session.questions,
        questionCount: session.questions.length,
      }));

      navigate("/interview", {
        state: {
          sessionId: session.session_id,
          mode,
          difficulty,
          targetRole,
          questions: session.questions,
          questionCount: session.questions.length,
        },
      });
    } catch (err) {
      console.error("Start interview error:", err);
      // Fallback local session if backend unreachable
      const fallbackQuestions = [
        { id: 1, question: "Explain REST API architecture and how HTTP status codes are utilized." },
        { id: 2, question: "Describe a challenging technical problem you solved in your past project." },
        { id: 3, question: "How do you handle database indexing and optimize slow queries?" },
      ].slice(0, questionCount);

      const fallbackSessionId = Date.now();
      setCurrentSessionId(fallbackSessionId);

      sessionStorage.setItem("interviewSetupState", JSON.stringify({
        sessionId: fallbackSessionId,
        mode,
        difficulty,
        targetRole,
        questions: fallbackQuestions,
        questionCount,
      }));

      navigate("/interview", {
        state: {
          sessionId: fallbackSessionId,
          mode,
          difficulty,
          targetRole,
          questions: fallbackQuestions,
          questionCount,
        },
      });
    } finally {
      setLoadingStart(false);
    }
  };

  const estimatedMinutes = (questionCount * 2.0).toFixed(0);

  return (
    <div style={{ maxWidth: "900px", margin: "0 auto", paddingBottom: "60px" }}>
      {/* HEADER */}
      <div>
        <h1 style={{ fontSize: "28px", color: "#0f172a" }}>Configure Mock Interview Session</h1>
        <p style={{ color: "#64748b", marginTop: "6px" }}>
          Tailor question difficulty, interview focus, and target role benchmarks before beginning.
        </p>
      </div>

      {/* RESUME PROFILE BANNER */}
      {activeResume && (
        <div style={resumeBanner}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "20px" }}>👤</span>
            <div>
              <strong>Profile Attached: {activeResume.candidate_name || "Candidate"}</strong>
              <div style={{ fontSize: "12px", color: "#1e3a8a", marginTop: "2px" }}>
                Skills: {Array.isArray(activeResume.skills) ? activeResume.skills.slice(0, 6).join(", ") : "Detected competencies"}
              </div>
            </div>
          </div>
          <span style={tailoredBadge}>Resume-Aware Questions Enabled</span>
        </div>
      )}

      {/* TARGET ROLE */}
      <div style={{ ...cardStyle, marginTop: "25px" }}>
        <h3 style={sectionHeader}>Target Job Title</h3>
        <input
          type="text"
          value={targetRole}
          onChange={(e) => setTargetRole(e.target.value)}
          placeholder="e.g. Software Engineer, Full Stack Developer, Backend Specialist"
          style={inputStyle}
        />
      </div>

      {/* MODE SELECTION */}
      <div style={{ ...cardStyle, marginTop: "20px" }}>
        <h3 style={sectionHeader}>Select Interview Mode</h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px", marginTop: "14px" }}>
          {modes.map((m) => {
            const isSelected = mode === m.id;
            return (
              <div
                key={m.id}
                onClick={() => setMode(m.id)}
                style={{
                  ...modeOptionCard,
                  borderColor: isSelected ? "#2563eb" : "#e2e8f0",
                  backgroundColor: isSelected ? "#eff6ff" : "white",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h4 style={{ fontSize: "15px", color: isSelected ? "#1e40af" : "#0f172a" }}>{m.title}</h4>
                  {isSelected && <span style={{ color: "#2563eb", fontWeight: "bold" }}>●</span>}
                </div>
                <p style={{ fontSize: "13px", color: "#64748b", marginTop: "6px", lineHeight: "1.4" }}>{m.desc}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* DIFFICULTY */}
      <div style={{ ...cardStyle, marginTop: "20px" }}>
        <h3 style={sectionHeader}>Select Difficulty</h3>
        <div style={{ display: "flex", gap: "12px", marginTop: "14px" }}>
          {difficulties.map((d) => {
            const isSelected = difficulty === d;
            return (
              <button
                key={d}
                onClick={() => setDifficulty(d)}
                style={{
                  ...difficultyPill,
                  backgroundColor: isSelected ? "#0f172a" : "#f1f5f9",
                  color: isSelected ? "white" : "#475569",
                  border: isSelected ? "1px solid #0f172a" : "1px solid #e2e8f0",
                }}
              >
                {d.toUpperCase()}
              </button>
            );
          })}
        </div>
      </div>

      {/* QUESTION COUNT */}
      <div style={{ ...cardStyle, marginTop: "20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={sectionHeader}>Number of Questions</h3>
          <span style={{ fontSize: "16px", fontWeight: "700", color: "#0f172a" }}>
            {questionCount} Questions (~{estimatedMinutes} mins)
          </span>
        </div>
        <input
          type="range"
          min="1"
          max="5"
          value={questionCount}
          onChange={(e) => setQuestionCount(Number(e.target.value))}
          style={{ width: "100%", marginTop: "14px" }}
        />
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>
          <span>1 (Quick Test)</span>
          <span>3 (Standard Round)</span>
          <span>5 (Full Assessment)</span>
        </div>
      </div>

      {/* HARDWARE PRE-CHECK */}
      <div style={{ ...cardStyle, marginTop: "20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h3 style={sectionHeader}>Hardware & Behavior Check (Optional)</h3>
            <p style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>
              Enable webcam and microphone for eye contact and speech analytics, or proceed directly in text mode.
            </p>
          </div>

          <button
            onClick={handleSystemCheck}
            disabled={isCheckingMedia}
            style={{
              ...checkButton,
              backgroundColor: systemReady ? "#16a34a" : "#0f172a",
            }}
          >
            {isCheckingMedia ? "Testing Hardware..." : systemReady ? "Hardware Checked ✓" : "Test Camera & Mic"}
          </button>
        </div>

        {errorMessage && (
          <p style={{ fontSize: "12px", color: "#b91c1c", marginTop: "10px" }}>
            {errorMessage}
          </p>
        )}
      </div>

      {/* START INTERVIEW CTA */}
      <div style={{ textAlign: "center", marginTop: "35px" }}>
        <button
          onClick={handleStart}
          disabled={loadingStart}
          style={{
            ...startInterviewButton,
            opacity: loadingStart ? 0.7 : 1,
            cursor: loadingStart ? "wait" : "pointer",
          }}
        >
          {loadingStart ? "Initializing AI Interview Room..." : "Begin Mock Interview →"}
        </button>
      </div>
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

const sectionHeader = {
  fontSize: "15px",
  color: "#0f172a",
  fontWeight: "600",
};

const inputStyle = {
  width: "100%",
  padding: "10px 14px",
  borderRadius: "6px",
  border: "1px solid #cbd5e1",
  marginTop: "10px",
  fontSize: "14px",
  boxSizing: "border-box",
};

const resumeBanner = {
  backgroundColor: "#eff6ff",
  border: "1px solid #bfdbfe",
  borderRadius: "8px",
  padding: "14px 20px",
  marginTop: "20px",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

const tailoredBadge = {
  fontSize: "11px",
  fontWeight: "700",
  color: "#1d4ed8",
  backgroundColor: "#dbeafe",
  padding: "4px 10px",
  borderRadius: "12px",
  textTransform: "uppercase",
  letterSpacing: "0.03em",
};

const modeOptionCard = {
  padding: "16px",
  borderRadius: "8px",
  border: "1px solid",
  cursor: "pointer",
  transition: "all 0.15s ease",
};

const difficultyPill = {
  padding: "8px 22px",
  borderRadius: "20px",
  fontSize: "13px",
  fontWeight: "600",
  cursor: "pointer",
  transition: "all 0.15s ease",
};

const checkButton = {
  padding: "9px 18px",
  borderRadius: "6px",
  color: "white",
  border: "none",
  fontSize: "13px",
  fontWeight: "600",
  cursor: "pointer",
};

const startInterviewButton = {
  padding: "14px 36px",
  backgroundColor: "#0f172a",
  color: "white",
  border: "none",
  borderRadius: "8px",
  fontSize: "16px",
  fontWeight: "600",
  cursor: "pointer",
  boxShadow: "0 4px 12px rgba(15, 23, 42, 0.15)",
};

export default InterviewSetup;