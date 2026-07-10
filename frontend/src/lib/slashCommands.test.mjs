import assert from "node:assert/strict";
import test from "node:test";

import {
  SLASH_COMMANDS,
  formatCollectionsMessage,
  formatHelpMessage,
  formatPurgeMessage,
  formatStatsMessage,
  formatSyncDeniedMessage,
  parseSlashCommand,
} from "./slashCommands.js";

test("parseSlashCommand returns null for normal chat", () => {
  assert.equal(parseSlashCommand("find neo-noir films"), null);
  assert.equal(parseSlashCommand("  hello  "), null);
});

test("parseSlashCommand parses command names and args", () => {
  assert.deepEqual(parseSlashCommand("/help"), {
    command: "help",
    args: "",
    raw: "/help",
  });
  assert.deepEqual(parseSlashCommand("  /STATS  "), {
    command: "stats",
    args: "",
    raw: "/STATS",
  });
  assert.deepEqual(parseSlashCommand("/sync full"), {
    command: "sync",
    args: "full",
    raw: "/sync full",
  });
});

test("formatHelpMessage lists core slash commands", () => {
  const text = formatHelpMessage("Flemming");
  assert.match(text, /Flemming slash commands/);
  for (const command of ["help", "stats", "sync", "rate", "purge"]) {
    assert.match(text, new RegExp(`/${command}`));
  }
  assert.doesNotMatch(text, /\/collections/);
});

test("formatHelpMessage includes collections when enabled", () => {
  const text = formatHelpMessage("Flemming", { plexCollectionsEnabled: true });
  assert.match(text, /\/collections/);
});

test("formatStatsMessage renders library counts", () => {
  const text = formatStatsMessage({ movies: 10, shows: 5, total: 15, last_sync: null });
  assert.match(text, /Movies: \*\*10\*\*/);
  assert.match(text, /TV shows: \*\*5\*\*/);
  assert.match(text, /Last sync: never/);
});

test("formatSyncDeniedMessage explains owner-only sync", () => {
  const text = formatSyncDeniedMessage();
  assert.match(text, /owner-only/i);
  assert.match(text, /Config/);
});

test("formatPurgeMessage summarizes purge candidates", () => {
  const text = formatPurgeMessage([
    { title: "Big Movie", recommendation_reason: "4.2 GB, 0 plays" },
  ]);
  assert.match(text, /Purge candidates/);
  assert.match(text, /Big Movie/);
});

test("formatCollectionsMessage lists Plex collections", () => {
  const text = formatCollectionsMessage(
    { items: [{ title: "Neo-Noir" }] },
    { items: [{ title: "Prestige TV" }] },
  );
  assert.match(text, /Neo-Noir/);
  assert.match(text, /Prestige TV/);
});
