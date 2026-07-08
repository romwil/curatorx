"""Library search helpers."""

from __future__ import annotations

import json
from typing import List, Optional

from mediacurator.config_store import Settings
from mediacurator.library.db import Database
from mediacurator.library.embeddings import embed_text, semantic_search
from mediacurator.models.schemas import TitleCard


def row_to_title_card(row, *, reason: str = "") -> TitleCard:
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
    )


async def search_library(
    db: Database,
    settings: Settings,
    query: str,
    *,
    media_type: Optional[str] = None,
    limit: int = 12,
) -> List[TitleCard]:
    vector = await embed_text(query, settings)
    hits = semantic_search(db, vector, limit=limit, media_type=media_type)
    items = {int(row["id"]): row for row in db.all_library_items()}
    cards: List[TitleCard] = []
    for item_id, score in hits:
        row = items.get(item_id)
        if row is None:
            continue
        cards.append(row_to_title_card(row, reason=f"Library match ({score:.0%})"))
    if not cards:
        for row in db.search_keyword(query, limit=limit):
            if media_type and row["media_type"] != media_type:
                continue
            cards.append(row_to_title_card(row, reason="Keyword match"))
    return cards[:limit]
