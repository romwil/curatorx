"""Facet index and FTS rebuild for library intelligence queries."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping

from curatorx.library.db import Database


def _parse_json_list(raw: Any) -> List[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(v).strip() for v in raw if str(v).strip()]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return [str(v).strip() for v in parsed if str(v).strip()]
    return []


def _country_values_from_row(row: Mapping[str, Any]) -> List[str]:
    return _parse_json_list(row["countries"] if "countries" in row.keys() else [])


def _language_value_from_row(row: Mapping[str, Any]) -> str:
    if "original_language" not in row.keys():
        return ""
    return str(row["original_language"] or "").strip()


def _facet_catalog_from_items(db: Database, facet_type: str, *, limit: int) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    for row in db.all_library_items():
        if facet_type == "country":
            for value in _country_values_from_row(row):
                counts[value] = counts.get(value, 0) + 1
        elif facet_type == "language":
            value = _language_value_from_row(row)
            if value:
                counts[value] = counts.get(value, 0) + 1
    facets = [
        {"value": value, "count": count}
        for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]
    return {"facet_type": facet_type, "facets": facets, "returned": len(facets)}


def ensure_library_facet_index(db: Database) -> int:
    """Rebuild facets when item columns have country/language data but the facet index does not."""
    with db.connect() as conn:
        country_facet_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM library_facets WHERE facet_type = 'country'"
        ).fetchone()["cnt"]
        language_facet_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM library_facets WHERE facet_type = 'language'"
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
    needs_rebuild = (
        (items_with_countries > 0 and country_facet_count == 0)
        or (items_with_language > 0 and language_facet_count == 0)
    )
    if not needs_rebuild:
        return 0
    return rebuild_library_facets(db)


def rebuild_library_facets(db: Database) -> int:
    db.clear_library_facets()
    count = 0
    for row in db.all_library_items():
        item_id = int(row["id"])
        for director in _parse_json_list(row["directors"]):
            db.add_library_facet(item_id, "director", director)
            count += 1
        for actor in _parse_json_list(row["cast"]):
            db.add_library_facet(item_id, "actor", actor)
            count += 1
        for keyword in _parse_json_list(row["keywords"]):
            db.add_library_facet(item_id, "keyword", keyword)
            count += 1
        for country in _country_values_from_row(row):
            db.add_library_facet(item_id, "country", country)
            count += 1
        language = _language_value_from_row(row)
        if language:
            db.add_library_facet(item_id, "language", language)
            count += 1
    return count


def rebuild_library_fts(db: Database) -> int:
    db.clear_library_fts()
    count = 0
    for row in db.all_library_items():
        cast_text = " ".join(_parse_json_list(row["cast"]))
        directors_text = " ".join(_parse_json_list(row["directors"]))
        keywords_text = " ".join(_parse_json_list(row["keywords"]))
        db.upsert_library_fts_row(
            int(row["id"]),
            str(row["title"] or ""),
            str(row["summary"] or ""),
            cast_text,
            directors_text,
            keywords_text,
        )
        count += 1
    return count


def library_facet_catalog(
    db: Database,
    facet_type: str,
    *,
    limit: int = 50,
) -> Dict[str, Any]:
    normalized = facet_type.strip().lower()
    allowed = {"director", "actor", "keyword", "country", "language"}
    if normalized not in allowed:
        raise ValueError(f"facet_type must be one of: {', '.join(sorted(allowed))}")
    capped = min(max(1, limit), 100)
    if normalized in {"country", "language"}:
        return _facet_catalog_from_items(db, normalized, limit=capped)
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT facet_value, COUNT(*) AS cnt
            FROM library_facets
            WHERE facet_type = ?
            GROUP BY facet_value
            ORDER BY cnt DESC, facet_value ASC
            LIMIT ?
            """,
            (normalized, capped),
        ).fetchall()
    facets = [{"value": str(r["facet_value"]), "count": int(r["cnt"])} for r in rows]
    return {"facet_type": normalized, "facets": facets, "returned": len(facets)}
