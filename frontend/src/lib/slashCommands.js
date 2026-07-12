import { createId } from "./id.js";

function reviewPromptBlock(prompt) {
  return {
    type: "review_prompt",
    content: "",
    payload: { prompt },
  };
}

export const SLASH_COMMANDS = ["help", "stats", "sync", "rate", "purge", "collections"];

export function parseSlashCommand(text) {
  const trimmed = String(text || "").trim();
  if (!trimmed.startsWith("/")) return null;
  const body = trimmed.slice(1).trim();
  if (!body) return { command: "", args: "", raw: trimmed };
  const spaceIndex = body.indexOf(" ");
  if (spaceIndex === -1) {
    return { command: body.toLowerCase(), args: "", raw: trimmed };
  }
  return {
    command: body.slice(0, spaceIndex).toLowerCase(),
    args: body.slice(spaceIndex + 1).trim(),
    raw: trimmed,
  };
}

export function formatHelpMessage(curatorName = "Curator", { plexCollectionsEnabled = false } = {}) {
  const lines = [
    `**${curatorName} slash commands**`,
    "",
    "- `/help` — show this command list",
    "- `/stats` — library item counts and last sync time",
    "- `/sync` — start a Plex library index job (owner only when multi-user mode is on)",
    "- `/rate <title>` — rate a library title you have watched (1–5 stars)",
    "- `/purge` — summarize top drive-space purge candidates",
  ];
  if (plexCollectionsEnabled) {
    lines.push("- `/collections` — list Plex movie and TV collections");
  }
  lines.push("", "Type anything else to chat normally.");
  return lines.join("\n");
}

export function formatStatsMessage(stats) {
  if (!stats) {
    return "Library stats are not available yet. Try again after setup completes.";
  }
  const lastSync = stats.last_sync
    ? new Date(Number(stats.last_sync) * 1000).toLocaleString()
    : "never";
  return [
    "**Library stats**",
    "",
    `- Movies: **${stats.movies ?? 0}**`,
    `- TV shows: **${stats.shows ?? 0}**`,
    `- Total indexed: **${stats.total ?? 0}**`,
    `- Last sync: ${lastSync}`,
  ].join("\n");
}

export function formatSyncDeniedMessage() {
  return [
    "**Library sync is owner-only**",
    "",
    "Multi-user mode is enabled. Start sync from **Config → Sync library** while signed in as the library owner.",
  ].join("\n");
}

export function formatSyncStartedMessage(_job) {
  return [
    "**Library sync queued**",
    "",
    "Watch progress in the status dock (bottom-left).",
  ].join("\n");
}

export function formatPurgeMessage(items) {
  const lines = [
    "**Purge candidates**",
    "",
    `${items.length} large, low-play titles worth reviewing for disk space:`,
  ];
  for (const item of items.slice(0, 8)) {
    const reason = item.recommendation_reason ? ` — ${item.recommendation_reason}` : "";
    lines.push(`- **${item.title}**${reason}`);
  }
  if (items.length > 8) {
    lines.push(`- …and ${items.length - 8} more`);
  }
  lines.push("", "Ask the curator to walk through removals — nothing is deleted automatically.");
  return lines.join("\n");
}

export function formatCollectionsMessage(movies, shows) {
  const movieItems = movies?.items || [];
  const showItems = shows?.items || [];
  if (!movieItems.length && !showItems.length) {
    return "**Plex collections** — none found in your mapped movie or TV libraries.";
  }
  const lines = ["**Plex collections**", ""];
  if (movieItems.length) {
    lines.push(`**Movies (${movieItems.length})**`);
    for (const item of movieItems.slice(0, 12)) {
      lines.push(`- ${item.title}`);
    }
    if (movieItems.length > 12) {
      lines.push(`- …and ${movieItems.length - 12} more`);
    }
    lines.push("");
  }
  if (showItems.length) {
    lines.push(`**TV (${showItems.length})**`);
    for (const item of showItems.slice(0, 12)) {
      lines.push(`- ${item.title}`);
    }
    if (showItems.length > 12) {
      lines.push(`- …and ${showItems.length - 12} more`);
    }
  }
  return lines.join("\n");
}

export function formatCollectionsDisabledMessage() {
  return [
    "**Plex collections are disabled**",
    "",
    "Turn on **Allow curator to manage Plex collections** in Configuration → Plex library mapping.",
  ].join("\n");
}

export function formatCollectionsDeniedMessage() {
  return [
    "**Plex collections require owner access**",
    "",
    "Sign in as the library owner or run this from a single-user install.",
  ].join("\n");
}

function assistantBlock(content, blocks = null) {
  return {
    id: createId(),
    role: "assistant",
    blocks: blocks || [{ type: "text", content }],
  };
}

async function resolveRateTarget(api, titleQuery) {
  const trimmed = String(titleQuery || "").trim();
  if (!trimmed) {
    return { error: "Usage: `/rate Title Name` — for example `/rate Inception`." };
  }
  const data = await api(`/library/query?query=${encodeURIComponent(trimmed)}&limit=5`);
  const items = (data.items || []).filter((item) => item.in_library !== false);
  if (!items.length) {
    return { error: `No library match for **${trimmed}**. Try the exact Plex title.` };
  }
  const match = items[0];
  return {
    prompt: {
      id: `slash-rate-${match.rating_key || match.tmdb_id || trimmed}`,
      rating_key: match.rating_key || String(match.tmdb_id || ""),
      media_type: match.media_type,
      title: match.title,
      completion_pct: 100,
    },
  };
}

export async function executeSlashCommand(parsed, { api, getFeatures, curatorName = "Curator" } = {}) {
  if (!parsed?.command) {
    return assistantBlock("Type `/help` to see available slash commands.");
  }

  switch (parsed.command) {
    case "help": {
      const features = getFeatures ? await getFeatures() : null;
      return assistantBlock(
        formatHelpMessage(curatorName, {
          plexCollectionsEnabled: Boolean(features?.features?.plex_collections_enabled),
        }),
      );
    }

    case "stats": {
      const stats = await api("/library/stats");
      return assistantBlock(formatStatsMessage(stats));
    }

    case "sync": {
      const features = getFeatures ? await getFeatures() : null;
      if (features?.features?.multi_user_enabled) {
        return assistantBlock(formatSyncDeniedMessage());
      }
      const job = await api("/library/sync", { method: "POST" });
      return assistantBlock(formatSyncStartedMessage(job));
    }

    case "rate": {
      const resolved = await resolveRateTarget(api, parsed.args);
      if (resolved.error) {
        return assistantBlock(resolved.error);
      }
      return assistantBlock(
        `${curatorName} — quick take on **${resolved.prompt.title}**?`,
        [reviewPromptBlock(resolved.prompt)]
      );
    }

    case "purge": {
      const data = await api("/library/purge-candidates?limit=12");
      const items = data.items || [];
      if (!items.length) {
        return assistantBlock("No purge candidates found — your library looks lean.");
      }
      return assistantBlock(formatPurgeMessage(items), [
        { type: "title_cards", content: "", items },
      ]);
    }

    case "collections": {
      const features = getFeatures ? await getFeatures() : null;
      if (!features?.features?.plex_collections_enabled) {
        return assistantBlock(formatCollectionsDisabledMessage());
      }
      try {
        const [movies, shows] = await Promise.all([
          api("/plex/collections?media_type=movie"),
          api("/plex/collections?media_type=show"),
        ]);
        return assistantBlock(formatCollectionsMessage(movies, shows));
      } catch (error) {
        const status = error?.status;
        if (status === 401 || status === 403) {
          return assistantBlock(formatCollectionsDeniedMessage());
        }
        throw error;
      }
    }

    default:
      return assistantBlock(
        `Unknown command \`/${parsed.command}\`. Type \`/help\` to see available commands.`
      );
  }
}
