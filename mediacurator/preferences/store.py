"""Preference storage and retrieval."""

from __future__ import annotations

from typing import List

from mediacurator.library.db import Database
from mediacurator.models.schemas import PreferenceSignal


def remember_preference(db: Database, signal: PreferenceSignal) -> None:
    weight = {
        "explicit": 2.0,
        "positive": 1.5,
        "negative": -1.5,
        "add": 1.0,
        "dismiss": -0.5,
    }.get(signal.signal_type, 1.0)
    db.add_preference(
        signal.signal_type,
        signal.text,
        weight=weight,
        tmdb_id=signal.tmdb_id,
        tvdb_id=signal.tvdb_id,
        media_type=signal.media_type,
    )


def preference_context(db: Database, limit: int = 20) -> str:
    facts = db.preference_facts(limit=limit)
    if not facts:
        return "No explicit preferences recorded yet."
    lines: List[str] = []
    for fact in facts:
        lines.append(f"- [{fact['signal_type']}] {fact['text']}")
    return "User preferences:\n" + "\n".join(lines)
