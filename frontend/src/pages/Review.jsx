import { useCallback, useEffect, useState } from "react";
import { useOutletContext, useSearchParams } from "react-router-dom";
import { api } from "../api";

function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

export default function Review() {
  const { org } = useOutletContext();
  const [params, setParams] = useSearchParams();
  const statusFilter = params.get("status") || "";
  const [rows, setRows] = useState([]);
  const [selected, setSelected] = useState(null);
  const [notes, setNotes] = useState("");

  const load = useCallback(() => {
    let q = `/organizations/${org.id}/activities/?`;
    if (statusFilter) q += `status=${statusFilter}&`;
    api(q).then((d) => setRows(d.results || d));
  }, [org.id, statusFilter]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (selected) setNotes(selected.analyst_notes || "");
  }, [selected]);

  async function approve(id) {
    await api(`/organizations/${org.id}/activities/${id}/approve/`, { method: "POST" });
    load();
    setSelected(null);
  }

  async function lock(id) {
    await api(`/organizations/${org.id}/activities/${id}/lock/`, { method: "POST" });
    load();
    setSelected(null);
  }

  async function saveNotes(id) {
    await api(`/organizations/${org.id}/activities/${id}/`, {
      method: "PATCH",
      body: JSON.stringify({ analyst_notes: notes }),
    });
    load();
  }

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Review queue</h1>
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        {["", "pending", "suspicious", "failed", "approved", "locked"].map((s) => (
          <button
            key={s || "all"}
            className={`btn ${statusFilter === s ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setParams(s ? { status: s } : {})}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: "1rem" }}>
        <div className="card" style={{ padding: 0, overflow: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
            <thead>
              <tr style={{ color: "var(--muted)", textAlign: "left" }}>
                <th style={{ padding: "0.5rem" }}>Status</th>
                <th>Scope</th>
                <th>Description</th>
                <th>Qty</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.id}
                  onClick={() => setSelected(r)}
                  style={{
                    borderTop: "1px solid var(--border)",
                    cursor: "pointer",
                    background: selected?.id === r.id ? "var(--surface-2)" : "transparent",
                  }}
                >
                  <td style={{ padding: "0.5rem" }}>
                    <StatusBadge status={r.review_status} />
                  </td>
                  <td>{r.scope}</td>
                  <td>{r.description?.slice(0, 50)}</td>
                  <td>
                    {r.quantity} {r.unit}
                  </td>
                  <td style={{ color: "var(--muted)" }}>{r.data_source_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {selected ? (
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Record detail</h3>
            <StatusBadge status={selected.review_status} />
            <dl style={{ fontSize: "0.875rem", marginTop: "1rem" }}>
              <dt style={{ color: "var(--muted)" }}>Category</dt>
              <dd>
                Scope {selected.scope} — {selected.category}
              </dd>
              <dt style={{ color: "var(--muted)" }}>Period</dt>
              <dd>
                {selected.period_start} → {selected.period_end}
              </dd>
              <dt style={{ color: "var(--muted)" }}>Facility</dt>
              <dd>
                {selected.facility_code} {selected.facility_name && `(${selected.facility_name})`}
              </dd>
              <dt style={{ color: "var(--muted)" }}>Normalized</dt>
              <dd>
                {selected.quantity} {selected.unit}
                {selected.original_unit !== selected.unit && (
                  <span style={{ color: "var(--muted)" }}>
                    {" "}
                    (from {selected.original_quantity} {selected.original_unit})
                  </span>
                )}
              </dd>
            </dl>
            {selected.suspicion_reasons?.length > 0 && (
              <div style={{ marginBottom: "1rem" }}>
                <strong style={{ color: "var(--warn)" }}>Flags</strong>
                <ul style={{ margin: "0.25rem 0", paddingLeft: "1.25rem" }}>
                  {selected.suspicion_reasons.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            )}
            {selected.validation_errors?.length > 0 && (
              <div style={{ marginBottom: "1rem" }}>
                <strong style={{ color: "var(--danger)" }}>Errors</strong>
                <ul style={{ margin: "0.25rem 0", paddingLeft: "1.25rem" }}>
                  {selected.validation_errors.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            )}
            <label style={{ display: "block", marginBottom: "0.75rem" }}>
              <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Analyst notes</span>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                style={{ width: "100%", marginTop: 4 }}
                disabled={selected.review_status === "locked"}
              />
            </label>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {selected.review_status !== "locked" && (
                <button className="btn btn-secondary" onClick={() => saveNotes(selected.id)}>
                  Save notes
                </button>
              )}
              {["pending", "suspicious"].includes(selected.review_status) && (
                <button className="btn btn-primary" onClick={() => approve(selected.id)}>
                  Approve
                </button>
              )}
              {selected.review_status === "approved" && (
                <button className="btn btn-primary" onClick={() => lock(selected.id)}>
                  Lock for audit
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="card" style={{ color: "var(--muted)" }}>
            Select a row to review details and approve.
          </div>
        )}
      </div>
    </div>
  );
}
