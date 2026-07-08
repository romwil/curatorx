import { useEffect, useRef } from "react";
import { relativeTime } from "../api/client";

const JOB_ICONS = {
  library_sync: "↻",
  default: "⧉",
};

function jobIcon(job) {
  return JOB_ICONS[job.job_type] || JOB_ICONS.default;
}

function jobLabel(job) {
  const message = job.progress?.message || job.job_type.replace(/_/g, " ");
  const status =
    job.status === "running"
      ? "Running"
      : job.status === "queued"
        ? "Queued"
        : job.status === "failed"
          ? "Failed"
          : "Done";
  return `${status}: ${message}`;
}

export default function TurnstyleViewport({
  lensName,
  input,
  onInputChange,
  onSubmit,
  onExpand,
  loading,
  jobs = [],
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
          <span className="lens-prefix">⧉ [{lensName || "General"}]</span>
          <span className="prompt-caret">&gt; _</span>
        </label>
        <input
          id="turnstyle-input"
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
        <button type="button" onClick={onSubmit} disabled={loading || !input.trim()}>
          {loading ? "Thinking…" : "Send"}
        </button>
        <button type="button" className="ghost" onClick={onExpand}>
          Expand viewport
        </button>
        <span className="turnstyle-hint">⌘↵ or type /expand</span>
      </div>

      <div className="thoughtstream">
        <div className="thoughtstream-header">
          <span className="eyebrow">Thoughtstream</span>
        </div>
        <div className="thoughtstream-feed">
          {jobs.length === 0 ? (
            <p className="thoughtstream-empty">No background jobs yet.</p>
          ) : (
            jobs.slice(0, 12).map((job) => (
              <div key={job.id} className={`thoughtstream-item status-${job.status}`}>
                <span className="thoughtstream-icon">{jobIcon(job)}</span>
                <div className="thoughtstream-body">
                  <span className="thoughtstream-label">{jobLabel(job)}</span>
                  <span className="thoughtstream-time">{relativeTime(job.created_at)}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
