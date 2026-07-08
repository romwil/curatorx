"""Setup wizard helpers."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from mediacurator.config_store import Settings
from mediacurator.connectors.plex import PlexClient
from mediacurator.connectors.radarr import RadarrClient
from mediacurator.connectors.sonarr import SonarrClient
from mediacurator.connectors.tautulli import TautulliClient
from mediacurator.connectors.tmdb import TMDBClient

CheckResult = Dict[str, Any]

SECRET_FIELDS = (
    "plex_token",
    "radarr_api_key",
    "sonarr_api_key",
    "tmdb_api_key",
    "tvdb_api_key",
    "fanart_api_key",
    "tautulli_api_key",
    "llm_api_key",
)


def test_plex(plex_url: str, plex_token: str) -> CheckResult:
    if not plex_url or not plex_token:
        return {"ok": False, "message": "Plex URL and token are required."}
    try:
        client = PlexClient(plex_url.strip().rstrip("/"), plex_token.strip())
        sections = [
            {"key": s.key, "title": s.title, "type": s.type}
            for s in client.list_sections()
        ]
        return {
            "ok": True,
            "message": f"Connected — {len(sections)} libraries found.",
            "sections": sections,
        }
    except Exception as error:  # noqa: BLE001
        return {"ok": False, "message": str(error), "sections": []}


def test_radarr(radarr_url: str, radarr_api_key: str) -> CheckResult:
    if not radarr_url or not radarr_api_key:
        return {"ok": False, "message": "Radarr URL and API key are required."}
    try:
        client = RadarrClient(radarr_url.strip().rstrip("/"), radarr_api_key.strip())
        status = client.system_status()
        movies = client.movies()
        return {
            "ok": True,
            "message": f"Radarr {status.get('version', 'unknown')} — {len(movies)} movies.",
            "movie_count": len(movies),
        }
    except Exception as error:  # noqa: BLE001
        return {"ok": False, "message": str(error)}


def test_sonarr(sonarr_url: str, sonarr_api_key: str) -> CheckResult:
    if not sonarr_url or not sonarr_api_key:
        return {"ok": False, "message": "Sonarr URL and API key are required."}
    try:
        client = SonarrClient(sonarr_url.strip().rstrip("/"), sonarr_api_key.strip())
        status = client.system_status()
        series = client.series_list()
        return {
            "ok": True,
            "message": f"Sonarr {status.get('version', 'unknown')} — {len(series)} series.",
            "series_count": len(series),
        }
    except Exception as error:  # noqa: BLE001
        return {"ok": False, "message": str(error)}


def test_tmdb(api_key: str) -> CheckResult:
    if not api_key:
        return {"ok": False, "message": "TMDB API key is required."}
    try:
        TMDBClient(api_key.strip()).genre_list_movies()
        return {"ok": True, "message": "TMDB connected."}
    except Exception as error:  # noqa: BLE001
        return {"ok": False, "message": str(error)}


def test_tautulli(url: str, api_key: str) -> CheckResult:
    if not url or not api_key:
        return {"ok": False, "message": "Tautulli URL and API key are required."}
    try:
        libraries = TautulliClient(url.strip().rstrip("/"), api_key.strip()).get_libraries()
        return {"ok": True, "message": f"Tautulli connected — {len(libraries)} libraries."}
    except Exception as error:  # noqa: BLE001
        return {"ok": False, "message": str(error)}


def build_setup_status(settings: Settings) -> Dict[str, Any]:
    plex_ok = bool(settings.plex_url and settings.plex_token)
    radarr_ok = bool(settings.radarr_url and settings.radarr_api_key)
    sonarr_ok = bool(settings.sonarr_url and settings.sonarr_api_key)
    tmdb_ok = bool(settings.tmdb_api_key)
    llm_ok = bool(settings.llm_api_key or settings.llm_provider == "ollama")

    return {
        "onboarding_complete": settings.onboarding_complete,
        "ready_to_curate": plex_ok and tmdb_ok,
        "checks": {
            "plex": {"ok": plex_ok, "message": "Configured" if plex_ok else "Plex required."},
            "radarr": {"ok": radarr_ok, "message": "Configured" if radarr_ok else "Optional for movie adds."},
            "sonarr": {"ok": sonarr_ok, "message": "Configured" if sonarr_ok else "Optional for TV adds."},
            "tmdb": {"ok": tmdb_ok, "message": "Configured" if tmdb_ok else "TMDB required for discovery."},
            "llm": {"ok": llm_ok, "message": "Configured" if llm_ok else "LLM API key or Ollama required."},
        },
    }


def merge_secret_fields(incoming: Mapping[str, Any], existing: Settings) -> Dict[str, Any]:
    merged = dict(incoming)
    for field in SECRET_FIELDS:
        if not str(merged.get(field) or "").strip():
            merged[field] = getattr(existing, field)
    return merged
