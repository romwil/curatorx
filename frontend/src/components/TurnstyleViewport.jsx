import { useEffect, useRef } from "react";
import ChatThread from "./ChatThread";
import InlineAlert from "./InlineAlert";
import Thoughtstream from "./Thoughtstream";

export default function TurnstyleViewport({
  contextLabel,
  threadTitle,
  input,
  onInputChange,
  onSubmit,
  onExpand,
  loading,
  jobs = [],
  chatError = "",
  messages = [],
  onAdd,
  onDismiss,
  onOpenViewport,
  onConfirmAllItems,
  onConfirmAllTokens,
  pendingTokenCount = 0,
  actionsDisabled = false,
}) {
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  function handleKeyDown(event) {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      onExpand?.();
      return;
    }
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSubmit?.();
    }
  }

  function handleChange(event) {
    const value = event.target.value;
    if (value === "/expand") {
      onInputChange("");
      onExpand?.();
      return;
    }
    onInputChange(value);
  }

  return (
    <div className="turnstyle-compact">
      <div className="turnstyle-command-lane">
        <label className="command-prefix" htmlFor="turnstyle-input">
          <span className="ambient-context-prefix">⧉ [{contextLabel || "Exploring…"}]</span>
          {threadTitle ? <span className="thread-context-prefix">↳ {threadTitle}</span> : null}
          <span className="prompt-caret">&gt; _</span>
        </label>
        <input
          id="turnstyle-input"
          data-testid="command-input"
          ref={inputRef}
          className="command-input font-mono"
          type="text"
          value={input}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Describe what you're hunting for…"
          disabled={loading}
          autoComplete="off"
          spellCheck={false}
        />
      </div>

      <div className="turnstyle-actions">
        <button type="button" data-testid="send-button" onClick={onSubmit} disabled={loading || !input.trim()}>
          {loading ? "Thinking…" : "Send"}
        </button>
        <button type="button" className="ghost" data-testid="expand-viewport" onClick={onExpand}>
          Expand viewport
        </button>
        <span className="turnstyle-hint">⌘↵ or type /expand</span>
      </div>

      <InlineAlert type="error" message={chatError} />

      {messages.length > 0 ? (
        <div className="turnstyle-transcript" data-testid="turnstyle-transcript">
          <ChatThread
            messages={messages}
            variant="compact"
            showErrors={false}
            onAdd={onAdd}
            onDismiss={onDismiss}
            onOpenViewport={onOpenViewport}
            onConfirmAllItems={onConfirmAllItems}
            onConfirmAllTokens={onConfirmAllTokens}
            pendingTokenCount={pendingTokenCount}
            actionsDisabled={actionsDisabled}
          />
        </div>
      ) : null}

      <Thoughtstream jobs={jobs} />
    </div>
  );
}
