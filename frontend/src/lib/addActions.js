export function isAddableToRadarr(item) {
  return Boolean(!item?.in_library && item?.media_type === "movie" && item?.tmdb_id);
}

export function isAddableToSonarr(item) {
  return Boolean(!item?.in_library && item?.media_type === "show" && item?.tvdb_id);
}

export function isRequestableInSeerr(item) {
  return Boolean(
    !item?.in_library &&
      item?.tmdb_id &&
      (item?.media_type === "movie" || item?.media_type === "show"),
  );
}

export function usesSeerrRequestPath(features) {
  return Boolean(features?.features?.seerr_enabled && features?.request_path === "seerr");
}

export function requestPathFromFeatures(features) {
  return usesSeerrRequestPath(features) ? "seerr" : "arr";
}

export function serviceLabelForTarget(target) {
  if (target === "seerr") return "Seerr";
  if (target === "sonarr") return "Sonarr";
  return "Radarr";
}

export function actionForTarget(target) {
  if (target === "seerr") return "request_seerr";
  if (target === "sonarr") return "add_sonarr";
  return "add_radarr";
}

export function buildProposeActionBody(item, target) {
  if (target === "seerr") {
    return {
      action: "request_seerr",
      media_type: item.media_type,
      tmdb_id: item.tmdb_id,
      tvdb_id: item.tvdb_id,
      title: item.title,
    };
  }
  if (target === "sonarr") {
    return { action: "add_sonarr", tvdb_id: item.tvdb_id, title: item.title };
  }
  return { action: "add_radarr", tmdb_id: item.tmdb_id, title: item.title };
}

export function isAlreadyInArr(response) {
  return Boolean(response?.already_exists);
}

export function alreadyInArrMessage(response, { label, service }) {
  return response?.message || `"${label}" is already in ${service}.`;
}

export function groupAddableItems(items = [], { requestPath = "arr" } = {}) {
  if (requestPath === "seerr") {
    const seerr = items.filter(isRequestableInSeerr);
    return { radarr: [], sonarr: [], seerr };
  }
  return {
    radarr: items.filter(isAddableToRadarr),
    sonarr: items.filter(isAddableToSonarr),
    seerr: [],
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

export function collectAddableFromMessage(message, options = {}) {
  if (!message || message.role !== "assistant") {
    return { radarr: [], sonarr: [], seerr: [] };
  }
  return groupAddableItems(collectTitleCardItems(message.blocks), options);
}
