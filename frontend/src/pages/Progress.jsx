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

function Progress() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/progress")
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
        // Fallback empty state
        setData({
          total_interviews: 0,
          average_readiness_score: 0,
          best_score: 0,
          latest_score: 0,
          improvement_percentage: 0,
          weakest_category: "N/A",
          sessions: [],
          trend: [],
        });
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "80px 0" }}>
        <h3 style={{ fontSize: "20px", color: "#0f172a" }}>Loading Candidate Progress History...</h3>
      </div>
    );
  }

  const hasData = data && data.total_interviews > 0;

  return (
    <div style={{ maxWidth: "1100px", margin: "0 auto", paddingBottom: "70px" }}>
      {/* HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "25px" }}>
        <div>
          <h1 style={{ fontSize: "28px", color: "#0f172a" }}>Interview Performance & Growth History</h1>
          <p style={{ color: "#64748b", marginTop: "4px" }}>
            Track readiness score trajectories and competency development across sessions.
          </p>
        </div>

        <button onClick={() => navigate("/setup")} style={primaryBtn}>
          Start New Interview →
        </button>
      </div>

      {!hasData ? (
        /* SENSIBLE EMPTY STATE */
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

          {/* TREND CHART */}
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
                <Line type="monotone" dataKey="behavioral_score" name="Behavioral Signals" stroke="#8b5cf6" strokeWidth={2} />
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
                        <span style={statusTag}>
                          {s.status}
                        </span>
                      </td>
                      <td style={{ padding: "12px 14px", textAlign: "right" }}>
                        <button
                          onClick={() => navigate(`/dashboard?sessionId=${s.session_id}`)}
                          style={viewBtn}
                        >
                          View Report →
                        </button>
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