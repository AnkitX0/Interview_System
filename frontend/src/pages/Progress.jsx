function Progress() {
  return (
    <div style={{ maxWidth: "900px", margin: "0 auto" }}>
      <h2>Performance History</h2>

      <div style={cardStyle}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #e5e7eb" }}>
              <th align="left">Attempt</th>
              <th align="left">Communication</th>
              <th align="left">Technical</th>
              <th align="left">Behavioral</th>
              <th align="left">Overall</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Attempt 1</td>
              <td>75%</td>
              <td>70%</td>
              <td>80%</td>
              <td>75%</td>
            </tr>
            <tr>
              <td>Attempt 2</td>
              <td>82%</td>
              <td>76%</td>
              <td>85%</td>
              <td>81%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

const cardStyle = {
  background: "white",
  padding: "30px",
  borderRadius: "8px",
  marginTop: "30px",
  boxShadow: "0 2px 8px rgba(0,0,0,0.05)"
};

export default Progress;