const API = "/api";
const SESSION_KEY = "curatorx_session";
const ACTIVE_LENS_KEY = "curatorx_active_lens";

export async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  if (response.status === 204) return null;
  return response.json();
}

export function sessionId() {
  let value = localStorage.getItem(SESSION_KEY);
  if (!value) {
    value = crypto.randomUUID().replace(/-/g, "");
    localStorage.setItem(SESSION_KEY, value);
  }
  return value;
}

export function getStoredActiveLensId() {
  return localStorage.getItem(ACTIVE_LENS_KEY);
}

export function setStoredActiveLensId(lensId) {
  if (lensId) {
    localStorage.setItem(ACTIVE_LENS_KEY, lensId);
  } else {
    localStorage.removeItem(ACTIVE_LENS_KEY);
  }
}

export async function listLenses() {
  return api("/lenses");
}

export async function getActiveLens() {
  return api("/lenses/active");
}

export async function setActiveLens(lensId) {
  const lens = await api("/lenses/active", {
    method: "PUT",
    body: JSON.stringify({ lens_id: lensId }),
  });
  setStoredActiveLensId(lens.lens_id);
  return lens;
}

export async function createLens(payload) {
  return api("/lenses", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateLens(lensId, payload) {
  return api(`/lenses/${encodeURIComponent(lensId)}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function getPersona() {
  return api("/persona");
}

export async function putPersona(payload) {
  return api("/persona", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function getSystemConfig() {
  return api("/system-config");
}

export async function putSystemConfig(values) {
  return api("/system-config", {
    method: "PUT",
    body: JSON.stringify({ values }),
  });
}

export async function listJobs() {
  return api("/jobs");
}

export async function sendChat(message, lensId) {
  const body = { message, session_id: sessionId() };
  if (lensId) body.lens_id = lensId;
  return api("/chat", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function relativeTime(timestamp) {
  const seconds = Math.floor(Date.now() / 1000 - timestamp);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function resolveAgentPulse(jobs = []) {
  if (jobs.some((job) => job.status === "failed")) return "error";
  if (jobs.some((job) => job.status === "running" || job.status === "queued")) return "running";
  return "idle";
}
