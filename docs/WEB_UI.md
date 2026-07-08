# CuratorX — Web UI

The CuratorX frontend is a Vite + React SPA served from the same origin as the FastAPI backend (`/` and `/api/*`).

---

## View modes

CuratorX toggles between two operational states without leaving the browser:

### Turnstyle widget

Lightweight overlay optimized for fast intent entry:

- **Command lane** — borderless monospace input; auto-focus on load.
- **Ambient context prefix** — inferred context indicator, e.g. `⧉ [Neo-noir exploration] > _`.
- **Thoughtstream feed** — compact activity log (sync status, job pulse) capped at ~320px height.

Expand to Immersive via hotkey, `/expand` token, or viewport card click.

### Immersive viewport

Full workspace for deep curation:

- **Sidebar (240px)** — ambient context label, thoughtstream, settings link, job pulse (`.agent-pulse`).
- **Chat pane (~45%)** — message thread with ambient context tag in composer.
- **Visual array (~55%)** — title cards clustered by genre, trope, or recommendation context.

Context is inferred automatically from conversation — no manual lens switching in the UI.

---

## Routes

| Route | Purpose |
|-------|---------|
| `/` | Curator chat — Turnstyle or Immersive depending on view state |
| `/config` | Onboarding wizard (first run) or maintenance dashboard |
| `/title/{movie\|show}/{id}` | Title detail — backdrop hero, metadata, purge notes |

Session ID persists in `localStorage` for chat continuity across reloads.

### Configuration page auto-certification

On `/config` load, the UI fetches certification status and sequentially tests any **uncertified** service that has credentials configured (including env-backed secrets). Results appear inline per service card; successful tests set `certified` in SQLite so repeat visits skip re-testing until credentials change.

---

## Chat features

- Streaming via `GET /api/chat/stream` (SSE; simulated deltas today, true LLM streaming planned)
- Inline **title cards** — poster, rating, genres, `recommendation_reason`
- **Turnstyle viewport** — horizontal scroll overlay for expanded result sets
- **Add to Radarr/Sonarr** — browser confirm + server confirmation token
- **Not interested** — `POST /api/preferences` with `dismiss` signal
- **Ambient context** — inferred from conversation; backend may still accept `lens_id` for compatibility

---

## API highlights

### Core

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Send message; optional `lens_id` in body |
| GET | `/api/chat/stream` | SSE stream; query `message`, `session_id`, `lens_id` |
| POST | `/api/library/sync` | Start Plex index job |
| GET | `/api/library/stats` | Item counts and last sync |
| GET | `/api/title/{media_type}/{id}` | Title detail (`id_type` query) |
| GET | `/api/context/active` | Inferred ambient context label |

### Setup and wizard

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/setup/status` | High-level readiness flags |
| GET | `/api/setup/wizard` | Gated wizard step progress (includes `certifications`) |
| GET | `/api/setup/certifications` | Per-service `certified` / `connection_status` / `last_tested_at` |
| GET | `/api/setup/llm-providers` | Default base URLs per provider |
| POST | `/api/setup/test/{service}` | Live connection test (`plex`, `radarr`, `sonarr`, `tmdb`, `fanart`, `tautulli`, `llm`) |
| GET/PUT | `/api/settings` | Connection settings (secrets masked on read) |

### Persona and lenses (backend)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/lenses` | List curation lenses (API only; no UI switcher) |
| GET/PUT | `/api/persona` | Curator name and tone sliders (advanced config) |
| GET/PUT | `/api/system-config` | Key-value config (includes `curator_name`) |

### Actions

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/actions/propose` | Create confirmation token |
| POST | `/api/actions/confirm` | Execute or cancel pending action |
| POST | `/api/preferences` | Record taste signal |

---

## Security

No built-in authentication. Run on a trusted LAN or behind an authenticated reverse proxy. Destructive *arr operations always require confirmation tokens (10-minute TTL).

---

## Related documentation

- [DESIGN.md](DESIGN.md) — block schema, interaction patterns
- [ARCHITECTURE.md](ARCHITECTURE.md) — chat and sync data flows
