const API = "/api";

function token() {
  return localStorage.getItem("access_token");
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (token()) headers.Authorization = `Bearer ${token()}`;
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API}${path}`, { ...options, headers });
  if (res.status === 401) {
    localStorage.removeItem("access_token");
    location.hash = "#/login";
    throw new Error("Unauthorized");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data) || res.statusText);
  return data;
}

function el(tag, attrs, ...children) {
  const n = document.createElement(tag);
  if (attrs) {
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === "className") n.className = v;
      else if (k.startsWith("on")) n.addEventListener(k.slice(2).toLowerCase(), v);
      else if (k === "html") n.innerHTML = v;
      else n.setAttribute(k, v);
    });
  }
  children.flat().forEach((c) => {
    if (c == null) return;
    n.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  });
  return n;
}

function badge(status) {
  return el("span", { className: `badge badge-${status}` }, status);
}

let state = { me: null, org: null, selected: null, rows: [], stats: null };

async function loadMe() {
  state.me = await api("/me/");
  state.org = state.me.organizations[0];
}

function layout(content) {
  const root = document.getElementById("root");
  root.innerHTML = "";
  const hash = location.hash.slice(1) || "/";
  const header = el("header", null,
    el("div", null,
      el("strong", { style: "color:var(--accent)" }, "Breathe ESG"),
      el("nav", { style: "display:inline;margin-left:1.5rem" },
        link("#/", "Dashboard", hash === "/"),
        link("#/review", "Review queue", hash.startsWith("/review")),
        link("#/upload", "Upload data", hash === "/upload")
      )
    ),
    el("div", null,
      state.org ? el("span", { style: "color:var(--muted);margin-right:1rem;font-size:0.875rem" }, state.org.name) : "",
      el("span", { style: "margin-right:1rem;font-size:0.875rem" }, state.me?.username || ""),
      el("button", { className: "btn btn-secondary", onClick: () => {
        localStorage.removeItem("access_token");
        location.hash = "#/login";
      }}, "Sign out")
    )
  );
  root.append(header, el("main", null, content));
}

function link(href, text, active) {
  return el("a", { href, className: active ? "active" : "" }, text);
}

async function pageLogin() {
  const root = document.getElementById("root");
  root.innerHTML = "";
  const err = el("p", { className: "error" });
  const form = el("form", { className: "card", style: "width:360px;margin:4rem auto" },
    el("h1", { style: "margin-top:0;color:var(--accent)" }, "Breathe ESG"),
    el("p", { style: "color:var(--muted)" }, "Analyst sign-in"),
    field("Username", "text", "analyst"),
    field("Password", "password", "demo-analyst-2025"),
    err,
    el("button", { className: "btn btn-primary", type: "submit", style: "width:100%" }, "Sign in"),
    el("p", { style: "font-size:0.75rem;color:var(--muted)" }, "Demo: analyst / demo-analyst-2025")
  );
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    err.textContent = "";
    try {
      const u = form.querySelector('[name="user"]').value;
      const p = form.querySelector('[name="pass"]').value;
      const data = await api("/auth/token/", {
        method: "POST",
        body: JSON.stringify({ username: u, password: p }),
      });
      localStorage.setItem("access_token", data.access);
      location.hash = "#/";
    } catch (ex) {
      err.textContent = ex.message;
    }
  });
  root.append(form);
}

function field(label, type, def) {
  const wrap = el("label", { style: "display:block;margin-bottom:0.75rem" });
  wrap.append(
    el("span", { style: "font-size:0.875rem;color:var(--muted);display:block" }, label),
    el("input", { name: type === "password" ? "pass" : "user", type, value: def, style: "width:100%;margin-top:4px" })
  );
  return wrap;
}

async function pageDashboard() {
  await loadMe();
  const stats = await api(`/organizations/${state.org.id}/dashboard/`);
  const batches = await api(`/organizations/${state.org.id}/batches/`);
  const list = batches.results || batches;
  const labels = { sap: "SAP", utility: "Utility", travel: "Travel" };

  layout(
    el("div", null,
      el("h1", { style: "margin-top:0" }, "Review dashboard"),
      el("div", { className: "stat-grid" },
        stat("Total", stats.total, "var(--text)"),
        stat("Pending", stats.pending, "var(--pending)", "#/review?status=pending"),
        stat("Suspicious", stats.suspicious, "var(--warn)", "#/review?status=suspicious"),
        stat("Failed", stats.failed, "var(--danger)", "#/review?status=failed"),
        stat("Approved", stats.approved, "var(--ok)", "#/review?status=approved"),
        stat("Locked", stats.locked, "var(--muted)")
      ),
      el("div", { className: "card" },
        el("h3", { style: "margin-top:0" }, "By source"),
        ...Object.entries(stats.by_source || {}).map(([k, v]) =>
          el("div", { style: "display:flex;justify-content:space-between;padding:0.35rem 0" },
            labels[k] || k, el("strong", null, String(v))
          )
        )
      ),
      el("h2", null, "Recent ingestions"),
      batchesTable(list, labels)
    )
  );
}

function stat(label, value, color, href) {
  const card = el("div", { className: "card", style: "text-align:center" },
    el("div", { style: `font-size:2rem;font-weight:700;color:${color}` }, String(value)),
    el("div", { style: "color:var(--muted);font-size:0.875rem" }, label)
  );
  return href ? el("a", { href }, card) : card;
}

function batchesTable(list, labels) {
  const t = el("table", null,
    el("thead", null, el("tr", null, th("File"), th("Source"), th("Status"), th("Rows"), th("When")))
  );
  const tb = el("tbody");
  list.forEach((b) => {
    tb.append(el("tr", null,
      el("td", null, b.filename),
      el("td", null, labels[b.data_source?.source_type] || ""),
      el("td", null, b.status),
      el("td", null, `${b.success_count} ok / ${b.error_count} issues`),
      el("td", { style: "color:var(--muted)" }, new Date(b.created_at).toLocaleString())
    ));
  });
  t.append(tb);
  return t;
}

function th(t) { return el("th", { style: "padding:0.5rem" }, t); }

async function pageReview() {
  await loadMe();
  const q = new URLSearchParams(location.hash.split("?")[1] || "");
  const status = q.get("status") || "";
  let url = `/organizations/${state.org.id}/activities/?`;
  if (status) url += `status=${status}&`;
  const rows = await api(url);
  state.rows = rows.results || rows;
  state.selected = null;

  const filters = el("div", { style: "margin-bottom:1rem" }, ...["", "pending", "suspicious", "failed", "approved", "locked"].map((s) =>
    el("button", {
      className: `btn ${status === s ? "btn-primary" : "btn-secondary"}`,
      style: "margin-right:0.5rem",
      onClick: () => { location.hash = s ? `#/review?status=${s}` : "#/review"; },
    }, s || "All")
  ));

  const detail = el("div", { className: "card" }, "Select a row to review.");

  function renderDetail() {
    detail.innerHTML = "";
    const r = state.selected;
    if (!r) {
      detail.append("Select a row to review.");
      return;
    }
    detail.append(
      el("h3", { style: "margin-top:0" }, "Record detail"),
      badge(r.review_status),
      el("dl", { style: "font-size:0.875rem" },
        dt("Category"), dd(`Scope ${r.scope} — ${r.category}`),
        dt("Period"), dd(`${r.period_start} → ${r.period_end}`),
        dt("Facility"), dd(`${r.facility_code} ${r.facility_name || ""}`),
        dt("Quantity"), dd(`${r.quantity} ${r.unit}`)
      )
    );
    if (r.suspicion_reasons?.length) {
      detail.append(el("strong", { style: "color:var(--warn)" }, "Flags"));
      detail.append(list(r.suspicion_reasons));
    }
    const notes = el("textarea", { rows: 3, style: "width:100%", value: r.analyst_notes || "" });
    detail.append(el("label", null, "Analyst notes", notes));
    if (r.review_status !== "locked") {
      detail.append(el("button", {
        className: "btn btn-secondary",
        style: "margin-top:0.5rem;display:block",
        onClick: async () => {
          await api(`/organizations/${state.org.id}/activities/${r.id}/`, {
            method: "PATCH",
            body: JSON.stringify({ analyst_notes: notes.value }),
          });
          alert("Notes saved");
        },
      }, "Save notes"));
    }
    if (["pending", "suspicious"].includes(r.review_status)) {
      detail.append(el("button", {
        className: "btn btn-primary",
        style: "margin-top:0.5rem;display:block",
        onClick: async () => {
          await api(`/organizations/${state.org.id}/activities/${r.id}/approve/`, { method: "POST" });
          location.reload();
        },
      }, "Approve"));
    }
    if (r.review_status === "approved") {
      detail.append(el("button", {
        className: "btn btn-primary",
        style: "margin-top:0.5rem;display:block",
        onClick: async () => {
          await api(`/organizations/${state.org.id}/activities/${r.id}/lock/`, { method: "POST" });
          location.reload();
        },
      }, "Lock for audit"));
    }
  }

  const tbody = el("tbody");
  state.rows.forEach((r) => {
    tbody.append(el("tr", {
      className: state.selected?.id === r.id ? "selected" : "",
      onClick: () => { state.selected = r; renderDetail(); document.querySelectorAll("tr").forEach((tr) => tr.classList.remove("selected")); tbody.querySelectorAll("tr").forEach((tr, i) => { if (state.rows[i].id === r.id) tr.classList.add("selected"); }); },
    },
      el("td", null, badge(r.review_status)),
      el("td", null, r.scope),
      el("td", null, (r.description || "").slice(0, 50)),
      el("td", null, `${r.quantity} ${r.unit}`),
      el("td", { style: "color:var(--muted)" }, r.data_source_type)
    ));
  });

  layout(el("div", null,
    el("h1", { style: "margin-top:0" }, "Review queue"),
    filters,
    el("div", { className: "review-grid" },
      el("div", { className: "card", style: "padding:0;overflow:auto" },
        el("table", null, el("thead", null, el("tr", null, th("Status"), th("Scope"), th("Description"), th("Qty"), th("Source"))), tbody)
      ),
      detail
    )
  ));
  renderDetail();
}

function dt(t) { return el("dt", { style: "color:var(--muted)" }, t); }
function dd(t) { return el("dd", null, t); }
function list(items) {
  const u = el("ul");
  items.forEach((i) => u.append(el("li", null, i)));
  return u;
}

async function pageUpload() {
  await loadMe();
  const sources = await api(`/organizations/${state.org.id}/sources/`);
  const list = sources.results || sources;
  const msg = el("p", { className: "ok" });
  const err = el("p", { className: "error" });
  const sel = el("select", { style: "width:100%;margin-top:4px" }, ...list.map((s) =>
    el("option", { value: s.id }, s.name)
  ));
  const file = el("input", { type: "file", style: "width:100%;margin-top:4px" });

  layout(el("div", null,
    el("h1", { style: "margin-top:0" }, "Upload data"),
    el("form", { className: "card", style: "max-width:520px", onSubmit: async (e) => {
      e.preventDefault();
      msg.textContent = "";
      err.textContent = "";
      const f = file.files[0];
      if (!f) return;
      const form = new FormData();
      form.append("file", f);
      form.append("data_source_id", sel.value);
      try {
        const data = await api(`/organizations/${state.org.id}/ingest/`, { method: "POST", body: form });
        msg.textContent = `Ingested: ${data.success_count} ok, ${data.error_count} issues`;
      } catch (ex) {
        err.textContent = ex.message;
      }
    }},
      el("label", null, "Data source", sel),
      el("label", { style: "display:block;margin:1rem 0" }, "File", file),
      err, msg,
      el("button", { className: "btn btn-primary", type: "submit" }, "Upload & parse")
    )
  ));
}

async function route() {
  const hash = location.hash.slice(1) || "/";
  const path = hash.split("?")[0];
  if (path === "/login" || (!token() && path !== "/login")) {
    if (!token()) return pageLogin();
  }
  if (!token()) return pageLogin();
  try {
    if (path === "/" || path === "") return pageDashboard();
    if (path.startsWith("/review")) return pageReview();
    if (path === "/upload") return pageUpload();
    return pageDashboard();
  } catch (e) {
    console.error(e);
    pageLogin();
  }
}

window.addEventListener("hashchange", route);
route();
