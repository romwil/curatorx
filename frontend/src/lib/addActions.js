export function isAddableToRadarr(item) {
  return Boolean(!item?.in_library && item?.media_type === "movie" && item?.tmdb_id);
}

export function isAddableToSonarr(item) {
  return Boolean(!item?.in_library && item?.media_type === "show" && item?.tvdb_id);
}

export function isAlreadyInArr(response) {
  return Boolean(response?.already_exists);
}

export function alreadyInArrMessage(response, { label, service }) {
  return response?.message || `"${label}" is already in ${service}.`;
}

export function groupAddableItems(items = []) {
  return {
    radarr: items.filter(isAddableToRadarr),
    sonarr: items.filter(isAddableToSonarr),
  };
}

export function collectTitleCardItems(blocks = []) {
  const items = [];
  for (const block of blocks) {
    if (block?.type === "title_cards") {
      items.push(...(block.items || []));
    }
  }
  return items;
}

export function collectAddableFromMessage(message) {
  if (!message || message.role !== "assistant") {
    return { radarr: [], sonarr: [] };
  }
  return groupAddableItems(collectTitleCardItems(message.blocks));
}
