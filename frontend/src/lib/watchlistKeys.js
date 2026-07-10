export function watchlistItemKey(item) {
  const mediaType = item?.media_type || "movie";
  const tmdb = item?.tmdb_id ?? "";
  const tvdb = item?.tvdb_id ?? "";
  return `${mediaType}:${tmdb}:${tvdb}`;
}

export function buildWatchlistLookup(pins = []) {
  const byItemKey = new Map();
  const byId = new Map();
  for (const pin of pins) {
    byItemKey.set(watchlistItemKey(pin), pin);
    byId.set(pin.id, pin);
  }
  return { byItemKey, byId };
}
