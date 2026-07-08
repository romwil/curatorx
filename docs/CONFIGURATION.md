# Configuration

Settings persist to `{DATA_DIR}/settings.json` (default `/config/settings.json`). Environment variables override file values when set.

## Required

| Setting | Description |
|---------|-------------|
| `PLEX_URL` / `PLEX_TOKEN` | Plex server connection |
| `PLEX_MOVIE_SECTION` / `PLEX_TV_SECTION` | Library section keys |
| `TMDB_API_KEY` | TMDB discovery and metadata |

## Recommended

| Setting | Description |
|---------|-------------|
| `RADARR_URL` / `RADARR_API_KEY` | Add movies after confirmation |
| `SONARR_URL` / `SONARR_API_KEY` | Add TV shows after confirmation |
| `LLM_PROVIDER` / `LLM_API_KEY` / `LLM_MODEL` | BYOP agent (OpenAI-compatible, Anthropic, Ollama) |

## Optional

| Setting | Description |
|---------|-------------|
| `FANART_API_KEY` | Rich poster/backdrop art |
| `TVDB_API_KEY` | TV metadata parity with Sonarr |
| `TAUTULLI_URL` / `TAUTULLI_API_KEY` | Watch stats for purge suggestions |
| `RADARR_ROOT_FOLDER` / `SONARR_ROOT_FOLDER` | Default add paths |
| `RADARR_QUALITY_PROFILE_ID` / `SONARR_QUALITY_PROFILE_ID` | Quality profiles for adds |

## LLM providers

- `openai_compatible` — OpenAI, OpenRouter, LiteLLM, etc. Set `LLM_BASE_URL` and `LLM_API_KEY`.
- `anthropic` — Set `LLM_API_KEY` and `LLM_MODEL` (e.g. `claude-3-5-sonnet-latest`).
- `ollama` — Local Unraid inference. Set `LLM_BASE_URL=http://host:11434/v1`.

Embeddings use `LLM_EMBEDDING_MODEL` and optional `LLM_EMBEDDING_BASE_URL`. Without an embedding API, deterministic hash embeddings are used.
