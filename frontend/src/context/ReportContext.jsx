import { createContext, useState, useEffect } from "react";

export const ReportContext = createContext();

export function ReportProvider({ children }) {
  const [reportData, setReportDataState] = useState(() => {
    try {
      const saved = sessionStorage.getItem("reportData");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [resumeData, setResumeDataState] = useState(() => {
    try {
      const saved = sessionStorage.getItem("resumeData");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [currentSessionId, setCurrentSessionIdState] = useState(() => {
    try {
      return sessionStorage.getItem("currentSessionId") || null;
    } catch {
      return null;
    }
  });

  const setReportData = (data) => {
    setReportDataState(data);
    try {
      if (data) {
        sessionStorage.setItem("reportData", JSON.stringify(data));
      } else {
        sessionStorage.removeItem("reportData");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const setResumeData = (data) => {
    setResumeDataState(data);
    try {
      if (data) {
        sessionStorage.setItem("resumeData", JSON.stringify(data));
      } else {
        sessionStorage.removeItem("resumeData");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const setCurrentSessionId = (id) => {
    setCurrentSessionIdState(id);
    try {
      if (id) {
        sessionStorage.setItem("currentSessionId", String(id));
      } else {
        sessionStorage.removeItem("currentSessionId");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const clearReportContext = () => {
    setReportDataState(null);
    setResumeDataState(null);
    setCurrentSessionIdState(null);
    try {
      sessionStorage.removeItem("reportData");
      sessionStorage.removeItem("resumeData");
      sessionStorage.removeItem("currentSessionId");
      sessionStorage.clear();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <ReportContext.Provider
      value={{
        reportData,
        setReportData,
        resumeData,
        setResumeData,
        currentSessionId,
        setCurrentSessionId,
        clearReportContext,
      }}
    >
      {children}
    </ReportContext.Provider>
  );
}