import { useNavigate } from "react-router-dom";

function Landing() {
  const navigate = useNavigate();

  return (
    <div style={container}>

      {/* HERO */}
      <section style={heroSection}>
        <div style={heroContent}>
          <h1 style={heroTitle}>
            AI-Powered Mock Interviews with Real Performance Analytics
          </h1>

          <p style={heroSubtitle}>
            Practice like a real interview. Get scored on communication, technical depth,
            eye contact, and confidence — not guesses.
          </p>

          <div style={heroButtons}>
            <button
              style={primaryButton}
              onClick={() => navigate("/setup")}
            >
              Start Interview →
            </button>

            <button
              style={secondaryButton}
              onClick={() => navigate("/resume")}
            >
              Upload Resume
            </button>
          </div>
        </div>
      </section>

      {/* VALUE PROPOSITION */}
      <section style={section}>
        <h2 style={sectionTitle}>What Makes This Different</h2>

        <div style={grid}>
          <Card
            title="Resume-Aware Questions"
            desc="Interview questions are generated based on your resume, not generic templates."
          />
          <Card
            title="Multimodal Evaluation"
            desc="We analyze answers, voice clarity, eye contact, and behavioral signals."
          />
          <Card
            title="Structured Scoring"
            desc="Communication, Technical Depth, Behavioral Confidence — all measured."
          />
          <Card
            title="Improvement Tracking"
            desc="Track your readiness score across sessions and see measurable growth."
          />
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section style={sectionAlt}>
        <h2 style={sectionTitle}>How It Works</h2>

        <div style={steps}>
          <Step number="01" title="Upload Resume" />
          <Step number="02" title="Take AI Interview" />
          <Step number="03" title="Get Performance Report" />
        </div>
      </section>

      {/* FINAL CTA */}
      <section style={ctaSection}>
        <h2 style={{ marginBottom: "20px" }}>
          Stop Guessing. Start Measuring.
        </h2>

        <button
          style={primaryButtonLarge}
          onClick={() => navigate("/setup")}
        >
          Begin Mock Interview
        </button>
      </section>

    </div>
  );
}

/* ---------- COMPONENTS ---------- */

function Card({ title, desc }) {
  return (
    <div style={card}>
      <h4 style={{ marginBottom: "10px" }}>{title}</h4>
      <p style={{ color: "#6b7280" }}>{desc}</p>
    </div>
  );
}

function Step({ number, title }) {
  return (
    <div style={stepBox}>
      <div style={stepNumber}>{number}</div>
      <h4>{title}</h4>
    </div>
  );
}

/* ---------- STYLES ---------- */

const container = {
  maxWidth: "1100px",
  margin: "0 auto",
  padding: "40px 20px",
  fontFamily: "Inter, sans-serif"
};

const heroSection = {
  padding: "100px 0",
  textAlign: "center"
};

const heroContent = {
  maxWidth: "700px",
  margin: "0 auto"
};

const heroTitle = {
  fontSize: "44px",
  fontWeight: "600",
  marginBottom: "20px"
};

const heroSubtitle = {
  fontSize: "18px",
  color: "#6b7280",
  marginBottom: "30px"
};

const heroButtons = {
  display: "flex",
  justifyContent: "center",
  gap: "15px"
};

const section = {
  padding: "80px 0"
};

const sectionAlt = {
  padding: "80px 0",
  backgroundColor: "#f9fafb"
};

const sectionTitle = {
  textAlign: "center",
  marginBottom: "40px",
  fontSize: "28px"
};

const grid = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "20px"
};

const card = {
  background: "white",
  padding: "25px",
  borderRadius: "10px",
  boxShadow: "0 4px 12px rgba(0,0,0,0.04)"
};

const steps = {
  display: "flex",
  justifyContent: "space-around",
  textAlign: "center"
};

const stepBox = {
  padding: "20px"
};

const stepNumber = {
  fontSize: "18px",
  fontWeight: "600",
  marginBottom: "10px",
  color: "#111827"
};

const ctaSection = {
  padding: "100px 0",
  textAlign: "center"
};

const primaryButton = {
  padding: "12px 24px",
  backgroundColor: "#111827",
  color: "white",
  border: "none",
  borderRadius: "6px",
  cursor: "pointer"
};

const primaryButtonLarge = {
  ...primaryButton,
  padding: "16px 36px",
  fontSize: "16px"
};

const secondaryButton = {
  padding: "12px 24px",
  backgroundColor: "transparent",
  color: "#111827",
  border: "1px solid #111827",
  borderRadius: "6px",
  cursor: "pointer"
};

export default Landing;