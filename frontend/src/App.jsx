import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { useLocation } from "react-router-dom";

import Layout from "./components/Layout";

import Landing from "./pages/Landing";
import ResumeUpload from "./pages/ResumeUpload";
import Interview from "./pages/Interview";
import Dashboard from "./pages/Dashboard";
import FixAnswer from "./pages/FixAnswer";
import Progress from "./pages/Progress";
import InterviewSetup from "./pages/InterviewSetup";

/* -------- Route Guards -------- */

function InterviewGuard() {
  const location = useLocation();

  if (!location.state) {
    return <Navigate to="/setup" replace />;
  }

  return <Interview />;
}

function DashboardGuard() {
  const sessionCompleted = sessionStorage.getItem("interviewCompleted");

  if (!sessionCompleted) {
    return <Navigate to="/" replace />;
  }

  return <Dashboard />;
}

/* -------- App -------- */

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/resume" element={<ResumeUpload />} />
          <Route path="/setup" element={<InterviewSetup />} />

          {/* Protected Interview */}
          <Route path="/interview" element={<InterviewGuard />} />

          {/* Protected Dashboard */}
          <Route path="/dashboard" element={<DashboardGuard />} />

          <Route path="/fix-answer" element={<FixAnswer />} />
          <Route path="/progress" element={<Progress />} />

          {/* Catch all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;