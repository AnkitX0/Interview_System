import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import { ReportProvider } from "./context/ReportContext";

ReactDOM.createRoot(document.getElementById("root")).render(
    <ReportProvider>
      <App />
    </ReportProvider>
);