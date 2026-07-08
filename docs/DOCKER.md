# Docker / Unraid

## Docker Compose

```bash
cp .env.example .env
docker compose up -d --build
```

Open `http://localhost:8788`.

## Unraid

Install from the Community Applications template (`templates/mediacurator.xml`) or add manually:

- **Port:** 8788
- **Config path:** `/mnt/user/appdata/mediacurator/config` → `/config`

Seed optional environment variables for Plex, *arr, TMDB, and LLM keys on first run.

## Data layout

| Path | Contents |
|------|----------|
| `/config/settings.json` | User settings |
| `/config/mediacurator.db` | Library index, chat, preferences, embeddings |

## Resources

- LLM via Ollama: allocate RAM on the Unraid host for your chosen model.
- Library sync: CPU-bound during TMDB enrichment; runs as a background job.
