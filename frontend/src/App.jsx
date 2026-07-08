import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, sessionId } from "./api/client";
import ChatThread from "./components/ChatThread";
import TurnstyleViewport from "./components/TurnstyleViewport";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [viewport, setViewport] = useState(null);
  const [stats, setStats] = useState(null);
  const [setup, setSetup] = useState(null);

  useEffect(() => {
    api("/setup/status").then(setSetup).catch(console.error);
    api("/library/stats").then(setStats).catch(console.error);
  }, []);

  async function sendMessage(text) {
    if (!text.trim()) return;
    setLoading(true);
    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      blocks: [{ type: "text", content: text }],
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    try {
      const result = await api("/chat", {
        method: "POST",
        body: JSON.stringify({ message: text, session_id: sessionId() }),
      });
      setMessages((prev) => [...prev, result.message]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "assistant", blocks: [{ type: "text", content: error.message }] },
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
      }),
    });
  }

  async function syncLibrary() {
    const job = await api("/library/sync", { method: "POST" });
    alert(`Library sync started (${job.id})`);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">MediaCurator</p>
          <h1>Your collection curator</h1>
        </div>
        <div className="topbar-actions">
          {stats ? (
            <span className="stat-chip">
              {stats.total} indexed · {stats.movies} movies · {stats.shows} shows
            </span>
          ) : null}
          <button type="button" onClick={syncLibrary}>
            Sync library
          </button>
          <Link to="/config" className="btn-link">
            Settings
          </Link>
        </div>
      </header>

      {setup && !setup.onboarding_complete ? (
        <div className="banner">
          Finish setup in <Link to="/config">Settings</Link> to connect Plex, TMDB, and your LLM provider.
        </div>
      ) : null}

      <main className="chat-layout">
        <ChatThread messages={messages} onAdd={handleAdd} onDismiss={handleDismiss} onOpenViewport={setViewport} />
        <form
          className="composer"
          onSubmit={(event) => {
            event.preventDefault();
            sendMessage(input);
          }}
        >
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="I love 70s movies about corporate dystopia — what's missing from my collection?"
            rows={3}
          />
          <button type="submit" disabled={loading}>
            {loading ? "Thinking…" : "Ask curator"}
          </button>
        </form>
      </main>

      {viewport ? (
        <TurnstyleViewport payload={viewport} onClose={() => setViewport(null)} onAdd={handleAdd} onDismiss={handleDismiss} />
      ) : null}
    </div>
  );
}
