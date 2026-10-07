import React from "react";
import Navbar from "./Navbar";

function Layout({ children }) {
  return (
    <div
      style={{
        backgroundColor: "var(--bg-app)",
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        color: "var(--text-primary)",
      }}
    >
      <Navbar />

      <main
        style={{
          flex: 1,
          paddingTop: "var(--space-6)",
          paddingBottom: "var(--space-12)",
        }}
      >
        {children}
      </main>

      <footer
        style={{
          backgroundColor: "#ffffff",
          borderTop: "1px solid var(--border-default)",
          padding: "20px 16px",
          marginTop: "auto",
        }}
      >
        <div
          className="container"
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "12px",
            fontSize: "12px",
            color: "var(--text-muted)",
          }}
        >
          <div>
            <strong>Interview Intelligence</strong> — Systematic career interview preparation.
          </div>
          <div>
            Video frames analyzed locally in browser. Audio processed for transcription. Your data is kept until you delete it.
          </div>
        </div>
      </footer>
    </div>
  );
}

export default Layout;