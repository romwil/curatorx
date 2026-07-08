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

export default function Thoughtstream({ jobs = [], compact = false, hideHeader = false }) {
  return (
    <div className={`thoughtstream ${compact ? "thoughtstream-compact" : ""}`} data-testid="thoughtstream">
      {hideHeader ? null : (
        <div className="thoughtstream-header">
          <span className="eyebrow">Thoughtstream</span>
        </div>
      )}
      <div className="thoughtstream-feed">
        {jobs.length === 0 ? (
          <p className="thoughtstream-empty">No background jobs yet.</p>
        ) : (
          jobs.slice(0, compact ? 6 : 12).map((job) => (
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
  );
}
