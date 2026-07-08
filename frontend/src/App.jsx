import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  getActiveLens,
  listJobs,
  listLenses,
  resolveAgentPulse,
  sendChat,
  setActiveLens,
  setStoredActiveLensId,
} from "./api/client";
import ChatThread from "./components/ChatThread";
import TurnstyleViewport from "./components/TurnstyleViewport";
import VisualFingerprint, { extractLatestCards } from "./components/VisualFingerprint";

const SERVICES = [
  { key: "plex", label: "Plex" },
  { key: "radarr", label: "Radarr" },
  { key: "sonarr", label: "Sonarr" },
  { key: "tmdb", label: "TMDB" },
  { key: "llm", label: "LLM" },
];

export default function App() {
  const [viewMode, setViewMode] = useState("compact");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [setup, setSetup] = useState(null);
  const [lenses, setLenses] = useState([]);
  const [activeLens, setActiveLensState] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [persona, setPersona] = useState(null);

  const refreshJobs = useCallback(() => {
    listJobs().then(setJobs).catch(console.error);
  }, []);

  useEffect(() => {
    Promise.all([
      api("/setup/status").then(setSetup),
      api("/library/stats").then(setStats),
      listLenses().then(setLenses),
      getActiveLens()
        .then((lens) => {
          setActiveLensState(lens);
          setStoredActiveLensId(lens.lens_id);
        })
        .catch(() => {
          setActiveLensState({ lens_id: "general", lens_name: "General", description: "" });
        }),
      api("/persona").then(setPersona).catch(console.error),
    ]).catch(console.error);
    refreshJobs();
    const interval = setInterval(refreshJobs, 5000);
    return () => clearInterval(interval);
  }, [refreshJobs]);

  async function handleLensSwitch(lensId) {
    try {
      const lens = await setActiveLens(lensId);
      setActiveLensState(lens);
    } catch (error) {
      console.error(error);
    }
  }

  async function sendMessage(text) {
    if (!text.trim() || loading) return;
    setLoading(true);
    const lensId = activeLens?.lens_id || "general";
    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      blocks: [{ type: "text", content: text }],
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    try {
      const result = await sendChat(text, lensId);
      setMessages((prev) => [...prev, result.message]);
      refreshJobs();
      if (extractLatestCards([result.message]).length > 0) {
        setViewMode("immersive");
      }
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          blocks: [{ type: "text", content: error.message }],
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleAdd(item, target) {
    const confirmText =
      target === "sonarr"
        ? `Add "${item.title}" to Sonarr?`
        : `Add "${item.title}" to Radarr?`;
    if (!window.confirm(confirmText)) return;
    const action = target === "sonarr" ? "add_sonarr" : "add_radarr";
    const body =
      target === "sonarr"
        ? { action, tvdb_id: item.tvdb_id, title: item.title }
        : { action, tmdb_id: item.tmdb_id, title: item.title };
    const proposal = await api("/actions/propose", { method: "POST", body: JSON.stringify(body) });
    await api("/actions/confirm", {
      method: "POST",
      body: JSON.stringify({ token: proposal.confirmation_token, confirmed: true }),
    });
    alert(`Added ${item.title}`);
  }

  async function handleDismiss(item) {
    await api("/preferences", {
      method: "POST",
      body: JSON.stringify({
        signal_type: "dismiss",
        text: `Not interested in ${item.title}`,
        tmdb_id: item.tmdb_id,
        tvdb_id: item.tvdb_id,
        media_type: item.media_type,
        lens_id: activeLens?.lens_id,
      }),
    });
  }

  async function syncLibrary() {
    const job = await api("/library/sync", { method: "POST" });
    refreshJobs();
    alert(`Library sync started (${job.id})`);
  }

  const agentPulse = resolveAgentPulse(jobs);
  const lensActive = Boolean(activeLens?.lens_id);
  const curatorName = persona?.curator_name || "Curator";

  return (
    <div className={`app-root ${viewMode} ${lensActive ? "lens-active" : ""}`}>
      {viewMode === "compact" ? (
        <div className="turnstyle-shell">
          <header className="turnstyle-topbar">
            <div>
              <p className="eyebrow">{curatorName}</p>
              <h1>CuratorX</h1>
            </div>
            <div className="topbar-actions">
              <span className={`agent-pulse ${agentPulse}`} title={`Agent ${agentPulse}`} />
              {stats ? (
                <span className="stat-chip">
                  {stats.total} indexed
                </span>
              ) : null}
              <Link to="/config" className="btn-link ghost">
                Config
              </Link>
            </div>
          </header>

          {setup && !setup.onboarding_complete ? (
            <div className="banner">
              Finish setup in <Link to="/config">Settings</Link> to connect Plex, TMDB, and your LLM provider.
            </div>
          ) : null}

          <TurnstyleViewport
            lensName={activeLens?.lens_name}
            input={input}
            onInputChange={setInput}
            onSubmit={() => sendMessage(input)}
            onExpand={() => setViewMode("immersive")}
            loading={loading}
            jobs={jobs}
          />
        </div>
      ) : (
        <div className="immersive-shell">
          <aside className="immersive-sidebar">
            <div className="sidebar-brand">
              <p className="eyebrow">{curatorName}</p>
              <h2>CuratorX</h2>
              <span className={`agent-pulse ${agentPulse}`} title={`Agent ${agentPulse}`} />
            </div>

            <section className="sidebar-section">
              <p className="eyebrow">Lenses</p>
              <div className="lens-switcher">
                {lenses.map((lens) => (
                  <button
                    key={lens.lens_id}
                    type="button"
                    className={`lens-chip ${lens.lens_id === activeLens?.lens_id ? "active" : ""}`}
                    onClick={() => handleLensSwitch(lens.lens_id)}
                  >
                    {lens.lens_name}
                  </button>
                ))}
              </div>
            </section>

            <section className="sidebar-section">
              <p className="eyebrow">Integrations</p>
              <div className="integration-chips">
                {SERVICES.map(({ key, label }) => {
                  const check = setup?.checks?.[key];
                  return (
                    <span key={key} className={`integration-chip ${check?.ok ? "ok" : "pending"}`}>
                      {label}
                    </span>
                  );
                })}
              </div>
            </section>

            <div className="sidebar-actions">
              <button type="button" className="ghost" onClick={() => setViewMode("compact")}>
                Collapse
              </button>
              <button type="button" onClick={syncLibrary}>
                Sync library
              </button>
              <Link to="/config" className="btn-link ghost">
                Configuration
              </Link>
            </div>

            {stats ? (
              <p className="sidebar-stats">
                {stats.total} titles · {stats.movies} movies · {stats.shows} shows
              </p>
            ) : null}
          </aside>

          <main className="immersive-main">
            <div className="immersive-chat">
              <ChatThread
                messages={messages}
                onAdd={handleAdd}
                onDismiss={handleDismiss}
                onOpenViewport={() => setViewMode("immersive")}
              />
              <form
                className="composer immersive-composer"
                onSubmit={(event) => {
                  event.preventDefault();
                  sendMessage(input);
                }}
              >
                <div className="composer-lens-tag">
                  ⧉ {activeLens?.lens_name || "General"}
                </div>
                <textarea
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  placeholder="Continue the conversation in this lens…"
                  rows={2}
                />
                <button type="submit" disabled={loading}>
                  {loading ? "Thinking…" : "Send"}
                </button>
              </form>
            </div>

            <div className="immersive-fingerprint">
              <VisualFingerprint messages={messages} onAdd={handleAdd} onDismiss={handleDismiss} />
            </div>
          </main>
        </div>
      )}
    </div>
  );
}
