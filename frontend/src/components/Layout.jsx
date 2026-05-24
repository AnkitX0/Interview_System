import Navbar from "./Navbar";

function Layout({ children }) {
  return (
    <div style={{ fontFamily: "Arial, sans-serif", backgroundColor: "#f4f6f8", minHeight: "100vh" }}>
      <Navbar />
      <div style={{ padding: "40px" }}>
        {children}
      </div>
    </div>
  );
}

export default Layout;