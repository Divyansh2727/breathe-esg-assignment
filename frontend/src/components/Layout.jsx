import { useEffect, useState } from "react";
import { Link, Outlet, useNavigate } from "react-router-dom";
import { api, logout } from "../api";

export default function Layout() {
  const [me, setMe] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    api("/me/").then(setMe).catch(() => navigate("/login"));
  }, [navigate]);

  const org = me?.organizations?.[0];

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header
        style={{
          borderBottom: "1px solid var(--border)",
          padding: "0.75rem 1.5rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "var(--surface)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "1.5rem" }}>
          <strong style={{ color: "var(--accent)" }}>Breathe ESG</strong>
          <nav style={{ display: "flex", gap: "1rem" }}>
            <Link to="/" style={{ color: "var(--text)", textDecoration: "none" }}>
              Dashboard
            </Link>
            <Link to="/review" style={{ color: "var(--text)", textDecoration: "none" }}>
              Review queue
            </Link>
            <Link to="/upload" style={{ color: "var(--text)", textDecoration: "none" }}>
              Upload data
            </Link>
          </nav>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          {org && (
            <span style={{ color: "var(--muted)", fontSize: "0.875rem" }}>
              {org.name}
            </span>
          )}
          <span style={{ fontSize: "0.875rem" }}>{me?.username}</span>
          <button
            className="btn btn-secondary"
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </header>
      <main style={{ flex: 1, padding: "1.5rem", maxWidth: 1200, margin: "0 auto", width: "100%" }}>
        {org ? <Outlet context={{ org }} /> : <p>Loading…</p>}
      </main>
    </div>
  );
}
