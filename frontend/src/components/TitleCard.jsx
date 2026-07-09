export default function TitleCard({ item, onAdd, onDismiss, compact = false }) {
  const badge = item.in_library ? "In library" : item.in_radarr || item.in_sonarr ? "In queue" : "New";
  const canAddRadarr = !item.in_library && item.media_type === "movie" && item.tmdb_id;
  const canAddSonarr = !item.in_library && item.media_type === "show" && item.tvdb_id;

  function handleAdd(target) {
    return (event) => {
      event.stopPropagation();
      onAdd?.(item, target);
    };
  }

  function handleDismiss(event) {
    event.stopPropagation();
    onDismiss?.(item);
  }

  const addActions = (
    <>
      {canAddRadarr ? (
        <button type="button" data-testid="add-radarr-button" onClick={handleAdd("radarr")}>
          Add to Radarr
        </button>
      ) : null}
      {canAddSonarr ? (
        <button type="button" data-testid="add-sonarr-button" onClick={handleAdd("sonarr")}>
          Add to Sonarr
        </button>
      ) : null}
    </>
  );

  return (
    <article className={`title-card ${compact ? "compact" : ""}`} data-testid="title-card">
      <div className="poster-wrap">
        {item.poster_url ? (
          <img src={item.poster_url} alt="" loading="lazy" />
        ) : (
          <div className="poster-fallback">{item.title?.slice(0, 1) || "?"}</div>
        )}
        <span className="badge">{badge}</span>
        {compact && (canAddRadarr || canAddSonarr) ? (
          <div className="title-card-overlay-actions">{addActions}</div>
        ) : null}
      </div>
      <div className="card-body">
        <h3>
          {item.title || "Unknown title"}
          {item.year ? <span className="year"> ({item.year})</span> : null}
        </h3>
        {item.rating ? <p className="rating">★ {item.rating.toFixed(1)}</p> : null}
        {item.genres?.length ? <p className="genres">{item.genres.slice(0, 3).join(" · ")}</p> : null}
        {!compact && item.overview ? <p className="overview">{item.overview.slice(0, 160)}…</p> : null}
        {item.recommendation_reason ? <p className="reason">{item.recommendation_reason}</p> : null}
        <div className="card-actions">
          {!compact ? addActions : null}
          {!compact ? (
            <button type="button" className="ghost" onClick={handleDismiss}>
              Not interested
            </button>
          ) : null}
        </div>
      </div>
    </article>
  );
}
