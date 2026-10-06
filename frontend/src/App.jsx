import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";

import Landing from "./pages/Landing";
import ResumeUpload from "./pages/ResumeUpload";
import Interview from "./pages/Interview";
import Dashboard from "./pages/Dashboard";
import FixAnswer from "./pages/FixAnswer";
import Progress from "./pages/Progress";
import InterviewSetup from "./pages/InterviewSetup";

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/resume" element={<ResumeUpload />} />
          <Route path="/setup" element={<InterviewSetup />} />

          {/* Interview Screen */}
          <Route path="/interview" element={<Interview />} />

          {/* Performance Report Screen */}
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/report" element={<Dashboard />} />

          {/* Fix My Answer & Progress */}
          <Route path="/fix-answer" element={<FixAnswer />} />
          <Route path="/progress" element={<Progress />} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;