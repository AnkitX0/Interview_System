import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { apiFetch } from "../utils/api";
import NextPracticeBanner from "../components/NextPracticeBanner";

function Progress() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch("/progress")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch progress");
        return res.json();
      })
      .then((prog) => {
        setData(prog);
        setLoading(false);
      })
      .catch((err) => {
        console.warn("Progress fetch fallback:", err);
        setData({
          total_interviews: 0,
          average_readiness_score: 0,
          best_score: 0,
          latest_score: 0,
          improvement_percentage: 0,
          weakest_category: "N/A",
          sessions: [],
          trend: [],
          longitudinal_readiness: null,
          recurring_weaknesses: [],
          improvement_velocity: null,
          next_practice: [],
        });
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "80px 0" }}>
        <h3 style={{ fontSize: "20px", color: "#0f172a" }}>Loading Candidate Performance Intelligence...</h3>
        <p style={{ color: "#64748b", marginTop: "8px" }}>Evaluating longitudinal trajectory and recurring weaknesses.</p>
      </div>
    );
  }

  const hasData = data && data.total_interviews > 0;
  const longi = data?.longitudinal_readiness;
  const velocity = data?.improvement_velocity;
  const recurring = data?.recurring_weaknesses || [];

  const getConfidenceBadgeColor = (conf) => {
    if (conf === "high") return { bg: "#dcfce7", color: "#166534" };
    if (conf === "medium") return { bg: "#dbeafe", color: "#1e40af" };
    if (conf === "low") return { bg: "#fef3c7", color: "#92400e" };
    return { bg: "#f1f5f9", color: "#475569" };
  };

  const getTrendBadgeColor = (trend) => {
    if (trend === "improving") return { bg: "#dcfce7", color: "#166534" };
    if (trend === "declining") return { bg: "#fee2e2", color: "#991b1b" };
    return { bg: "#f1f5f9", color: "#334155" };
  };

  return (
    <div style={{ maxWidth: "1100px", margin: "0 auto", paddingBottom: "70px" }}>
      {/* HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "25px" }}>
        <div>
          <h1 style={{ fontSize: "28px", color: "#0f172a" }}>Performance Intelligence & Learning Loop</h1>
          <p style={{ color: "#64748b", marginTop: "4px" }}>
            Longitudinal readiness estimation, recurring weakness diagnosis, and targeted practice prescribing.
          </p>
        </div>

        <button onClick={() => navigate("/setup")} style={primaryBtn}>
          Start Full Interview →
        </button>
      </div>

      {!hasData ? (
        <div style={{ ...cardStyle, textAlign: "center", padding: "60px 20px" }}>
          <div style={{ fontSize: "44px", marginBottom: "12px" }}>📊</div>
          <h3 style={{ fontSize: "20px", color: "#0f172a" }}>No Interview Sessions Recorded Yet</h3>
          <p style={{ color: "#64748b", maxWidth: "500px", margin: "8px auto 24px" }}>
            Complete your first AI mock interview to establish your performance baseline and track progress over time.
          </p>
          <button onClick={() => navigate("/setup")} style={primaryBtn}>
            Take Your First Mock Interview →
          </button>
        </div>
      ) : (
        <>
          {/* NEXT BEST PRACTICE BANNER */}
          {data.next_practice && data.next_practice.length > 0 && (
            <NextPracticeBanner
              recommendations={data.next_practice}
              targetRole={data.sessions?.[0]?.target_role}
            />
          )}

          {/* LONGITUDINAL READINESS & VELOCITY PROFILE */}
          {longi && (
            <div
              style={{
                ...cardStyle,
                marginBottom: "25px",
                borderLeft: "4px solid #2563eb",
                backgroundColor: "#f8fafc",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
                    <span style={{ fontSize: "12px", fontWeight: "700", textTransform: "uppercase", color: "#64748b" }}>
                      Longitudinal Readiness Engine
                    </span>
                    {longi.confidence && (
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: "700",
                          textTransform: "uppercase",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          backgroundColor: getConfidenceBadgeColor(longi.confidence).bg,
                          color: getConfidenceBadgeColor(longi.confidence).color,
                        }}
                      >
                        Confidence: {longi.confidence.replace("_", " ")}
                      </span>
                    )}
                    {longi.trend && (
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: "700",
                          textTransform: "uppercase",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          backgroundColor: getTrendBadgeColor(longi.trend).bg,
                          color: getTrendBadgeColor(longi.trend).color,
                        }}
                      >
                        Trend: {longi.trend}
                      </span>
                    )}
                  </div>

                  <div style={{ display: "flex", alignItems: "baseline", gap: "12px" }}>
                    <div style={{ fontSize: "36px", fontWeight: "800", color: "#0f172a" }}>
                      {longi.current_readiness ?? data.latest_score}
                    </div>
                    <div style={{ fontSize: "16px", color: "#64748b" }}>/100 readiness estimate</div>
                    {velocity && velocity.status === "computed" && (
                      <div style={{ fontSize: "13px", color: velocity.readiness_delta >= 0 ? "#16a34a" : "#dc2626", fontWeight: "600" }}>
                        ({velocity.readiness_delta >= 0 ? "+" : ""}{velocity.readiness_delta} pts across {velocity.sessions_count} comparable sessions)
                      </div>
                    )}
                  </div>

                  <p style={{ fontSize: "13px", color: "#475569", marginTop: "6px" }}>
                    {longi.trend_description}
                  </p>
                </div>

                {longi.target && (
                  <div
                    style={{
                      backgroundColor: "#ffffff",
                      padding: "14px 18px",
                      borderRadius: "8px",
                      border: "1px solid #e2e8f0",
                      minWidth: "260px",
                    }}
                  >
                    <div style={{ fontSize: "11px", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
                      Target Readiness: {longi.target.threshold}%
                    </div>
                    <div style={{ fontSize: "18px", fontWeight: "700", color: longi.target.gap <= 0 ? "#16a34a" : "#0f172a", marginTop: "4px" }}>
                      {longi.target.gap <= 0 ? "Target Achieved" : `${longi.target.gap} points away`}
                    </div>
                    <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px", lineHeight: "1.4" }}>
                      {longi.target.message}
                    </div>
                  </div>
                )}
              </div>

              {/* Baseline Projection notice */}
              {longi.projection && longi.projection.is_meaningful && (
                <div style={{ marginTop: "14px", paddingTop: "12px", borderTop: "1px solid #e2e8f0", fontSize: "12px", color: "#475569" }}>
                  <strong style={{ color: "#0f172a" }}>{longi.projection.type}: </strong>
                  {longi.projection.description}
                </div>
              )}
            </div>
          )}

          {/* STAT CARDS ROW */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "14px", marginBottom: "25px" }}>
            <MetricCard title="Total Sessions" value={data.total_interviews} subtitle="Attempts logged" />
            <MetricCard title="Avg Readiness" value={`${data.average_readiness_score}%`} subtitle="Overall average" color="#2563eb" />
            <MetricCard title="Peak Score" value={`${data.best_score}%`} subtitle="Personal best" color="#16a34a" />
            <MetricCard title="Latest Score" value={`${data.latest_score}%`} subtitle="Most recent attempt" />
            <MetricCard
              title="Growth Trend"
              value={`${data.improvement_percentage >= 0 ? "+" : ""}${data.improvement_percentage}%`}
              subtitle="Baseline to latest"
              color={data.improvement_percentage >= 0 ? "#16a34a" : "#dc2626"}
            />
          </div>

          {/* RECURRING WEAKNESS HISTORY TABLE */}
          {recurring.length > 0 && (
            <div style={{ ...cardStyle, marginBottom: "25px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <div>
                  <h3 style={sectionTitle}>Recurring Weakness Diagnosis & Trajectory</h3>
                  <p style={{ fontSize: "12px", color: "#64748b", marginTop: "2px" }}>
                    Longitudinal patterns tracked across consecutive comparable sessions
                  </p>
                </div>
                <span style={{ fontSize: "12px", color: "#64748b" }}>
                  {recurring.filter((w) => w.recurring).length} Recurring • {recurring.length} Total Tracked
                </span>
              </div>

              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid #e2e8f0", textAlign: "left", color: "#64748b" }}>
                      <th style={{ padding: "10px 14px" }}>Weakness & Root Diagnosis</th>
                      <th style={{ padding: "10px 14px" }}>Dimension</th>
                      <th style={{ padding: "10px 14px" }}>Occurrences</th>
                      <th style={{ padding: "10px 14px" }}>Severity</th>
                      <th style={{ padding: "10px 14px" }}>Trend</th>
                      <th style={{ padding: "10px 14px" }}>Recommended Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recurring.map((w) => (
                      <tr key={w.weakness_id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                        <td style={{ padding: "12px 14px" }}>
                          <div style={{ fontWeight: "600", color: "#0f172a" }}>
                            {w.root_weakness || w.weakness_id}
                          </div>
                          <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
                            {w.symptom}
                          </div>
                        </td>
                        <td style={{ padding: "12px 14px", textTransform: "capitalize", color: "#475569" }}>
                          {w.dimension}
                        </td>
                        <td style={{ padding: "12px 14px" }}>
                          <span
                            style={{
                              fontSize: "12px",
                              fontWeight: "700",
                              padding: "2px 8px",
                              borderRadius: "4px",
                              backgroundColor: w.recurring ? "#fee2e2" : "#f1f5f9",
                              color: w.recurring ? "#991b1b" : "#475569",
                            }}
                          >
                            {w.occurrence_count} / {w.total_sessions_analyzed || data.total_interviews} sessions
                            {w.recurring ? " (Recurring)" : ""}
                          </span>
                        </td>
                        <td style={{ padding: "12px 14px" }}>
                          <span
                            style={{
                              fontSize: "11px",
                              fontWeight: "700",
                              textTransform: "uppercase",
                              padding: "2px 6px",
                              borderRadius: "4px",
                              backgroundColor: w.latest_severity === "high" ? "#fee2e2" : "#fef3c7",
                              color: w.latest_severity === "high" ? "#991b1b" : "#92400e",
                            }}
                          >
                            {w.latest_severity}
                          </span>
                        </td>
                        <td style={{ padding: "12px 14px" }}>
                          <span
                            style={{
                              fontSize: "12px",
                              fontWeight: "600",
                              color: w.trend === "improving" ? "#16a34a" : w.trend === "worsening" ? "#dc2626" : "#64748b",
                            }}
                          >
                            {w.trend}
                          </span>
                          <div style={{ fontSize: "11px", color: "#94a3b8" }}>{w.trend_explanation}</div>
                        </td>
                        <td style={{ padding: "12px 14px", color: "#2563eb", fontWeight: "500", fontSize: "12px" }}>
                          {w.recommended_action?.practice_type?.replace(/_/g, " ") || "Targeted Drill"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* MULTI-SESSION SCORE TRAJECTORY CHART */}
          <div style={{ ...cardStyle, marginBottom: "25px" }}>
            <h3 style={sectionTitle}>Multi-Session Score Trajectory</h3>
            <p style={{ fontSize: "12px", color: "#64748b", marginBottom: "16px" }}>
              Evolution of your readiness and dimension scores across consecutive mock interview attempts
            </p>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={data.trend} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="attempt" style={{ fontSize: "12px" }} />
                <YAxis domain={[0, 100]} style={{ fontSize: "12px" }} />
                <Tooltip formatter={(value) => [`${value}%`]} />
                <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                <Line type="monotone" dataKey="readiness_score" name="Readiness Score" stroke="#0f172a" strokeWidth={3} dot={{ r: 5 }} />
                <Line type="monotone" dataKey="technical_score" name="Technical Depth" stroke="#10b981" strokeWidth={2} />
                <Line type="monotone" dataKey="communication_score" name="Communication" stroke="#3b82f6" strokeWidth={2} />
                <Line type="monotone" dataKey="behavioral_score" name="Delivery & Stability" stroke="#8b5cf6" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* SESSIONS TABLE */}
          <div style={cardStyle}>
            <h3 style={sectionTitle}>Historical Sessions Audit Log</h3>
            <div style={{ overflowX: "auto", marginTop: "14px" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #e2e8f0", textAlign: "left", color: "#64748b" }}>
                    <th style={{ padding: "10px 14px" }}>Session</th>
                    <th style={{ padding: "10px 14px" }}>Date & Time</th>
                    <th style={{ padding: "10px 14px" }}>Round Mode</th>
                    <th style={{ padding: "10px 14px" }}>Difficulty</th>
                    <th style={{ padding: "10px 14px" }}>Readiness Score</th>
                    <th style={{ padding: "10px 14px" }}>Status</th>
                    <th style={{ padding: "10px 14px", textAlign: "right" }}>Report Action</th>
                  </tr>
                </thead>
                <tbody>
                  {data.sessions?.map((s) => (
                    <tr key={s.session_id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "12px 14px", fontWeight: "600", color: "#0f172a" }}>
                        #{s.session_id}
                      </td>
                      <td style={{ padding: "12px 14px", color: "#475569" }}>{s.date}</td>
                      <td style={{ padding: "12px 14px", color: "#334155" }}>{s.mode}</td>
                      <td style={{ padding: "12px 14px", color: "#64748b" }}>{s.difficulty}</td>
                      <td style={{ padding: "12px 14px" }}>
                        <span
                          style={{
                            fontWeight: "700",
                            color: s.readiness_score >= 80 ? "#16a34a" : s.readiness_score >= 65 ? "#2563eb" : "#dc2626",
                          }}
                        >
                          {s.readiness_score}%
                        </span>
                      </td>
                      <td style={{ padding: "12px 14px" }}>
                        <span style={statusTag}>{s.status}</span>
                      </td>
                      <td style={{ padding: "12px 14px", textAlign: "right" }}>
                        <div style={{ display: "inline-flex", gap: "8px" }}>
                          <button
                            onClick={() => navigate(`/report?sessionId=${s.session_id}`, { state: { sessionId: s.session_id } })}
                            style={viewBtn}
                          >
                            View Report
                          </button>
                          <button
                            onClick={async () => {
                              if (window.confirm(`Permanently delete interview session #${s.session_id}?`)) {
                                try {
                                  const res = await apiFetch(`/interview/${s.session_id}`, { method: "DELETE" });
                                  if (res.ok) {
                                    setData((prev) => ({
                                      ...prev,
                                      total_interviews: prev.total_interviews - 1,
                                      sessions: prev.sessions.filter((item) => item.session_id !== s.session_id),
                                      trend: prev.trend.filter((item) => item.session_id !== s.session_id),
                                    }));
                                  }
                                } catch (err) {
                                  alert(`Could not delete session: ${err.message}`);
                                }
                              }
                            }}
                            style={{
                              padding: "6px 10px",
                              backgroundColor: "rgba(239, 68, 68, 0.08)",
                              color: "#dc2626",
                              border: "1px solid rgba(239, 68, 68, 0.2)",
                              borderRadius: "6px",
                              fontSize: "12px",
                              fontWeight: "600",
                              cursor: "pointer",
                            }}
                            title="Delete session"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function MetricCard({ title, value, subtitle, color = "#0f172a" }) {
  return (
    <div style={cardStyle}>
      <span style={{ fontSize: "11px", fontWeight: "600", color: "#64748b", textTransform: "uppercase" }}>{title}</span>
      <div style={{ fontSize: "24px", fontWeight: "800", color, marginTop: "4px" }}>{value}</div>
      <p style={{ fontSize: "11px", color: "#94a3b8", marginTop: "2px" }}>{subtitle}</p>
    </div>
  );
}

/* STYLES */
const cardStyle = {
  background: "white",
  padding: "20px",
  borderRadius: "10px",
  border: "1px solid #e2e8f0",
  boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
};

const sectionTitle = {
  fontSize: "16px",
  color: "#0f172a",
  fontWeight: "600",
};

const primaryBtn = {
  padding: "10px 18px",
  backgroundColor: "#0f172a",
  color: "white",
  border: "none",
  borderRadius: "6px",
  fontSize: "13px",
  fontWeight: "600",
  cursor: "pointer",
};

const viewBtn = {
  padding: "6px 12px",
  backgroundColor: "#f1f5f9",
  color: "#0f172a",
  border: "1px solid #cbd5e1",
  borderRadius: "6px",
  fontSize: "12px",
  fontWeight: "600",
  cursor: "pointer",
};

const statusTag = {
  fontSize: "11px",
  fontWeight: "700",
  padding: "3px 8px",
  borderRadius: "12px",
  backgroundColor: "#dcfce7",
  color: "#15803d",
  textTransform: "capitalize",
};

export default Progress;