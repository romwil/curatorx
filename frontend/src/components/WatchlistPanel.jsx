import { relativeTime } from "../api/client";

export default function WatchlistPanel({ pins = [], open, onToggle, onRemove }) {
  if (!pins.length) return null;

  return (
    <div className="watchlist-panel" data-testid="watchlist-panel">
      <button
        type="button"
        className="watchlist-panel-toggle ghost"
        data-testid="watchlist-panel-toggle"
        onClick={onToggle}
        aria-expanded={open}
      >
        Watchlist ({pins.length})
      </button>
      {open ? (
        <ul className="watchlist-panel-list">
          {pins.map((pin) => (
            <li key={pin.id} className="watchlist-panel-item">
              <div className="watchlist-panel-item-body">
                <span className="watchlist-panel-title">{pin.title}</span>
                <span className="watchlist-panel-meta">
                  {pin.media_type === "show" ? "Show" : "Movie"} · {relativeTime(pin.created_at)}
                </span>
              </div>
              <button
                type="button"
                className="ghost watchlist-panel-remove"
                data-testid={`watchlist-remove-${pin.id}`}
                onClick={() => onRemove?.(pin)}
                aria-label={`Remove ${pin.title} from watchlist`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
