import { useNavigate } from "react-router-dom";

function Landing() {
  const navigate = useNavigate();

  return (
    <div style={container}>
      {/* HERO */}
      <section style={heroSection}>
        <div style={heroContent}>
          <div style={badgeHero}>Enterprise AI Interview Preparation</div>
          <h1 style={heroTitle}>
            Practice Interviews with Objective AI Intelligence & Real Performance Analytics
          </h1>

          <p style={heroSubtitle}>
            Tailor questions to your actual resume. Get rigorous rubric evaluations on technical depth,
            STAR reasoning, communication clarity, and behavioral presence.
          </p>

          <div style={heroButtons}>
            <button style={primaryButton} onClick={() => navigate("/resume")}>
              Upload Resume & Begin →
            </button>

            <button style={secondaryButton} onClick={() => navigate("/setup")}>
              Quick Mock Interview
            </button>
          </div>
        </div>
      </section>

      {/* VALUE PROPOSITION */}
      <section style={section}>
        <h2 style={sectionTitle}>Why Interview Intelligence Outperforms Generic Practice</h2>

        <div style={grid}>
          <Card
            title="Resume-Aware Dynamic Questioning"
            desc="Questions are automatically tailored to your specific technologies, frameworks, and career history."
          />
          <Card
            title="Structured Rubric Scoring"
            desc="Standardized 0-100 rubric evaluations across Technical Depth, STAR Structure, Reasoning, and Consistency."
          />
          <Card
            title="Multimodal Diagnostic Signals"
            desc="Tracks speech pacing (WPM), filler word habits, eye contact, and response structure."
          />
          <Card
            title="Fix My Answer AI Coach"
            desc="Directly refactors weak answers into polished STAR responses while preserving your real experience."
          />
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section style={sectionAlt}>
        <h2 style={sectionTitle}>Complete End-to-End Interview Workflow</h2>

        <div style={steps}>
          <Step
            number="01"
            title="Upload Resume"
            desc="Extract technical competencies, detect weak phrasing, and audit clarity."
            onClick={() => navigate("/resume")}
          />
          <Step
            number="02"
            title="AI Mock Interview"
            desc="Answer dynamic technical and behavioral questions under realistic pressure."
            onClick={() => navigate("/setup")}
          />
          <Step
            number="03"
            title="Performance Report"
            desc="Review multidimensional subscores, radar analytics, and actionable advice."
            onClick={() => navigate("/dashboard")}
          />
          <Step
            number="04"
            title="Fix Weak Answers"
            desc="Iteratively polish your weak answers using the structured STAR framework."
            onClick={() => navigate("/fix-answer")}
          />
        </div>
      </section>

      {/* FINAL CTA */}
      <section style={ctaSection}>
        <h2 style={{ fontSize: "32px", marginBottom: "16px", color: "#0f172a" }}>
          Ready to Test Your Real Interview Readiness?
        </h2>
        <p style={{ color: "#64748b", marginBottom: "30px", fontSize: "16px" }}>
          Start with your resume to experience personalized mock interview rounds.
        </p>

        <button style={primaryButtonLarge} onClick={() => navigate("/resume")}>
          Get Started Now — Upload Resume →
        </button>
      </section>
    </div>
  );
}

function Card({ title, desc }) {
  return (
    <div style={card}>
      <h4 style={{ marginBottom: "10px", fontSize: "16px", color: "#0f172a" }}>{title}</h4>
      <p style={{ color: "#64748b", fontSize: "14px", lineHeight: "1.5" }}>{desc}</p>
    </div>
  );
}

function Step({ number, title, desc, onClick }) {
  return (
    <div style={stepBox} onClick={onClick}>
      <div style={stepNumber}>{number}</div>
      <h4 style={{ fontSize: "15px", color: "#0f172a" }}>{title}</h4>
      <p style={{ fontSize: "12px", color: "#64748b", marginTop: "6px", lineHeight: "1.4" }}>{desc}</p>
    </div>
  );
}

/* STYLES */
const container = {
  maxWidth: "1100px",
  margin: "0 auto",
  padding: "20px 20px 60px",
  fontFamily: "Inter, sans-serif",
};

const badgeHero = {
  display: "inline-block",
  fontSize: "12px",
  fontWeight: "700",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  padding: "4px 12px",
  backgroundColor: "#eff6ff",
  color: "#2563eb",
  borderRadius: "20px",
  marginBottom: "16px",
};

const heroSection = {
  padding: "70px 0 60px",
  textAlign: "center",
};

const heroContent = {
  maxWidth: "760px",
  margin: "0 auto",
};

const heroTitle = {
  fontSize: "42px",
  fontWeight: "700",
  lineHeight: "1.2",
  color: "#0f172a",
  marginBottom: "18px",
  letterSpacing: "-0.02em",
};

const heroSubtitle = {
  fontSize: "17px",
  color: "#64748b",
  lineHeight: "1.6",
  marginBottom: "32px",
};

const heroButtons = {
  display: "flex",
  justifyContent: "center",
  gap: "14px",
};

const section = {
  padding: "60px 0",
};

const sectionAlt = {
  padding: "60px 24px",
  backgroundColor: "white",
  borderRadius: "12px",
  border: "1px solid #e2e8f0",
};

const sectionTitle = {
  textAlign: "center",
  marginBottom: "35px",
  fontSize: "24px",
  color: "#0f172a",
};

const grid = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "20px",
};

const card = {
  background: "white",
  padding: "24px",
  borderRadius: "10px",
  border: "1px solid #e2e8f0",
  boxShadow: "0 1px 3px rgba(0,0,0,0.03)",
};

const steps = {
  display: "grid",
  gridTemplateColumns: "repeat(4, 1fr)",
  gap: "15px",
  textAlign: "center",
};

const stepBox = {
  padding: "16px 12px",
  background: "#f8fafc",
  borderRadius: "8px",
  border: "1px solid #e2e8f0",
  cursor: "pointer",
  transition: "all 0.15s ease",
};

const stepNumber = {
  fontSize: "14px",
  fontWeight: "800",
  marginBottom: "8px",
  color: "#2563eb",
};

const ctaSection = {
  padding: "70px 0 40px",
  textAlign: "center",
};

const primaryButton = {
  padding: "13px 26px",
  backgroundColor: "#0f172a",
  color: "white",
  border: "none",
  borderRadius: "6px",
  fontSize: "15px",
  fontWeight: "600",
  cursor: "pointer",
};

const primaryButtonLarge = {
  ...primaryButton,
  padding: "15px 36px",
  fontSize: "16px",
  backgroundColor: "#2563eb",
};

const secondaryButton = {
  padding: "13px 26px",
  backgroundColor: "white",
  color: "#0f172a",
  border: "1px solid #cbd5e1",
  borderRadius: "6px",
  fontSize: "15px",
  fontWeight: "600",
  cursor: "pointer",
};

export default Landing;