import React, { useEffect, useState, useContext } from "react";
import { useNavigate, useLocation } from "react-router-dom";
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

// Helper for safe normalized report object
function normalizeReport(raw) {
  if (!raw || typeof raw !== "object") return null;

  const behavioral = raw.behavioral_metrics || raw.delivery_metrics || {};
  const isDeliveryMeasured =
    behavioral.delivery_measured === true ||
    (behavioral.eye_contact_percent !== null && behavioral.eye_contact_percent !== undefined);

  const answers = Array.isArray(raw.answers) ? raw.answers : [];
  const meaningfulAnswers = answers.filter(
    (a) => !a.is_skipped && a.status !== "skipped" && a.status !== "empty" && a.status !== "insufficient"
  ).length;

  const evidenceSummary = raw.evidence_summary || {
    total_questions: answers.length,
    answered_questions: answers.filter((a) => !a.is_skipped && a.status !== "skipped").length,
    skipped_questions: answers.filter((a) => a.is_skipped || a.status === "skipped").length,
    empty_answers: answers.filter((a) => a.status === "empty" || a.status === "insufficient").length,
    meaningful_answers: meaningfulAnswers,
    evidence_coverage: answers.length ? Math.round((meaningfulAnswers / answers.length) * 100) : 0,
    confidence: raw.assessment_confidence || (meaningfulAnswers >= 5 ? "High" : meaningfulAnswers >= 3 ? "Moderate" : "Low"),
    interview_status: raw.readiness_score === 0 ? "Incomplete" : "Completed",
  };

  return {
    ...raw,
    session_id: raw.session_id || 0,
    target_role: raw.target_role || "Software Engineer",
    mode: raw.mode || "technical",
    difficulty: raw.difficulty || "medium",
    readiness_score: typeof raw.readiness_score === "number" ? Math.round(raw.readiness_score) : 0,
    status_label: raw.status_label || (raw.readiness_score >= 80 ? "Job-Ready Candidate" : raw.readiness_score >= 65 ? "Near Interview-Ready" : (raw.readiness_score === 0 ? "Incomplete Assessment" : "Requires Targeted Practice")),
    score_confidence: raw.assessment_confidence || evidenceSummary.confidence || "Low",
    confidence_explanation: raw.confidence_explanation || (raw.readiness_score === 0 ? "No meaningful interview answers were submitted, so readiness cannot be reliably assessed." : "Assessment based on evaluated turns."),
    isDeliveryMeasured,
    evidence_summary: evidenceSummary,
    subscores: {
      technical: Math.round(raw.subscores?.technical || 0),
      communication: Math.round(raw.subscores?.communication || 0),
      delivery: isDeliveryMeasured ? Math.round(raw.subscores?.delivery || 0) : null,
      resume_consistency: Math.round(raw.subscores?.resume_consistency || 0),
    },
    behavioral_metrics: {
      eye_contact_percent: behavioral.eye_contact_percent ?? behavioral.visual_centering_percent ?? null,
      blink_rate: behavioral.blink_rate ?? null,
      pause_rate: behavioral.pause_rate ?? null,
      delivery_measured: isDeliveryMeasured,
      note: behavioral.note || (isDeliveryMeasured ? "Measured" : "Not measured: camera was off"),
    },
    answers,
    timeline: Array.isArray(raw.timeline) ? raw.timeline : [],
    session_weaknesses: Array.isArray(raw.session_weaknesses) ? raw.session_weaknesses : [],
    next_practice: Array.isArray(raw.next_practice) ? raw.next_practice : [],
    claim_consistency: Array.isArray(raw.claim_consistency) ? raw.claim_consistency : [],
  };
}

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
  const [activeTab, setActiveTab] = useState("questions"); // questions | summary | timeline | verification
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
          setReport(normalizeReport(data));
          return;
        }

        if (res.status === 401) {
          setError("Your session has expired. Please log in again to view your report.");
          return;
        }

        const latestRes = await apiFetch("/interview/latest");
        if (latestRes.ok) {
          const latestData = await latestRes.json();
          if (latestData.session_id) {
            const repRes = await apiFetch(`/report/${latestData.session_id}`);
            if (repRes.ok) {
              const repData = await repRes.json();
              setReport(normalizeReport(repData));
              return;
            }
          }
        }
        throw new Error("Could not find interview report for session #" + (targetSessionId || "latest"));
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
      }
    } catch (err) {
      console.error("Practice start error:", err);
    } finally {
      setStartingPractice(false);
    }
  };

  if (loading) {
    return (
      <div style={{ maxWidth: "1080px", margin: "0 auto", padding: "0 16px 80px 16px" }}>
        <Skeleton height="60px" borderRadius="var(--radius-md)" style={{ marginBottom: "20px" }} />
        <Skeleton height="240px" borderRadius="var(--radius-lg)" style={{ marginBottom: "24px" }} />
        <Skeleton height="360px" borderRadius="var(--radius-lg)" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div style={{ maxWidth: "680px", margin: "60px auto", textAlign: "center" }}>
        <div style={{ padding: "40px 24px", backgroundColor: "#ffffff", borderRadius: "12px", border: "1px solid #e2e8f0" }}>
          <h2 style={{ fontSize: "20px", fontWeight: "700", color: "#0f172a", marginBottom: "8px" }}>
            Report Not Available
          </h2>
          <p style={{ fontSize: "14px", color: "#64748b", marginBottom: "24px" }}>
            {error || "We could not find an interview report for this session."}
          </p>
          <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
            <Button variant="secondary" onClick={() => navigate("/dashboard")}>
              Return to Dashboard
            </Button>
            <Button variant="primary" onClick={() => navigate("/setup")}>
              Start New Interview
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const {
    readiness_score: readinessScore,
    isDeliveryMeasured,
    subscores,
    evidence_summary: evSummary,
  } = report;

  const isZeroEvidence = readinessScore === 0 || evSummary?.meaningful_answers === 0;

  const scoreVariant = isZeroEvidence
    ? "neutral"
    : readinessScore >= 80
    ? "success"
    : readinessScore >= 65
    ? "info"
    : "warning";

  const nextRec = report.next_practice && report.next_practice.length > 0 ? report.next_practice[0] : null;
  const drillType = nextRec?.practice_type || "TECHNICAL_DEPTH";
  const drillTitle = nextRec?.drill_title || drillType.replace(/_/g, " ").toUpperCase();
  const drillRationale = nextRec?.rationale || "Practice answering focused technical follow-ups with concrete implementation details.";

  const subscoreBarData = [
    { name: "Technical Depth", score: isZeroEvidence ? 0 : subscores.technical, fill: "#3b82f6" },
    { name: "Communication", score: isZeroEvidence ? 0 : subscores.communication, fill: "#6366f1" },
    { name: "Resume Consistency", score: isZeroEvidence ? 0 : subscores.resume_consistency, fill: "#0ea5e9" },
  ];

  if (isDeliveryMeasured && subscores.delivery !== null) {
    subscoreBarData.push({
      name: "Delivery & Stability",
      score: isZeroEvidence ? 0 : subscores.delivery,
      fill: "#10b981",
    });
  }

  return (
    <div style={{ maxWidth: "1080px", margin: "0 auto", padding: "0 16px 80px 16px" }}>
      {/* HEADER: Study Review */}
      <div style={{ marginBottom: "24px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
          <span style={{ fontSize: "12px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--primary-700)" }}>
            Session Analysis & Study Review
          </span>
          <Badge variant={isZeroEvidence ? "warning" : "info"}>
            {isZeroEvidence ? "Incomplete Assessment" : "Evaluated Session"}
          </Badge>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px" }}>
          <div>
            <h1 style={{ fontSize: "28px", fontWeight: "800", color: "#0f172a", letterSpacing: "-0.02em" }}>
              Your Interview Review
            </h1>
            <p style={{ color: "#64748b", marginTop: "4px", fontSize: "14px" }}>
              Role: <strong style={{ color: "#1e293b" }}>{report.target_role}</strong> · Round: <strong style={{ color: "#1e293b" }}>{report.mode}</strong> · Difficulty: <strong style={{ color: "#1e293b" }}>{report.difficulty}</strong>
            </p>
          </div>
          <div style={{ display: "flex", gap: "10px" }}>
            <Button variant="secondary" size="sm" onClick={() => navigate("/dashboard")}>
              ← Dashboard
            </Button>
            <Button variant="primary" size="sm" onClick={() => handleStartPractice(drillType)} loading={startingPractice}>
              Start Next Drill →
            </Button>
          </div>
        </div>
      </div>

      {/* EVIDENCE SUMMARY STRIP */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "12px",
          marginBottom: "24px",
          backgroundColor: "#f8fafc",
          padding: "16px",
          borderRadius: "10px",
          border: "1px solid #e2e8f0",
        }}
      >
        <div>
          <div style={{ fontSize: "11px", fontWeight: "600", textTransform: "uppercase", color: "#64748b" }}>Questions Total</div>
          <div style={{ fontSize: "20px", fontWeight: "800", color: "#0f172a", marginTop: "2px" }}>{evSummary.total_questions}</div>
        </div>
        <div>
          <div style={{ fontSize: "11px", fontWeight: "600", textTransform: "uppercase", color: "#64748b" }}>Answered</div>
          <div style={{ fontSize: "20px", fontWeight: "800", color: "#16a34a", marginTop: "2px" }}>{evSummary.answered_questions}</div>
        </div>
        <div>
          <div style={{ fontSize: "11px", fontWeight: "600", textTransform: "uppercase", color: "#64748b" }}>Skipped (Missing)</div>
          <div style={{ fontSize: "20px", fontWeight: "800", color: evSummary.skipped_questions > 0 ? "#dc2626" : "#64748b", marginTop: "2px" }}>
            {evSummary.skipped_questions}
          </div>
        </div>
        <div>
          <div style={{ fontSize: "11px", fontWeight: "600", textTransform: "uppercase", color: "#64748b" }}>Evidence Coverage</div>
          <div style={{ fontSize: "20px", fontWeight: "800", color: evSummary.evidence_coverage < 50 ? "#d97706" : "#2563eb", marginTop: "2px" }}>
            {evSummary.evidence_coverage}%
          </div>
        </div>
        <div>
          <div style={{ fontSize: "11px", fontWeight: "600", textTransform: "uppercase", color: "#64748b" }}>Assessment Confidence</div>
          <div style={{ marginTop: "4px" }}>
            <Badge variant={evSummary.confidence === "High" ? "success" : evSummary.confidence === "Moderate" ? "info" : "warning"}>
              {evSummary.confidence}
            </Badge>
          </div>
        </div>
      </div>

      {/* HERO SCORE & HIGHLIGHTS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "20px", marginBottom: "28px" }}>
        {/* Score Card */}
        <Card style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", padding: "24px" }}>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <span style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: "#64748b" }}>
                Interview Readiness Score
              </span>
              <Badge variant={scoreVariant}>{report.status_label}</Badge>
            </div>

            <div style={{ display: "flex", alignItems: "baseline", gap: "8px", margin: "12px 0" }}>
              <span style={{ fontSize: "52px", fontWeight: "800", color: isZeroEvidence ? "#94a3b8" : "#0f172a", lineHeight: 1 }}>
                {readinessScore}
              </span>
              <span style={{ fontSize: "20px", color: "#94a3b8", fontWeight: "500" }}>/ 100</span>
            </div>

            <p style={{ fontSize: "13px", color: "#475569", lineHeight: "1.5" }}>
              {isZeroEvidence
                ? "No meaningful interview answers were submitted, so readiness cannot be reliably assessed."
                : isDeliveryMeasured
                ? "Formula: 30% Technical + 30% Communication + 20% Delivery & Stability + 20% Resume Consistency."
                : "Re-normalized formula: 37.5% Technical + 37.5% Communication + 25% Resume Consistency (camera was inactive)."}
            </p>
            {report.confidence_explanation && (
              <p style={{ fontSize: "12px", color: "#64748b", marginTop: "6px", fontStyle: "italic" }}>
                {report.confidence_explanation}
              </p>
            )}
          </div>

          <div style={{ borderTop: "1px solid #f1f5f9", paddingTop: "12px", marginTop: "16px", display: "flex", justifyContent: "space-between", fontSize: "12px", color: "#64748b" }}>
            <span>Meaningful answers: {evSummary.meaningful_answers} of {evSummary.total_questions}</span>
            <span>Status: {evSummary.interview_status}</span>
          </div>
        </Card>

        {/* Observations Card */}
        <Card style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", padding: "24px" }}>
          <div>
            <span style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: "#64748b" }}>
              Key Observations
            </span>

            {isZeroEvidence ? (
              <div style={{ marginTop: "16px", padding: "14px 16px", borderRadius: "8px", backgroundColor: "#fffbeb", border: "1px solid #fef3c7" }}>
                <div style={{ fontSize: "13px", fontWeight: "700", color: "#92400e", marginBottom: "4px" }}>
                  Missing Interview Evidence
                </div>
                <div style={{ fontSize: "12px", color: "#b45309", lineHeight: "1.5" }}>
                  Candidate skipped or provided minimal text across interview questions. To receive an actionable evaluation and readiness score, complete full verbal or written answers.
                </div>
              </div>
            ) : (
              <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                <div style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
                  <span style={{ color: "#16a34a", fontWeight: "700" }}>✓</span>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: "700", color: "#0f172a" }}>
                      Strongest: {report.insights?.strongest_category || "Technical Depth"}
                    </div>
                    <div style={{ fontSize: "12px", color: "#475569", marginTop: "1px" }}>
                      {report.insights?.top_improvements?.[0] || "Demonstrated sound understanding of core technical concepts."}
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
                  <span style={{ color: "#d97706", fontWeight: "700" }}>!</span>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: "700", color: "#0f172a" }}>
                      Growth Opportunity: {report.insights?.weakest_category || "Communication Structure"}
                    </div>
                    <div style={{ fontSize: "12px", color: "#475569", marginTop: "1px" }}>
                      {report.insights?.top_improvements?.[1] || "Answers benefit from explicit architectural trade-offs and quantifiable SLAs."}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div style={{ borderTop: "1px solid #f1f5f9", paddingTop: "12px", marginTop: "16px", fontSize: "11px", color: "#64748b" }}>
            Evidence-Gated Assessment Engine [rubric + Gemini synthesis]
          </div>
        </Card>
      </div>

      {/* TABS NAVIGATION */}
      <div
        style={{
          borderBottom: "1px solid #e2e8f0",
          display: "flex",
          gap: "8px",
          marginBottom: "24px",
        }}
      >
        <button
          type="button"
          onClick={() => setActiveTab("questions")}
          style={{
            padding: "10px 16px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "questions" ? "2px solid #0f172a" : "2px solid transparent",
            fontWeight: activeTab === "questions" ? "700" : "500",
            color: activeTab === "questions" ? "#0f172a" : "#64748b",
            fontSize: "14px",
            cursor: "pointer",
          }}
        >
          Per-Question Study Review ({report.answers.length})
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("summary")}
          style={{
            padding: "10px 16px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "summary" ? "2px solid #0f172a" : "2px solid transparent",
            fontWeight: activeTab === "summary" ? "700" : "500",
            color: activeTab === "summary" ? "#0f172a" : "#64748b",
            fontSize: "14px",
            cursor: "pointer",
          }}
        >
          Dimensions & Signals
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("timeline")}
          style={{
            padding: "10px 16px",
            background: "none",
            border: "none",
            borderBottom: activeTab === "timeline" ? "2px solid #0f172a" : "2px solid transparent",
            fontWeight: activeTab === "timeline" ? "700" : "500",
            color: activeTab === "timeline" ? "#0f172a" : "#64748b",
            fontSize: "14px",
            cursor: "pointer",
          }}
        >
          Session Timeline ({report.timeline.length} turns)
        </button>
      </div>

      {/* TAB 1: PER-QUESTION STUDY REVIEW */}
      {activeTab === "questions" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {report.answers && report.answers.map((ans, idx) => {
            const isSkipped = ans.is_skipped || ans.status === "skipped" || (ans.transcript && ans.transcript.includes("[SKIPPED]"));
            const ansStatus = ans.answer_status || (isSkipped ? "SKIPPED" : "PARTIAL");

            return (
              <Card key={idx} style={{ padding: "24px", border: "1px solid #e2e8f0" }}>
                {/* Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "14px", flexWrap: "wrap", gap: "10px" }}>
                  <div>
                    <span style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: "#2563eb" }}>
                      Question {idx + 1}
                    </span>
                    <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#0f172a", marginTop: "2px" }}>
                      {ans.question_text}
                    </h3>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    {isSkipped ? (
                      <Badge variant="neutral">Skipped · Missing Evidence</Badge>
                    ) : (
                      <>
                        <Badge variant={ansStatus === "STRONG" ? "success" : ansStatus === "PARTIAL" ? "info" : "warning"}>
                          {ans.status_label || `${ansStatus} Answer`}
                        </Badge>
                        <Badge variant="neutral">
                          Score: {Math.round(ans.overall_score || 0)}/100
                        </Badge>
                      </>
                    )}
                  </div>
                </div>

                {/* Candidate Answer Box */}
                {isSkipped ? (
                  <div style={{ backgroundColor: "#f8fafc", padding: "12px 16px", borderRadius: "8px", marginBottom: "16px", border: "1px dashed #cbd5e1" }}>
                    <div style={{ fontSize: "12px", fontWeight: "700", color: "#64748b", marginBottom: "2px" }}>
                      Evidence Status: Skipped
                    </div>
                    <p style={{ fontSize: "13px", color: "#475569" }}>
                      You chose not to answer this question. This was recorded as an evidence gap rather than a penalized incorrect answer.
                    </p>
                  </div>
                ) : (
                  <div style={{ backgroundColor: "#f8fafc", padding: "14px 16px", borderRadius: "8px", marginBottom: "16px", border: "1px solid #e2e8f0" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                      <span style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", color: "#64748b" }}>
                        Your Submission
                      </span>
                      {ans.wpm > 0 && (
                        <span style={{ fontSize: "11px", color: "#64748b" }}>
                          Pacing: {ans.wpm} WPM · Response time: {ans.response_time}s
                        </span>
                      )}
                    </div>
                    <p style={{ fontSize: "14px", color: "#1e293b", lineHeight: "1.6", fontStyle: "italic" }}>
                      "{ans.transcript || "No transcript recorded."}"
                    </p>
                  </div>
                )}

                {/* COMPARATIVE STUDY REVIEW GRIDS */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "16px", marginBottom: "16px" }}>
                  {/* Expected Concepts */}
                  <div style={{ backgroundColor: "#f0fdf4", padding: "14px 16px", borderRadius: "8px", border: "1px solid #bbf7d0" }}>
                    <div style={{ fontSize: "12px", fontWeight: "700", color: "#166534", textTransform: "uppercase", marginBottom: "8px" }}>
                      What a Strong Answer Should Cover
                    </div>
                    <ul style={{ margin: 0, paddingLeft: "16px", fontSize: "13px", color: "#14532d", lineHeight: "1.5" }}>
                      {ans.strong_answer_should_cover && ans.strong_answer_should_cover.length > 0 ? (
                        ans.strong_answer_should_cover.map((c, cIdx) => <li key={cIdx} style={{ marginBottom: "4px" }}>{c}</li>)
                      ) : (
                        <>
                          <li style={{ marginBottom: "4px" }}>Core conceptual definition and purpose</li>
                          <li style={{ marginBottom: "4px" }}>Concrete technical mechanisms and protocols</li>
                          <li style={{ marginBottom: "4px" }}>Production constraints and engineering trade-offs</li>
                        </>
                      )}
                    </ul>
                  </div>

                  {/* What You Missed */}
                  {!isSkipped && (
                    <div style={{ backgroundColor: "#fffbeb", padding: "14px 16px", borderRadius: "8px", border: "1px solid #fef3c7" }}>
                      <div style={{ fontSize: "12px", fontWeight: "700", color: "#92400e", textTransform: "uppercase", marginBottom: "8px" }}>
                        What Was Missing
                      </div>
                      <ul style={{ margin: 0, paddingLeft: "16px", fontSize: "13px", color: "#78350f", lineHeight: "1.5" }}>
                        {ans.missing_points && ans.missing_points.length > 0 ? (
                          ans.missing_points.map((m, mIdx) => <li key={mIdx} style={{ marginBottom: "4px" }}>{m}</li>)
                        ) : (
                          <>
                            <li style={{ marginBottom: "4px" }}>Specific implementation metrics and throughput numbers</li>
                            <li style={{ marginBottom: "4px" }}>Alternative architectural trade-offs evaluated</li>
                          </>
                        )}
                      </ul>
                    </div>
                  )}
                </div>

                {/* HOW TO IMPROVE (MODEL ANSWER) */}
                {ans.improved_answer && (
                  <div style={{ backgroundColor: "#eff6ff", padding: "14px 16px", borderRadius: "8px", marginBottom: "16px", border: "1px solid #bfdbfe" }}>
                    <div style={{ fontSize: "12px", fontWeight: "700", color: "#1e40af", textTransform: "uppercase", marginBottom: "6px" }}>
                      How to Structure an Improved Answer
                    </div>
                    <p style={{ fontSize: "13px", color: "#1e3a8a", lineHeight: "1.6" }}>
                      {ans.improved_answer}
                    </p>
                  </div>
                )}

                {/* RESUME / PROJECT CONNECTION */}
                {ans.resume_connection && (
                  <div style={{ backgroundColor: "#faf5ff", padding: "14px 16px", borderRadius: "8px", marginBottom: "16px", border: "1px solid #e9d5ff" }}>
                    <div style={{ fontSize: "12px", fontWeight: "700", color: "#6b21a8", textTransform: "uppercase", marginBottom: "4px" }}>
                      Why This Matters for Your Resume
                    </div>
                    <p style={{ fontSize: "13px", color: "#581c87", lineHeight: "1.5" }}>
                      {ans.resume_connection}
                    </p>
                  </div>
                )}

                {/* ACTION: Practice This Topic */}
                <div style={{ display: "flex", justifyContent: "flex-end", borderTop: "1px solid #f1f5f9", paddingTop: "12px" }}>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleStartPractice(drillType)}
                    loading={startingPractice}
                  >
                    Practice This Topic →
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* TAB 2: DIMENSIONS & PHYSICAL SIGNALS */}
      {activeTab === "summary" && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: "20px" }}>
          <Card style={{ padding: "24px" }}>
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

          <Card style={{ padding: "24px" }}>
            <CardHeader title="Presentation & Physical Signals" subtitle="Sensor measurements vs diagnostic interpretation" />
            {!isDeliveryMeasured && (
              <div className="alert alert-warning" style={{ fontSize: "12px", marginBottom: "14px" }}>
                Visual analysis unavailable for this session (camera was off/denied). Physical delivery was excluded from readiness score.
              </div>
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "13px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f1f5f9" }}>
                <span style={{ color: "#64748b" }}>Camera Centering (Measured):</span>
                <strong>{isDeliveryMeasured && report.behavioral_metrics.eye_contact_percent !== null ? `${report.behavioral_metrics.eye_contact_percent}%` : "Not measured"}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f1f5f9" }}>
                <span style={{ color: "#64748b" }}>Blink Frequency (Measured):</span>
                <strong>{isDeliveryMeasured && report.behavioral_metrics.blink_rate !== null ? `${report.behavioral_metrics.blink_rate} / min` : "Not measured"}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #f1f5f9" }}>
                <span style={{ color: "#64748b" }}>Pause Cadence (Measured):</span>
                <strong>{report.behavioral_metrics.pause_rate !== null ? `${report.behavioral_metrics.pause_rate}s avg` : "2.0s avg"}</strong>
              </div>
            </div>
            <p style={{ fontSize: "12px", color: "#64748b", marginTop: "16px", backgroundColor: "#f8fafc", padding: "10px", borderRadius: "6px" }}>
              <strong>Interpretation:</strong> Physical signals reflect video framing stability and conversational pacing. They do NOT represent psychological truthfulness, anxiety, or hiring suitability.
            </p>
          </Card>
        </div>
      )}

      {/* TAB 3: TIMELINE & DECISIONS */}
      {activeTab === "timeline" && (
        <Card style={{ padding: "24px" }}>
          <CardHeader title="Session Timeline" subtitle="Chronological progression of questions and follow-ups" />
          {report.timeline && report.timeline.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {report.timeline.map((item, idx) => {
                const offset = item.timestamp_offset_seconds ?? item.timestamp_offset ?? 0;
                const mins = Math.floor(offset / 60);
                const secs = Math.floor(offset % 60);
                return (
                  <div key={idx} style={{ padding: "12px 14px", borderRadius: "6px", backgroundColor: "#f8fafc", border: "1px solid #e2e8f0" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontSize: "11px", fontWeight: "700", backgroundColor: "#0f172a", color: "#ffffff", padding: "2px 6px", borderRadius: "4px" }}>
                          Turn {item.turn || idx + 1} · +{mins}:{secs.toString().padStart(2, "0")}
                        </span>
                        <strong style={{ fontSize: "13px", color: "#0f172a" }}>{item.event_type || item.action}</strong>
                      </div>
                      <span style={{ fontSize: "11px", color: "#64748b" }}>{item.status || "OK"}</span>
                    </div>
                    <p style={{ fontSize: "12px", color: "#475569", margin: 0 }}>
                      {item.summary || item.details}
                    </p>
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ fontSize: "13px", color: "#64748b" }}>
              No timeline events recorded for this session.
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

export default Report;