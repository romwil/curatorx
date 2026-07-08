"""FastAPI application for MediaCurator."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from mediacurator import __version__
from mediacurator.agent.curator import CuratorAgent, stream_agent
from mediacurator.agent.tools import execute_confirmed_action
from mediacurator.config_store import Settings, load_merged_settings, save_settings
from mediacurator.connectors.plex import PlexClient
from mediacurator.library.titles import get_title_detail
from mediacurator.models.schemas import ActionConfirmRequest, ChatRequest, PreferenceSignal
from mediacurator.preferences.store import remember_preference
from mediacurator.web.jobs import get_job_manager, get_sync_scheduler
from mediacurator.web.setup import (
    SECRET_FIELDS,
    build_setup_status,
    merge_secret_fields,
    test_plex,
    test_radarr,
    test_sonarr,
    test_tautulli,
    test_tmdb,
)

DATA_DIR = Path(os.environ.get("DATA_DIR", "/config"))
STATIC_DIR = Path(__file__).resolve().parent / "static"
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

app = FastAPI(title="MediaCurator", version=__version__)


@app.on_event("startup")
def _startup() -> None:
    get_job_manager()
    get_sync_scheduler().start()


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")
elif STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class SettingsPayload(BaseModel):
    plex_url: str = ""
    plex_token: str = ""
    plex_movie_section: str = ""
    plex_tv_section: str = ""
    radarr_url: str = ""
    radarr_api_key: str = ""
    sonarr_url: str = ""
    sonarr_api_key: str = ""
    movies_root: str = ""
    tv_root: str = ""
    radarr_root_folder: str = ""
    sonarr_root_folder: str = ""
    radarr_quality_profile_id: int = 1
    sonarr_quality_profile_id: int = 1
    tmdb_api_key: str = ""
    tvdb_api_key: str = ""
    fanart_api_key: str = ""
    tautulli_url: str = ""
    tautulli_api_key: str = ""
    llm_provider: str = "openai_compatible"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_embedding_model: str = ""
    llm_embedding_base_url: str = ""
    onboarding_complete: bool = False
    library_sync_interval_hours: int = Field(default=24, ge=1, le=168)
    tv_page_size: int = Field(default=500, ge=50, le=2000)


class TestPayload(BaseModel):
    plex_url: str = ""
    plex_token: str = ""
    radarr_url: str = ""
    radarr_api_key: str = ""
    sonarr_url: str = ""
    sonarr_api_key: str = ""
    tmdb_api_key: str = ""
    tautulli_url: str = ""
    tautulli_api_key: str = ""


def _settings() -> Settings:
    return load_merged_settings(DATA_DIR)


def _mask_settings(settings: Settings) -> Dict[str, Any]:
    payload = asdict(settings)
    for field in SECRET_FIELDS:
        payload[f"{field}_set"] = bool(getattr(settings, field))
        payload[field] = ""
    return payload


def _db():
    return get_job_manager().db


def _serve_index() -> HTMLResponse:
    index = FRONTEND_DIST / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    fallback = STATIC_DIR / "index.html"
    if fallback.exists():
        return HTMLResponse(fallback.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>MediaCurator</h1><p>Build the frontend with <code>npm run build</code>.</p>")


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return _serve_index()


@app.get("/config", response_class=HTMLResponse)
def config_page() -> HTMLResponse:
    return _serve_index()


@app.get("/title/{media_type}/{item_id}", response_class=HTMLResponse)
def title_page(media_type: str, item_id: str) -> HTMLResponse:
    return _serve_index()


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/api/setup/status")
def setup_status() -> Dict[str, Any]:
    return build_setup_status(_settings())


@app.get("/api/settings")
def get_settings() -> Dict[str, Any]:
    return _mask_settings(_settings())


@app.put("/api/settings")
def put_settings(payload: SettingsPayload) -> Dict[str, Any]:
    existing = _settings()
    merged = merge_secret_fields(payload.model_dump(), existing)
    settings = Settings.from_mapping(merged)
    save_settings(DATA_DIR, settings)
    return _mask_settings(settings)


@app.post("/api/setup/test/plex")
def api_test_plex(payload: TestPayload) -> Dict[str, Any]:
    return test_plex(payload.plex_url, payload.plex_token)


@app.post("/api/setup/test/radarr")
def api_test_radarr(payload: TestPayload) -> Dict[str, Any]:
    return test_radarr(payload.radarr_url, payload.radarr_api_key)


@app.post("/api/setup/test/sonarr")
def api_test_sonarr(payload: TestPayload) -> Dict[str, Any]:
    return test_sonarr(payload.sonarr_url, payload.sonarr_api_key)


@app.post("/api/setup/test/tmdb")
def api_test_tmdb(payload: TestPayload) -> Dict[str, Any]:
    return test_tmdb(payload.tmdb_api_key)


@app.post("/api/setup/test/tautulli")
def api_test_tautulli(payload: TestPayload) -> Dict[str, Any]:
    return test_tautulli(payload.tautulli_url, payload.tautulli_api_key)


@app.get("/api/plex/sections")
def plex_sections() -> List[Dict[str, str]]:
    settings = _settings()
    if not settings.plex_url or not settings.plex_token:
        raise HTTPException(status_code=400, detail="Plex not configured")
    client = PlexClient(settings.plex_url, settings.plex_token)
    return [{"key": s.key, "title": s.title, "type": s.type} for s in client.list_sections()]


@app.get("/api/jobs")
def list_jobs() -> List[Dict[str, Any]]:
    return [job.to_dict() for job in get_job_manager().list_jobs()]


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> Dict[str, Any]:
    job = get_job_manager().get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@app.post("/api/library/sync")
def start_library_sync() -> Dict[str, Any]:
    job = get_job_manager().start_sync(_settings())
    return job.to_dict()


@app.get("/api/library/stats")
def library_stats() -> Dict[str, Any]:
    db = _db()
    items = db.all_library_items()
    movies = sum(1 for i in items if i["media_type"] == "movie")
    shows = sum(1 for i in items if i["media_type"] == "show")
    return {
        "total": len(items),
        "movies": movies,
        "shows": shows,
        "last_sync": db.get_sync_state("last_sync"),
    }


@app.post("/api/chat")
async def chat(payload: ChatRequest) -> Dict[str, Any]:
    session_id = payload.session_id or uuid.uuid4().hex
    try:
        return await CuratorAgent(_db(), _settings()).run(session_id, payload.message)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/api/chat/stream")
async def chat_stream(message: str, session_id: Optional[str] = None) -> EventSourceResponse:
    sid = session_id or uuid.uuid4().hex

    async def event_generator():
        try:
            async for chunk in stream_agent(_db(), _settings(), sid, message):
                data = json.loads(chunk)
                yield {"event": data.get("type", "message"), "data": chunk.strip()}
        except Exception as error:  # noqa: BLE001
            yield {"event": "error", "data": json.dumps({"error": str(error)})}

    return EventSourceResponse(event_generator())


@app.get("/api/title/{media_type}/{item_id}")
def title_detail(media_type: str, item_id: str, id_type: str = "tmdb") -> Dict[str, Any]:
    settings = _settings()
    db = _db()
    kwargs: Dict[str, Any] = {"media_type": media_type}
    if id_type == "rating_key":
        kwargs["rating_key"] = item_id
    elif media_type == "show" and id_type == "tvdb":
        kwargs["tvdb_id"] = int(item_id)
    else:
        kwargs["tmdb_id"] = int(item_id)
    detail = get_title_detail(db, settings, **kwargs)
    return detail.model_dump()


@app.post("/api/actions/propose")
def propose_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    import uuid as uuid_mod

    action = payload.get("action")
    if action == "add_radarr":
        token = uuid_mod.uuid4().hex
        _db().save_pending_action(
            token,
            "add_radarr",
            {"action": "add_radarr", "tmdb_id": int(payload["tmdb_id"]), "title": payload.get("title", "")},
        )
        return {"confirmation_token": token}
    if action == "add_sonarr":
        token = uuid_mod.uuid4().hex
        _db().save_pending_action(
            token,
            "add_sonarr",
            {"action": "add_sonarr", "tvdb_id": int(payload["tvdb_id"]), "title": payload.get("title", "")},
        )
        return {"confirmation_token": token}
    raise HTTPException(status_code=400, detail="Unknown action")


@app.post("/api/actions/confirm")
async def confirm_action(payload: ActionConfirmRequest) -> Dict[str, Any]:
    if not payload.confirmed:
        _db().pop_pending_action(payload.token)
        return {"cancelled": True}
    try:
        result = await execute_confirmed_action(_db(), _settings(), payload.token)
        return {"ok": True, **result}
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/preferences")
def add_preference(payload: PreferenceSignal) -> Dict[str, bool]:
    remember_preference(_db(), payload)
    return {"saved": True}
