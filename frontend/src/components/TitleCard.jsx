export default function TitleCard({ item, onAdd, onDismiss, compact = false }) {
  const badge = item.in_library ? "In library" : item.in_radarr || item.in_sonarr ? "In queue" : "New";
  return (
    <article className={`title-card ${compact ? "compact" : ""}`}>
      <div className="poster-wrap">
        {item.poster_url ? (
          <img src={item.poster_url} alt="" loading="lazy" />
        ) : (
          <div className="poster-fallback">{item.title.slice(0, 1)}</div>
        )}
        <span className="badge">{badge}</span>
      </div>
      <div className="card-body">
        <h3>
          {item.title}
          {item.year ? <span className="year"> ({item.year})</span> : null}
        </h3>
        {item.rating ? <p className="rating">★ {item.rating.toFixed(1)}</p> : null}
        {item.genres?.length ? <p className="genres">{item.genres.slice(0, 3).join(" · ")}</p> : null}
        {!compact && item.overview ? <p className="overview">{item.overview.slice(0, 160)}…</p> : null}
        {item.recommendation_reason ? <p className="reason">{item.recommendation_reason}</p> : null}
        <div className="card-actions">
          {!item.in_library && item.media_type === "movie" && item.tmdb_id ? (
            <button type="button" onClick={() => onAdd?.(item, "radarr")}>
              Add to Radarr
            </button>
          ) : null}
          {!item.in_library && item.media_type === "show" && item.tvdb_id ? (
            <button type="button" onClick={() => onAdd?.(item, "sonarr")}>
              Add to Sonarr
            </button>
          ) : null}
          <button type="button" className="ghost" onClick={() => onDismiss?.(item)}>
            Not interested
          </button>
        </div>
      </div>
    </article>
  );
}
