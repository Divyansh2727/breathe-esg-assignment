import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { api } from "../api";

const SOURCE_HINTS = {
  sap: "Semicolon-delimited SAP ME2N/ME23N extract (fuel & procurement)",
  utility: "Green Button–style utility portal CSV (billing periods, kWh)",
  travel: "Concur Expense Report v4 JSON export",
};

export default function Upload() {
  const { org } = useOutletContext();
  const [sources, setSources] = useState([]);
  const [sourceId, setSourceId] = useState("");
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api(`/organizations/${org.id}/sources/`).then((d) => {
      const list = d.results || d;
      setSources(list);
      if (list.length) setSourceId(String(list[0].id));
    });
  }, [org.id]);

  const selected = sources.find((s) => String(s.id) === sourceId);

  async function handleUpload(e) {
    e.preventDefault();
    if (!file || !sourceId) return;
    setLoading(true);
    setError("");
    setResult(null);
    const form = new FormData();
    form.append("file", file);
    form.append("data_source_id", sourceId);
    try {
      const data = await api(`/organizations/${org.id}/ingest/`, {
        method: "POST",
        body: form,
      });
      setResult(data);
      setFile(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Upload data</h1>
      <p style={{ color: "var(--muted)" }}>
        Upload files from each client system. Parsing runs immediately; rows appear in the review queue.
      </p>

      <form className="card" onSubmit={handleUpload} style={{ maxWidth: 520 }}>
        <label style={{ display: "block", marginBottom: "1rem" }}>
          <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>Data source</span>
          <select
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
            style={{ width: "100%", marginTop: 4 }}
          >
            {sources.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        {selected && (
          <p style={{ fontSize: "0.875rem", color: "var(--muted)", marginTop: -8 }}>
            {SOURCE_HINTS[selected.source_type]}
          </p>
        )}
        <label style={{ display: "block", marginBottom: "1rem" }}>
          <span style={{ fontSize: "0.875rem", color: "var(--muted)" }}>File</span>
          <input
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            style={{ width: "100%", marginTop: 4 }}
            accept=".csv,.json,.txt"
          />
        </label>
        {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
        {result && (
          <p style={{ color: "var(--ok)" }}>
            Ingested {result.filename}: {result.success_count} rows ready, {result.error_count}{" "}
            need attention
          </p>
        )}
        <button className="btn btn-primary" type="submit" disabled={loading || !file}>
          {loading ? "Uploading…" : "Upload & parse"}
        </button>
      </form>

      <div className="card" style={{ marginTop: "1.5rem", maxWidth: 520 }}>
        <h3 style={{ marginTop: 0 }}>Sample files</h3>
        <p style={{ fontSize: "0.875rem", color: "var(--muted)" }}>
          Use files from <code>sample_data/</code> in the repository: realistic shapes with deliberate edge
          cases (unknown plant, partial billing periods, airport-only flights).
        </p>
      </div>
    </div>
  );
}
