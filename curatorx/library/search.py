"""Library search helpers."""

from __future__ import annotations

import json
from typing import List, Optional

from curatorx.config_store import Settings
from curatorx.library.db import Database
from curatorx.library.query import filters_from_mapping, query_library_async
from curatorx.models.schemas import TitleCard


def row_to_title_card(row, *, reason: str = "", facet_matches: Optional[List[str]] = None) -> TitleCard:
    genres = json.loads(row["genres"]) if row["genres"] else []
    return TitleCard(
        media_type=row["media_type"],
        title=row["title"],
        year=row["year"],
        tmdb_id=row["tmdb_id"],
        tvdb_id=row["tvdb_id"],
        rating_key=row["rating_key"],
        poster_url=row["poster_url"] or "",
        backdrop_url=row["backdrop_url"] or "",
        overview=row["summary"] or "",
        genres=genres,
        in_library=True,
        in_radarr=bool(row["in_radarr"]),
        in_sonarr=bool(row["in_sonarr"]),
        recommendation_reason=reason,
        facet_matches=list(facet_matches or []),
        runtime_minutes=int(row["runtime_minutes"]) if "runtime_minutes" in row.keys() and row["runtime_minutes"] else None,
        total_episode_count=int(row["total_episode_count"])
        if "total_episode_count" in row.keys() and row["total_episode_count"]
        else None,
        unwatched_episode_count=int(row["unwatched_episode_count"])
        if "unwatched_episode_count" in row.keys() and row["unwatched_episode_count"] is not None
        else None,
    )


async def search_library(
    db: Database,
    settings: Settings,
    query: str,
    *,
    media_type: Optional[str] = None,
    limit: int = 12,
) -> List[TitleCard]:
    filters = filters_from_mapping(
        {
            "semantic_query": query,
            "media_type": media_type,
            "limit": limit,
        }
    )
    result = await query_library_async(db, filters, settings)
    cards: List[TitleCard] = []
    for item in result.get("items", []):
        row = db.library_item_by_id(int(item["id"])) if item.get("id") else None
        if row is None:
            continue
        mode = result.get("search_mode", "semantic")
        cards.append(row_to_title_card(row, reason=f"Library match ({mode})"))
    return cards[:limit]
