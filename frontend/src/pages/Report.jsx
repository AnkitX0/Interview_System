import React, { useEffect, useState, useContext } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer
} from "recharts";
import { ReportContext } from "../context/ReportContext";
import { apiFetch } from "../utils/api";
import { Card, CardHeader } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Skeleton } from "../components/ui/Skeleton";

function Report() {
  const navigate = useNavigate();
  const location = useLocation();
  const { currentSessionId } = useContext(ReportContext);

  const queryParams = new URLSearchParams(location.search);
  const targetSessionId =
    queryParams.get("sessionId") ||
    location.state?.sessionId ||
    currentSessionId ||
    sessionStorage.getItem("currentSessionId");

  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("summary"); // summary | questions | timeline | verification
  const [startingPractice, setStartingPractice] = useState(false);

  useEffect(() => {
    const fetchReport = async () => {
      setLoading(true);
      setError(null);

      try {
        let endpoint = "/report/latest";
        if (targetSessionId) {
          endpoint = `/report/${targetSessionId}`;
        }

        const res = await apiFetch(endpoint);
        if (res.ok) {
          const data = await res.json();
          setReport(data);
          return;
        }

        // If specific session failed, try latest session score
        const latestRes = await apiFetch("/interview/latest");
        if (latestRes.ok) {
          const latestData = await latestRes.json();
          if (latestData.session_id) {
            const repRes = await apiFetch(`/report/${latestData.session_id}`);
            if (repRes.ok) {
              const repData = await repRes.json();
              setReport(repData);
              return;
            }
          }
        }
        throw new Error("Could not find session data.");
      } catch (err) {
        console.warn("Report fetch notice:", err);
        setError("Could not load interview report. Please verify the session exists.");
      } finally {
        setLoading(false);
      }
    };

    fetchReport();
  }, [targetSessionId]);

  const handleStartPractice = async (drillType = "TECHNICAL_DEPTH") => {
    setStartingPractice(true);
    try {
      const res = await apiFetch("/practice/start", {
        method: "POST",
        body: JSON.stringify({
          practice_type: drillType,
          target_role: report?.target_role || "Software Engineer",
          difficulty: report?.difficulty || "medium",
          question_count: 5,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        navigate("/interview", { state: { sessionId: data.session_id, isPractice: true } });
      } else {
        navigate("/practice");
      }
    } catch {
      navigate("/practice");
    } finally {
      setStartingPractice(false);
    }
  };

  if (loading) {
    return (
      <div className="container" style={{ padding: "20px 0" }}>
        <Skeleton width="280px" height="32px" style={{ marginBottom: "12px" }} />
        <Skeleton width="450px" height="18px" style={{ marginBottom: "28px" }} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "20px", marginBottom: "24px" }}>
          <Skeleton height="180px" borderRadius="var(--radius-lg)" />
          <Skeleton height="180px" borderRadius="var(--radius-lg)" />
        </div>
        <Skeleton height="300px" borderRadius="var(--radius-lg)" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="container" style={{ textAlign: "center", padding: "60px 20px" }}>
        <h2 style={{ fontSize: "20px", fontWeight: "700", marginBottom: "8px" }}>Report Not Found</h2>
        <p style={{ color: "var(--text-secondary)", marginBottom: "20px" }}>
          {error || "We could not find an interview report for this session."}
        </p>
        <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
          <Button variant="secondary" onClick={() => navigate("/history")}>View History</Button>
          <Button variant="primary" onClick={() => navigate("/setup")}>Start New Interview</Button>
        </div>
      </div>
    );
  }

  const isDeliveryMeasured =
    report.behavioral_metrics?.eye_contact_percent !== null &&
    report.behavioral_metrics?.eye_contact_percent !== undefined;

  const weights = report.weights_used || {
    communication: 0.3,
    technical: 0.3,
    delivery: 0.2,
    resume_consistency: 0.2,
  };

  const readinessScore = Math.round(report.readiness_score || 0);
  const scoreVariant = readinessScore >= 75 ? "success" : readinessScore >= 60 ? "info" : "warning";

  const nextRec = report.next_practice && report.next_practice.length > 0 ? report.next_practice[0] : null;

  // Chart data for subscores
  const subscoreBarData = [
    { name: "Technical Depth", score: Math.round(report.subscores?.technical || 0), fill: "#2563eb" },
    { name: "Communication", score: Math.round(report.subscores?.communication || 0), fill: "#0ea5e9" },
    ...(isDeliveryMeasured
      ? [{ name: "Delivery & Stability", score: Math.round(report.subscores?.delivery || 0), fill: "#6366f1" }]
      : []),
    { name: "Resume Consistency", score: Math.round(report.subscores?.resume_consistency || 0), fill: "#f59e0b" },
  ];

  return (
    <div className="container" style={{ maxWidth: "1080px", paddingBottom: "60px" }}>
      {/* Top Breadcrumb & Actions */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "14px",
          marginBottom: "20px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Link to="/history" style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              ← Interview History
            </Link>
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>/</span>
            <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: "600" }}>
              Session #{report.session_id}
            </span>
          </div>
          <h1 style={{ fontSize: "24px", fontWeight: "700", color: "var(--text-primary)", marginTop: "4px" }}>
            Performance Report
          </h1>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
            {report.target_role || "Software Engineer"} · {report.mode || "Technical"} · {report.difficulty || "medium"} difficulty
          </div>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <Button variant="secondary" size="sm" onClick={() => navigate("/dashboard")}>
            Dashboard
          </Button>
          <Button variant="primary" size="sm" onClick={() => navigate("/setup")}>
            New Interview
          </Button>
        </div>
      </div>

      {/* Hero Overview: Score & Focus Highlights */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
          gap: "20px",
          marginBottom: "24px",
        }}
      >
        {/* Score Card */}
        <Card style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <span style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-muted)" }}>
                Interview Readiness Score
              </span>
              <Badge variant={scoreVariant}>{report.status_label || "Evaluated"}</Badge>
            </div>

            <div style={{ display: "flex", alignItems: "baseline", gap: "8px", margin: "8px 0" }}>
              <span style={{ fontSize: "48px", fontWeight: "800", color: "var(--text-primary)", lineHeight: 1 }}>
                {readinessScore}
              </span>
              <span style={{ fontSize: "18px", color: "var(--text-muted)", fontWeight: "500" }}>/ 100</span>
            </div>

            <p style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: "1.5" }}>
              {isDeliveryMeasured ? (
                "Formula: 30% Technical + 30% Communication + 20% Delivery & Stability + 20% Resume Consistency."
              ) : (
                "Re-normalized formula: 37.5% Technical + 37.5% Communication + 25% Resume Consistency (camera was inactive)."
              )}
            </p>
          </div>

          <div style={{ borderTop: "1px solid var(--border-default)", paddingTop: "12px", marginTop: "16px", display: "flex", justifyContent: "space-between", fontSize: "12px", color: "var(--text-muted)" }}>
            <span>Evaluated answers: {report.answers?.length || 0}</span>
            <span>Duration: {Math.round((report.duration_seconds || 180) / 60)} min</span>
          </div>
        </Card>

        {/* Highlights & Growth Focus Card */}
        <Card style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div>
            <span style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-muted)" }}>
              Key Observations
            </span>

            <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
              <div style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
                <span style={{ color: "var(--success-text)", fontWeight: "700" }}>✓</span>
                <div>
                  <div style={{ fontSize: "12px", fontWeight: "700", color: "var(--text-primary)" }}>
                    Strongest: {report.insights?.strongest_category || "Technical Depth"}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "1px" }}>
                    {report.insights?.top_improvements?.[0] || "Solid mastery of core technical decisions."}
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
                <span style={{ color: "var(--warning-text)", fontWeight: "700" }}>!</span>
                <div>
                  <div style={{ fontSize: "12px", fontWeight: "700", color: "var(--text-primary)" }}>
                    Needs Attention: {report.insights?.weakest_category || "Communication Structure"}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "1px" }}>
                    {report.insights?.top_improvements?.[1] || "Answers benefit from tighter STAR structure and fewer filler pauses."}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {report.evaluation_engine && (
            <div style={{ borderTop: "1px solid var(--border-default)", paddingTop: "12px", marginTop: "16px", fontSize: "11px", color: "var(--text-muted)" }}>
              Evaluated by: {report.evaluation_engine.toUpperCase()} [{report.prompt_version || "rubric v1.0"}]
            </div>
          )}
        </Card>
      </div>

      {/* WHAT WENT WELL / WHAT HELD YOU BACK / NEXT PRACTICE (Core 3 Pillars) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "20px",
          marginBottom: "32px",
        }}
      >
        {/* Pillar 1: What Went Well */}
        <Card style={{ borderTop: "3px solid var(--success-text)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "12px" }}>
            <span style={{ color: "var(--success-text)", fontWeight: "bold" }}>●</span>
            <h3 style={{ fontSize: "15px", fontWeight: "700", color: "var(--text-primary)" }}>
              What Went Well
            </h3>
          </div>

          <div style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.5", display: "flex", flexDirection: "column", gap: "10px" }}>
            {report.answers && report.answers.flatMap((a) => a.strengths || []).length > 0 ? (
              Array.from(new Set(report.answers.flatMap((a) => a.strengths || [])))
                .slice(0, 3)
                .map((str, idx) => (
                  <div key={idx} style={{ display: "flex", gap: "8px" }}>
                    <span style={{ color: "var(--success-text)" }}>✓</span>
                    <span>{str}</span>
                  </div>
                ))
            ) : (
              <div>Maintained structured explanations across interview questions.</div>
            )}
          </div>
        </Card>

        {/* Pillar 2: What Held You Back */}
        <Card style={{ borderTop: "3px solid var(--warning-text)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "12px" }}>
            <span style={{ color: "var(--warning-text)", fontWeight: "bold" }}>●</span>
            <h3 style={{ fontSize: "15px", fontWeight: "700", color: "var(--text-primary)" }}>
              What Held You Back
            </h3>
          </div>

          <div style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.5", display: "flex", flexDirection: "column", gap: "10px" }}>
            {report.session_weaknesses && report.session_weaknesses.length > 0 ? (
              report.session_weaknesses.slice(0, 2).map((w, idx) => (
                <div key={idx} style={{ backgroundColor: "var(--slate-50)", padding: "10px 12px", borderRadius: "6px", border: "1px solid var(--border-default)" }}>
                  <div style={{ fontSize: "12px", fontWeight: "700", color: "var(--text-primary)", marginBottom: "2px" }}>
                    {w.weakness_type.replace(/_/g, " ").toUpperCase()}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "4px" }}>
                    {w.explanation}
                  </div>
                  {w.actionable_guidance && (
                    <div style={{ fontSize: "11px", color: "var(--primary-700)", fontWeight: "500" }}>
                      Action: {w.actionable_guidance}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div>Answers would be stronger with more specific metrics and architectural constraints.</div>
            )}
          </div>
        </Card>

        {/* Pillar 3: Next Recommended Practice */}
        <Card style={{ borderTop: "3px solid var(--primary-600)", backgroundColor: "var(--slate-50)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <h3 style={{ fontSize: "15px", fontWeight: "700", color: "var(--primary-900)" }}>
              Recommended Next Practice
            </h3>
            <Badge variant="info">Targeted</Badge>
          </div>

          <div style={{ marginBottom: "14px" }}>
            <div style={{ fontSize: "14px", fontWeight: "700", color: "var(--text-primary)", marginBottom: "4px" }}>
              {nextRec?.drill_title || "Technical Question Defense"}
            </div>
            <p style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: "1.5", marginBottom: "10px" }}>
              {nextRec?.rationale || "Sharpen your explanations on architecture constraints and failure handling."}
            </p>
            <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
              {nextRec?.target_count || 5} questions · ~10 minutes
            </div>
          </div>

          <Button
            variant="primary"
            fullWidth
            onClick={() => handleStartPractice(nextRec?.practice_type)}
            loading={startingPractice}
          >
            Start This Practice Drill
          </Button>
        </Card>
      </div>

      {/* Progressive Disclosure Tabs */}
      <div
        style={{
          borderBottom: "1px solid var(--border-default)",
          display: "flex",
          gap: "8px",
          marginBottom: "24px",
        }}
      >
        <button
          type="button"
          onClick={() => setActiveTab("summary")}
          style={{
            padding: "10px 16px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "summary" ? "2px solid var(--slate-900)" : "2px solid transparent",
            fontWeight: activeTab === "summary" ? "600" : "500",
            color: activeTab === "summary" ? "var(--text-primary)" : "var(--text-secondary)",
            fontSize: "13px",
            cursor: "pointer",
          }}
        >
          Dimension Breakdown
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("questions")}
          style={{
            padding: "10px 16px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "questions" ? "2px solid var(--slate-900)" : "2px solid transparent",
            fontWeight: activeTab === "questions" ? "600" : "500",
            color: activeTab === "questions" ? "var(--text-primary)" : "var(--text-secondary)",
            fontSize: "13px",
            cursor: "pointer",
          }}
        >
          Per-Question Review ({report.answers?.length || 0})
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("timeline")}
          style={{
            padding: "10px 16px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "timeline" ? "2px solid var(--slate-900)" : "2px solid transparent",
            fontWeight: activeTab === "timeline" ? "600" : "500",
            color: activeTab === "timeline" ? "var(--text-primary)" : "var(--text-secondary)",
            fontSize: "13px",
            cursor: "pointer",
          }}
        >
          Interview Timeline ({report.timeline?.length || 0} turns)
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("verification")}
          style={{
            padding: "10px 16px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "verification" ? "2px solid var(--slate-900)" : "2px solid transparent",
            fontWeight: activeTab === "verification" ? "600" : "500",
            color: activeTab === "verification" ? "var(--text-primary)" : "var(--text-secondary)",
            fontSize: "13px",
            cursor: "pointer",
          }}
        >
          Resume Verification
        </button>
      </div>

      {/* Tab 1: Dimension Breakdown */}
      {activeTab === "summary" && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: "20px" }}>
          <Card>
            <CardHeader title="Dimensions Breakdown" subtitle="Relative performance across measured competencies" />
            <div style={{ height: "240px", width: "100%" }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={subscoreBarData} layout="vertical" margin={{ left: 10, right: 20, top: 10, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" domain={[0, 100]} />
                  <YAxis dataKey="name" type="category" width={140} style={{ fontSize: "11px" }} />
                  <Tooltip formatter={(value) => [`${value}%`, "Score"]} />
                  <Bar dataKey="score" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card>
            <CardHeader title="Delivery & Centering" subtitle="Observable physical and speech cadence signals" />
            {!isDeliveryMeasured && (
              <div className="alert alert-warning" style={{ fontSize: "12px", marginBottom: "14px" }}>
                Camera was inactive during this interview. Physical centering was excluded from scoring.
              </div>
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "13px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--border-default)" }}>
                <span style={{ color: "var(--text-secondary)" }}>Camera Positioning (Centering proxy):</span>
                <strong>{isDeliveryMeasured ? `${report.behavioral_metrics?.eye_contact_percent}%` : "Not measured"}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--border-default)" }}>
                <span style={{ color: "var(--text-secondary)" }}>Blink Frequency:</span>
                <strong>{isDeliveryMeasured ? `${report.behavioral_metrics?.blink_rate} / min` : "Not measured"}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--border-default)" }}>
                <span style={{ color: "var(--text-secondary)" }}>Speaking Cadence / Pauses:</span>
                <strong>{report.behavioral_metrics?.pause_rate !== null ? `${report.behavioral_metrics?.pause_rate}s avg` : "2.0s avg"}</strong>
              </div>
            </div>
            <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "14px" }}>
              Note: Physical signals are diagnostic framing and pacing indicators, not assessments of confidence or psychology.
            </p>
          </Card>
        </div>
      )}

      {/* Tab 2: Question Reviews */}
      {activeTab === "questions" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {report.answers && report.answers.map((ans, idx) => (
            <Card key={idx}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
                <div>
                  <span style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", color: "var(--primary-700)" }}>
                    Question {idx + 1}
                  </span>
                  <h4 style={{ fontSize: "15px", fontWeight: "700", color: "var(--text-primary)", marginTop: "2px" }}>
                    {ans.question_text}
                  </h4>
                </div>
                <Badge variant={ans.overall_score >= 75 ? "success" : "neutral"}>
                  Score: {Math.round(ans.overall_score || 0)}
                </Badge>
              </div>

              <div style={{ backgroundColor: "var(--slate-50)", padding: "12px 14px", borderRadius: "6px", marginBottom: "14px", fontSize: "13px", color: "var(--text-primary)", fontStyle: "italic", border: "1px solid var(--border-default)" }}>
                "{ans.transcript || "No transcript recorded."}"
              </div>

              {/* Rubric Dimension Breakdown */}
              {ans.dimensions && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "10px", marginBottom: "12px" }}>
                  {Object.entries(ans.dimensions).map(([dimKey, dimVal]) => (
                    <div key={dimKey} style={{ padding: "8px 10px", borderRadius: "6px", border: "1px solid var(--border-default)", backgroundColor: "#ffffff" }}>
                      <div style={{ fontSize: "11px", fontWeight: "600", textTransform: "capitalize", color: "var(--text-muted)" }}>
                        {dimKey}
                      </div>
                      <div style={{ fontSize: "14px", fontWeight: "700", color: "var(--text-primary)" }}>
                        {Math.round(dimVal?.score || 0)}/100
                      </div>
                      <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>
                        {dimVal?.explanation}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {ans.suggestions && ans.suggestions.length > 0 && (
                <div style={{ fontSize: "12px", color: "var(--primary-800)", backgroundColor: "var(--primary-50)", padding: "8px 12px", borderRadius: "6px" }}>
                  <strong>Suggestion:</strong> {ans.suggestions[0]}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* Tab 3: Timeline & Decisions */}
      {activeTab === "timeline" && (
        <Card>
          <CardHeader title="Session Timeline" subtitle="Chronological progression of questions and follow-ups" />
          {report.timeline && report.timeline.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {report.timeline.map((item, idx) => {
                const mins = Math.floor((item.timestamp_offset_seconds || 0) / 60);
                const secs = (item.timestamp_offset_seconds || 0) % 60;
                return (
                  <div key={idx} style={{ padding: "12px 14px", borderRadius: "6px", backgroundColor: "var(--slate-50)", border: "1px solid var(--border-default)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontSize: "11px", fontWeight: "700", backgroundColor: "var(--slate-900)", color: "#ffffff", padding: "2px 6px", borderRadius: "4px" }}>
                          Turn {item.turn} · +{mins}:{secs.toString().padStart(2, "0")}
                        </span>
                        <span style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-primary)" }}>
                          {item.question_type || "Question"}
                        </span>
                      </div>
                      <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                        {item.word_count || 0} words
                      </span>
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
                      {item.question_text}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>No timeline events recorded.</p>
          )}
        </Card>
      )}

      {/* Tab 4: Resume Verification */}
      {activeTab === "verification" && (
        <Card>
          <CardHeader title="Resume Verification" subtitle="Alignment between resume claims and interview responses" />
          {report.claim_consistency && report.claim_consistency.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {report.claim_consistency.map((claim, idx) => (
                <div key={idx} style={{ padding: "12px 14px", borderRadius: "6px", backgroundColor: "var(--slate-50)", border: "1px solid var(--border-default)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                    <span style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-primary)" }}>
                      {claim.claim_text || `Claim #${claim.claim_id}`}
                    </span>
                    <Badge variant={claim.label === "consistent" ? "success" : "neutral"}>
                      {claim.label}
                    </Badge>
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                    {claim.explanation || "Verified against spoken implementation details."}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
              No specific resume claims were targeted in this session.
            </p>
          )}

          <div style={{ marginTop: "16px", padding: "10px 12px", backgroundColor: "var(--slate-100)", borderRadius: "6px", fontSize: "11px", color: "var(--text-muted)" }}>
            Resume verification evaluates whether interview answers provide supporting detail for claims listed on your resume. It does not make accusations or truth conclusions.
          </div>
        </Card>
      )}
    </div>
  );
}

export default Report;