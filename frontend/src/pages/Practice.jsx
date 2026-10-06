import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../utils/api";
import { Card, CardHeader } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Skeleton } from "../components/ui/Skeleton";

const DRILL_CATALOG = [
  {
    type: "TECHNICAL_DEPTH",
    title: "Technical Deep Dive",
    subtitle: "Architecture & System Mechanics",
    description: "Practice explaining complex engineering choices, bottleneck optimizations, and failure handling with concrete specifics.",
    defaultQuestions: 5,
    estimatedMinutes: 10,
    badge: "Core Technical",
    badgeVariant: "neutral",
  },
  {
    type: "FOLLOWUP_DEFENSE",
    title: "Follow-up & Probe Defense",
    subtitle: "Multi-turn Question Ladders",
    description: "Strengthen how you respond when an interviewer digs into trade-offs, edge cases, and architectural alternatives.",
    defaultQuestions: 5,
    estimatedMinutes: 10,
    badge: "Interview Agility",
    badgeVariant: "info",
  },
  {
    type: "PROJECT_DEFENSE",
    title: "Project & Claim Defense",
    subtitle: "Resume-Grounded Questions",
    description: "Validate deliverables, system metrics, and architectural ownership from projects cited on your resume.",
    defaultQuestions: 5,
    estimatedMinutes: 10,
    badge: "Resume Anchored",
    badgeVariant: "info",
  },
  {
    type: "STRUCTURED_ANSWER",
    title: "Structured Communication",
    subtitle: "Context, Action & Impact",
    description: "Sharpen verbal delivery using structured frameworks. Eliminate mid-sentence hesitation and reduce verbal fillers.",
    defaultQuestions: 5,
    estimatedMinutes: 8,
    badge: "Delivery & Clarity",
    badgeVariant: "neutral",
  },
  {
    type: "BEHAVIORAL_STAR",
    title: "Behavioral Scenarios",
    subtitle: "STAR Method Practice",
    description: "Walk through high-impact teamwork, disagreement, conflict resolution, and prioritization examples.",
    defaultQuestions: 5,
    estimatedMinutes: 10,
    badge: "Culture & Leadership",
    badgeVariant: "neutral",
  },
  {
    type: "PRESSURE_RESPONSE",
    title: "High-Urgency Pressure Practice",
    subtitle: "45-Second Incident Response",
    description: "Simulate high-stakes incident post-mortems and live troubleshooting with strict 45-second answer windows.",
    defaultQuestions: 5,
    estimatedMinutes: 8,
    badge: "Pressure Drill",
    badgeVariant: "warning",
  },
];

function Practice() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [launchingType, setLaunchingType] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchRecs() {
      setLoading(true);
      setError(null);
      try {
        const res = await apiFetch("/practice/recommendations");
        if (res.ok) {
          const data = await res.json();
          setRecommendations(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        console.error("Failed to load practice recommendations:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchRecs();
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
    <div className="container" style={{ maxWidth: "var(--container-max-w)" }}>
      {/* Header */}
      <div style={{ marginBottom: "28px" }}>
        <h1 style={{ fontSize: "26px", fontWeight: "700", color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
          Targeted Practice
        </h1>
        <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginTop: "4px" }}>
          Target specific skills and recurring weaknesses with concise, 5-question focused drills.
        </p>
      </div>

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: "20px" }}>
          {error}
        </div>
      )}

      {/* Primary Recommended Practice Hero */}
      {loading ? (
        <Skeleton height="180px" borderRadius="var(--radius-lg)" style={{ marginBottom: "32px" }} />
      ) : primaryRec ? (
        <Card
          style={{
            marginBottom: "32px",
            backgroundColor: "var(--slate-50)",
            borderColor: "var(--primary-200)",
            padding: "24px 28px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "12px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--primary-700)" }}>
                Recommended For You
              </span>
              <Badge variant="warning">Priority 1</Badge>
            </div>
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              Based on your recent performance
            </span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "24px", alignItems: "center" }}>
            <div>
              <h2 style={{ fontSize: "20px", fontWeight: "700", color: "var(--text-primary)", marginBottom: "8px" }}>
                {primaryRec.drill_title || primaryRec.practice_type?.replace(/_/g, " ")}
              </h2>
              <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: "1.5", marginBottom: "12px", maxWidth: "680px" }}>
                {primaryRec.rationale || "Practice answering focused technical follow-ups with concrete implementation details."}
              </p>
              <div style={{ display: "flex", gap: "14px", fontSize: "12px", color: "var(--text-muted)" }}>
                <span>{primaryRec.target_count || 5} questions</span>
                <span>·</span>
                <span>~10 minutes</span>
                {primaryRec.dimension && (
                  <>
                    <span>·</span>
                    <span style={{ color: "var(--primary-700)", fontWeight: "500" }}>
                      Dimension: {primaryRec.dimension}
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
                Start Recommended Drill
              </Button>
            </div>
          </div>
        </Card>
      ) : null}

      {/* Drill Catalog */}
      <div style={{ marginBottom: "20px" }}>
        <h3 style={{ fontSize: "18px", fontWeight: "700", color: "var(--text-primary)", marginBottom: "4px" }}>
          All Practice Drills
        </h3>
        <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
          Choose a specific dimension to practice at your own pace.
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
                padding: "20px",
              }}
            >
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                  <Badge variant={drill.badgeVariant}>{drill.badge}</Badge>
                  <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    {drill.defaultQuestions} questions · ~{drill.estimatedMinutes}m
                  </span>
                </div>

                <h4 style={{ fontSize: "16px", fontWeight: "700", color: "var(--text-primary)", marginBottom: "4px" }}>
                  {drill.title}
                </h4>
                <div style={{ fontSize: "12px", fontWeight: "500", color: "var(--text-muted)", marginBottom: "10px" }}>
                  {drill.subtitle}
                </div>
                <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.5", marginBottom: "20px" }}>
                  {drill.description}
                </p>
              </div>

              <div style={{ borderTop: "1px solid var(--border-default)", paddingTop: "14px" }}>
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

