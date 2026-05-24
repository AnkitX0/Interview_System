import { useEffect, useState } from "react";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer
} from "recharts";

function Dashboard() {
  const [sessionData, setSessionData] = useState(null);
  const [trendData, setTrendData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch latest session score
    fetch("http://127.0.0.1:8000/interview/latest")
      .then((res) => res.json())
      .then((data) => {
        setSessionData(data);
      })
      .catch((err) => {
        console.error("Error fetching latest session:", err);
      });

    // Fetch all sessions for trend
    fetch("http://127.0.0.1:8000/interview/all")
      .then((res) => res.json())
      .then((data) => {
        setTrendData(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching trend data:", err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <h3 style={{ textAlign: "center", marginTop: "50px" }}>
        Loading session data...
      </h3>
    );
  }

  if (!sessionData || sessionData.message) {
    return (
      <h3 style={{ textAlign: "center", marginTop: "50px" }}>
        No interview data available.
      </h3>
    );
  }

  return (
    <div style={{ maxWidth: "1100px", margin: "0 auto" }}>
      <h2>Interview Performance Analytics</h2>

      {/* ================= OVERALL METRICS ================= */}
      <div style={metricsContainer}>
        <MetricCard
          title="Behavioral Score"
          value={sessionData.behavioral_score}
        />
      </div>

      {/* ================= BEHAVIORAL TREND ================= */}
      <div style={sectionCard}>
        <h3>Behavioral Trend</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="attempt" />
            <YAxis />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="behavioral_score"
              stroke="#0f172a"
              strokeWidth={3}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/* ================= SMALL COMPONENTS ================= */

function MetricCard({ title, value }) {
  return (
    <div style={metricCard}>
      <h4>{title}</h4>
      <p style={{ fontSize: "28px", fontWeight: "bold" }}>{value}</p>
    </div>
  );
}

/* ================= STYLES ================= */

const metricsContainer = {
  display: "flex",
  gap: "20px",
  flexWrap: "wrap",
  marginTop: "30px"
};

const metricCard = {
  background: "white",
  padding: "20px",
  borderRadius: "8px",
  boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
  minWidth: "180px"
};

const sectionCard = {
  background: "white",
  padding: "25px",
  borderRadius: "8px",
  marginTop: "30px",
  boxShadow: "0 2px 8px rgba(0,0,0,0.05)"
};

export default Dashboard;