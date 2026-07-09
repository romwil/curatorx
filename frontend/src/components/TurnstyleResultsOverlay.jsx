import { groupAddableItems } from "../lib/addActions";
import ConfirmAllButton from "./ConfirmAllButton";
import TitleCard from "./TitleCard";

function isDisplayableCard(item) {
  return Boolean(item?.title || item?.tmdb_id || item?.tvdb_id || item?.rating_key);
}

export default function TurnstyleResultsOverlay({
  payload,
  onClose,
  onAdd,
  onDismiss,
  onConfirmAllItems,
  actionsDisabled = false,
}) {
  const items = (payload?.items || []).filter(isDisplayableCard);
  if (!items.length) return null;

  const { radarr, sonarr } = groupAddableItems(items);

  return (
    <div className="viewport-overlay" data-testid="turnstyle-results-overlay" onClick={onClose}>
      <div
        className="viewport"
        role="dialog"
        aria-modal="true"
        aria-label={payload?.title || "Recommendations"}
        onClick={(event) => event.stopPropagation()}
      >
        <header>
          <div>
            <p className="eyebrow">Turnstyle view</p>
            <h2>{payload?.title || "Recommendations"}</h2>
          </div>
          <button type="button" className="ghost" data-testid="close-turnstyle-results" onClick={onClose}>
            Close
          </button>
        </header>
        {(radarr.length >= 2 || sonarr.length >= 2) && onConfirmAllItems ? (
          <div className="bulk-confirm-actions viewport-bulk-actions">
            {radarr.length >= 2 ? (
              <ConfirmAllButton
                count={radarr.length}
                target="radarr"
                onClick={() => onConfirmAllItems(radarr, "radarr")}
                disabled={actionsDisabled}
              />
            ) : null}
            {sonarr.length >= 2 ? (
              <ConfirmAllButton
                count={sonarr.length}
                target="sonarr"
                onClick={() => onConfirmAllItems(sonarr, "sonarr")}
                disabled={actionsDisabled}
              />
            ) : null}
          </div>
        ) : null}
        <div className="turnstyle-track">
          {items.map((item) => (
            <TitleCard
              key={`${item.media_type}-${item.tmdb_id || item.tvdb_id || item.title}`}
              item={item}
              onAdd={onAdd}
              onDismiss={onDismiss}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
