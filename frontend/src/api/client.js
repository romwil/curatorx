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

export const LLM_PROVIDER_DEFAULTS = {
  openai: "https://api.openai.com/v1",
  anthropic: "https://api.anthropic.com",
  gemini: "https://generativelanguage.googleapis.com/v1beta/openai",
  groq: "https://api.groq.com/openai/v1",
  mistral: "https://api.mistral.ai/v1",
  together: "https://api.together.xyz/v1",
  deepseek: "https://api.deepseek.com/v1",
  ollama: "http://localhost:11434/v1",
  openrouter: "https://openrouter.ai/api/v1",
  custom_openai_compatible: "",
  openai_compatible: "https://api.openai.com/v1",
};

export const LLM_MODEL_DEFAULTS = {
  openai: "gpt-4o-mini",
  anthropic: "claude-sonnet-4-6",
  gemini: "gemini-2.0-flash",
  groq: "llama-3.3-70b-versatile",
  mistral: "mistral-small-latest",
  together: "meta-llama/Llama-3.3-70B-Instruct-Turbo",
  deepseek: "deepseek-chat",
  ollama: "llama3",
  openrouter: "openai/gpt-4o-mini",
  custom_openai_compatible: "gpt-4o-mini",
  openai_compatible: "gpt-4o-mini",
};

export const ANTHROPIC_MODEL_OPTIONS = [
  "claude-sonnet-4-6",
  "claude-sonnet-4-20250514",
  "claude-sonnet-4-5-20250929",
  "claude-3-5-haiku-20241022",
  "claude-3-haiku-20240307",
  "claude-haiku-4-5",
];

const ANTHROPIC_MODEL_ALIASES = {
  "claude-sonnet-4": "claude-sonnet-4-6",
  "claude-sonnet-4-5": "claude-sonnet-4-5-20250929",
  "claude-sonnet-4-0": "claude-sonnet-4-6",
  "claude-3-5-sonnet": "claude-sonnet-4-6",
  "claude-3-5-sonnet-latest": "claude-sonnet-4-6",
  "claude-3-sonnet": "claude-sonnet-4-6",
  "claude-3-5-haiku": "claude-3-5-haiku-20241022",
  "claude-3-5-haiku-latest": "claude-3-5-haiku-20241022",
  "claude-3-haiku": "claude-3-haiku-20240307",
  "claude-3-haiku-latest": "claude-3-haiku-20240307",
  "claude-haiku-4-5-20251001": "claude-haiku-4-5",
};

const DEPRECATED_ANTHROPIC_MODELS = {
  "claude-3-5-sonnet-20241022": "claude-sonnet-4-6",
  "claude-3-5-sonnet-20240620": "claude-sonnet-4-6",
  "claude-3-opus-20240229": "claude-sonnet-4-6",
};

const ANTHROPIC_DATED_MODEL = /^claude-[a-z0-9.-]+-\d{8}$/i;

const OPENAI_MODEL_PREFIXES = ["gpt-", "o1", "o3", "o4", "text-embedding", "chatgpt-"];

export function modelLooksOpenai(model) {
  const cleaned = String(model || "").toLowerCase().trim();
  return OPENAI_MODEL_PREFIXES.some((prefix) => cleaned.startsWith(prefix));
}

export function modelLooksAnthropic(model) {
  return String(model || "").toLowerCase().trim().startsWith("claude");
}

export function normalizeAnthropicModel(model) {
  const defaultModel = LLM_MODEL_DEFAULTS.anthropic;
  const cleaned = String(model || "").trim();
  if (!cleaned) return defaultModel;
  if (modelLooksOpenai(cleaned)) return defaultModel;

  const lowered = cleaned.toLowerCase();
  if (ANTHROPIC_MODEL_ALIASES[lowered]) return ANTHROPIC_MODEL_ALIASES[lowered];
  if (DEPRECATED_ANTHROPIC_MODELS[lowered]) return DEPRECATED_ANTHROPIC_MODELS[lowered];
  if (lowered.endsWith("-latest")) return defaultModel;
  const known = ANTHROPIC_MODEL_OPTIONS.find((option) => option.toLowerCase() === lowered);
  if (known) return known;
  if (ANTHROPIC_DATED_MODEL.test(lowered)) return lowered;
  if (modelLooksAnthropic(lowered)) return defaultModel;
  return defaultModel;
}

export function resolveModelForProvider(provider, model) {
  const defaultModel = LLM_MODEL_DEFAULTS[provider] ?? LLM_MODEL_DEFAULTS.openai;
  const cleaned = String(model || "").trim();
  if (!cleaned) return defaultModel;
  if (provider === "anthropic") return normalizeAnthropicModel(cleaned);
  if (
    ["openai", "openai_compatible", "custom_openai_compatible"].includes(provider) &&
    modelLooksAnthropic(cleaned)
  ) {
    return LLM_MODEL_DEFAULTS.openai;
  }
  return cleaned;
}

export const LLM_PROVIDER_OPTIONS = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic (Claude)" },
  { value: "gemini", label: "Google Gemini" },
  { value: "groq", label: "Groq" },
  { value: "mistral", label: "Mistral" },
  { value: "together", label: "Together AI" },
  { value: "deepseek", label: "DeepSeek" },
  { value: "openrouter", label: "OpenRouter" },
  { value: "ollama", label: "Ollama (local)" },
  { value: "custom_openai_compatible", label: "Custom OpenAI-compatible" },
];

export const WIZARD_STEPS = [
  "identity_llm",
  "media_core",
  "automation",
  "persona",
  "optional_services",
];

export const AUTO_CERTIFY_SERVICES = [
  "llm",
  "plex",
  "radarr",
  "sonarr",
  "tmdb",
  "fanart",
  "tautulli",
];

export async function getWizardStatus() {
  return api("/setup/wizard");
}

export async function getCertifications() {
  return api("/setup/certifications");
}

export async function getSettings() {
  return api("/settings");
}

export async function saveSettings(payload) {
  return api("/settings", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function testService(service, settings) {
  return api(`/setup/test/${service}`, {
    method: "POST",
    body: JSON.stringify(settings),
  });
}
