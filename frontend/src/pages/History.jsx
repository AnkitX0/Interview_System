import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../utils/api";

function History() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [deletingId, setDeletingId] = useState(null);
  const limit = 10;

  const fetchHistory = async (pageNum = 1) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch(`/interview/history?page=${pageNum}&limit=${limit}`);
      if (!res.ok) throw new Error("Failed to load interview history");
      const data = await res.json();
      setSessions(data.items || []);
      setTotal(data.total || 0);
      setPage(data.page || 1);
    } catch (err) {
      console.warn("History fetch error:", err);
      setError("Unable to load interview session history. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory(page);
  }, [page]);

  const handleDeleteSession = async (sessionId) => {
    const confirmed = window.confirm(
      `Are you sure you want to permanently delete Interview Session #${sessionId}? This will remove all associated responses, scores, and audio/video metrics.`
    );
    if (!confirmed) return;

    setDeletingId(sessionId);
    try {
      const res = await apiFetch(`/interview/${sessionId}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete interview session");
      // Refresh or filter out deleted session
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      setTotal((prev) => Math.max(0, prev - 1));
    } catch (err) {
      alert(`Could not delete session: ${err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  const totalPages = Math.ceil(total / limit) || 1;

  return (
    <div style={{ maxWidth: "1100px", margin: "0 auto", paddingBottom: "70px" }}>
      {/* HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "25px" }}>
        <div>
          <h1 style={{ fontSize: "28px", color: "#0f172a" }}>Interview Session History</h1>
          <p style={{ color: "#64748b", marginTop: "4px" }}>
            Review past mock interview assessments, reopen rubric intelligence reports, or manage your data.
          </p>
        </div>

        <button onClick={() => navigate("/setup")} style={primaryBtn}>
          Start New Interview →
        </button>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", backgroundColor: "#fef2f2", color: "#991b1b", borderRadius: "8px", marginBottom: "20px", fontSize: "14px" }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: "center", padding: "80px 0" }}>
          <h3 style={{ fontSize: "20px", color: "#0f172a" }}>Loading Session Records...</h3>
        </div>
      ) : sessions.length === 0 ? (
        <div style={{ ...cardStyle, textAlign: "center", padding: "60px 20px" }}>
          <div style={{ fontSize: "40px", marginBottom: "12px" }}>📋</div>
          <h3 style={{ fontSize: "20px", color: "#0f172a" }}>No Interview Sessions Yet</h3>
          <p style={{ color: "#64748b", maxWidth: "450px", margin: "8px auto 20px" }}>
            You haven't recorded any interview sessions yet. Launch your first mock session to generate an analytics report.
          </p>
          <button onClick={() => navigate("/setup")} style={primaryBtn}>
            Start Your First Interview →
          </button>
        </div>
      ) : (
        <div style={cardStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
            <h3 style={sectionTitle}>All Recorded Sessions ({total})</h3>
            <span style={{ fontSize: "12px", color: "#64748b" }}>
              Page {page} of {totalPages}
            </span>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #e2e8f0", textAlign: "left", color: "#64748b" }}>
                  <th style={{ padding: "12px 14px" }}>Session</th>
                  <th style={{ padding: "12px 14px" }}>Date</th>
                  <th style={{ padding: "12px 14px" }}>Target Role</th>
                  <th style={{ padding: "12px 14px" }}>Mode & Difficulty</th>
                  <th style={{ padding: "12px 14px" }}>Readiness</th>
                  <th style={{ padding: "12px 14px" }}>Delivery Stability</th>
                  <th style={{ padding: "12px 14px", textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr key={s.session_id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "14px", fontWeight: "600", color: "#0f172a" }}>
                      #{s.session_id}
                    </td>
                    <td style={{ padding: "14px", color: "#475569" }}>
                      {s.created_at ? new Date(s.created_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—"}
                    </td>
                    <td style={{ padding: "14px", color: "#0f172a", fontWeight: "500" }}>
                      {s.target_role || "Software Engineer"}
                    </td>
                    <td style={{ padding: "14px", color: "#334155" }}>
                      <span style={{ textTransform: "capitalize" }}>{s.mode}</span> ({s.difficulty})
                    </td>
                    <td style={{ padding: "14px" }}>
                      {s.status === "completed" && s.readiness_score !== null && s.readiness_score > 0 ? (
                        <span
                          style={{
                            fontWeight: "700",
                            color: s.readiness_score >= 80 ? "#16a34a" : s.readiness_score >= 65 ? "#2563eb" : "#dc2626",
                          }}
                        >
                          {Math.round(s.readiness_score)}%
                        </span>
                      ) : (
                        <span style={{ color: "#94a3b8", fontSize: "12px" }}>
                          {s.status === "completed" ? "Not assessed" : "Incomplete"}
                        </span>
                      )}
                    </td>
                    <td style={{ padding: "14px" }}>
                      {s.delivery_score !== null && s.delivery_score !== undefined ? (
                        <span style={{ color: "#475569" }}>{Math.round(s.delivery_score)}%</span>
                      ) : (
                        <span style={{ color: "#94a3b8", fontSize: "12px" }}>Not measured</span>
                      )}
                    </td>
                    <td style={{ padding: "14px", textAlign: "right" }}>
                      <div style={{ display: "inline-flex", gap: "8px" }}>
                        <button
                          onClick={() => navigate(`/report?sessionId=${s.session_id}`)}
                          style={viewBtn}
                        >
                          View Report →
                        </button>
                        <button
                          onClick={() => handleDeleteSession(s.session_id)}
                          disabled={deletingId === s.session_id}
                          style={deleteBtn}
                          title="Delete session and its associated answers and metrics"
                        >
                          {deletingId === s.session_id ? "Deleting..." : "Delete"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* PAGINATION CONTROLS */}
          {totalPages > 1 && (
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "20px", paddingTop: "14px", borderTop: "1px solid #f1f5f9" }}>
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                style={{ ...viewBtn, opacity: page <= 1 ? 0.5 : 1 }}
              >
                ← Previous
              </button>
              <span style={{ fontSize: "13px", color: "#64748b" }}>
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                style={{ ...viewBtn, opacity: page >= totalPages ? 0.5 : 1 }}
              >
                Next →
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const cardStyle = {
  background: "white",
  padding: "24px",
  borderRadius: "10px",
  border: "1px solid #e2e8f0",
  boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
};

const sectionTitle = {
  fontSize: "16px",
  color: "#0f172a",
  fontWeight: "600",
  margin: 0,
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

const deleteBtn = {
  padding: "6px 10px",
  backgroundColor: "rgba(239, 68, 68, 0.08)",
  color: "#dc2626",
  border: "1px solid rgba(239, 68, 68, 0.2)",
  borderRadius: "6px",
  fontSize: "12px",
  fontWeight: "600",
  cursor: "pointer",
};

export default History;
