import { useEffect, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import { api } from "../api";

function StatCard({ label, value, color, to }) {
  const inner = (
    <div className="card" style={{ textAlign: "center" }}>
      <div style={{ fontSize: "2rem", fontWeight: 700, color }}>{value}</div>
      <div style={{ color: "var(--muted)", fontSize: "0.875rem" }}>{label}</div>
    </div>
  );
  return to ? <Link to={to} style={{ textDecoration: "none" }}>{inner}</Link> : inner;
}

export default function Dashboard() {
  const { org } = useOutletContext();
  const [stats, setStats] = useState(null);
  const [batches, setBatches] = useState([]);

  useEffect(() => {
    api(`/organizations/${org.id}/dashboard/`).then(setStats);
    api(`/organizations/${org.id}/batches/`).then((d) => setBatches(d.results || d));
  }, [org.id]);

  if (!stats) return <p>Loading dashboard…</p>;

  const sourceLabels = { sap: "SAP", utility: "Utility", travel: "Travel" };

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Review dashboard</h1>
      <p style={{ color: "var(--muted)" }}>
        What came in, what needs attention, and what is ready for auditors.
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
          gap: "1rem",
          margin: "1.5rem 0",
        }}
      >
        <StatCard label="Total records" value={stats.total} color="var(--text)" />
        <StatCard
          label="Pending review"
          value={stats.pending}
          color="var(--pending)"
          to="/review?status=pending"
        />
        <StatCard
          label="Suspicious"
          value={stats.suspicious}
          color="var(--warn)"
          to="/review?status=suspicious"
        />
        <StatCard
          label="Failed"
          value={stats.failed}
          color="var(--danger)"
          to="/review?status=failed"
        />
        <StatCard
          label="Approved"
          value={stats.approved}
          color="var(--ok)"
          to="/review?status=approved"
        />
        <StatCard label="Locked (audit)" value={stats.locked} color="var(--muted)" />
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ marginTop: 0 }}>By source</h3>
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {Object.entries(stats.by_source || {}).map(([k, v]) => (
            <li key={k} style={{ display: "flex", justifyContent: "space-between", padding: "0.35rem 0" }}>
              <span>{sourceLabels[k] || k}</span>
              <strong>{v}</strong>
            </li>
          ))}
        </ul>
      </div>

      <h2>Recent ingestions</h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", color: "var(--muted)", fontSize: "0.875rem" }}>
            <th style={{ padding: "0.5rem" }}>File</th>
            <th>Source</th>
            <th>Status</th>
            <th>Rows</th>
            <th>When</th>
          </tr>
        </thead>
        <tbody>
          {batches.map((b) => (
            <tr key={b.id} style={{ borderTop: "1px solid var(--border)" }}>
              <td style={{ padding: "0.5rem" }}>{b.filename}</td>
              <td>{sourceLabels[b.data_source?.source_type] || b.data_source?.source_type}</td>
              <td>{b.status}</td>
              <td>
                {b.success_count} ok / {b.error_count} issues
              </td>
              <td style={{ color: "var(--muted)", fontSize: "0.875rem" }}>
                {new Date(b.created_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
