"""Library sync from Plex with TMDB enrichment."""

from __future__ import annotations

import json
import logging
import time
from typing import Callable, List, Optional

from curatorx.config_store import Settings
from curatorx.connectors.fanart import FanartClient
from curatorx.connectors.plex import PlexClient
from curatorx.connectors.radarr import RadarrClient
from curatorx.connectors.sonarr import SonarrClient
from curatorx.connectors.tmdb import TMDBClient
from curatorx.library.db import Database
from curatorx.library.embeddings import rebuild_embeddings
from curatorx.library.episodes import sync_tv_episodes
from curatorx.library.facets import rebuild_library_facets, rebuild_library_fts
from curatorx.library.query import refresh_library_overview_cache
from curatorx.reviews.store import scan_for_rating_prompts

logger = logging.getLogger(__name__)

ProgressCallback = Optional[Callable[[str, int, int, str], None]]


def _runtime_minutes_from_ms(duration_ms: Optional[int]) -> Optional[int]:
    if not duration_ms:
        return None
    return int(duration_ms / 60000)


def _countries_from_tmdb(details: dict) -> List[str]:
    countries = [
        str(c.get("name") or "").strip()
        for c in (details.get("production_countries") or [])
        if c.get("name")
    ]
    if countries:
        return countries
    return [
        str(code or "").strip()
        for code in (details.get("origin_country") or [])
        if str(code or "").strip()
    ]


def _apply_tmdb_enrichment(
    row: dict,
    details: dict,
    *,
    media_type: str,
    tmdb_client: Optional[TMDBClient] = None,
) -> None:
    if not details:
        return
    if not row.get("poster_url") and details.get("poster_path") and tmdb_client:
        row["poster_url"] = tmdb_client.poster_url(details.get("poster_path"))
    if not row.get("backdrop_url") and details.get("backdrop_path") and tmdb_client:
        row["backdrop_url"] = tmdb_client.backdrop_url(details.get("backdrop_path"))

    vote = details.get("vote_average")
    if vote is not None:
        row["vote_average"] = float(vote)

    language = str(details.get("original_language") or "").strip()
    if language:
        row["original_language"] = language

    countries = _countries_from_tmdb(details)
    if countries:
        row["countries"] = countries

    keywords_payload = details.get("keywords") or {}
    keyword_list = keywords_payload.get("keywords") or keywords_payload.get("results") or []
    keywords = [k.get("name", "") for k in keyword_list if k.get("name")]
    if keywords:
        row["keywords"] = keywords

    credits = details.get("credits") or {}
    if not row.get("cast"):
        row["cast"] = [c.get("name", "") for c in credits.get("cast", [])[:8] if c.get("name")]
    if not row.get("directors"):
        if media_type == "movie":
            row["directors"] = [
                c.get("name", "") for c in credits.get("crew", []) if c.get("job") == "Director"
            ]
        else:
            row["directors"] = [
                c.get("name", "") for c in credits.get("crew", []) if c.get("job") in {"Director", "Creator"}
            ]

    if media_type == "movie":
        runtime = details.get("runtime")
        if runtime:
            row["runtime_minutes"] = int(runtime)
    else:
        runtimes = details.get("episode_run_time") or []
        if runtimes:
            row["runtime_minutes"] = int(runtimes[0])


def _row_from_plex_item(
    item,
    plex: PlexClient,
    tmdb: Optional[TMDBClient],
    fanart: Optional[FanartClient],
    *,
    in_radarr: bool,
    in_sonarr: bool,
) -> dict:
    poster = plex.thumb_url(item.thumb)
    backdrop = plex.thumb_url(item.art)
    keywords: list[str] = []
    tmdb_id = int(item.tmdb_id) if item.tmdb_id else None
    tvdb_id = int(item.tvdb_id) if item.tvdb_id else None
    runtime_minutes = _runtime_minutes_from_ms(item.duration_ms)
    countries: list[str] = []
    vote_average = None
    original_language = ""

    item_cast = item.cast
    item_directors = item.directors

    if tmdb and tmdb_id:
        try:
            if item.media_type == "movie":
                details = tmdb.movie_details(tmdb_id)
            else:
                details = tmdb.tv_details(tmdb_id)
            if details.get("poster_path"):
                poster = tmdb.poster_url(details["poster_path"])
            if details.get("backdrop_path"):
                backdrop = tmdb.backdrop_url(details["backdrop_path"])
            keywords = [
                k.get("name", "")
                for k in (details.get("keywords") or {}).get("keywords", [])
                if k.get("name")
            ]
            vote_average = float(details.get("vote_average") or 0) or None
            original_language = str(details.get("original_language") or "")
            countries = _countries_from_tmdb(details)
            if item.media_type == "movie" and details.get("runtime"):
                runtime_minutes = int(details["runtime"])
            elif item.media_type == "show":
                runtimes = details.get("episode_run_time") or []
                if runtimes:
                    runtime_minutes = int(runtimes[0])
            row_stub = {
                "cast": item.cast,
                "directors": item.directors,
                "keywords": keywords,
                "poster_url": poster,
                "backdrop_url": backdrop,
                "vote_average": vote_average,
                "original_language": original_language,
                "countries": countries,
                "runtime_minutes": runtime_minutes,
            }
            _apply_tmdb_enrichment(row_stub, details, media_type=item.media_type, tmdb_client=tmdb)
            keywords = row_stub.get("keywords") or keywords
            poster = row_stub.get("poster_url") or poster
            backdrop = row_stub.get("backdrop_url") or backdrop
            vote_average = row_stub.get("vote_average", vote_average)
            original_language = row_stub.get("original_language", original_language)
            countries = row_stub.get("countries") or countries
            runtime_minutes = row_stub.get("runtime_minutes", runtime_minutes)
            item_cast = row_stub.get("cast") or item.cast
            item_directors = row_stub.get("directors") or item.directors
        except RuntimeError as error:
            logger.debug(
                "TMDB enrichment skipped %s tmdb_id=%s: %s",
                item.media_type,
                tmdb_id,
                error,
            )

    if fanart and tmdb_id and item.media_type == "movie":
        try:
            art = fanart.movie(tmdb_id)
            if not poster:
                poster = fanart.best_poster(art)
            if not backdrop:
                backdrop = fanart.best_backdrop(art)
        except RuntimeError as error:
            logger.debug("Fanart movie enrichment skipped tmdb_id=%s: %s", tmdb_id, error)
    elif fanart and tvdb_id and item.media_type == "show":
        try:
            art = fanart.tv(tvdb_id)
            if not poster:
                poster = fanart.best_poster(art)
            if not backdrop:
                backdrop = fanart.best_backdrop(art)
        except RuntimeError as error:
            logger.debug("Fanart TV enrichment skipped tvdb_id=%s: %s", tvdb_id, error)

    return {
        "rating_key": item.rating_key,
        "media_type": item.media_type,
        "title": item.title,
        "year": item.year,
        "summary": item.summary,
        "genres": item.genres,
        "cast": item_cast,
        "directors": item_directors,
        "keywords": keywords,
        "tmdb_id": tmdb_id,
        "tvdb_id": tvdb_id,
        "imdb_id": item.imdb_id,
        "poster_url": poster,
        "backdrop_url": backdrop,
        "view_count": item.view_count,
        "added_at": item.added_at,
        "last_viewed_at": item.last_viewed_at,
        "file_size": item.file_size,
        "in_radarr": in_radarr,
        "in_sonarr": in_sonarr,
        "runtime_minutes": runtime_minutes,
        "content_rating": item.content_rating,
        "vote_average": vote_average,
        "original_language": original_language,
        "countries": countries,
        "season_count": item.season_count,
        "leaf_count": item.leaf_count,
        "viewed_leaf_count": item.viewed_leaf_count,
        "view_offset_ms": item.view_offset_ms,
        "duration_ms": item.duration_ms,
        "plex_user_rating_stars": item.user_rating_stars,
    }


async def sync_library(
    db: Database,
    settings: Settings,
    *,
    progress: ProgressCallback = None,
) -> dict:
    if not settings.plex_url or not settings.plex_token:
        raise RuntimeError("Plex is not configured")

    logger.info("Library sync starting")

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
        logger.debug("Fetching Radarr movie index")
        radarr_tmdb = {m.tmdb_id for m in RadarrClient(settings.radarr_url, settings.radarr_api_key).movies()}
        logger.debug("Radarr index loaded count=%s", len(radarr_tmdb))
    if settings.sonarr_url and settings.sonarr_api_key:
        logger.debug("Fetching Sonarr series index")
        sonarr_tvdb = {s.tvdb_id for s in SonarrClient(settings.sonarr_url, settings.sonarr_api_key).series_list()}
        logger.debug("Sonarr index loaded count=%s", len(sonarr_tvdb))

    if progress:
        progress("movies", 0, 1, "Fetching Plex movies")
    movies = plex.movie_items()
    logger.info("Plex movies fetched count=%s", len(movies))
    if progress:
        progress("movies", 1, 1, f"Indexed {len(movies)} movies")

    def tv_progress(current: int, total: int, message: str) -> None:
        if progress:
            progress("tv", current, total, message)

    if progress:
        progress("tv", 0, 1, "Fetching Plex TV shows")
    shows = plex.show_items(page_size=settings.tv_page_size, progress_callback=tv_progress)
    logger.info("Plex TV shows fetched count=%s", len(shows))

    count = 0
    skipped_no_rating_key = 0
    for item in movies + shows:
        rating_key = str(item.rating_key or "").strip()
        if not rating_key:
            skipped_no_rating_key += 1
            logger.debug(
                "Skipping Plex item without rating_key title=%r media_type=%s",
                item.title,
                item.media_type,
            )
            continue
        in_radarr = bool(item.tmdb_id and int(item.tmdb_id) in radarr_tmdb)
        in_sonarr = bool(item.tvdb_id and int(item.tvdb_id) in sonarr_tvdb)
        row = _row_from_plex_item(item, plex, tmdb, fanart, in_radarr=in_radarr, in_sonarr=in_sonarr)
        row["rating_key"] = rating_key
        db.upsert_library_item(row)
        count += 1

    logger.info("Library items upserted count=%s", count)
    with db.connect() as conn:
        items_with_tmdb = conn.execute(
            "SELECT COUNT(*) AS cnt FROM library_items WHERE tmdb_id IS NOT NULL"
        ).fetchone()["cnt"]
        items_with_countries = conn.execute(
            """
            SELECT COUNT(*) AS cnt FROM library_items
            WHERE countries IS NOT NULL AND countries != '' AND countries != '[]'
            """
        ).fetchone()["cnt"]
        items_with_language = conn.execute(
            """
            SELECT COUNT(*) AS cnt FROM library_items
            WHERE original_language IS NOT NULL AND original_language != ''
            """
        ).fetchone()["cnt"]
    logger.info(
        "Library metadata coverage after sync: tmdb_id=%s countries=%s original_language=%s (of %s items)",
        items_with_tmdb,
        items_with_countries,
        items_with_language,
        count,
    )
    if count and items_with_tmdb == 0:
        logger.warning(
            "No library items have tmdb_id — country/language enrichment requires Plex includeGuids "
            "and a TMDB API key; verify Plex metadata is matched (not local:// only)."
        )
    elif count and items_with_countries == 0 and tmdb is not None:
        logger.warning(
            "No library items have countries after sync despite TMDB client — check TMDB API key and enrichment errors."
        )
    if skipped_no_rating_key:
        logger.warning(
            "Skipped %s Plex items without rating_key during library sync",
            skipped_no_rating_key,
        )

    if progress:
        progress("facets", 0, 1, "Building facet index")
    facet_count = rebuild_library_facets(db)
    logger.debug("Facet index rebuilt count=%s", facet_count)

    if progress:
        progress("fts", 0, 1, "Building full-text index")
    fts_count = rebuild_library_fts(db)
    logger.debug("FTS index rebuilt count=%s", fts_count)

    if progress:
        progress("episodes", 0, 1, "Syncing TV episodes")
    episode_stats = sync_tv_episodes(db, plex, progress=progress, plex_shows=shows)
    logger.info(
        "TV episodes synced shows=%s episodes=%s",
        episode_stats.get("shows_synced"),
        episode_stats.get("episodes_synced"),
    )

    if progress:
        progress("embeddings", 0, 1, "Building embeddings")
    embedded = await rebuild_embeddings(db, settings)
    logger.info("Embeddings rebuilt count=%s", embedded)
    refresh_library_overview_cache(db)
    rating_prompts = scan_for_rating_prompts(db, settings)
    logger.info("Rating prompts queued count=%s", rating_prompts)
    db.set_sync_state(
        "last_sync",
        json.dumps(
            {
                "items": count,
                "embeddings": embedded,
                "facets": facet_count,
                "fts": fts_count,
                "episodes": episode_stats,
                "rating_prompts": rating_prompts,
                "timestamp": time.time(),
            }
        ),
    )

    return {
        "items_synced": count,
        "embeddings": embedded,
        "facets": facet_count,
        "fts": fts_count,
        "episodes": episode_stats,
        "rating_prompts": rating_prompts,
    }
