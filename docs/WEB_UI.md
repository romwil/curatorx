# Web UI

## Routes

| Route | Purpose |
|-------|---------|
| `/` | Chat curator with inline title cards |
| `/config` | Setup wizard / settings |
| `/title/{movie\|show}/{id}` | Full title detail page |

## Chat features

- Streaming responses via `/api/chat/stream` (SSE)
- Inline **title cards** with poster, rating, genres, recommendation reason
- **Turnstyle viewport** for expanded list browsing
- **Add to Radarr/Sonarr** with confirmation dialog
- **Not interested** signals feed preference learning

## API highlights

- `POST /api/chat` — send a message
- `POST /api/library/sync` — background Plex index job
- `GET /api/title/{media_type}/{id}` — title detail payload
- `POST /api/actions/propose` + `POST /api/actions/confirm` — gated *arr actions
- `POST /api/preferences` — record taste signals

## Security

No built-in authentication. Use on a trusted LAN or behind an authenticated reverse proxy.
