"""Setup wizard helpers."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Mapping

from curatorx.agent.providers import get_chat_provider
from curatorx.config_store import Settings, resolve_llm_base_url, resolve_llm_model, validate_llm_settings
from curatorx.connectors.fanart import FanartClient
from curatorx.connectors.plex import PlexClient
from curatorx.connectors.radarr import RadarrClient
from curatorx.connectors.sonarr import SonarrClient
from curatorx.connectors.tautulli import TautulliClient
from curatorx.connectors.tmdb import TMDBClient
from curatorx.library.db import Database

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

CERTIFIED_SERVICES = (
    "llm",
    "plex",
    "radarr",
    "sonarr",
    "tmdb",
    "fanart",
    "tautulli",
)

ONBOARDING_HINTS = [
    "Name me — I'll adapt my voice as we explore your library together.",
    "Verify LLM, Plex, Radarr, and Sonarr so I can read and act on your collection.",
    "Pick your movie and TV Plex libraries — I'll handle the rest automatically.",
]

PLEX_TYPE_ALIASES = {
    "movie": "movie",
    "movies": "movie",
    "show": "show",
    "shows": "show",
    "tv": "show",
}


def normalize_plex_type(raw_type: str) -> str:
    return PLEX_TYPE_ALIASES.get(str(raw_type or "").lower().strip(), str(raw_type or "").lower().strip())


def _integration_token_marker(token: str) -> str:
    cleaned = str(token or "").strip()
    if not cleaned:
        return ""
    return "***configured***"


def record_service_integration(
    db: Database,
    service_name: str,
    *,
    base_url: str = "",
    api_token: str = "",
    ok: bool,
) -> None:
    db.upsert_service_integration(
        service_name,
        base_url=base_url.strip().rstrip("/"),
        api_token_encrypted=_integration_token_marker(api_token),
        connection_status="verified" if ok else "failed",
        last_tested_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        certified=1 if ok else 0,
    )


def test_plex(plex_url: str, plex_token: str) -> CheckResult:
    if not plex_url or not plex_token:
        return {"ok": False, "message": "Plex URL and token are required.", "sections": []}
    try:
        client = PlexClient(plex_url.strip().rstrip("/"), plex_token.strip())
        sections = [
            {
                "key": s.key,
                "title": s.title,
                "type": normalize_plex_type(s.type),
            }
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
        version = status.get("version", "unknown")
        count = len(movies)
        return {
            "ok": True,
            "message": f"Connected — Radarr v{version} | {count:,} Movies Found",
            "version": version,
            "movie_count": count,
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
        version = status.get("version", "unknown")
        count = len(series)
        return {
            "ok": True,
            "message": f"Connected — Sonarr v{version} | {count:,} Series Found",
            "version": version,
            "series_count": count,
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


def test_fanart(api_key: str) -> CheckResult:
    if not api_key:
        return {"ok": False, "message": "Fanart API key is required."}
    try:
        FanartClient(api_key.strip()).movie(550)
        return {"ok": True, "message": "Fanart.tv connected."}
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


async def _ping_llm(settings: Settings) -> None:
    provider = get_chat_provider(settings)
    response = await provider.chat([{"role": "user", "content": "ping"}])
    if not response:
        raise RuntimeError("Empty response from LLM provider.")


def test_llm(
    llm_provider: str,
    llm_base_url: str,
    llm_api_key: str,
    llm_model: str,
) -> CheckResult:
    provider = (llm_provider or "openai").lower().strip()
    model = resolve_llm_model(provider, llm_model)
    if not model:
        return {"ok": False, "message": "LLM model identifier is required."}
    if provider != "ollama" and not str(llm_api_key or "").strip():
        return {"ok": False, "message": "LLM API key is required for this provider."}
    resolved_base = resolve_llm_base_url(provider, llm_base_url)
    if provider == "custom_openai_compatible" and not resolved_base:
        return {"ok": False, "message": "Base URL is required for custom OpenAI-compatible providers."}
    settings = Settings(
        llm_provider=provider,
        llm_base_url=resolved_base,
        llm_api_key=str(llm_api_key or "").strip(),
        llm_model=model,
    )
    config_error = validate_llm_settings(settings)
    if config_error:
        return {"ok": False, "message": config_error}
    try:
        asyncio.run(_ping_llm(settings))
        return {
            "ok": True,
            "message": f"LLM connected — {provider} / {model}",
            "hint": ONBOARDING_HINTS[0],
            "hints": ONBOARDING_HINTS,
        }
    except Exception as error:  # noqa: BLE001
        return {"ok": False, "message": str(error)}


def _integration_certified(db: Database, service_name: str) -> bool:
    row = db.get_service_integration(service_name)
    if not row:
        return False
    keys = row.keys()
    if "certified" in keys:
        return bool(row["certified"])
    return str(row["connection_status"]) == "verified"


def build_certifications_status(db: Database) -> Dict[str, Any]:
    services: Dict[str, Any] = {}
    for service_name in CERTIFIED_SERVICES:
        row = db.get_service_integration(service_name)
        if row:
            services[service_name] = {
                "certified": _integration_certified(db, service_name),
                "connection_status": str(row["connection_status"] or "unverified"),
                "message": "",
                "last_tested_at": row["last_tested_at"],
            }
        else:
            services[service_name] = {
                "certified": False,
                "connection_status": "unverified",
                "message": "",
                "last_tested_at": None,
            }
    return {"services": services}


def _incoming_secret_changed(
    incoming: Mapping[str, Any],
    field: str,
    before_value: str,
) -> bool:
    incoming_value = str(incoming.get(field) or "").strip()
    if not incoming_value:
        return False
    return incoming_value != str(before_value or "").strip()


def invalidate_certifications_on_settings_change(
    db: Database,
    before: Settings,
    after: Settings,
    incoming: Mapping[str, Any],
) -> None:
    checks = {
        "llm": (
            before.llm_base_url != after.llm_base_url
            or before.llm_provider != after.llm_provider
            or before.llm_model != after.llm_model
            or _incoming_secret_changed(incoming, "llm_api_key", before.llm_api_key)
        ),
        "plex": (
            before.plex_url != after.plex_url
            or _incoming_secret_changed(incoming, "plex_token", before.plex_token)
        ),
        "radarr": (
            before.radarr_url != after.radarr_url
            or _incoming_secret_changed(incoming, "radarr_api_key", before.radarr_api_key)
        ),
        "sonarr": (
            before.sonarr_url != after.sonarr_url
            or _incoming_secret_changed(incoming, "sonarr_api_key", before.sonarr_api_key)
        ),
        "tmdb": (
            before.tmdb_api_key != after.tmdb_api_key
            or _incoming_secret_changed(incoming, "tmdb_api_key", before.tmdb_api_key)
        ),
        "fanart": (
            before.fanart_api_key != after.fanart_api_key
            or _incoming_secret_changed(incoming, "fanart_api_key", before.fanart_api_key)
        ),
        "tautulli": (
            before.tautulli_url != after.tautulli_url
            or _incoming_secret_changed(incoming, "tautulli_api_key", before.tautulli_api_key)
        ),
    }
    for service_name, changed in checks.items():
        if changed:
            db.invalidate_service_certification(service_name)


def build_wizard_status(settings: Settings, db: Database) -> Dict[str, Any]:
    llm_verified = _integration_certified(db, "llm")
    plex_verified = _integration_certified(db, "plex")
    sections_set = bool(settings.plex_movie_section and settings.plex_tv_section)
    radarr_verified = _integration_certified(db, "radarr")
    sonarr_verified = _integration_certified(db, "sonarr")
    persona = db.get_persona()
    identity_complete = bool(persona and str(persona["curator_name"] or "").strip())

    infrastructure_complete = (
        llm_verified and plex_verified and radarr_verified and sonarr_verified
    )
    mapping_complete = plex_verified and sections_set

    steps = {
        "identity_seed": {
            "complete": identity_complete,
            "curator_name_set": identity_complete,
        },
        "infrastructure": {
            "complete": infrastructure_complete,
            "llm_verified": llm_verified,
            "plex_verified": plex_verified,
            "radarr_verified": radarr_verified,
            "sonarr_verified": sonarr_verified,
        },
        "dropdown_mapping": {
            "complete": mapping_complete,
            "plex_verified": plex_verified,
            "sections_set": sections_set,
        },
    }

    if settings.onboarding_complete:
        current_step = 3
    elif mapping_complete and infrastructure_complete and identity_complete:
        current_step = 2
    elif infrastructure_complete:
        current_step = 2
    elif identity_complete:
        current_step = 1
    else:
        current_step = 0

    return {
        "current_step": current_step,
        "steps": steps,
        "onboarding_complete": settings.onboarding_complete,
        "certifications": build_certifications_status(db)["services"],
    }


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


def resolve_test_payload(payload: Mapping[str, Any], existing: Settings) -> Dict[str, Any]:
    """Fill empty test payload fields from merged settings (incl. env-backed secrets)."""
    merged = merge_secret_fields(payload, existing)
    for field in ("plex_url", "radarr_url", "sonarr_url", "tautulli_url", "llm_base_url"):
        if not str(merged.get(field) or "").strip():
            merged[field] = getattr(existing, field)
    if not str(merged.get("llm_provider") or "").strip():
        merged["llm_provider"] = existing.llm_provider
    if not str(merged.get("llm_model") or "").strip():
        merged["llm_model"] = existing.llm_model
    return merged


def sync_settings_to_db(db: Database, settings: Settings) -> None:
    db.sync_llm_config(
        llm_provider=settings.llm_provider,
        llm_base_url=settings.llm_base_url,
        llm_model=settings.llm_model,
    )
    persona = db.get_persona()
    if persona:
        db.set_config("curator_name", str(persona["curator_name"] or "Curator"))
