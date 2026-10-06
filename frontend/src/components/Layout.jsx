import Navbar from "./Navbar";

function Layout({ children }) {
  return (
    <div style={{ fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif", backgroundColor: "#f8fafc", minHeight: "100vh", color: "#0f172a" }}>
      <Navbar />
      <main style={{ padding: "35px 24px" }}>
        {children}
      </main>
    </div>
  );
}

export default Layout;