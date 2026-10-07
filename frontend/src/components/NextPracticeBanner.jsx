import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../utils/api";

export default function NextPracticeBanner({ recommendations, targetRole = "Software Engineer", difficulty = "medium" }) {
  const navigate = useNavigate();
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState(null);

  const primaryRec = recommendations && recommendations.length > 0 ? recommendations[0] : null;
  if (!primaryRec) return null;

  const handleStart = async () => {
    setStarting(true);
    setError(null);
    try {
      const res = await apiFetch("/practice/start", {
        method: "POST",
        body: JSON.stringify({
          practice_type: primaryRec.practice_type || "TECHNICAL_DEPTH",
          recommendation_id: primaryRec.id,
          target_role: targetRole,
          difficulty: primaryRec.difficulty || difficulty || "medium",
          question_count: primaryRec.target_count || 5,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error?.message || "Failed to initialize practice session.");
      }

      const data = await res.json();
      sessionStorage.setItem("currentSessionId", data.session_id);
      navigate("/interview", { state: { sessionId: data.session_id } });
    } catch (err) {
      console.error("Practice start error:", err);
      setError(err.message || "Failed to start targeted practice.");
      setStarting(false);
    }
  };

  const practiceTypeFormatted = (primaryRec.practice_type || "Technical Depth").replace(/_/g, " ").toLowerCase();
  const titleFormatted = practiceTypeFormatted.replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div
      style={{
        backgroundColor: "#0f172a",
        color: "#ffffff",
        borderRadius: "12px",
        padding: "24px 28px",
        marginBottom: "28px",
        border: "1px solid #1e293b",
        boxShadow: "0 4px 12px rgba(15, 23, 42, 0.15)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
        <div style={{ flex: 1, minWidth: "300px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
            <span
              style={{
                fontSize: "11px",
                fontWeight: "700",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                backgroundColor: "#2563eb",
                color: "#ffffff",
                padding: "3px 8px",
                borderRadius: "4px",
              }}
            >
              Next Best Practice
            </span>
            <span style={{ fontSize: "13px", color: "#94a3b8" }}>
              Targeted Drill • {primaryRec.target_count || 5} Questions • Est. 5–10 min
            </span>
          </div>

          <h2 style={{ fontSize: "22px", fontWeight: "700", color: "#f8fafc", margin: "0 0 8px 0" }}>
            Next Recommended Practice: {primaryRec.weakness || titleFormatted}
          </h2>

          <p style={{ fontSize: "14px", color: "#cbd5e1", margin: "0 0 10px 0", lineHeight: "1.5" }}>
            <strong style={{ color: "#38bdf8" }}>
              {primaryRec.source_session_id ? `Diagnosed in Session #${primaryRec.source_session_id}: ` : "Why: "}
            </strong>
            {primaryRec.rationale || "Address recurring performance gaps identified during evaluation."}
          </p>

          <div style={{ fontSize: "13px", color: "#94a3b8" }}>
            <strong>Goal: </strong>
            {primaryRec.practice_objective || "Enhance response structure and concrete evidence depth."}
          </div>

          {error && (
            <div style={{ marginTop: "10px", color: "#f87171", fontSize: "13px" }}>
              {error}
            </div>
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", justifyContent: "center" }}>
          <button
            onClick={handleStart}
            disabled={starting}
            style={{
              backgroundColor: "#2563eb",
              color: "#ffffff",
              padding: "12px 24px",
              borderRadius: "8px",
              fontWeight: "600",
              fontSize: "15px",
              border: "none",
              cursor: starting ? "not-allowed" : "pointer",
              transition: "background-color 0.2s",
              boxShadow: "0 2px 6px rgba(37, 99, 235, 0.4)",
            }}
          >
            {starting ? "Launching Drill..." : "Start Practice Drill →"}
          </button>
          <span style={{ fontSize: "12px", color: "#64748b", marginTop: "8px" }}>
            Mode: {primaryRec.practice_type === "PRESSURE_RESPONSE" ? "45s Safe Pressure" : "Adaptive Practice"} • 5–10 min
          </span>
        </div>
      </div>
    </div>
  );
}
