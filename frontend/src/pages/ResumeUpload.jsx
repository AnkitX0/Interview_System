import { useState } from "react";

function ResumeUpload() {
  const [file, setFile] = useState(null);
  const [analyzed, setAnalyzed] = useState(false);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile || selectedFile.type !== "application/pdf") {
      alert("Please upload a valid PDF resume.");
      return;
    }
    setFile(selectedFile);
  };

  const handleAnalyze = () => {
    if (!file) {
      alert("Upload a resume first.");
      return;
    }

    // Placeholder logic (backend later)
    setAnalyzed(true);
  };

  return (
    <div style={{ maxWidth: "900px", margin: "0 auto" }}>
      <h2>Resume Analysis</h2>

      <div style={cardStyle}>
        <input type="file" accept=".pdf" onChange={handleFileChange} />
        
        {file && (
          <p style={{ marginTop: "10px" }}>
            Selected: <strong>{file.name}</strong>
          </p>
        )}

        <button style={primaryBtn} onClick={handleAnalyze}>
          Analyze Resume
        </button>
      </div>

      {analyzed && (
        <div style={{ ...cardStyle, marginTop: "30px" }}>
          <h3>Extracted Profile Summary</h3>
          <p><strong>Skills:</strong> Java, Python, React</p>
          <p><strong>Education:</strong> B.Tech CSE</p>
          <p><strong>Experience:</strong> Internship - Software Dev</p>
          <p style={{ marginTop: "10px", color: "#6b7280" }}>
            (AI parsing will replace this mock data)
          </p>
        </div>
      )}
    </div>
  );
}

const cardStyle = {
  background: "white",
  padding: "30px",
  borderRadius: "8px",
  marginTop: "20px",
  boxShadow: "0 2px 8px rgba(0,0,0,0.05)"
};

const primaryBtn = {
  marginTop: "20px",
  padding: "10px 20px",
  backgroundColor: "#0f172a",
  color: "white",
  border: "none",
  borderRadius: "6px",
  cursor: "pointer"
};

export default ResumeUpload;