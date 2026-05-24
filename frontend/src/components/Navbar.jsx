import { Link } from "react-router-dom";

function Navbar() {
  return (
    <nav style={navStyle}>
      <h2 style={{ margin: 0 }}>Vortex</h2>
      <div>
        <Link to="/" style={linkStyle}>Home</Link>
        <Link to="/resume" style={linkStyle}>Resume</Link>
        <Link to="/interview" style={linkStyle}>Interview</Link>
        <Link to="/dashboard" style={linkStyle}>Dashboard</Link>
        <Link to="/progress" style={linkStyle}>Progress</Link>
      </div>
    </nav>
  );
}

const navStyle = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "18px 60px",
  backgroundColor: "#0f172a",
  color: "white",
  borderBottom: "1px solid #1e293b"
};

const linkStyle = {
  marginLeft: "30px",
  textDecoration: "none",
  color: "#cbd5e1",
  fontSize: "14px",
  fontWeight: "500"
};

export default Navbar;