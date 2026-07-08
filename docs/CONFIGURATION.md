# CuratorX — Configuration

Settings persist to `{DATA_DIR}/settings.json` (default `/config/settings.json` in Docker, `./config` locally). Environment variables override file values when set.

---

## Required

| Setting | Env var | Description |
|---------|---------|-------------|
| Plex URL | `PLEX_URL` | Plex server base URL |
| Plex token | `PLEX_TOKEN` | Plex authentication token |
| Movie section | `PLEX_MOVIE_SECTION` | Plex movie library section key |
| TV section | `PLEX_TV_SECTION` | Plex TV library section key |
| TMDB API key | `TMDB_API_KEY` | Discovery and metadata enrichment |

---

## Recommended

| Setting | Env var | Description |
|---------|---------|-------------|
| Radarr URL / key | `RADARR_URL`, `RADARR_API_KEY` | Add movies after confirmation |
| Sonarr URL / key | `SONARR_URL`, `SONARR_API_KEY` | Add TV shows after confirmation |
| LLM provider | `LLM_PROVIDER` | `openai_compatible`, `anthropic`, or `ollama` |
| LLM API key | `LLM_API_KEY` | Provider key (not required for Ollama) |
| LLM model | `LLM_MODEL` | e.g. `gpt-4o-mini`, `claude-3-5-sonnet-latest` |

---

## Optional

| Setting | Env var | Description |
|---------|---------|-------------|
| Fanart.tv key | `FANART_API_KEY` | Rich poster/backdrop art |
| TVDB key | `TVDB_API_KEY` | TV metadata parity (client present; sync wiring partial) |
| Tautulli URL / key | `TAUTULLI_URL`, `TAUTULLI_API_KEY` | Watch stats for purge scoring |
| Radarr root folder | `RADARR_ROOT_FOLDER` | Default path for movie adds |
| Sonarr root folder | `SONARR_ROOT_FOLDER` | Default path for series adds |
| Quality profile IDs | `RADARR_QUALITY_PROFILE_ID`, `SONARR_QUALITY_PROFILE_ID` | *arr quality profiles |
| Library sync interval | `library_sync_interval_hours` in settings | Auto-sync cadence (1–168 h, default 24) |
| TV page size | `tv_page_size` in settings | Plex TV fetch batch size (50–2000, default 500) |

---

## LLM providers

| Provider | Configuration |
|----------|---------------|
| **openai_compatible** | OpenAI, OpenRouter, LiteLLM, etc. Set `LLM_BASE_URL` and `LLM_API_KEY`. |
| **anthropic** | Set `LLM_API_KEY` and `LLM_MODEL`. |
| **ollama** | Local inference on the homelab host. `LLM_BASE_URL=http://host:11434/v1`, provider `ollama`. |

Embeddings use `LLM_EMBEDDING_MODEL` and optional `LLM_EMBEDDING_BASE_URL`. Without an embedding API, deterministic hash embeddings (384-dim) are used.

---

## Curator persona (database-backed)

Persona settings live in SQLite (`curator_persona_metrics`), not only `settings.json`:

| Field | API | Description |
|-------|-----|-------------|
| Curator name | `PUT /api/persona` | Display name; injected into system prompt |
| Vocabulary density | `val_bro_prof` | 0.0 (bro) → 1.0 (professorial) |
| Interaction friction | `val_dipl_snark` | 0.0 (diplomatic) → 1.0 (snarky) |
| Automation autonomy | `val_pass_auto` | 0.0 (passive) → 1.0 (autonomous) |

Curator name can also be stored in `curator_system_config` via `PUT /api/system-config`.

---

## Curation lenses

| Concept | Storage | API |
|---------|---------|-----|
| Active lens | `curator_system_config.active_lens_id` | `GET/PUT /api/lenses/active` |
| Lens registry | `curation_lenses` table | `GET/POST /api/lenses` |
| Taste weights | `lens_taste_profile` | Per-lens cluster tags with optional explicit lock |
| Chat scope | `lens_id` on sessions/messages | Pass `lens_id` on `POST /api/chat` |

Default lens: **`general`**.

---

## Secrets handling

API keys are stored in `settings.json` on the config volume. `GET /api/settings` masks secret fields and returns `{field}_set: true` instead of values. The browser never receives raw tokens after save.

---

## Related documentation

- [ONBOARDING.md](ONBOARDING.md) — first-run flow
- [DATA_MODEL.md](DATA_MODEL.md) — full schema reference
- [DOCKER.md](DOCKER.md) — container env seeding
