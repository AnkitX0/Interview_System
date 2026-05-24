function StatCard({ title, value }) {
  return (
    <div style={{
      backgroundColor: "white",
      padding: "20px",
      borderRadius: "8px",
      width: "200px",
      boxShadow: "0 2px 8px rgba(0,0,0,0.05)"
    }}>
      <p style={{ fontSize: "14px", color: "#6b7280" }}>{title}</p>
      <h3 style={{ marginTop: "10px" }}>{value}</h3>
    </div>
  );
}

export default StatCard;