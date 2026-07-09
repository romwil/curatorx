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
| LLM provider | `LLM_PROVIDER` | Preset: `openai`, `anthropic`, `gemini`, `groq`, `mistral`, `together`, `deepseek`, `openrouter`, `ollama`, or `custom_openai_compatible` |
| LLM base URL | `LLM_BASE_URL` | Optional when using a preset provider (defaults apply) |
| LLM API key | `LLM_API_KEY` | Provider key (not required for Ollama) |
| LLM model | `LLM_MODEL` | e.g. `gpt-4o-mini`, `claude-sonnet-4-20250514`, `gemini-2.0-flash` |

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
| Log level | `CURATORX_LOG_LEVEL` or `LOG_LEVEL` | `ERROR`, `WARNING`, `INFO` (default), or `DEBUG` |
| Log format | `LOG_FORMAT` or `CURATORX_LOG_FORMAT` | `text` (default) or `json` |

---

## Logging

CuratorX logs to **stdout/stderr** for Docker and systemd deployments. Set the level in `.env` or `docker-compose.yml`:

| Level | What you see |
|-------|----------------|
| **ERROR** | Failures only (sync crashes, tool errors, HTTP hard failures) |
| **WARNING** | HTTP errors/timeouts, episode sync skips, LLM chat errors, invalid settings |
| **INFO** | Startup, sync start/finish, scheduler triggers, action propose/confirm, phase counts |
| **DEBUG** | Per-job progress, TMDB/Fanart enrichment skips, agent tool calls, env/settings merge |

Examples:

```bash
# Follow live logs
docker compose logs -f curatorx

# Verbose troubleshooting
CURATORX_LOG_LEVEL=DEBUG docker compose up -d

# Errors only
CURATORX_LOG_LEVEL=ERROR docker compose up -d
```

API keys and tokens are never written to logs (URLs and error bodies are redacted).

---

## LLM providers

| Provider | Default base URL | Notes |
|----------|------------------|-------|
| **openai** | `https://api.openai.com/v1` | OpenAI API |
| **anthropic** | `https://api.anthropic.com` | Native Claude API (`LLM_API_KEY` + `LLM_MODEL`) |
| **gemini** | `https://generativelanguage.googleapis.com/v1beta/openai` | Google Gemini via OpenAI-compatible layer |
| **groq** | `https://api.groq.com/openai/v1` | Groq inference |
| **mistral** | `https://api.mistral.ai/v1` | Mistral API |
| **together** | `https://api.together.xyz/v1` | Together AI |
| **deepseek** | `https://api.deepseek.com/v1` | DeepSeek API |
| **openrouter** | `https://openrouter.ai/api/v1` | OpenRouter gateway |
| **ollama** | `http://localhost:11434/v1` | Local inference; no API key required |
| **custom_openai_compatible** | User-defined | Set `LLM_BASE_URL` manually (LiteLLM, vLLM, etc.) |

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

API keys are stored in `settings.json` on the config volume when saved via the UI. Environment variables (including values from `.env` when running locally or via Docker `env_file`) override file values at runtime and are **not** written back unless you explicitly save a new value in Settings.

`GET /api/settings` masks secret fields and returns `{field}_set: true` plus `{field}_source` (`env` or `file`) instead of raw values. The config UI shows placeholders such as “Configured via environment (.env)” for env-backed secrets.

Local dev: copy `.env.example` to `.env` — the web app loads it on startup (`load_dotenv_file`). Docker Compose also passes `.env` via `env_file`.

---

## Related documentation

- [ONBOARDING.md](ONBOARDING.md) — first-run flow
- [DATA_MODEL.md](DATA_MODEL.md) — full schema reference
- [DOCKER.md](DOCKER.md) — container env seeding
