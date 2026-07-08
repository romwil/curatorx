import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  createThread,
  formatApiError,
  getActiveContext,
  getThreadMessages,
  listJobs,
  listThreads,
  resolveAgentPulse,
  sendChat,
  sessionId,
  setActiveSession,
} from "./api/client";
import ChatThread from "./components/ChatThread";
import InlineAlert from "./components/InlineAlert";
import IntegrationStatus from "./components/IntegrationStatus";
import SidebarSection from "./components/SidebarSection";
import Thoughtstream from "./components/Thoughtstream";
import ThreadList from "./components/ThreadList";
import TurnstyleViewport from "./components/TurnstyleViewport";
import VisualFingerprint, { extractLatestCards } from "./components/VisualFingerprint";

const SIDEBAR_RAIL_KEY = "curatorx.sidebar.rail";
const MEDIUM_BREAKPOINT = "(max-width: 1100px)";

export default function App() {
  const [viewMode, setViewMode] = useState("compact");
  const [messages, setMessages] = useState([]);
  const [threads, setThreads] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(() => sessionId());
  const [threadsReady, setThreadsReady] = useState(false);
  const [showCompactThreads, setShowCompactThreads] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [chatError, setChatError] = useState("");
  const [stats, setStats] = useState(null);
  const [setup, setSetup] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [persona, setPersona] = useState(null);
  const [activeContext, setActiveContext] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try {
      return sessionStorage.getItem(SIDEBAR_RAIL_KEY) === "true";
    } catch {
      return false;
    }
  });
  const [isMediumViewport, setIsMediumViewport] = useState(() =>
    typeof window !== "undefined" ? window.matchMedia(MEDIUM_BREAKPOINT).matches : false
  );

  const refreshJobs = useCallback(() => {
    listJobs().then(setJobs).catch(console.error);
  }, []);

  const refreshThreads = useCallback(async () => {
    try {
      const nextThreads = await listThreads();
      setThreads(nextThreads);
      return nextThreads;
    } catch (error) {
      console.error(error);
      return [];
    }
  }, []);

  const loadThreadMessages = useCallback(async (session) => {
    try {
      const data = await getThreadMessages(session);
      setMessages(data.messages || []);
      setChatError("");
      return true;
    } catch (error) {
      if (error.message?.includes("Thread not found")) {
        setMessages([]);
        return false;
      }
      console.error(error);
      return false;
    }
  }, []);

  const switchThread = useCallback(
    async (session) => {
      if (!session || session === activeSessionId) return;
      setActiveSession(session);
      setActiveSessionId(session);
      setChatError("");
      await loadThreadMessages(session);
    },
    [activeSessionId, loadThreadMessages]
  );

  const handleCreateThread = useCallback(async () => {
    try {
      const created = await createThread();
      const nextId = created.session_id;
      setActiveSession(nextId);
      setActiveSessionId(nextId);
      setMessages([]);
      setChatError("");
      setShowCompactThreads(false);
      await refreshThreads();
    } catch (error) {
      console.error(error);
    }
  }, [refreshThreads]);

  useEffect(() => {
    const mediaQuery = window.matchMedia(MEDIUM_BREAKPOINT);
    const syncViewport = (event) => setIsMediumViewport(event.matches);
    syncViewport(mediaQuery);
    mediaQuery.addEventListener("change", syncViewport);
    return () => mediaQuery.removeEventListener("change", syncViewport);
  }, []);

  function toggleSidebarRail() {
    setSidebarCollapsed((collapsed) => {
      const next = !collapsed;
      try {
        sessionStorage.setItem(SIDEBAR_RAIL_KEY, String(next));
      } catch {
        // sessionStorage unavailable
      }
      return next;
    });
  }

  useEffect(() => {
    async function initializeThreads() {
      let storedId = sessionId();
      let threadList = await refreshThreads();
      let loaded = await loadThreadMessages(storedId);
      const storedExists = threadList.some((thread) => thread.id === storedId);

      if (!storedExists && !loaded) {
        if (threadList.length > 0) {
          storedId = threadList[0].id;
          setActiveSession(storedId);
          setActiveSessionId(storedId);
          await loadThreadMessages(storedId);
        } else {
          const created = await createThread();
          storedId = created.session_id;
          setActiveSession(storedId);
          setActiveSessionId(storedId);
          threadList = await refreshThreads();
        }
      } else if (!storedExists) {
        threadList = await refreshThreads();
      }

      setActiveSessionId(storedId);
      setThreadsReady(true);
    }

    initializeThreads().catch(console.error);
  }, [loadThreadMessages, refreshThreads]);

  useEffect(() => {
    Promise.all([
      api("/setup/status").then(setSetup),
      api("/library/stats").then(setStats),
      api("/persona").then(setPersona).catch(console.error),
      getActiveContext()
        .then(setActiveContext)
        .catch(() => setActiveContext({ context_hash: "general", inferred_label: "General Exploration" })),
    ]).catch(console.error);
    refreshJobs();
    const interval = setInterval(refreshJobs, 5000);
    return () => clearInterval(interval);
  }, [refreshJobs]);

  function appendChatError(reason) {
    const message = `Curator couldn't respond: ${reason}`;
    setChatError(message);
    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: "error",
        blocks: [{ type: "error", content: message }],
      },
    ]);
  }

  async function sendMessage(text) {
    if (!text.trim() || loading) return;
    setLoading(true);
    setChatError("");
    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      blocks: [{ type: "text", content: text }],
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    try {
      const result = await sendChat(text, "general", { sessionId: activeSessionId });
      if (!result?.message?.blocks?.length) {
        appendChatError(
          "The curator returned no content blocks. Check your LLM provider, API key, and model in Settings."
        );
        return;
      }
      setMessages((prev) => [...prev, result.message]);
      refreshJobs();
      refreshThreads();
      getActiveContext()
        .then(setActiveContext)
        .catch(() => {});
      if (extractLatestCards([result.message]).length > 0) {
        setViewMode("immersive");
      }
    } catch (error) {
      appendChatError(formatApiError(error));
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
    refreshJobs();
    alert(`Library sync started (${job.id})`);
  }

  const agentPulse = resolveAgentPulse(jobs);
  const curatorName = persona?.curator_name || "Curator";
  const contextLabel = activeContext?.inferred_label || "Exploring…";
  const activeThread = threads.find((thread) => thread.id === activeSessionId);
  const activeThreadTitle = activeThread?.thread_title || "New conversation";

  return (
    <div className={`app-root ${viewMode}`}>
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
            <div className="banner" data-testid="setup-banner">
              Finish setup in <Link to="/config">Settings</Link> to connect Plex, TMDB, and your LLM provider.
            </div>
          ) : null}

          <div className="turnstyle-thread-indicator">
            <button
              type="button"
              className="thread-indicator-btn"
              data-testid="thread-indicator"
              onClick={() => setShowCompactThreads((open) => !open)}
            >
              <span className="thread-indicator-label">{activeThreadTitle}</span>
              <span className="thread-indicator-hint">{showCompactThreads ? "Hide threads" : "Switch thread"}</span>
            </button>
          </div>

          {showCompactThreads ? (
            <div className="turnstyle-thread-panel">
              <ThreadList
                threads={threads}
                activeSessionId={activeSessionId}
                onSelect={switchThread}
                onCreate={handleCreateThread}
                compact
              />
            </div>
          ) : null}

          <TurnstyleViewport
            contextLabel={contextLabel}
            threadTitle={activeThreadTitle}
            input={input}
            onInputChange={setInput}
            onSubmit={() => sendMessage(input)}
            onExpand={() => setViewMode("immersive")}
            loading={loading || !threadsReady}
            jobs={jobs}
            chatError={chatError}
            messages={messages}
            onAdd={handleAdd}
            onDismiss={handleDismiss}
            onOpenViewport={() => setViewMode("immersive")}
          />
        </div>
      ) : (
        <div className="immersive-shell" data-testid="immersive-viewport">
          <aside
            className={`immersive-sidebar ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}
            data-testid="immersive-sidebar"
          >
            <div className="sidebar-top">
              <div className="sidebar-brand">
                <p className="eyebrow">{curatorName}</p>
                <h2>CuratorX</h2>
                <span className={`agent-pulse ${agentPulse}`} title={`Agent ${agentPulse}`} />
              </div>
              <button
                type="button"
                className="sidebar-rail-toggle ghost"
                data-testid="sidebar-rail-toggle"
                onClick={toggleSidebarRail}
                aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar to icons"}
                title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              >
                {sidebarCollapsed ? "»" : "«"}
              </button>
            </div>

            <div className="sidebar-scroll">
              <SidebarSection
                sectionId="conversations"
                title="Conversations"
                icon="💬"
                alwaysVisible
                sidebarCollapsed={sidebarCollapsed}
              >
                <ThreadList
                  threads={threads}
                  activeSessionId={activeSessionId}
                  onSelect={switchThread}
                  onCreate={handleCreateThread}
                  hideHeader
                />
              </SidebarSection>

              <SidebarSection
                sectionId="context"
                title="Active context"
                icon="⧉"
                alwaysVisible
                sidebarCollapsed={sidebarCollapsed}
              >
                <div className="ambient-context-indicator ambient-context-compact" data-testid="ambient-context">
                  <span className="ambient-context-label">{contextLabel}</span>
                  <span className="ambient-context-hint">Inferred from conversation</span>
                </div>
              </SidebarSection>

              <SidebarSection
                sectionId="integrations"
                title="Integrations"
                icon="⚡"
                defaultCollapsed={isMediumViewport}
                sidebarCollapsed={sidebarCollapsed}
              >
                <IntegrationStatus checks={setup?.checks} />
              </SidebarSection>

              <SidebarSection
                sectionId="thoughtstream"
                title="Thoughtstream"
                icon="↻"
                defaultCollapsed={isMediumViewport}
                sidebarCollapsed={sidebarCollapsed}
              >
                <Thoughtstream jobs={jobs} compact hideHeader />
              </SidebarSection>
            </div>

            <div className="sidebar-footer">
              <div className="sidebar-actions">
                <button
                  type="button"
                  className="ghost sidebar-action-btn"
                  data-testid="collapse-viewport"
                  onClick={() => setViewMode("compact")}
                >
                  <span className="sidebar-action-icon" aria-hidden="true">
                    ⊟
                  </span>
                  <span className="sidebar-action-label">Collapse</span>
                </button>
                <button type="button" className="sidebar-action-btn" onClick={syncLibrary}>
                  <span className="sidebar-action-icon" aria-hidden="true">
                    ↻
                  </span>
                  <span className="sidebar-action-label">Sync library</span>
                </button>
                <Link to="/config" className="btn-link ghost sidebar-action-btn">
                  <span className="sidebar-action-icon" aria-hidden="true">
                    ⚙
                  </span>
                  <span className="sidebar-action-label">Configuration</span>
                </Link>
              </div>

              {stats ? (
                <p className="sidebar-stats">
                  {stats.total} titles · {stats.movies} movies · {stats.shows} shows
                </p>
              ) : null}
            </div>
          </aside>

          <main className="immersive-main">
            <div className="immersive-chat">
              <div className="immersive-chat-header">
                <p className="eyebrow">Conversation</p>
                <h3 data-testid="active-thread-title">{activeThreadTitle}</h3>
              </div>
              <ChatThread
                messages={messages}
                chatError={chatError}
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
                <div className="ambient-context-tag">
                  ⧉ {contextLabel}
                </div>
                <InlineAlert type="error" message={chatError} />
                <textarea
                  data-testid="immersive-composer-input"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  placeholder="Continue the conversation…"
                  rows={2}
                  disabled={loading || !threadsReady}
                />
                <button type="submit" data-testid="immersive-send-button" disabled={loading || !threadsReady}>
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
