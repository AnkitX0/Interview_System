import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../utils/api";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Skeleton } from "../components/ui/Skeleton";

const DRILL_CATALOG = [
  {
    type: "TECHNICAL_DEPTH",
    title: "Technical Deep Dive",
    subtitle: "Architecture & System Mechanics",
    icon: "⚙",
    description: "Master system mechanics, database concurrency, memory management, and scaling limits with deep technical precision.",
    defaultQuestions: 5,
    estimatedMinutes: 10,
    badge: "Architecture & Systems",
    badgeVariant: "neutral",
  },
  {
    type: "TRADEOFF_REASONING",
    title: "Trade-off Reasoning",
    subtitle: "Comparative Architectural Choices",
    icon: "⚖",
    description: "Defend engineering choices under real constraints: relational vs document models, sync vs async messaging, and caching trade-offs.",
    defaultQuestions: 5,
    estimatedMinutes: 10,
    badge: "Architectural Decisions",
    badgeVariant: "info",
  },
  {
    type: "FOLLOWUP_DEFENSE",
    title: "Follow-up & Probe Defense",
    subtitle: "Handling Pressure & Edge Cases",
    icon: "↳",
    description: "Strengthen how you respond when interviewers probe deeper into failure modes, cache stampedes, and 10x traffic spikes.",
    defaultQuestions: 5,
    estimatedMinutes: 10,
    badge: "Interview Pressure",
    badgeVariant: "info",
  },
  {
    type: "PROJECT_DEFENSE",
    title: "Project & Claim Defense",
    subtitle: "Resume-Grounded Evidence",
    icon: "▣",
    description: "Defend projects, frameworks, and architecture claims directly cited on your resume with authentic personal ownership.",
    defaultQuestions: 5,
    estimatedMinutes: 10,
    badge: "Resume & Projects",
    badgeVariant: "info",
  },
  {
    type: "STRUCTURED_ANSWER",
    title: "Structured Communication",
    subtitle: "Context, Action & Impact",
    icon: "Aa",
    description: "Sharpen verbal delivery using structured frameworks. Deliver concise 90-second technical briefings without rambling.",
    defaultQuestions: 5,
    estimatedMinutes: 8,
    badge: "Answer Structure",
    badgeVariant: "neutral",
  },
  {
    type: "BEHAVIORAL_STAR",
    title: "Behavioral Scenarios",
    subtitle: "STAR Method Practice",
    icon: "◎",
    description: "Master STAR scenarios: architectural disagreements, production outages under your watch, and team mentoring.",
    defaultQuestions: 5,
    estimatedMinutes: 10,
    badge: "Real Situations",
    badgeVariant: "neutral",
  },
  {
    type: "PRESSURE_RESPONSE",
    title: "High-Urgency Pressure Practice",
    subtitle: "45-Second Incident Response",
    icon: "◷",
    description: "Simulate live production incident triage, database locks, and outage recovery with strict 45-second answer timers.",
    defaultQuestions: 5,
    estimatedMinutes: 8,
    badge: "Fast Decisions",
    badgeVariant: "warning",
  },
];

function Practice() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [recommendations, setRecommendations] = useState([]);
  const [progressData, setProgressData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [launchingType, setLaunchingType] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const [recsRes, progRes] = await Promise.all([
          apiFetch("/practice/recommendations"),
          apiFetch("/analytics/progress"),
        ]);

        if (recsRes.ok) {
          const recsData = await recsRes.json();
          setRecommendations(Array.isArray(recsData) ? recsData : []);
        }
        if (progRes.ok) {
          const prog = await progRes.json();
          setProgressData(prog);
        }
      } catch (err) {
        console.error("Failed to load practice hub data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const handleStartDrill = async (drillType, count = 5) => {
    setLaunchingType(drillType);
    setError(null);
    try {
      const res = await apiFetch("/practice/start", {
        method: "POST",
        body: JSON.stringify({
          practice_type: drillType,
          target_role: user?.profile?.target_role || "Software Engineer",
          difficulty: user?.profile?.preferred_difficulty || "medium",
          question_count: count,
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData?.error?.message || errData?.detail || "Could not launch practice drill.");
      }

      const sessionData = await res.json();
      navigate("/interview", {
        state: {
          sessionId: sessionData.session_id,
          isPractice: true,
          practiceType: drillType,
        },
      });
    } catch (err) {
      setError(err.message || "Failed to start practice session. Please try again.");
      setLaunchingType(null);
    }
  };

  const primaryRec = recommendations.length > 0 ? recommendations[0] : null;

  return (
    <div style={{ maxWidth: "1080px", margin: "0 auto", padding: "0 16px 80px 16px" }}>
      {/* Header: Study Style */}
      <div style={{ marginBottom: "28px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
          <span style={{ fontSize: "12px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--primary-700)" }}>
            Study · Practice · Improve
          </span>
          <Badge variant="info">Targeted Drills</Badge>
        </div>
        <h1 style={{ fontSize: "28px", fontWeight: "800", color: "#0f172a", letterSpacing: "-0.02em" }}>
          Your Interview Practice
        </h1>
        <p style={{ fontSize: "14px", color: "#64748b", marginTop: "4px" }}>
          Build stronger answers one session at a time. Each drill targets a specific cognitive dimension with dedicated question pools.
        </p>
      </div>

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: "20px" }}>
          {error}
        </div>
      )}

      {/* TODAY'S FOCUS HERO */}
      {loading ? (
        <Skeleton height="180px" borderRadius="var(--radius-lg)" style={{ marginBottom: "32px" }} />
      ) : primaryRec ? (
        <Card
          style={{
            marginBottom: "32px",
            backgroundColor: "#f8fafc",
            borderColor: "#cbd5e1",
            padding: "24px 28px",
            borderLeft: "4px solid #3b82f6",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.06em", color: "#2563eb" }}>
                Today's Focus
              </span>
              <Badge variant={primaryRec.decision_metadata?.rule === "no_active_weakness_fallback" ? "info" : "warning"}>
                {primaryRec.decision_metadata?.rule === "no_active_weakness_fallback" ? "Mastery Focus" : `Priority ${primaryRec.priority || 1}`}
              </Badge>
            </div>
            <span style={{ fontSize: "12px", color: "#64748b" }}>
              Calibrated from recent session performance
            </span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "24px", alignItems: "center" }}>
            <div>
              <h2 style={{ fontSize: "20px", fontWeight: "700", color: "#0f172a", marginBottom: "8px" }}>
                {primaryRec.drill_title || primaryRec.practice_type?.replace(/_/g, " ")}
              </h2>
              <p style={{ fontSize: "14px", color: "#334155", lineHeight: "1.5", marginBottom: "12px", maxWidth: "680px" }}>
                {primaryRec.rationale || "Practice answering focused technical follow-ups with concrete implementation details."}
              </p>
              <div style={{ display: "flex", gap: "14px", fontSize: "12px", color: "#64748b" }}>
                <span>{primaryRec.target_count || 5} questions</span>
                <span>·</span>
                <span>~10 minutes</span>
                {primaryRec.dimension && (
                  <>
                    <span>·</span>
                    <span style={{ color: "#2563eb", fontWeight: "600" }}>
                      Target: {primaryRec.dimension.toUpperCase()}
                    </span>
                  </>
                )}
              </div>
            </div>

            <div>
              <Button
                variant="primary"
                size="lg"
                onClick={() => handleStartDrill(primaryRec.practice_type, primaryRec.target_count || 5)}
                loading={launchingType === primaryRec.practice_type}
              >
                Start Practice →
              </Button>
            </div>
          </div>
        </Card>
      ) : null}

      {/* COMPACT LEARNING PROGRESS SECTION */}
      <div style={{ marginBottom: "32px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
          <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#0f172a" }}>
            Interview Skill Mastery
          </h3>
          <span style={{ fontSize: "12px", color: "#64748b" }}>
            {progressData?.total_interviews ? `${progressData.total_interviews} sessions completed` : "No sessions recorded"}
          </span>
        </div>

        {progressData && progressData.total_interviews > 0 ? (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "14px",
            }}
          >
            {[
              { label: "Technical Depth", score: Math.round(progressData.latest_score ? (progressData.sessions?.[progressData.sessions.length - 1]?.technical_score || progressData.latest_score) : 0) },
              { label: "Structured Communication", score: Math.round(progressData.latest_score ? (progressData.sessions?.[progressData.sessions.length - 1]?.communication_score || progressData.latest_score) : 0) },
              { label: "Behavioral & STAR", score: Math.round(progressData.latest_score ? (progressData.sessions?.[progressData.sessions.length - 1]?.behavioral_score || progressData.latest_score) : 0) },
              { label: "Overall Preparation", score: Math.round(progressData.latest_score || 0) },
            ].map((skill, idx) => (
              <div
                key={idx}
                style={{
                  padding: "14px 16px",
                  borderRadius: "8px",
                  backgroundColor: "#ffffff",
                  border: "1px solid #e2e8f0",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <span style={{ fontSize: "12px", color: "#64748b", fontWeight: "500" }}>{skill.label}</span>
                  <span style={{ fontSize: "14px", fontWeight: "700", color: "#0f172a" }}>{skill.score}/100</span>
                </div>
                <div style={{ height: "6px", backgroundColor: "#f1f5f9", borderRadius: "3px", overflow: "hidden" }}>
                  <div
                    style={{
                      height: "100%",
                      width: `${Math.min(100, Math.max(0, skill.score))}%`,
                      backgroundColor: skill.score >= 75 ? "#16a34a" : skill.score >= 60 ? "#3b82f6" : "#f59e0b",
                      borderRadius: "3px",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div
            style={{
              padding: "16px 20px",
              borderRadius: "8px",
              backgroundColor: "#f8fafc",
              border: "1px dashed #cbd5e1",
              fontSize: "13px",
              color: "#64748b",
            }}
          >
            No practice history yet. Complete a targeted drill or mock interview to track longitudinal skill progress.
          </div>
        )}
      </div>

      {/* PRACTICE LIBRARY */}
      <div style={{ marginBottom: "16px" }}>
        <h3 style={{ fontSize: "18px", fontWeight: "700", color: "#0f172a", marginBottom: "4px" }}>
          Practice Library
        </h3>
        <p style={{ fontSize: "13px", color: "#64748b" }}>
          Select a dedicated curriculum module to drill specific interview competencies.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "20px",
        }}
      >
        {DRILL_CATALOG.map((drill) => {
          const isCurrentLoading = launchingType === drill.type;
          return (
            <Card
              key={drill.type}
              style={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                padding: "22px",
                border: "1px solid #e2e8f0",
                transition: "box-shadow 0.2s ease",
              }}
            >
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontSize: "16px", fontWeight: "700", color: "#3b82f6" }}>{drill.icon}</span>
                    <Badge variant={drill.badgeVariant}>{drill.badge}</Badge>
                  </div>
                  <span style={{ fontSize: "11px", color: "#64748b" }}>
                    {drill.defaultQuestions} questions · ~{drill.estimatedMinutes}m
                  </span>
                </div>

                <h4 style={{ fontSize: "16px", fontWeight: "700", color: "#0f172a", marginBottom: "4px" }}>
                  {drill.title}
                </h4>
                <div style={{ fontSize: "12px", fontWeight: "500", color: "#64748b", marginBottom: "10px" }}>
                  {drill.subtitle}
                </div>
                <p style={{ fontSize: "13px", color: "#334155", lineHeight: "1.5", marginBottom: "20px" }}>
                  {drill.description}
                </p>
              </div>

              <div style={{ borderTop: "1px solid #f1f5f9", paddingTop: "14px" }}>
                <Button
                  variant="secondary"
                  fullWidth
                  onClick={() => handleStartDrill(drill.type, drill.defaultQuestions)}
                  loading={isCurrentLoading}
                >
                  Start This Drill
                </Button>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

export default Practice;
