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
      <h4 style={{ marginBottom: "10px", fontSize: "16px", color: "var(--text-primary)", fontWeight: "600" }}>{title}</h4>
      <p style={{ color: "var(--text-secondary)", fontSize: "14px", lineHeight: "1.5", margin: 0 }}>{desc}</p>
    </div>
  );
}

function Step({ number, title, desc, onClick }) {
  return (
    <div style={stepBox} onClick={onClick}>
      <div style={stepNumber}>{number}</div>
      <h4 style={{ fontSize: "15px", color: "var(--text-primary)", fontWeight: "600" }}>{title}</h4>
      <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "6px", lineHeight: "1.4" }}>{desc}</p>
    </div>
  );
}

/* STYLES (Aligned with Design Tokens) */
const container = {
  maxWidth: "1100px",
  margin: "0 auto",
  padding: "20px 20px 60px",
  fontFamily: "inherit",
};

const badgeHero = {
  display: "inline-block",
  fontSize: "12px",
  fontWeight: "700",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  padding: "4px 12px",
  backgroundColor: "var(--primary-50)",
  color: "var(--primary-600)",
  borderRadius: "20px",
  marginBottom: "16px",
};

const heroSection = {
  padding: "60px 0 50px",
  textAlign: "center",
};

const heroContent = {
  maxWidth: "760px",
  margin: "0 auto",
};

const heroTitle = {
  fontSize: "38px",
  fontWeight: "700",
  lineHeight: "1.25",
  color: "var(--text-primary)",
  marginBottom: "18px",
  letterSpacing: "-0.02em",
};

const heroSubtitle = {
  fontSize: "16px",
  color: "var(--text-secondary)",
  lineHeight: "1.6",
  marginBottom: "32px",
};

const heroButtons = {
  display: "flex",
  justifyContent: "center",
  flexWrap: "wrap",
  gap: "14px",
};

const section = {
  padding: "50px 0",
};

const sectionAlt = {
  padding: "50px 24px",
  backgroundColor: "var(--bg-surface)",
  borderRadius: "12px",
  border: "1px solid var(--border-default)",
};

const sectionTitle = {
  textAlign: "center",
  marginBottom: "35px",
  fontSize: "24px",
  fontWeight: "700",
  color: "var(--text-primary)",
};

const grid = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
  gap: "20px",
};

const card = {
  backgroundColor: "var(--bg-surface)",
  padding: "24px",
  borderRadius: "10px",
  border: "1px solid var(--border-default)",
  boxShadow: "var(--shadow-xs)",
};

const steps = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
  gap: "16px",
  textAlign: "center",
};

const stepBox = {
  padding: "20px 16px",
  backgroundColor: "var(--bg-app)",
  borderRadius: "8px",
  border: "1px solid var(--border-default)",
  cursor: "pointer",
  transition: "border-color 150ms ease, box-shadow 150ms ease",
};

const stepNumber = {
  fontSize: "13px",
  fontWeight: "800",
  marginBottom: "8px",
  color: "var(--primary-600)",
};

const ctaSection = {
  padding: "60px 0 30px",
  textAlign: "center",
};

const primaryButton = {
  padding: "12px 24px",
  backgroundColor: "var(--primary-600)",
  color: "#FFFFFF",
  border: "none",
  borderRadius: "8px",
  fontSize: "14px",
  fontWeight: "600",
  cursor: "pointer",
  transition: "opacity 150ms ease",
};

const primaryButtonLarge = {
  ...primaryButton,
  padding: "14px 32px",
  fontSize: "15px",
};

const secondaryButton = {
  padding: "12px 24px",
  backgroundColor: "var(--bg-surface)",
  color: "var(--text-primary)",
  border: "1px solid var(--border-default)",
  borderRadius: "8px",
  fontSize: "14px",
  fontWeight: "600",
  cursor: "pointer",
};

export default Landing;