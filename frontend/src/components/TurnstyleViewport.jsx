import TitleCard from "./TitleCard";

export default function TurnstyleViewport({ payload, onClose, onAdd, onDismiss }) {
  if (!payload?.items?.length) return null;
  return (
    <div className="viewport-overlay">
      <div className="viewport">
        <header>
          <div>
            <p className="eyebrow">Turnstyle view</p>
            <h2>{payload.title || "Recommendations"}</h2>
          </div>
          <button type="button" className="ghost" onClick={onClose}>
            Close
          </button>
        </header>
        <div className="turnstyle-track">
          {payload.items.map((item) => (
            <TitleCard key={`${item.media_type}-${item.tmdb_id || item.tvdb_id || item.title}`} item={item} onAdd={onAdd} onDismiss={onDismiss} />
          ))}
        </div>
      </div>
    </div>
  );
}
