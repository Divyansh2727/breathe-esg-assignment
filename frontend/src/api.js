const API_BASE = import.meta.env.VITE_API_URL || "/api";

function getToken() {
  return localStorage.getItem("access_token");
}

export async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    localStorage.removeItem("access_token");
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data) || res.statusText);
  return data;
}

export async function login(username, password) {
  const data = await api("/auth/token/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  localStorage.setItem("access_token", data.access);
  return data;
}

export function logout() {
  localStorage.removeItem("access_token");
}
