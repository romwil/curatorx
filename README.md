# MediaCurator

Agentic movie and TV collection curator for Plex libraries. Chat with an AI curator that knows your library, learns your taste, recommends hidden gems, and adds titles to Radarr/Sonarr after confirmation.

## Features

- **Chat-first UI** with inline movie/TV cards and a turnstyle viewport for browsing recommendations
- **BYOP LLM** — configure OpenAI, Anthropic, Ollama, or any OpenAI-compatible provider
- **RAG over your Plex library** — informed conversations grounded in what you own and watch
- **Metadata enrichment** — TMDB, TVDB, Fanart.tv, optional Tautulli watch stats
- **Add to collection** — confirmation-gated Radarr/Sonarr queue actions from chat or cards
- **Purge suggestions** — find clunkers wasting drive space based on watch history and taste fit
- **Unraid-ready** — Docker container with setup wizard

## Quick start

```bash
docker compose up -d
# Open http://localhost:8788 and complete the setup wizard
```

### Local development (Mac)

Project path: `/Users/willrompala/code/mediacurator`

```bash
cd /Users/willrompala/code/mediacurator
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[web]"
cd frontend && npm install && npm run build && cd ..
DATA_DIR=./config python -m mediacurator.web
# Open http://localhost:8788
```

Or with Docker from the same directory:

```bash
cd /Users/willrompala/code/mediacurator
docker compose up -d --build
```

Legacy quick start without path:

```bash
pip install ".[web]"
cd frontend && npm install && npm run build
DATA_DIR=./config python -m mediacurator.web
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — platform design, data flows, deployment, security
- [Design](docs/DESIGN.md) — product principles, UX, agent tools, API surface
- [Data model](docs/DATA_MODEL.md) — SQLite schema, settings, Pydantic types
- [Configuration](docs/CONFIGURATION.md)
- [Onboarding](docs/ONBOARDING.md)
- [Docker / Unraid](docs/DOCKER.md)
- [Web UI](docs/WEB_UI.md)

## License

MIT — see [LICENSE](LICENSE).
