"""FastAPI application for CuratorX."""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from curatorx import __version__
from curatorx.agent.curator import CuratorAgent, stream_agent
from curatorx.agent.tools import execute_confirmed_action
from curatorx.config_store import Settings, load_merged_settings, save_settings
from curatorx.connectors.plex import PlexClient
from curatorx.library.db import DEFAULT_LENS_ID
from curatorx.library.titles import get_title_detail
from curatorx.models.schemas import (
    ActionConfirmRequest,
    ActiveLensPayload,
    ChatRequest,
    Lens,
    LensCreate,
    LensUpdate,
    PersonaMetrics,
    PersonaMetricsUpdate,
    PreferenceSignal,
    SystemConfigUpdate,
)
from curatorx.preferences.store import remember_preference
from curatorx.web.jobs import get_job_manager, get_sync_scheduler
from curatorx.web.setup import (
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

app = FastAPI(title="CuratorX", version=__version__)


def _row_to_lens(row: Any) -> Lens:
    return Lens(
        lens_id=str(row["lens_id"]),
        lens_name=str(row["lens_name"]),
        description=str(row["description"] or ""),
        created_at=str(row["created_at"]) if row["created_at"] is not None else None,
    )


def _row_to_persona(row: Any) -> PersonaMetrics:
    return PersonaMetrics(
        metric_id=str(row["metric_id"]),
        curator_name=str(row["curator_name"] or "Curator"),
        val_bro_prof=float(row["val_bro_prof"]),
        val_dipl_snark=float(row["val_dipl_snark"]),
        val_pass_auto=float(row["val_pass_auto"]),
        last_modified=str(row["last_modified"]) if row["last_modified"] is not None else None,
    )


def _resolve_lens_id(lens_id: Optional[str]) -> str:
    db = _db()
    resolved = (lens_id or db.get_active_lens_id() or DEFAULT_LENS_ID).strip() or DEFAULT_LENS_ID
    if not db.get_lens(resolved):
        raise HTTPException(status_code=404, detail=f"Unknown lens_id: {resolved}")
    return resolved


@app.on_event("startup")
def _startup() -> None:
    get_job_manager()
    get_job_manager().db.ensure_seed_data()
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
    return HTMLResponse("<h1>CuratorX</h1><p>Build the frontend with <code>npm run build</code>.</p>")


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


@app.get("/api/lenses", response_model=List[Lens])
def list_lenses() -> List[Lens]:
    return [_row_to_lens(row) for row in _db().list_lenses()]


@app.get("/api/lenses/active", response_model=Lens)
def get_active_lens() -> Lens:
    lens_id = _db().get_active_lens_id()
    row = _db().get_lens(lens_id)
    if not row:
        raise HTTPException(status_code=404, detail="Active lens not found")
    return _row_to_lens(row)


@app.put("/api/lenses/active", response_model=Lens)
def set_active_lens(payload: ActiveLensPayload) -> Lens:
    try:
        _db().set_active_lens_id(payload.lens_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    row = _db().get_lens(payload.lens_id)
    assert row is not None
    return _row_to_lens(row)


@app.post("/api/lenses", response_model=Lens)
def create_lens(payload: LensCreate) -> Lens:
    lens_id = re.sub(r"[^a-z0-9_-]+", "-", payload.lens_id.strip().lower()).strip("-")
    if not lens_id:
        raise HTTPException(status_code=400, detail="Invalid lens_id")
    if _db().get_lens(lens_id):
        raise HTTPException(status_code=409, detail="Lens already exists")
    return _row_to_lens(_db().create_lens(lens_id, payload.lens_name.strip(), payload.description.strip()))


@app.put("/api/lenses/{lens_id}", response_model=Lens)
def update_lens(lens_id: str, payload: LensUpdate) -> Lens:
    if not _db().get_lens(lens_id):
        raise HTTPException(status_code=404, detail="Lens not found")
    try:
        row = _db().update_lens(
            lens_id,
            lens_name=payload.lens_name,
            description=payload.description,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return _row_to_lens(row)


@app.get("/api/persona", response_model=PersonaMetrics)
def get_persona() -> PersonaMetrics:
    row = _db().get_persona()
    if not row:
        _db().ensure_seed_data()
        row = _db().get_persona()
    if not row:
        raise HTTPException(status_code=500, detail="Persona seed failed")
    return _row_to_persona(row)


@app.put("/api/persona", response_model=PersonaMetrics)
def put_persona(payload: PersonaMetricsUpdate) -> PersonaMetrics:
    row = _db().upsert_persona(
        curator_name=payload.curator_name,
        val_bro_prof=payload.val_bro_prof,
        val_dipl_snark=payload.val_dipl_snark,
        val_pass_auto=payload.val_pass_auto,
    )
    return _row_to_persona(row)


@app.get("/api/system-config")
def get_system_config() -> Dict[str, str]:
    return _db().get_all_config()


@app.put("/api/system-config")
def put_system_config(payload: SystemConfigUpdate) -> Dict[str, str]:
    if not payload.values:
        raise HTTPException(status_code=400, detail="No config values provided")
    db = _db()
    for key, value in payload.values.items():
        key_clean = str(key).strip()
        if not key_clean:
            continue
        db.set_config(key_clean, str(value))
        if key_clean == "curator_name":
            db.upsert_persona(curator_name=str(value))
        if key_clean == "active_lens_id":
            try:
                db.set_active_lens_id(str(value))
            except ValueError as error:
                raise HTTPException(status_code=404, detail=str(error)) from error
    return db.get_all_config()


@app.post("/api/chat")
async def chat(payload: ChatRequest) -> Dict[str, Any]:
    session_id = payload.session_id or uuid.uuid4().hex
    lens_id = _resolve_lens_id(payload.lens_id)
    try:
        return await CuratorAgent(_db(), _settings(), lens_id=lens_id).run(session_id, payload.message)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/api/chat/stream")
async def chat_stream(
    message: str,
    session_id: Optional[str] = None,
    lens_id: Optional[str] = None,
) -> EventSourceResponse:
    sid = session_id or uuid.uuid4().hex
    resolved_lens = _resolve_lens_id(lens_id)

    async def event_generator():
        try:
            async for chunk in stream_agent(_db(), _settings(), sid, message, lens_id=resolved_lens):
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
