import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api";

export default function Login() {
  const [username, setUsername] = useState("analyst");
  const [password, setPassword] = useState("demo-analyst-2025");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(username, password);
      navigate("/");
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <form className="card" onSubmit={handleSubmit} style={{ width: 360 }}>
        <h1 style={{ marginTop: 0, color: "var(--accent)" }}>Breathe ESG</h1>
        <p style={{ color: "var(--muted)", marginBottom: "1.5rem" }}>
          Analyst sign-in for emissions data review
        </p>
        <label style={{ display: "block", marginBottom: "0.75rem" }}>
          <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Username</span>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={{ width: "100%", marginTop: 4 }}
            autoComplete="username"
          />
        </label>
        <label style={{ display: "block", marginBottom: "1rem" }}>
          <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ width: "100%", marginTop: 4 }}
            autoComplete="current-password"
          />
        </label>
        {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
        <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: "100%" }}>
          {loading ? "Signing in…" : "Sign in"}
        </button>
        <p style={{ fontSize: "0.75rem", color: "var(--muted)", marginTop: "1rem" }}>
          Demo: analyst / demo-analyst-2025
        </p>
      </form>
    </div>
  );
}
