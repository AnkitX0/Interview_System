import React, { useState, useContext, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { ReportContext } from "../context/ReportContext";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../utils/api";
import { Card, CardHeader } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";

function InterviewSetup() {
  const navigate = useNavigate();
  const location = useLocation();
  const { resumeData, setCurrentSessionId } = useContext(ReportContext);
  const { user } = useAuth();

  const [mode, setMode] = useState("technical");
  const [difficulty, setDifficulty] = useState("medium");
  const [questionCount, setQuestionCount] = useState(3);
  const [targetRole, setTargetRole] = useState(user?.profile?.target_role || "Software Engineer");
  const [mediaPreference, setMediaPreference] = useState("standard"); // "standard" (mic/camera) | "text_only"
  const [hardwareChecked, setHardwareChecked] = useState(false);
  const [isCheckingMedia, setIsCheckingMedia] = useState(false);
  const [loadingStart, setLoadingStart] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [pressureAcknowledged, setPressureAcknowledged] = useState(false);

  // Privacy consent tracking
  const [consentStatus, setConsentStatus] = useState("loading"); // "loading" | "granted" | "declined" | "unspecified"
  const [showConsentModal, setShowConsentModal] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);

  useEffect(() => {
    apiFetch("/consent")
      .then((res) => (res.ok ? res.json() : []))
      .then((records) => {
        const camMicRecord = records.find(
          (r) => r.consent_type === "camera_mic_processing" && (r.policy_version === "2.0" || r.policy_version === "v2.0")
        );
        if (camMicRecord) {
          setConsentStatus(camMicRecord.granted ? "granted" : "declined");
          if (!camMicRecord.granted) {
            setMediaPreference("text_only");
          }
        } else {
          setConsentStatus("unspecified");
        }
      })
      .catch(() => setConsentStatus("unspecified"));
  }, []);

  // Pre-fill preferences from authenticated user profile
  useEffect(() => {
    if (user?.profile?.target_role) {
      setTargetRole(user.profile.target_role);
    }
    if (user?.profile?.preferred_difficulty) {
      setDifficulty(user.profile.preferred_difficulty);
    }
  }, [user]);

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
      id: "technical",
      title: "Technical Interview",
      desc: "System design, architectural decisions, database choices, and trade-offs.",
    },
    {
      id: "practice",
      title: "Comprehensive Practice",
      desc: "Balanced coverage across technical competencies, communication structure, and delivery.",
    },
    {
      id: "hr",
      title: "Behavioral & Situational",
      desc: "Past project challenges, teamwork, leadership, and structured STAR scenarios.",
    },
    {
      id: "pressure",
      title: "Incident Response",
      desc: "Challenging live incident postmortems, production failure recovery, and 45s timers.",
    },
  ];

  const difficulties = [
    { id: "easy", label: "Introductory" },
    { id: "medium", label: "Standard (Mid-Level)" },
    { id: "hard", label: "Advanced (Senior)" },
  ];

  const runHardwareCheck = async () => {
    setIsCheckingMedia(true);
    setErrorMessage(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      stream.getTracks().forEach((track) => track.stop());
      setHardwareChecked(true);
    } catch (err) {
      console.warn("Hardware test notification:", err);
      setErrorMessage("Camera or microphone access was not granted. You can practice in Text-Only mode.");
      setMediaPreference("text_only");
    } finally {
      setIsCheckingMedia(false);
    }
  };

  const handleTestHardware = async () => {
    if (consentStatus === "unspecified") {
      setPendingAction("check");
      setShowConsentModal(true);
      return;
    }
    runHardwareCheck();
  };

  const handleGrantConsent = async () => {
    try {
      await apiFetch("/consent", {
        method: "POST",
        body: JSON.stringify({
          consent_type: "camera_mic_processing",
          granted: true,
          policy_version: "2.0",
        }),
      });
    } catch (e) {
      console.warn("Consent persist notice:", e);
    }
    setConsentStatus("granted");
    setShowConsentModal(false);
    if (pendingAction === "check") {
      runHardwareCheck();
    } else if (pendingAction === "start") {
      executeStart(mediaPreference === "text_only");
    }
  };

  const handleDeclineConsent = async () => {
    try {
      await apiFetch("/consent", {
        method: "POST",
        body: JSON.stringify({
          consent_type: "camera_mic_processing",
          granted: false,
          policy_version: "2.0",
        }),
      });
    } catch (e) {
      console.warn("Consent persist notice:", e);
    }
    setConsentStatus("declined");
    setMediaPreference("text_only");
    setShowConsentModal(false);
    if (pendingAction === "start") {
      executeStart(true);
    }
  };

  const handleStart = async () => {
    if (mode === "pressure" && !pressureAcknowledged) {
      setErrorMessage("Please acknowledge the Incident Response notice below before continuing.");
      return;
    }
    if (mediaPreference === "standard" && consentStatus === "unspecified") {
      setPendingAction("start");
      setShowConsentModal(true);
      return;
    }
    executeStart(mediaPreference === "text_only" || consentStatus === "declined");
  };

  const executeStart = async (isTextOnly = false) => {
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

      const res = await apiFetch("/interview/start", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`Failed to initialize session: status ${res.status}`);
      }

      const session = await res.json();
      setCurrentSessionId(session.session_id);

      sessionStorage.setItem("interviewCompleted", "false");
      sessionStorage.setItem(
        "interviewSetupState",
        JSON.stringify({
          sessionId: session.session_id,
          mode,
          difficulty,
          targetRole,
          questions: session.questions,
          questionCount: session.questions.length,
          textOnly: isTextOnly,
        })
      );

      navigate("/interview", {
        state: {
          sessionId: session.session_id,
          mode,
          difficulty,
          targetRole,
          questions: session.questions,
          questionCount: session.questions.length,
          textOnly: isTextOnly,
        },
      });
    } catch (err) {
      console.error("Start interview error:", err);
      setErrorMessage("Could not start interview session. Please check your connection and try again.");
    } finally {
      setLoadingStart(false);
    }
  };

  const selectedModeObj = modes.find((m) => m.id === mode) || modes[0];
  const estimatedMins = questionCount * 3;

  return (
    <div className="container" style={{ maxWidth: "860px" }}>
      {/* Title */}
      <div style={{ marginBottom: "28px" }}>
        <h1 style={{ fontSize: "26px", fontWeight: "700", color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
          Interview Setup
        </h1>
        <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginTop: "4px" }}>
          Configure your target role, round format, and preferences before beginning.
        </p>
      </div>

      {errorMessage && (
        <div className="alert alert-danger" style={{ marginBottom: "20px" }}>
          {errorMessage}
        </div>
      )}

      {/* Resume Attached Banner */}
      {activeResume && (
        <div
          style={{
            backgroundColor: "var(--primary-50)",
            border: "1px solid var(--primary-200)",
            borderRadius: "var(--radius-md)",
            padding: "12px 16px",
            marginBottom: "24px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div>
            <div style={{ fontSize: "13px", fontWeight: "600", color: "var(--primary-900)" }}>
              Attached Resume: {activeResume.candidate_name || "Candidate"}
            </div>
            <div style={{ fontSize: "12px", color: "var(--primary-700)", marginTop: "2px" }}>
              Questions will be anchored to your experience and resume claims.
            </div>
          </div>
          <Badge variant="info">Resume Active</Badge>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "20px" }}>
        {/* Step 1: Target Role */}
        <Card>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label" style={{ fontWeight: "600" }}>
              Target Job Title
            </label>
            <input
              type="text"
              className="form-input"
              value={targetRole}
              onChange={(e) => setTargetRole(e.target.value)}
              placeholder="e.g. Backend Engineer, Full Stack Developer, Systems Engineer"
            />
            <span className="form-hint">
              Used to calibrate question relevance and domain concepts.
            </span>
          </div>
        </Card>

        {/* Step 2: Interview Type */}
        <Card>
          <label className="form-label" style={{ fontWeight: "600", marginBottom: "12px" }}>
            Interview Type
          </label>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
              gap: "12px",
            }}
          >
            {modes.map((m) => {
              const isSelected = mode === m.id;
              return (
                <div
                  key={m.id}
                  onClick={() => setMode(m.id)}
                  style={{
                    padding: "14px 16px",
                    borderRadius: "var(--radius-md)",
                    border: isSelected ? "2px solid var(--slate-900)" : "1px solid var(--border-default)",
                    backgroundColor: isSelected ? "var(--slate-50)" : "#ffffff",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                    <div style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-primary)" }}>
                      {m.title}
                    </div>
                    {isSelected && <Badge variant="neutral">Selected</Badge>}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: "1.4" }}>
                    {m.desc}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Incident / Pressure Mode notice */}
          {mode === "pressure" && (
            <div
              style={{
                marginTop: "16px",
                padding: "14px",
                backgroundColor: "var(--warning-bg)",
                border: "1px solid var(--warning-border)",
                borderRadius: "var(--radius-md)",
              }}
            >
              <div style={{ fontSize: "13px", fontWeight: "600", color: "var(--warning-text)", marginBottom: "4px" }}>
                Incident Response Notice
              </div>
              <p style={{ fontSize: "12px", color: "#78350f", lineHeight: "1.5", marginBottom: "10px" }}>
                Simulates real-world urgent troubleshooting with strict 45-second response timers. You can switch back to standard timing at any time without penalty.
              </p>
              <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", color: "#78350f", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={pressureAcknowledged}
                  onChange={(e) => setPressureAcknowledged(e.target.checked)}
                />
                <span>I understand this mode simulates fast-paced incident reasoning with 45s timers.</span>
              </label>
            </div>
          )}
        </Card>

        {/* Step 3: Difficulty & Length */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "20px" }}>
          <Card>
            <label className="form-label" style={{ fontWeight: "600", marginBottom: "10px" }}>
              Difficulty Level
            </label>
            <div style={{ display: "flex", gap: "8px" }}>
              {difficulties.map((d) => (
                <button
                  key={d.id}
                  type="button"
                  onClick={() => setDifficulty(d.id)}
                  style={{
                    flex: 1,
                    padding: "8px 10px",
                    borderRadius: "var(--radius-md)",
                    border: difficulty === d.id ? "1px solid var(--slate-900)" : "1px solid var(--border-default)",
                    backgroundColor: difficulty === d.id ? "var(--slate-900)" : "var(--bg-surface)",
                    color: difficulty === d.id ? "var(--text-inverse)" : "var(--text-secondary)",
                    fontSize: "12px",
                    fontWeight: "600",
                    cursor: "pointer",
                  }}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </Card>

          <Card>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <label className="form-label" style={{ fontWeight: "600", margin: 0 }}>
                Question Count
              </label>
              <span style={{ fontSize: "13px", fontWeight: "700", color: "var(--text-primary)" }}>
                {questionCount} questions (~{estimatedMins} min)
              </span>
            </div>
            <input
              type="range"
              min="2"
              max="6"
              value={questionCount}
              onChange={(e) => setQuestionCount(Number(e.target.value))}
              style={{ width: "100%", marginTop: "8px" }}
            />
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
              <span>2 (Brief)</span>
              <span>4 (Standard)</span>
              <span>6 (Comprehensive)</span>
            </div>
          </Card>
        </div>

        {/* Step 4: Hardware & Input Mode */}
        <Card>
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "16px" }}>
            <div>
              <div style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-primary)", marginBottom: "4px" }}>
                Input & Hardware Preference
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                {mediaPreference === "standard"
                  ? "Standard: Camera for alignment framing and microphone for speech transcription."
                  : "Text-Only: Camera and microphone are completely disabled. Type your responses."}
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <button
                type="button"
                onClick={() => setMediaPreference(mediaPreference === "standard" ? "text_only" : "standard")}
                style={{
                  padding: "6px 12px",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border-default)",
                  backgroundColor: "var(--slate-100)",
                  fontSize: "12px",
                  fontWeight: "500",
                  cursor: "pointer",
                }}
              >
                Switch to {mediaPreference === "standard" ? "Text-Only" : "Standard Audio/Video"}
              </button>

              {mediaPreference === "standard" && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleTestHardware}
                  loading={isCheckingMedia}
                >
                  {hardwareChecked ? "Hardware Ready ✓" : "Test Camera & Mic"}
                </Button>
              )}
            </div>
          </div>
        </Card>

        {/* Summary Card & Start Action */}
        <Card
          style={{
            backgroundColor: "var(--slate-50)",
            borderColor: "var(--slate-300)",
            padding: "20px 24px",
          }}
        >
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "16px" }}>
            <div>
              <div style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-muted)", fontWeight: "600", marginBottom: "4px" }}>
                Interview Summary
              </div>
              <div style={{ fontSize: "16px", fontWeight: "700", color: "var(--text-primary)" }}>
                {selectedModeObj.title} · {targetRole}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
                {difficulty.toUpperCase()} difficulty · {questionCount} questions · ~{estimatedMins} minutes · {mediaPreference === "standard" ? "Audio/Video" : "Text-Only"}
              </div>
            </div>

            <div>
              <Button
                variant="primary"
                size="lg"
                onClick={handleStart}
                loading={loadingStart}
              >
                Start Interview →
              </Button>
            </div>
          </div>
        </Card>
      </div>

      {/* Sensor Privacy Consent Modal */}
      {showConsentModal && (
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
        >
          <div
            style={{
              backgroundColor: "#ffffff",
              borderRadius: "var(--radius-lg)",
              maxWidth: "520px",
              width: "100%",
              padding: "24px",
              boxShadow: "var(--shadow-lg)",
            }}
          >
            <h3 style={{ fontSize: "18px", fontWeight: "700", color: "var(--text-primary)", marginBottom: "8px" }}>
              Sensor Processing & Privacy
            </h3>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.6", marginBottom: "14px" }}>
              To practice with natural speech and camera framing, please review our sensor policies:
            </p>
            <ul style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.5", paddingLeft: "18px", marginBottom: "20px", display: "flex", flexDirection: "column", gap: "6px" }}>
              <li>
                <strong>Video:</strong> Frames are analyzed locally in your browser for camera positioning. Video is never uploaded or stored.
              </li>
              <li>
                <strong>Audio:</strong> Spoken answers use your browser’s speech service. Only transcribed text is evaluated.
              </li>
              <li>
                <strong>Alternative:</strong> You can decline and practice in Text-Only mode at any time.
              </li>
            </ul>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <Button variant="secondary" onClick={handleDeclineConsent}>
                Use Text-Only Mode
              </Button>
              <Button variant="primary" onClick={handleGrantConsent}>
                Enable Audio & Video
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default InterviewSetup;