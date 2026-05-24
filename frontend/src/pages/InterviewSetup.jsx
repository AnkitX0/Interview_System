import { useState } from "react";
import { useNavigate } from "react-router-dom";

function InterviewSetup() {
  const navigate = useNavigate();

  const [mode, setMode] = useState("practice");
  const [difficulty, setDifficulty] = useState("easy");
  const [questionCount, setQuestionCount] = useState(3);
  const [systemReady, setSystemReady] = useState(false);

  const modes = [
    {
      id: "practice",
      title: "Practice Mode",
      desc: "Confidence building with guided feedback."
    },
    {
      id: "technical",
      title: "Technical Round",
      desc: "Concept depth + structured evaluation."
    },
    {
      id: "hr",
      title: "HR Round",
      desc: "Behavioral and personality assessment."
    }
  ];

  const difficulties = ["easy", "medium", "hard"];

  const handleSystemCheck = async () => {
    try {
      await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      setSystemReady(true);
      alert("Camera & Mic ready.");
    } catch {
      alert("Please allow camera and microphone access.");
    }
  };

  const handleStart = () => {
    if (!systemReady) {
      alert("Please check camera & mic before starting.");
      return;
    }

    navigate("/interview", {
      state: { mode, difficulty, questionCount }
    });
  };

  const estimatedMinutes = (questionCount * 1.5).toFixed(1);

  return (
    <div style={{ maxWidth: "900px", margin: "0 auto", padding: "40px 20px" }}>
      <h1>Interview Setup</h1>
      <p style={{ color: "#555", marginTop: "8px" }}>
        Configure your mock interview session before starting.
      </p>

      {/* MODE SELECTION */}
      <h3 style={{ marginTop: "40px" }}>Select Interview Mode</h3>
      <div style={{ display: "flex", gap: "20px", marginTop: "15px" }}>
        {modes.map((m) => (
          <div
            key={m.id}
            onClick={() => setMode(m.id)}
            style={{
              flex: 1,
              padding: "20px",
              borderRadius: "12px",
              cursor: "pointer",
              border: mode === m.id ? "2px solid #0f172a" : "1px solid #ddd",
              background: mode === m.id ? "#f1f5f9" : "white",
              transition: "0.2s ease"
            }}
          >
            <h4>{m.title}</h4>
            <p style={{ fontSize: "14px", color: "#555" }}>{m.desc}</p>
          </div>
        ))}
      </div>

      {/* DIFFICULTY */}
      <h3 style={{ marginTop: "40px" }}>Select Difficulty</h3>
      <div style={{ display: "flex", gap: "10px", marginTop: "15px" }}>
        {difficulties.map((d) => (
          <button
            key={d}
            onClick={() => setDifficulty(d)}
            style={{
              padding: "8px 18px",
              borderRadius: "20px",
              border: difficulty === d ? "2px solid #0f172a" : "1px solid #ccc",
              background: difficulty === d ? "#0f172a" : "white",
              color: difficulty === d ? "white" : "black",
              cursor: "pointer",
              textTransform: "capitalize"
            }}
          >
            {d}
          </button>
        ))}
      </div>

      {/* QUESTION COUNT */}
      <h3 style={{ marginTop: "40px" }}>Number of Questions</h3>
      <input
        type="range"
        min="1"
        max="5"
        value={questionCount}
        onChange={(e) => setQuestionCount(Number(e.target.value))}
        style={{ width: "100%", marginTop: "15px" }}
      />
      <p style={{ marginTop: "8px" }}>
        {questionCount} question{questionCount > 1 && "s"}
      </p>

      {/* ESTIMATED TIME */}
      <div style={{ marginTop: "25px", fontWeight: "500" }}>
        Estimated Duration: {estimatedMinutes} minutes
      </div>

      {/* EVALUATION PREVIEW */}
      <div style={{
        marginTop: "30px",
        padding: "20px",
        background: "white",
        borderRadius: "10px",
        border: "1px solid #eee"
      }}>
        <h4>This session will evaluate:</h4>
        <ul style={{ marginTop: "10px", color: "#555" }}>
          <li>✔ Eye Contact & Visual Stability</li>
          <li>✔ Blink & Stress Indicators</li>
          <li>✔ Speech Behavior (Pause & Fillers)</li>
          <li>✔ Response Structure</li>
        </ul>
      </div>

      {/* SYSTEM CHECK */}
      <button
        onClick={handleSystemCheck}
        style={{
          marginTop: "30px",
          padding: "10px 20px",
          borderRadius: "8px",
          border: "none",
          background: systemReady ? "#16a34a" : "#0f172a",
          color: "white",
          cursor: "pointer"
        }}
      >
        {systemReady ? "System Ready ✓" : "Check Camera & Mic"}
      </button>

      {/* START */}
      <div style={{ textAlign: "center", marginTop: "40px" }}>
        <button
          onClick={handleStart}
          style={{
            padding: "14px 30px",
            borderRadius: "8px",
            border: "none",
            background: "#0f172a",
            color: "white",
            fontSize: "16px",
            cursor: "pointer"
          }}
        >
          Start Interview
        </button>
      </div>
    </div>
  );
}

export default InterviewSetup;