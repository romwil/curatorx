# CuratorX — Onboarding

Follow this checklist after deploying CuratorX (Docker, Unraid, or local dev). Default URL: **http://localhost:8788**.

---

## Setup wizard

1. Open **Settings** (`/config`).
2. **Plex** — enter URL and token, test connection, pick movie and TV section keys.
3. **Radarr / Sonarr** — optional; required for add-to-queue actions after confirmation.
4. **TMDB** — add API key from [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api).
5. **LLM** — configure BYOP provider (OpenAI-compatible, Anthropic) or point at Ollama on your host.
6. **Optional** — Fanart.tv for art, Tautulli for watch stats and purge scoring.
7. **Persona** — name your curator and adjust tone sliders (bro↔professorial, diplomatic↔snarky, passive↔autonomous).
8. **Save** and return to the chat UI.

Service cards run live connection tests — success shows green borders and item counts; failures surface actionable guidance (401, timeout, etc.).

---

## Index your library

1. Click **Sync library** on the chat page (or `POST /api/library/sync`).
2. Wait for the background job to finish — Plex metadata, TMDB enrichment, and embeddings are rebuilt.
3. Confirm stats via `GET /api/library/stats`.

---

## Choose your lens

CuratorX scopes taste and chat by **curation lens**:

- Default: **`general`** — everyday discovery and viewing advice.
- Create additional lenses in Settings for isolated contexts (e.g. Director Studies, 70s Exploitation).
- Switch active lens from the Immersive sidebar or `PUT /api/lenses/active`.

Chat history under one lens does not appear when browsing another — this prevents casual watches from contaminating curated study lanes.

---

## Start curating

Try these prompts:

- "I love 70s paranoid thrillers — what's missing from my collection?"
- "Show me hidden gems in sci-fi I don't own yet."
- "What should we watch tonight under 2 hours?"
- "Which large files have never been watched?"
- "Explore neo-noir with me based on what I already love."

Use **Turnstyle** mode for quick one-liners; expand to **Immersive** for longer sessions with the full card grid.

---

## Related documentation

- [CONFIGURATION.md](CONFIGURATION.md) — settings reference
- [WEB_UI.md](WEB_UI.md) — routes and chat features
- [curatorx_prd.md](curatorx_prd.md) — product vision
