"""TV episode sync and query helpers."""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from curatorx.connectors.plex import PlexClient, PlexEpisode, PlexLibraryItem, PlexSeason
from curatorx.library.db import Database

logger = logging.getLogger(__name__)

ProgressCallback = Optional[Callable[[str, int, int, str], None]]


def _normalize_show_title(title: str) -> str:
    normalized = str(title or "").strip().lower()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _show_rating_key(show: Mapping[str, Any]) -> str:
    value = show["rating_key"] if "rating_key" in show.keys() else None
    return str(value or "").strip()


def _show_field(show: Mapping[str, Any], key: str, default: Any = None) -> Any:
    if key in show.keys():
        return show[key]
    return default


def _build_plex_show_lookups(
    plex_shows: Sequence[PlexLibraryItem],
) -> Tuple[
    Dict[str, PlexLibraryItem],
    Dict[str, PlexLibraryItem],
    Dict[Tuple[str, Optional[int]], PlexLibraryItem],
]:
    by_tmdb: Dict[str, PlexLibraryItem] = {}
    by_tvdb: Dict[str, PlexLibraryItem] = {}
    by_title_year: Dict[Tuple[str, Optional[int]], PlexLibraryItem] = {}

    for item in plex_shows:
        rating_key = str(item.rating_key or "").strip()
        if not rating_key:
            continue

        tmdb_id = str(item.tmdb_id or "").strip()
        if tmdb_id and tmdb_id not in by_tmdb:
            by_tmdb[tmdb_id] = item

        tvdb_id = str(item.tvdb_id or "").strip()
        if tvdb_id and tvdb_id not in by_tvdb:
            by_tvdb[tvdb_id] = item

        title_key = (_normalize_show_title(item.title), item.year)
        if title_key not in by_title_year:
            by_title_year[title_key] = item

    return by_tmdb, by_tvdb, by_title_year


def _match_plex_show(
    show: Mapping[str, Any],
    *,
    by_tmdb: Mapping[str, PlexLibraryItem],
    by_tvdb: Mapping[str, PlexLibraryItem],
    by_title_year: Mapping[Tuple[str, Optional[int]], PlexLibraryItem],
) -> Optional[PlexLibraryItem]:
    existing_key = _show_rating_key(show)
    if existing_key:
        return None

    tmdb_id = _show_field(show, "tmdb_id")
    if tmdb_id is not None:
        match = by_tmdb.get(str(tmdb_id).strip())
        if match:
            return match

    tvdb_id = _show_field(show, "tvdb_id")
    if tvdb_id is not None:
        match = by_tvdb.get(str(tvdb_id).strip())
        if match:
            return match

    title = _normalize_show_title(str(_show_field(show, "title") or ""))
    if not title:
        return None

    year = _show_field(show, "year")
    year_value = int(year) if year is not None else None
    match = by_title_year.get((title, year_value))
    if match:
        return match

    if year_value is None:
        for (candidate_title, _), candidate in by_title_year.items():
            if candidate_title == title:
                return candidate

    return None


def backfill_show_rating_keys(
    db: Database,
    plex: PlexClient,
    *,
    plex_shows: Optional[Sequence[PlexLibraryItem]] = None,
) -> Dict[str, int]:
    shows = db.library_shows()
    missing = [show for show in shows if not _show_rating_key(show)]
    if not missing:
        return {"backfilled": 0, "unmatchable": 0, "conflicts": 0}

    catalog = list(plex_shows) if plex_shows is not None else plex.show_items()
    by_tmdb, by_tvdb, by_title_year = _build_plex_show_lookups(catalog)

    backfilled = 0
    unmatchable = 0
    conflicts = 0

    for show in missing:
        show_id = int(show["id"])
        match = _match_plex_show(
            show,
            by_tmdb=by_tmdb,
            by_tvdb=by_tvdb,
            by_title_year=by_title_year,
        )
        if match is None:
            unmatchable += 1
            logger.debug(
                "No Plex match for show without rating_key show_id=%s title=%r year=%s tmdb_id=%s",
                show_id,
                show["title"],
                _show_field(show, "year"),
                _show_field(show, "tmdb_id"),
            )
            continue

        rating_key = str(match.rating_key or "").strip()
        if not rating_key:
            unmatchable += 1
            continue

        if db.update_library_item_rating_key(show_id, rating_key):
            backfilled += 1
            logger.debug(
                "Backfilled Plex rating_key show_id=%s title=%r rating_key=%s",
                show_id,
                show["title"],
                rating_key,
            )
        else:
            conflicts += 1
            logger.debug(
                "Could not backfill rating_key due to conflict show_id=%s title=%r rating_key=%s",
                show_id,
                show["title"],
                rating_key,
            )

    if backfilled:
        logger.info("Backfilled Plex rating_key for %s shows before episode sync", backfilled)
    if unmatchable:
        logger.info(
            "Could not match %s shows to Plex during rating_key backfill",
            unmatchable,
        )
    if conflicts:
        logger.info(
            "Skipped rating_key backfill for %s shows due to existing rating_key conflicts",
            conflicts,
        )

    return {"backfilled": backfilled, "unmatchable": unmatchable, "conflicts": conflicts}


def _log_episode_sync_sample(shows: Sequence[Mapping[str, Any]]) -> None:
    sample = []
    for show in shows[:3]:
        rating_key = _show_rating_key(show)
        sample.append(
            {
                "show_id": int(show["id"]),
                "title": str(show["title"]),
                "rating_key": rating_key or None,
                "has_rating_key": bool(rating_key),
                "tmdb_id": _show_field(show, "tmdb_id"),
                "tvdb_id": _show_field(show, "tvdb_id"),
            }
        )
    with_key = sum(1 for show in shows if _show_rating_key(show))
    logger.info(
        "Episode sync sample (first %s shows)=%s with_rating_key=%s without_rating_key=%s",
        len(sample),
        sample,
        with_key,
        len(shows) - with_key,
    )


def _upsert_episodes_for_show(
    db: Database,
    show_id: int,
    episodes: Sequence[PlexEpisode],
    *,
    default_season_number: Optional[int] = None,
) -> int:
    synced = 0
    for episode in episodes:
        episode_key = str(episode.rating_key or "").strip()
        if not episode_key:
            continue
        db.upsert_library_episode(
            {
                "show_item_id": show_id,
                "rating_key": episode_key,
                "season_number": episode.season_number if episode.season_number is not None else default_season_number,
                "episode_number": episode.episode_number,
                "title": episode.title,
                "runtime_minutes": episode.runtime_minutes,
                "view_count": episode.view_count,
                "last_viewed_at": episode.last_viewed_at,
                "file_size": episode.file_size,
                "aired_at": episode.aired_at,
                "view_offset_ms": episode.view_offset_ms,
                "duration_ms": episode.duration_ms,
                "plex_user_rating_stars": episode.user_rating_stars,
            }
        )
        synced += 1
    return synced


def sync_tv_episodes(
    db: Database,
    plex: PlexClient,
    *,
    progress: ProgressCallback = None,
    plex_shows: Optional[Sequence[PlexLibraryItem]] = None,
) -> Dict[str, int]:
    backfill_stats = backfill_show_rating_keys(db, plex, plex_shows=plex_shows)
    shows = db.library_shows()
    total = len(shows)
    episodes_synced = 0
    shows_synced = 0
    unmatchable_shows = int(backfill_stats["unmatchable"]) + int(backfill_stats["conflicts"])
    skipped_empty_seasons = 0
    failed_show_fetches = 0
    failed_season_fetches = 0
    all_leaves_fallbacks = 0
    logger.info("Episode sync starting show_count=%s", total)
    _log_episode_sync_sample(shows)

    for index, show in enumerate(shows, start=1):
        show_id = int(show["id"])
        rating_key = _show_rating_key(show)
        if not rating_key:
            logger.debug(
                "Skipping episode sync for unmatchable show show_id=%s title=%r",
                show_id,
                show["title"],
            )
            continue
        if progress:
            progress("episodes", index, max(total, 1), f"Syncing {show['title']}")

        db.delete_episodes_for_show(show_id)
        episodes_synced_for_show = 0
        seasons: List[PlexSeason] = []
        seasons_fetch_error: Optional[str] = None
        try:
            seasons = plex.show_seasons(rating_key)
        except (RuntimeError, ValueError) as error:
            seasons_fetch_error = str(error)
            logger.debug(
                "Failed to fetch seasons show_id=%s title=%r rating_key=%s: %s",
                show_id,
                show["title"],
                rating_key,
                error,
            )

        for season in seasons:
            season_key = str(season.rating_key or "").strip()
            if not season_key:
                skipped_empty_seasons += 1
                logger.debug(
                    "Skipping season without Plex rating_key show_id=%s season=%s title=%r",
                    show_id,
                    season.season_number,
                    season.title,
                )
                continue
            try:
                episodes = plex.season_episodes(season_key)
            except (RuntimeError, ValueError) as error:
                failed_season_fetches += 1
                logger.debug(
                    "Failed to fetch episodes show_id=%s season=%s rating_key=%s: %s",
                    show_id,
                    season.season_number,
                    season_key,
                    error,
                )
                continue
            episodes_synced_for_show += _upsert_episodes_for_show(
                db,
                show_id,
                episodes,
                default_season_number=season.season_number,
            )

        if episodes_synced_for_show == 0:
            try:
                fallback_episodes = plex.show_all_episodes(rating_key)
            except (RuntimeError, ValueError) as error:
                failed_show_fetches += 1
                logger.debug(
                    "Failed to fetch episodes for show show_id=%s title=%r rating_key=%s "
                    "seasons_error=%s allLeaves_error=%s",
                    show_id,
                    show["title"],
                    rating_key,
                    seasons_fetch_error,
                    error,
                )
            else:
                if fallback_episodes:
                    all_leaves_fallbacks += 1
                    episodes_synced_for_show = _upsert_episodes_for_show(
                        db,
                        show_id,
                        fallback_episodes,
                    )
                    logger.info(
                        "Synced %s episodes via Plex allLeaves for show_id=%s title=%r "
                        "rating_key=%s (seasons=%s; hidden/flattened season libraries use allLeaves)",
                        episodes_synced_for_show,
                        show_id,
                        show["title"],
                        rating_key,
                        len(seasons),
                    )
                elif seasons_fetch_error:
                    failed_show_fetches += 1
                elif not seasons:
                    logger.info(
                        "No Plex seasons or episodes for show_id=%s title=%r rating_key=%s "
                        "leaf_count=%s (empty show or check Plex flattenSeasons setting)",
                        show_id,
                        show["title"],
                        rating_key,
                        _show_field(show, "leaf_count"),
                    )

        episodes_synced += episodes_synced_for_show
        db.update_show_episode_rollups(show_id)
        shows_synced += 1

    if unmatchable_shows:
        logger.info(
            "Skipped episode sync for %s unmatchable shows without Plex rating_key",
            unmatchable_shows,
        )
    if skipped_empty_seasons:
        logger.info(
            "Skipped %s seasons without Plex rating_key during episode sync",
            skipped_empty_seasons,
        )
    if failed_show_fetches:
        logger.warning(
            "Failed to fetch seasons for %s shows during episode sync",
            failed_show_fetches,
        )
    if failed_season_fetches:
        logger.warning(
            "Failed to fetch episodes for %s seasons during episode sync",
            failed_season_fetches,
        )
    if all_leaves_fallbacks:
        logger.info(
            "Used Plex allLeaves fallback for %s shows (flattened/hidden seasons)",
            all_leaves_fallbacks,
        )

    return {
        "shows_synced": shows_synced,
        "episodes_synced": episodes_synced,
        "backfilled_rating_key": int(backfill_stats["backfilled"]),
        "unmatchable_shows": unmatchable_shows,
        "skipped_no_rating_key": unmatchable_shows,
        "skipped_empty_seasons": skipped_empty_seasons,
        "failed_show_fetches": failed_show_fetches,
        "failed_season_fetches": failed_season_fetches,
        "all_leaves_fallbacks": all_leaves_fallbacks,
    }


def _resolve_show(db: Database, show: Optional[str] = None, show_id: Optional[int] = None):
    if show_id is not None:
        return db.library_item_by_id(int(show_id))
    if show:
        return db.library_item_by_title(str(show), media_type="show")
    return None


def query_episodes(
    db: Database,
    *,
    show: Optional[str] = None,
    show_id: Optional[int] = None,
    season: Optional[int] = None,
    unwatched_only: bool = False,
    offset: int = 0,
    limit: int = 25,
) -> Dict[str, Any]:
    show_row = _resolve_show(db, show=show, show_id=show_id)
    if show_row is None:
        return {"error": "Show not found", "total_matched": 0, "returned": 0, "items": []}

    clauses = ["show_item_id = ?"]
    params: List[Any] = [int(show_row["id"])]
    if season is not None:
        clauses.append("season_number = ?")
        params.append(int(season))
    if unwatched_only:
        clauses.append("(view_count IS NULL OR view_count = 0)")

    where_sql = " AND ".join(clauses)
    capped_limit = min(max(1, limit), 50)
    capped_offset = max(0, offset)

    with db.connect() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS cnt FROM library_episodes WHERE {where_sql}",
            params,
        ).fetchone()["cnt"]
        rows = conn.execute(
            f"""
            SELECT * FROM library_episodes
            WHERE {where_sql}
            ORDER BY season_number ASC, episode_number ASC
            LIMIT ? OFFSET ?
            """,
            [*params, capped_limit, capped_offset],
        ).fetchall()

    items = [
        {
            "show_title": str(show_row["title"]),
            "season_number": int(r["season_number"]) if r["season_number"] is not None else None,
            "episode_number": int(r["episode_number"]) if r["episode_number"] is not None else None,
            "title": str(r["title"] or ""),
            "runtime_minutes": int(r["runtime_minutes"]) if r["runtime_minutes"] is not None else None,
            "view_count": int(r["view_count"] or 0),
            "unwatched": int(r["view_count"] or 0) == 0,
        }
        for r in rows
    ]
    returned = len(items)
    total_matched = int(total)
    return {
        "show_title": str(show_row["title"]),
        "total_matched": total_matched,
        "returned": returned,
        "offset": capped_offset,
        "has_more": capped_offset + returned < total_matched,
        "items": items,
    }


def summarize_tv_progress(
    db: Database,
    *,
    group_by: str = "show",
    in_progress_only: bool = False,
    limit: int = 25,
) -> Dict[str, Any]:
    normalized = group_by.strip().lower()
    if normalized not in {"show", "season"}:
        raise ValueError("group_by must be show or season")

    capped = min(max(1, limit), 50)
    if normalized == "show":
        with db.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, title, total_episode_count, unwatched_episode_count,
                       viewed_leaf_count, leaf_count
                FROM library_items
                WHERE media_type = 'show' AND total_episode_count > 0
                ORDER BY title ASC
                """
            ).fetchall()

        buckets: List[Dict[str, Any]] = []
        for row in rows:
            total_eps = int(row["total_episode_count"] or 0)
            unwatched = int(row["unwatched_episode_count"] or 0)
            watched = max(0, total_eps - unwatched)
            completion = round((watched / total_eps) * 100, 1) if total_eps else 0.0
            if in_progress_only and (completion <= 0 or completion >= 100):
                continue
            buckets.append(
                {
                    "show_title": str(row["title"]),
                    "total_episodes": total_eps,
                    "watched_episodes": watched,
                    "unwatched_episodes": unwatched,
                    "completion_percent": completion,
                }
            )
        buckets.sort(key=lambda item: (-item["completion_percent"], item["show_title"]))
        buckets = buckets[:capped]
        return {"group_by": "show", "buckets": buckets, "returned": len(buckets)}

    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT li.title AS show_title, le.season_number,
                   COUNT(*) AS total,
                   SUM(CASE WHEN le.view_count IS NULL OR le.view_count = 0 THEN 1 ELSE 0 END) AS unwatched
            FROM library_episodes le
            JOIN library_items li ON li.id = le.show_item_id
            GROUP BY le.show_item_id, le.season_number
            ORDER BY li.title ASC, le.season_number ASC
            LIMIT ?
            """,
            (capped,),
        ).fetchall()

    buckets = []
    for row in rows:
        total_eps = int(row["total"])
        unwatched = int(row["unwatched"])
        watched = max(0, total_eps - unwatched)
        completion = round((watched / total_eps) * 100, 1) if total_eps else 0.0
        if in_progress_only and (completion <= 0 or completion >= 100):
            continue
        buckets.append(
            {
                "show_title": str(row["show_title"]),
                "season_number": int(row["season_number"]) if row["season_number"] is not None else None,
                "total_episodes": total_eps,
                "watched_episodes": watched,
                "unwatched_episodes": unwatched,
                "completion_percent": completion,
            }
        )
    return {"group_by": "season", "buckets": buckets, "returned": len(buckets)}
