import { createContext, useState } from "react";

export const ReportContext = createContext();

export function ReportProvider({ children }) {
  const [reportData, setReportData] = useState(null);

  return (
    <ReportContext.Provider value={{ reportData, setReportData }}>
      {children}
    </ReportContext.Provider>
  );
}