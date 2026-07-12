# Troubleshooting

## Container will not start

- Confirm port `8788` is free (or remap the host port)
- Check logs: `docker logs curatorx` / `docker compose logs -f curatorx`
- Ensure the `/config` volume is writable by the container user

## Setup wizard stuck

- Verify each service with **Test / Verify** on the Config page
- Plex section dropdowns unlock only after Plex verifies successfully
- Env-backed API keys work for Verify without re-typing secrets into the UI

## Sync fails or looks stuck

- After a **container restart**, any in-flight sync is marked failed: *Interrupted by server restart — start sync again*
- Confirm Plex URL/token and movie/TV section mapping
- Check TMDB key if enrichment fails mid-sync
- Tail logs with `CURATORX_LOG_LEVEL=DEBUG`

## Status dock shows no progress

- Open Config → Library sync card for the same job payload
- Hard-refresh the browser; jobs are polled from `GET /api/jobs`
- Ensure you are not looking at an interrupted (failed) job from a prior restart

## Chat / LLM errors

- Confirm `LLM_PROVIDER`, base URL, API key, and model
- For Ollama on Unraid, use a reachable host URL from inside the container (see [Unraid](Unraid.md))

## Radarr / Sonarr add fails

- Root folder and quality profile must be set
- Adds are confirmation-gated — confirm the status-dock prompt
- “Already exists” responses are handled gracefully; check the dock feedback

## Multi-user / Seerr

- Features are off by default — enable flags explicitly
- OIDC/local login are not available in 1.0
- Sync via `/sync` is blocked for members when multi-user is on — use Config as owner

More: [FAQ](FAQ.md) · [Library Sync](Library-Sync.md)
