"""Library sync from Plex with TMDB enrichment."""

from __future__ import annotations

import json
import time
from typing import Callable, Optional

from curatorx.config_store import Settings
from curatorx.connectors.fanart import FanartClient
from curatorx.connectors.plex import PlexClient
from curatorx.connectors.radarr import RadarrClient
from curatorx.connectors.sonarr import SonarrClient
from curatorx.connectors.tmdb import TMDBClient
from curatorx.library.db import Database
from curatorx.library.embeddings import rebuild_embeddings


ProgressCallback = Optional[Callable[[str, int, int, str], None]]


def _row_from_plex_item(item, plex: PlexClient, tmdb: Optional[TMDBClient], fanart: Optional[FanartClient], *, in_radarr: bool, in_sonarr: bool) -> dict:
    poster = plex.thumb_url(item.thumb)
    backdrop = plex.thumb_url(item.art)
    keywords: list[str] = []
    tmdb_id = int(item.tmdb_id) if item.tmdb_id else None
    tvdb_id = int(item.tvdb_id) if item.tvdb_id else None

    if tmdb and tmdb_id and item.media_type == "movie":
        try:
            details = tmdb.movie_details(tmdb_id)
            if not poster and details.get("poster_path"):
                poster = tmdb.poster_url(details["poster_path"])
            if not backdrop and details.get("backdrop_path"):
                backdrop = tmdb.backdrop_url(details["backdrop_path"])
            keywords = [k.get("name", "") for k in (details.get("keywords") or {}).get("keywords", []) if k.get("name")]
        except RuntimeError:
            pass
    elif tmdb and tmdb_id and item.media_type == "show":
        try:
            details = tmdb.tv_details(tmdb_id)
            if not poster and details.get("poster_path"):
                poster = tmdb.poster_url(details["poster_path"])
            if not backdrop and details.get("backdrop_path"):
                backdrop = tmdb.backdrop_url(details["backdrop_path"])
        except RuntimeError:
            pass

    if fanart and tmdb_id and item.media_type == "movie":
        try:
            art = fanart.movie(tmdb_id)
            if not poster:
                poster = fanart.best_poster(art)
            if not backdrop:
                backdrop = fanart.best_backdrop(art)
        except RuntimeError:
            pass
    elif fanart and tvdb_id and item.media_type == "show":
        try:
            art = fanart.tv(tvdb_id)
            if not poster:
                poster = fanart.best_poster(art)
            if not backdrop:
                backdrop = fanart.best_backdrop(art)
        except RuntimeError:
            pass

    return {
        "rating_key": item.rating_key,
        "media_type": item.media_type,
        "title": item.title,
        "year": item.year,
        "summary": item.summary,
        "genres": item.genres,
        "cast": item.cast,
        "directors": item.directors,
        "keywords": keywords,
        "tmdb_id": tmdb_id,
        "tvdb_id": tvdb_id,
        "imdb_id": item.imdb_id,
        "poster_url": poster,
        "backdrop_url": backdrop,
        "view_count": item.view_count,
        "last_viewed_at": item.last_viewed_at,
        "file_size": item.file_size,
        "in_radarr": in_radarr,
        "in_sonarr": in_sonarr,
    }


async def sync_library(
    db: Database,
    settings: Settings,
    *,
    progress: ProgressCallback = None,
) -> dict:
    if not settings.plex_url or not settings.plex_token:
        raise RuntimeError("Plex is not configured")

    plex = PlexClient(
        settings.plex_url,
        settings.plex_token,
        movie_section=settings.plex_movie_section or None,
        tv_section=settings.plex_tv_section or None,
    )
    tmdb = TMDBClient(settings.tmdb_api_key) if settings.tmdb_api_key else None
    fanart = FanartClient(settings.fanart_api_key) if settings.fanart_api_key else None

    radarr_tmdb: set[int] = set()
    sonarr_tvdb: set[int] = set()
    if settings.radarr_url and settings.radarr_api_key:
        radarr_tmdb = {m.tmdb_id for m in RadarrClient(settings.radarr_url, settings.radarr_api_key).movies()}
    if settings.sonarr_url and settings.sonarr_api_key:
        sonarr_tvdb = {s.tvdb_id for s in SonarrClient(settings.sonarr_url, settings.sonarr_api_key).series_list()}

    if progress:
        progress("movies", 0, 1, "Fetching Plex movies")
    movies = plex.movie_items()
    if progress:
        progress("movies", 1, 1, f"Indexed {len(movies)} movies")

    def tv_progress(current: int, total: int, message: str) -> None:
        if progress:
            progress("tv", current, total, message)

    if progress:
        progress("tv", 0, 1, "Fetching Plex TV shows")
    shows = plex.show_items(page_size=settings.tv_page_size, progress_callback=tv_progress)

    count = 0
    for item in movies + shows:
        in_radarr = bool(item.tmdb_id and int(item.tmdb_id) in radarr_tmdb)
        in_sonarr = bool(item.tvdb_id and int(item.tvdb_id) in sonarr_tvdb)
        row = _row_from_plex_item(item, plex, tmdb, fanart, in_radarr=in_radarr, in_sonarr=in_sonarr)
        db.upsert_library_item(row)
        count += 1

    if progress:
        progress("embeddings", 0, 1, "Building embeddings")
    embedded = await rebuild_embeddings(db, settings)
    db.set_sync_state("last_sync", json.dumps({"items": count, "embeddings": embedded, "timestamp": time.time()}))

    return {"items_synced": count, "embeddings": embedded}
