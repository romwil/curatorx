import { useEffect, useRef, useState } from "react";
import { relativeTime } from "../api/client";
import { isSyncChimeMuted, playSyncChime, setSyncChimeMuted } from "../lib/syncChime";
import { readTitleCardDragData, statusDockDropHint } from "../lib/easterEggs.js";
import AddActionBanner from "./AddActionBanner";
import InlineAlert from "./InlineAlert";

const JOB_ICONS = {
  library_sync: "↻",
  default: "⧉",
};

function jobIcon(job) {
  return JOB_ICONS[job.job_type] || JOB_ICONS.default;
}

function jobLabel(job, jobStatusPhrases = []) {
  const progressMessage = job.progress?.message;
  let message = progressMessage || job.job_type.replace(/_/g, " ");
  if (
    job.job_type === "library_sync" &&
    (job.status === "running" || job.status === "queued") &&
    jobStatusPhrases.length
  ) {
    const phraseIndex = Math.abs(Number(job.id?.length || 0)) % jobStatusPhrases.length;
    message = jobStatusPhrases[phraseIndex];
  }
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

function AddProgress({ progress }) {
  if (!progress?.total) return null;
  const current = Math.min(progress.current || 0, progress.total);
  const pct = Math.round((current / progress.total) * 100);
  const title = progress.title ? ` — ${progress.title}` : "";

  return (
    <div className="status-dock-progress" data-testid="status-dock-progress">
      <p className="status-dock-progress-label">
        Adding {current} of {progress.total}
        {title}…
      </p>
      <div className="status-dock-progress-bar" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <span className="status-dock-progress-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function StatusDock({
  jobs = [],
  jobStatusPhrases = [],
  pendingAdd,
  pendingBulk,
  pendingTokens,
  addInProgress = false,
  addProgress,
  addFeedback,
  onConfirm,
  onCancel,
  onDismissFeedback,
  onDropTitle,
  radarrConnected = false,
  sonarrConnected = false,
}) {
  const [chimeMuted, setChimeMuted] = useState(() => isSyncChimeMuted());
  const [dropActive, setDropActive] = useState(false);
  const jobStatusRef = useRef(new Map());

  useEffect(() => {
    for (const job of jobs) {
      const previous = jobStatusRef.current.get(job.id);
      if (
        job.job_type === "library_sync" &&
        previous &&
        (previous === "running" || previous === "queued") &&
        job.status === "done"
      ) {
        playSyncChime();
      }
      jobStatusRef.current.set(job.id, job.status);
    }
  }, [jobs]);

  const hasPendingAction = Boolean(pendingAdd || pendingBulk || pendingTokens?.length);
  const activeJobs = jobs.filter((job) => job.status === "running" || job.status === "queued");
  const hasJobs = activeJobs.length > 0;
  const hasFeedback = Boolean(addFeedback?.message);
  const showAddBanner = hasPendingAction && !addInProgress;
  const showDropHint = Boolean(onDropTitle && (radarrConnected || sonarrConnected));
  const dropHint = statusDockDropHint({ radarrConnected, sonarrConnected });

  if (!hasJobs && !showAddBanner && !addInProgress && !hasFeedback && !showDropHint) {
    return null;
  }

  function toggleChimeMute() {
    const next = !chimeMuted;
    setChimeMuted(next);
    setSyncChimeMuted(next);
  }

  return (
    <div
      className={`status-dock ${dropActive ? "drop-active" : ""}`}
      data-testid="status-dock"
      onDragOver={
        showDropHint
          ? (event) => {
              event.preventDefault();
              setDropActive(true);
            }
          : undefined
      }
      onDragLeave={showDropHint ? () => setDropActive(false) : undefined}
      onDrop={
        showDropHint
          ? (event) => {
              event.preventDefault();
              setDropActive(false);
              const item = readTitleCardDragData(event);
              if (item) onDropTitle?.(item);
            }
          : undefined
      }
    >
      {showDropHint ? (
        <p className="status-dock-drop-hint" data-testid="status-dock-drop-hint">
          {dropHint}
        </p>
      ) : null}
      {hasJobs ? (
        <div className="status-dock-jobs" data-testid="status-dock-jobs">
          {activeJobs.slice(0, 4).map((job) => (
            <div key={job.id} className={`status-dock-job status-${job.status}`}>
              <span className="status-dock-job-icon">{jobIcon(job)}</span>
              <div className="status-dock-job-body">
                <span className="status-dock-job-label">{jobLabel(job, jobStatusPhrases)}</span>
                <span className="status-dock-job-time">{relativeTime(job.created_at)}</span>
              </div>
            </div>
          ))}
          <button
            type="button"
            className="ghost status-dock-chime-toggle"
            data-testid="sync-chime-toggle"
            onClick={toggleChimeMute}
            title={chimeMuted ? "Unmute sync chime" : "Mute sync chime"}
            aria-label={chimeMuted ? "Unmute sync chime" : "Mute sync chime"}
          >
            {chimeMuted ? "🔕" : "🔔"}
          </button>
        </div>
      ) : null}

      {addInProgress ? <AddProgress progress={addProgress} /> : null}

      {showAddBanner ? (
        <AddActionBanner
          pendingAdd={pendingAdd}
          pendingBulk={pendingBulk}
          pendingTokens={pendingTokens}
          inProgress={false}
          progress={addProgress}
          onConfirm={onConfirm}
          onCancel={onCancel}
        />
      ) : null}

      {hasFeedback ? (
        <InlineAlert
          type={addFeedback.type}
          message={addFeedback.message}
          testId="add-action-feedback"
          onDismiss={onDismissFeedback}
        />
      ) : null}
    </div>
  );
}
