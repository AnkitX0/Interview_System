import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid
} from "recharts";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../utils/api";
import { Card, CardHeader } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { Skeleton } from "../components/ui/Skeleton";

function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [readinessData, setReadinessData] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [recentSessions, setRecentSessions] = useState([]);
  const [readinessHistory, setReadinessHistory] = useState([]);
  const [startingPractice, setStartingPractice] = useState(false);

  useEffect(() => {
    async function loadDashboard() {
      setLoading(true);
      setError(null);
      try {
        const [readinessRes, recsRes, sessionsRes, historyRes] = await Promise.all([
          apiFetch("/readiness/current").catch(() => null),
          apiFetch("/practice/recommendations").catch(() => null),
          apiFetch("/interview/history?page=1&limit=5").catch(() => null),
          apiFetch("/readiness/history").catch(() => null),
        ]);

        if (readinessRes?.ok) {
          const rData = await readinessRes.json();
          setReadinessData(rData);
        }
        if (recsRes?.ok) {
          const recsData = await recsRes.json();
          setRecommendations(Array.isArray(recsData) ? recsData : []);
        }
        if (sessionsRes?.ok) {
          const sData = await sessionsRes.json();
          setRecentSessions(sData?.items || []);
        }
        if (historyRes?.ok) {
          const hData = await historyRes.json();
          setReadinessHistory(hData?.sessions || []);
        }
      } catch (err) {
        console.error("Dashboard data load error:", err);
        setError("Failed to load dashboard data. Please refresh to try again.");
      } finally {
        setLoading(false);
      }
    }
    loadDashboard();
  }, []);

  const handleStartPractice = async (drillType = "TECHNICAL_DEPTH") => {
    setStartingPractice(true);
    try {
      const res = await apiFetch("/practice/start", {
        method: "POST",
        body: JSON.stringify({
          drill_type: drillType,
          target_role: user?.profile?.target_role || "Software Engineer",
          difficulty: user?.profile?.preferred_difficulty || "medium",
          sensor_mode: "standard",
        }),
      });
      if (res.ok) {
        const data = await res.json();
        navigate("/interview", { state: { sessionId: data.session_id, isPractice: true } });
      } else {
        navigate("/setup");
      }
    } catch {
      navigate("/setup");
    } finally {
      setStartingPractice(false);
    }
  };

  if (loading) {
    return (
      <div className="container" style={{ padding: "16px 0" }}>
        <div style={{ marginBottom: "28px" }}>
          <Skeleton width="220px" height="32px" style={{ marginBottom: "8px" }} />
          <Skeleton width="340px" height="18px" />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "20px", marginBottom: "24px" }}>
          <Skeleton height="180px" borderRadius="var(--radius-lg)" />
          <Skeleton height="180px" borderRadius="var(--radius-lg)" />
        </div>
        <Skeleton height="160px" borderRadius="var(--radius-lg)" style={{ marginBottom: "24px" }} />
        <Skeleton height="260px" borderRadius="var(--radius-lg)" />
      </div>
    );
  }

  const hasSessions = recentSessions.length > 0;
  const currentReadiness = readinessData?.current_readiness;
  const confidence = readinessData?.confidence || "insufficient_data";
  const trend = readinessData?.trend || "insufficient_data";
  const nextPractice = recommendations.length > 0 ? recommendations[0] : null;

  // Format trend badge
  const trendBadgeVariant =
    trend === "improving" ? "success" : trend === "declining" ? "danger" : "neutral";
  const trendLabel =
    trend === "improving" ? "Improving" : trend === "declining" ? "Declining" : trend === "stable" ? "Stable" : "Building Baseline";

  // Dimension scores
  const dimensions = readinessData?.dimensions || {};
  const commScore = dimensions.communication ?? 0;
  const techScore = dimensions.technical ?? 0;
  const deliveryScore = dimensions.delivery ?? 0;
  const resumeScore = dimensions.resume_consistency ?? 0;

  // Chart data: ONLY completed and evaluated sessions with actual evidence
  const chartData = readinessHistory
    .filter((s) => s.readiness_score !== null && s.readiness_score > 0)
    .slice(-8)
    .map((s, idx) => ({
      index: idx + 1,
      name: `Session ${idx + 1}`,
      date: s.created_at ? new Date(s.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : `S${idx + 1}`,
      score: Math.round(s.readiness_score),
    }));

  return (
    <div className="container" style={{ maxWidth: "var(--container-max-w)" }}>
      {/* Welcome & Overview Header */}
      <div style={{ marginBottom: "28px", display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "flex-end", gap: "16px" }}>
        <div>
          <h1 style={{ fontSize: "26px", fontWeight: "700", color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
            Good morning{user?.full_name ? `, ${user.full_name}` : ""}
          </h1>
          <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginTop: "4px" }}>
            Let's make today's interview practice count.
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <Button variant="secondary" onClick={() => navigate("/practice")}>
            Browse Practice Hub
          </Button>
          <Button variant="primary" onClick={() => navigate("/setup")}>
            New Interview
          </Button>
        </div>
      </div>

      {error && (
        <div className="alert alert-warning" style={{ marginBottom: "20px" }}>
          {error}
        </div>
      )}

      {!hasSessions ? (
        <EmptyState
          title="No interview sessions yet"
          description="Complete your first practice interview to build your readiness score, diagnose recurring patterns, and receive targeted drill recommendations."
          action={
            <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
              <Button variant="secondary" onClick={() => navigate("/resume")}>
                Upload Resume First
              </Button>
              <Button variant="primary" onClick={() => navigate("/setup")}>
                Start First Interview
              </Button>
            </div>
          }
        />
      ) : (
        <>
          {/* Top Row: Readiness Card + Next Recommended Practice */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
              gap: "20px",
              marginBottom: "24px",
            }}
          >
            {/* Readiness Card */}
            <Card style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <span style={{ fontSize: "12px", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--text-muted)" }}>
                    Interview Readiness
                  </span>
                  <Badge variant={trendBadgeVariant}>{trendLabel}</Badge>
                </div>

                <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginBottom: "8px" }}>
                  <span style={{ fontSize: "42px", fontWeight: "800", color: "var(--text-primary)", lineHeight: 1 }}>
                    {currentReadiness !== null && currentReadiness !== undefined
                      ? Math.round(currentReadiness)
                      : "—"}
                  </span>
                  <span style={{ fontSize: "16px", color: "var(--text-muted)", fontWeight: "500" }}>/ 100</span>
                </div>

                <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "16px" }}>
                  {confidence === "insufficient_data" ? (
                    "Building your baseline. Complete more comparable interviews to establish a reliable trend."
                  ) : (
                    `Based on ${readinessData?.comparable_sessions_count || 0} comparable sessions in your target role.`
                  )}
                </p>
              </div>

              <div style={{ borderTop: "1px solid var(--border-default)", paddingTop: "14px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                  Observable practice score · Not an employment guarantee
                </span>
                <Link to="/progress" style={{ fontSize: "12px", fontWeight: "600" }}>
                  View Progress →
                </Link>
              </div>
            </Card>

            {/* Next Recommended Practice Card */}
            <Card
              style={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                borderColor: nextPractice ? "var(--primary-200)" : "var(--border-default)",
                backgroundColor: nextPractice ? "var(--slate-50)" : "#ffffff",
              }}
            >
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                  <span style={{ fontSize: "12px", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--primary-700)" }}>
                    Next Recommended Practice
                  </span>
                  <Badge variant="info">Targeted Drill</Badge>
                </div>

                <h3 style={{ fontSize: "18px", fontWeight: "700", color: "var(--text-primary)", marginBottom: "6px" }}>
                  {nextPractice?.drill_title || "Technical Question Defense"}
                </h3>

                <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "12px", lineHeight: "1.5" }}>
                  {nextPractice?.rationale ||
                    "Practice answering structured technical follow-ups with concrete implementation details."}
                </p>

                <div style={{ display: "flex", alignItems: "center", gap: "12px", fontSize: "12px", color: "var(--text-muted)", marginBottom: "16px" }}>
                  <span>{nextPractice?.estimated_questions || 5} questions</span>
                  <span>·</span>
                  <span>~{nextPractice?.estimated_minutes || 10} minutes</span>
                  {nextPractice?.trigger_weakness_label && (
                    <>
                      <span>·</span>
                      <span style={{ color: "var(--warning-text)" }}>Focus: {nextPractice.trigger_weakness_label}</span>
                    </>
                  )}
                </div>
              </div>

              <div>
                <Button
                  variant="primary"
                  onClick={() => handleStartPractice(nextPractice?.drill_type)}
                  loading={startingPractice}
                  fullWidth
                >
                  Start Recommended Drill
                </Button>
              </div>
            </Card>
          </div>

          {/* Performance Dimensions Overview */}
          <Card style={{ marginBottom: "24px" }}>
            <CardHeader
              title="Performance Dimensions"
              subtitle="Current proficiency derived across your completed sessions"
            />

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: "16px" }}>
              <DimensionItem label="Technical Depth" score={techScore} benchmark="Target 80" />
              <DimensionItem label="Communication Structure" score={commScore} benchmark="Target 80" />
              <DimensionItem label="Delivery & Stability" score={deliveryScore} benchmark="Centering & Cadence" />
              <DimensionItem label="Resume Verification" score={resumeScore} benchmark="Claim Consistency" />
            </div>
          </Card>

          {/* Split: Recent Progress Chart + Recent Sessions */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
              gap: "20px",
            }}
          >
            {/* Recent Progress Chart */}
            <Card>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                <div>
                  <h3 className="card-title" style={{ fontSize: "16px" }}>Recent Progress</h3>
                  <p className="card-subtitle" style={{ fontSize: "12px" }}>Readiness trajectory across recent sessions</p>
                </div>
                <Link to="/progress" style={{ fontSize: "12px", fontWeight: "600" }}>
                  Full History →
                </Link>
              </div>

              {chartData.length < 2 ? (
                <div style={{ padding: "40px 16px", textAlign: "center", color: "var(--text-muted)", fontSize: "13px" }}>
                  Complete at least 2 sessions to visualize your readiness trend line.
                </div>
              ) : (
                <div style={{ height: "200px", width: "100%" }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border-default)" />
                      <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
                      <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#ffffff",
                          borderColor: "var(--border-default)",
                          borderRadius: "6px",
                          fontSize: "12px",
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="score"
                        stroke="#2563eb"
                        strokeWidth={2.5}
                        dot={{ r: 4, fill: "#2563eb" }}
                        activeDot={{ r: 6 }}
                        name="Readiness"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>

            {/* Recent Sessions List */}
            <Card>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                <div>
                  <h3 className="card-title" style={{ fontSize: "16px" }}>Recent Interviews</h3>
                  <p className="card-subtitle" style={{ fontSize: "12px" }}>Latest completed practice sessions</p>
                </div>
                <Link to="/history" style={{ fontSize: "12px", fontWeight: "600" }}>
                  All Sessions →
                </Link>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {recentSessions.map((s) => (
                  <div
                    key={s.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "10px 12px",
                      borderRadius: "6px",
                      backgroundColor: "var(--slate-50)",
                      border: "1px solid var(--border-default)",
                    }}
                  >
                    <div>
                      <div style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-primary)" }}>
                        {s.target_role || "General Interview"}
                      </div>
                      <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                        {s.created_at ? new Date(s.created_at).toLocaleDateString() : "Recent"} · {s.mode || "standard"}
                      </div>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                      <div style={{ textAlign: "right" }}>
                        <div style={{ fontSize: "15px", fontWeight: "700", color: "var(--text-primary)" }}>
                          {s.readiness_score !== null && s.readiness_score !== undefined
                            ? Math.round(s.readiness_score)
                            : "—"}
                        </div>
                        <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>Readiness</div>
                      </div>

                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => navigate(`/report?sessionId=${s.id}`)}
                      >
                        Report
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

function DimensionItem({ label, score, benchmark }) {
  const rounded = Math.round(score || 0);
  const color = rounded >= 75 ? "var(--success-text)" : rounded >= 60 ? "var(--primary-600)" : "var(--warning-text)";

  return (
    <div
      style={{
        padding: "12px",
        borderRadius: "var(--radius-md)",
        backgroundColor: "var(--slate-50)",
        border: "1px solid var(--border-default)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "6px" }}>
        <span style={{ fontSize: "12px", fontWeight: "500", color: "var(--text-secondary)" }}>{label}</span>
        <span style={{ fontSize: "16px", fontWeight: "700", color }}>{rounded}</span>
      </div>

      <div
        style={{
          height: "5px",
          width: "100%",
          backgroundColor: "var(--border-default)",
          borderRadius: "999px",
          overflow: "hidden",
          marginBottom: "6px",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${Math.min(100, Math.max(0, rounded))}%`,
            backgroundColor: color,
            borderRadius: "999px",
          }}
        />
      </div>

      <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>{benchmark}</span>
    </div>
  );
}

export default Dashboard;