"""Background job manager for library sync."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Literal, Optional

from curatorx.config_store import Settings, load_merged_settings
from curatorx.library.db import Database
from curatorx.library.facets import ensure_library_facet_index
from curatorx.library.query import refresh_library_overview_cache
from curatorx.library.sync import sync_library
from curatorx.logging_config import configure_logging

logger = logging.getLogger(__name__)

JobStatus = Literal["queued", "running", "completed", "failed"]

_manager: Optional["JobManager"] = None
_lock = threading.Lock()


@dataclass
class JobProgress:
    phase: str = "queued"
    current: int = 0
    total: int = 1
    message: str = ""

    def to_dict(self) -> Dict[str, object]:
        percent = int((self.current / self.total) * 100) if self.total > 0 else 0
        return {
            "phase": self.phase,
            "current": self.current,
            "total": self.total,
            "percent": min(percent, 100),
            "message": self.message,
        }


@dataclass
class Job:
    id: str
    job_type: str
    status: JobStatus
    created_at: float
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    summary: Dict[str, object] = field(default_factory=dict)
    progress: JobProgress = field(default_factory=JobProgress)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["progress"] = self.progress.to_dict()
        return payload


def _resolve_db_path(data_dir: Path) -> Path:
    """Prefer curatorx.db; adopt legacy mediacurator.db once if present."""
    new_path = data_dir / "curatorx.db"
    legacy_path = data_dir / "mediacurator.db"
    if not new_path.exists() and legacy_path.exists():
        legacy_path.rename(new_path)
    return new_path


class JobManager:
    def __init__(self, data_dir: Path) -> None:
        configure_logging()
        self.data_dir = data_dir
        self.db = Database(_resolve_db_path(data_dir))
        ensure_library_facet_index(self.db)
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        logger.info("JobManager initialized data_dir=%s", data_dir)

    def list_jobs(self) -> List[Job]:
        with self._lock:
            return sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)

    def get_job(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def start_sync(self, settings: Settings) -> Job:
        job_id = uuid.uuid4().hex[:12]
        job = Job(id=job_id, job_type="library_sync", status="queued", created_at=time.time())
        with self._lock:
            self._jobs[job_id] = job
        logger.info("Library sync job queued job_id=%s", job_id)
        thread = threading.Thread(target=self._run_sync, args=(job_id, settings), daemon=True)
        thread.start()
        return job

    def _update_progress(self, job_id: str, phase: str, current: int, total: int, message: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.progress = JobProgress(phase=phase, current=current, total=total, message=message)
        logger.debug(
            "Sync progress job_id=%s phase=%s %s/%s %s",
            job_id,
            phase,
            current,
            total,
            message,
        )

    def _run_sync(self, job_id: str, settings: Settings) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "running"
            job.started_at = time.time()

        logger.info("Library sync started job_id=%s", job_id)

        def progress(phase: str, current: int, total: int, message: str) -> None:
            self._update_progress(job_id, phase, current, total, message)

        try:
            result = asyncio.run(sync_library(self.db, settings, progress=progress))
            refresh_library_overview_cache(self.db)
            elapsed = time.time() - (job.started_at or time.time())
            with self._lock:
                job.status = "completed"
                job.finished_at = time.time()
                job.summary = result
                job.progress = JobProgress(phase="completed", current=1, total=1, message="Done")
            logger.info(
                "Library sync completed job_id=%s elapsed=%.1fs items=%s embeddings=%s",
                job_id,
                elapsed,
                result.get("items_synced"),
                result.get("embeddings"),
            )
        except Exception as error:  # noqa: BLE001
            logger.exception("Library sync failed job_id=%s: %s", job_id, error)
            with self._lock:
                job.status = "failed"
                job.finished_at = time.time()
                job.error = str(error)
                job.summary = {"traceback": traceback.format_exc()}


class SyncScheduler:
    """Background scheduler for periodic library re-sync."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, daemon=True, name="library-sync-scheduler")
        self._thread.start()
        logger.info("Library sync scheduler started")

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                settings = load_merged_settings(self.data_dir)
                if settings.plex_url and settings.plex_token:
                    interval_hours = max(1, int(settings.library_sync_interval_hours))
                    last_raw = get_job_manager().db.get_sync_state("last_sync")
                    should_run = last_raw is None
                    if last_raw:
                        try:
                            last_data = json.loads(last_raw)
                            last_ts = float(last_data.get("timestamp") or 0)
                            should_run = (time.time() - last_ts) >= interval_hours * 3600
                        except (json.JSONDecodeError, TypeError, ValueError):
                            should_run = True
                    running = any(j.status in ("queued", "running") for j in get_job_manager().list_jobs())
                    if should_run and not running:
                        logger.info(
                            "Scheduler triggering library sync interval_hours=%s",
                            interval_hours,
                        )
                        get_job_manager().start_sync(settings)
            except Exception as error:  # noqa: BLE001
                logger.exception("Sync scheduler loop error: %s", error)
            self._stop.wait(timeout=3600)


_scheduler: Optional[SyncScheduler] = None


def get_sync_scheduler() -> SyncScheduler:
    global _scheduler
    with _lock:
        if _scheduler is None:
            data_dir = Path(os.environ.get("DATA_DIR", "/config"))
            _scheduler = SyncScheduler(data_dir)
        return _scheduler


def get_job_manager() -> JobManager:
    global _manager
    with _lock:
        if _manager is None:
            data_dir = Path(os.environ.get("DATA_DIR", "/config"))
            _manager = JobManager(data_dir)
        return _manager
