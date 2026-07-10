import assert from "node:assert/strict";
import test from "node:test";

import {
  normalizePendingTokens,
  summarizePendingTokenActions,
  tokenConfirmButtonLabel,
  tokenConfirmFailureMessage,
  tokenConfirmPrompt,
  tokenConfirmSuccessMessage,
} from "./addActions.js";

test("normalizePendingTokens accepts legacy string tokens", () => {
  assert.deepEqual(normalizePendingTokens(["abc", "def"]), [
    { token: "abc", action: "add_radarr" },
    { token: "def", action: "add_radarr" },
  ]);
});

test("normalizePendingTokens preserves action metadata", () => {
  assert.deepEqual(
    normalizePendingTokens([
      { token: "a", action: "remove_arr" },
      { token: "b", action: "remove_arr" },
    ]),
    [
      { token: "a", action: "remove_arr" },
      { token: "b", action: "remove_arr" },
    ],
  );
});

test("token confirm copy distinguishes removals from adds", () => {
  const removals = [
    { token: "a", action: "remove_arr" },
    { token: "b", action: "remove_arr" },
  ];
  assert.equal(tokenConfirmPrompt(2, removals), "Confirm all 2 proposed removals?");
  assert.equal(tokenConfirmButtonLabel(2, removals), "Confirm all 2 removals");
  assert.equal(tokenConfirmSuccessMessage(2, removals), "Confirmed 2 removals.");
  assert.equal(tokenConfirmFailureMessage(removals), "Could not confirm proposed removals.");

  const adds = [
    { token: "a", action: "add_radarr" },
    { token: "b", action: "add_sonarr" },
  ];
  assert.equal(tokenConfirmPrompt(2, adds), "Confirm all 2 proposed adds?");
  assert.equal(tokenConfirmButtonLabel(2, adds), "Confirm all 2 adds");
});

test("summarizePendingTokenActions counts mixed action types", () => {
  assert.deepEqual(
    summarizePendingTokenActions([
      { token: "a", action: "remove_arr" },
      { token: "b", action: "add_radarr" },
      { token: "c", action: "create_plex_collection" },
    ]),
    { add: 1, remove: 1, plex: 1, other: 0 },
  );
});
