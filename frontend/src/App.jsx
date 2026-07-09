import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  confirmAction,
  createThread,
  formatApiError,
  getActiveContext,
  getThreadMessages,
  listJobs,
  listThreads,
  proposeAction,
  resolveAgentPulse,
  sendChat,
  sessionId,
  setActiveSession,
} from "./api/client";
import { alreadyInArrMessage, isAlreadyInArr } from "./lib/addActions.js";
import AddActionBanner from "./components/AddActionBanner";
import ChatThread from "./components/ChatThread";
import InlineAlert from "./components/InlineAlert";
import IntegrationStatus from "./components/IntegrationStatus";
import SidebarSection from "./components/SidebarSection";
import Thoughtstream from "./components/Thoughtstream";
import ThreadList from "./components/ThreadList";
import TurnstyleResultsOverlay from "./components/TurnstyleResultsOverlay";
import TurnstyleViewport from "./components/TurnstyleViewport";
import VisualFingerprint from "./components/VisualFingerprint";

const SIDEBAR_RAIL_KEY = "curatorx.sidebar.rail";
const MEDIUM_BREAKPOINT = "(max-width: 1100px)";
const ADD_FEEDBACK_DISMISS_MS = 5000;

export default function App() {
  const [viewMode, setViewMode] = useState("compact");
  const [messages, setMessages] = useState([]);
  const [threads, setThreads] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(() => sessionId());
  const [threadsReady, setThreadsReady] = useState(false);
  const [showCompactThreads, setShowCompactThreads] = useState(false);
  const [turnstyleResults, setTurnstyleResults] = useState(null);
  const [pendingAdd, setPendingAdd] = useState(null);
  const [pendingBulk, setPendingBulk] = useState(null);
  const [pendingTokens, setPendingTokens] = useState([]);
  const [addInProgress, setAddInProgress] = useState(false);
  const [addProgress, setAddProgress] = useState(null);
  const [addFeedback, setAddFeedback] = useState(null);
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
      setPendingAdd(null);
      setPendingBulk(null);
      setPendingTokens([]);
      setAddFeedback(null);
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

  useEffect(() => {
    if (!addFeedback) return undefined;
    const timer = setTimeout(() => setAddFeedback(null), ADD_FEEDBACK_DISMISS_MS);
    return () => clearTimeout(timer);
  }, [addFeedback]);

  function dismissAddFeedback() {
    setAddFeedback(null);
  }

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
      setPendingTokens(Array.isArray(result.pending_tokens) ? result.pending_tokens : []);
      if (Array.isArray(result.pending_tokens) && result.pending_tokens.length >= 2) {
        setPendingBulk(null);
        setPendingAdd(null);
      }
      refreshJobs();
      refreshThreads();
      getActiveContext()
        .then(setActiveContext)
        .catch(() => {});
    } catch (error) {
      appendChatError(formatApiError(error));
    } finally {
      setLoading(false);
    }
  }

  function handleAdd(item, target) {
    setAddFeedback(null);
    setPendingBulk(null);
    setPendingTokens([]);
    setPendingAdd({ item, target });
  }

  function handleConfirmAllItems(items, target) {
    if (!items?.length || addInProgress) return;
    setAddFeedback(null);
    setPendingAdd(null);
    setPendingTokens([]);
    setPendingBulk({ items, target });
  }

  function handleConfirmAllTokens() {
    if (pendingTokens.length < 2 || addInProgress) return;
    setAddFeedback(null);
    setPendingAdd(null);
    setPendingBulk(null);
    executeConfirmAllTokens();
  }

  function cancelPendingBulk() {
    if (addInProgress) return;
    setPendingBulk(null);
  }

  function cancelPendingTokens() {
    if (addInProgress) return;
    setPendingTokens([]);
  }

  function cancelPendingAdd() {
    if (addInProgress) return;
    setPendingAdd(null);
  }

  async function executeBulkAdd(items, target) {
    const service = target === "sonarr" ? "Sonarr" : "Radarr";
    const action = target === "sonarr" ? "add_sonarr" : "add_radarr";
    let successCount = 0;
    const failures = [];

    setAddInProgress(true);
    setAddProgress({ current: 0, total: items.length });

    for (let index = 0; index < items.length; index += 1) {
      const item = items[index];
      setAddProgress({ current: index + 1, total: items.length, title: item.title });
      const body =
        target === "sonarr"
          ? { action, tvdb_id: item.tvdb_id, title: item.title }
          : { action, tmdb_id: item.tmdb_id, title: item.title };
      try {
        const proposal = await proposeAction(body);
        if (isAlreadyInArr(proposal)) {
          successCount += 1;
          continue;
        }
        const confirm = await confirmAction(proposal.confirmation_token);
        if (isAlreadyInArr(confirm)) {
          successCount += 1;
          continue;
        }
        successCount += 1;
      } catch (error) {
        failures.push({ title: item.title || "Unknown title", message: formatApiError(error) });
      }
    }

    setAddInProgress(false);
    setAddProgress(null);
    setPendingBulk(null);

    if (successCount === items.length) {
      setAddFeedback({
        type: "success",
        message: `Added ${successCount} title${successCount === 1 ? "" : "s"} to ${service}.`,
      });
      return;
    }

    if (successCount > 0) {
      setAddFeedback({
        type: "error",
        message: `Added ${successCount} of ${items.length} to ${service}. ${failures.length} failed.`,
      });
      return;
    }

    setAddFeedback({
      type: "error",
      message: failures[0]?.message || `Could not add titles to ${service}.`,
    });
  }

  async function executeConfirmAllTokens() {
    const tokens = [...pendingTokens];
    let successCount = 0;
    const failures = [];

    setAddInProgress(true);
    setAddProgress({ current: 0, total: tokens.length });

    for (let index = 0; index < tokens.length; index += 1) {
      const token = tokens[index];
      setAddProgress({ current: index + 1, total: tokens.length });
      try {
        const confirm = await confirmAction(token);
        if (isAlreadyInArr(confirm)) {
          successCount += 1;
          continue;
        }
        successCount += 1;
      } catch (error) {
        failures.push(formatApiError(error));
      }
    }

    setAddInProgress(false);
    setAddProgress(null);
    setPendingTokens([]);

    if (successCount === tokens.length) {
      setAddFeedback({
        type: "success",
        message: `Confirmed ${successCount} add${successCount === 1 ? "" : "s"}.`,
      });
      return;
    }

    if (successCount > 0) {
      setAddFeedback({
        type: "error",
        message: `Confirmed ${successCount} of ${tokens.length}. ${failures.length} failed.`,
      });
      return;
    }

    setAddFeedback({
      type: "error",
      message: failures[0] || "Could not confirm proposed adds.",
    });
  }

  async function confirmActiveAction() {
    if (pendingBulk) {
      await executeBulkAdd(pendingBulk.items, pendingBulk.target);
      return;
    }
    if (pendingTokens.length >= 2) {
      await executeConfirmAllTokens();
      return;
    }
    await confirmPendingAdd();
  }

  function cancelActiveAction() {
    if (pendingBulk) {
      cancelPendingBulk();
      return;
    }
    if (pendingTokens.length >= 2) {
      cancelPendingTokens();
      return;
    }
    cancelPendingAdd();
  }

  async function confirmPendingAdd() {
    if (!pendingAdd || addInProgress) return;

    const { item, target } = pendingAdd;
    const label = item.title || "this title";
    const service = target === "sonarr" ? "Sonarr" : "Radarr";
    const action = target === "sonarr" ? "add_sonarr" : "add_radarr";
    const body =
      target === "sonarr"
        ? { action, tvdb_id: item.tvdb_id, title: item.title }
        : { action, tmdb_id: item.tmdb_id, title: item.title };

    setAddInProgress(true);
    try {
      const proposal = await proposeAction(body);
      if (isAlreadyInArr(proposal)) {
        setAddFeedback({
          type: "success",
          message: alreadyInArrMessage(proposal, { label, service }),
        });
        setPendingAdd(null);
        return;
      }
      const confirm = await confirmAction(proposal.confirmation_token);
      if (isAlreadyInArr(confirm)) {
        setAddFeedback({
          type: "success",
          message: alreadyInArrMessage(confirm, { label, service }),
        });
      } else {
        setAddFeedback({ type: "success", message: `Added "${label}" to ${service}.` });
      }
      setPendingAdd(null);
    } catch (error) {
      setAddFeedback({ type: "error", message: formatApiError(error) });
    } finally {
      setAddInProgress(false);
    }
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
            onOpenViewport={setTurnstyleResults}
            onConfirmAllItems={handleConfirmAllItems}
            onConfirmAllTokens={handleConfirmAllTokens}
            pendingTokenCount={pendingTokens.length}
            actionsDisabled={addInProgress}
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
              <div className="sidebar-footer-callout">
                <div className="sidebar-actions">
                  <button
                    type="button"
                    className="sidebar-action-btn sidebar-action-btn--ghost"
                    data-testid="collapse-viewport"
                    onClick={() => setViewMode("compact")}
                  >
                    <span className="sidebar-action-icon" aria-hidden="true">
                      ⊟
                    </span>
                    <span className="sidebar-action-label">Collapse</span>
                  </button>
                  <button
                    type="button"
                    className="sidebar-action-btn sidebar-action-btn--primary"
                    onClick={syncLibrary}
                  >
                    <span className="sidebar-action-icon" aria-hidden="true">
                      ↻
                    </span>
                    <span className="sidebar-action-label">Sync library</span>
                  </button>
                  <Link to="/config" className="sidebar-action-btn sidebar-action-btn--ghost">
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
                onOpenViewport={setTurnstyleResults}
                onConfirmAllItems={handleConfirmAllItems}
                onConfirmAllTokens={handleConfirmAllTokens}
                pendingTokenCount={pendingTokens.length}
                actionsDisabled={addInProgress}
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

            {!isMediumViewport ? (
              <div className="immersive-fingerprint" data-testid="immersive-fingerprint">
                <VisualFingerprint messages={messages} onAdd={handleAdd} onDismiss={handleDismiss} />
              </div>
            ) : null}
          </main>
        </div>
      )}

      {turnstyleResults ? (
        <TurnstyleResultsOverlay
          payload={turnstyleResults}
          onClose={() => setTurnstyleResults(null)}
          onAdd={handleAdd}
          onDismiss={handleDismiss}
          onConfirmAllItems={handleConfirmAllItems}
          actionsDisabled={addInProgress}
        />
      ) : null}

      <div className="add-action-layer">
        <AddActionBanner
          pendingAdd={pendingAdd}
          pendingBulk={pendingBulk}
          pendingTokens={pendingTokens.length >= 2 ? pendingTokens : null}
          inProgress={addInProgress}
          progress={addProgress}
          onConfirm={confirmActiveAction}
          onCancel={cancelActiveAction}
        />
        <InlineAlert
          type={addFeedback?.type}
          message={addFeedback?.message}
          testId="add-action-feedback"
          onDismiss={dismissAddFeedback}
        />
      </div>
    </div>
  );
}
