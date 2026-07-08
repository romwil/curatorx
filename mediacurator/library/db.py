"""SQLite database for library index, chat, preferences, and embeddings."""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA = """
CREATE TABLE IF NOT EXISTS library_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rating_key TEXT UNIQUE,
    media_type TEXT NOT NULL,
    title TEXT NOT NULL,
    year INTEGER,
    summary TEXT DEFAULT '',
    genres TEXT DEFAULT '[]',
    cast TEXT DEFAULT '[]',
    directors TEXT DEFAULT '[]',
    keywords TEXT DEFAULT '[]',
    tmdb_id INTEGER,
    tvdb_id INTEGER,
    imdb_id TEXT,
    poster_url TEXT DEFAULT '',
    backdrop_url TEXT DEFAULT '',
    view_count INTEGER DEFAULT 0,
    last_viewed_at INTEGER,
    file_size INTEGER DEFAULT 0,
    in_radarr INTEGER DEFAULT 0,
    in_sonarr INTEGER DEFAULT 0,
    updated_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_library_tmdb ON library_items(tmdb_id);
CREATE INDEX IF NOT EXISTS idx_library_tvdb ON library_items(tvdb_id);
CREATE INDEX IF NOT EXISTS idx_library_type ON library_items(media_type);

CREATE TABLE IF NOT EXISTS embeddings (
    item_id INTEGER PRIMARY KEY,
    vector TEXT NOT NULL,
    FOREIGN KEY(item_id) REFERENCES library_items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS preference_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_type TEXT NOT NULL,
    text TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    tmdb_id INTEGER,
    tvdb_id INTEGER,
    media_type TEXT,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    blocks_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pending_actions (
    token TEXT PRIMARY KEY,
    action_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at REAL NOT NULL
);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def upsert_library_item(self, item: Mapping[str, Any]) -> int:
        now = time.time()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO library_items (
                    rating_key, media_type, title, year, summary, genres, cast, directors,
                    keywords, tmdb_id, tvdb_id, imdb_id, poster_url, backdrop_url,
                    view_count, last_viewed_at, file_size, in_radarr, in_sonarr, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(rating_key) DO UPDATE SET
                    media_type=excluded.media_type,
                    title=excluded.title,
                    year=excluded.year,
                    summary=excluded.summary,
                    genres=excluded.genres,
                    cast=excluded.cast,
                    directors=excluded.directors,
                    keywords=excluded.keywords,
                    tmdb_id=excluded.tmdb_id,
                    tvdb_id=excluded.tvdb_id,
                    imdb_id=excluded.imdb_id,
                    poster_url=excluded.poster_url,
                    backdrop_url=excluded.backdrop_url,
                    view_count=excluded.view_count,
                    last_viewed_at=excluded.last_viewed_at,
                    file_size=excluded.file_size,
                    in_radarr=excluded.in_radarr,
                    in_sonarr=excluded.in_sonarr,
                    updated_at=excluded.updated_at
                """,
                (
                    item.get("rating_key"),
                    item["media_type"],
                    item["title"],
                    item.get("year"),
                    item.get("summary", ""),
                    json.dumps(item.get("genres", [])),
                    json.dumps(item.get("cast", [])),
                    json.dumps(item.get("directors", [])),
                    json.dumps(item.get("keywords", [])),
                    item.get("tmdb_id"),
                    item.get("tvdb_id"),
                    item.get("imdb_id"),
                    item.get("poster_url", ""),
                    item.get("backdrop_url", ""),
                    item.get("view_count", 0),
                    item.get("last_viewed_at"),
                    item.get("file_size", 0),
                    int(bool(item.get("in_radarr"))),
                    int(bool(item.get("in_sonarr"))),
                    now,
                ),
            )
            row = conn.execute(
                "SELECT id FROM library_items WHERE rating_key = ?",
                (item.get("rating_key"),),
            ).fetchone()
            return int(row["id"]) if row else 0

    def set_embedding(self, item_id: int, vector: Sequence[float]) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO embeddings (item_id, vector) VALUES (?, ?)",
                (item_id, json.dumps(list(vector))),
            )

    def all_library_items(self) -> List[sqlite3.Row]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM library_items ORDER BY title").fetchall()
            return list(rows)

    def library_item_by_tmdb(self, tmdb_id: int, media_type: str) -> Optional[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM library_items WHERE tmdb_id = ? AND media_type = ?",
                (tmdb_id, media_type),
            ).fetchone()

    def library_item_by_tvdb(self, tvdb_id: int) -> Optional[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM library_items WHERE tvdb_id = ? AND media_type = 'show'",
                (tvdb_id,),
            ).fetchone()

    def owned_tmdb_ids(self, media_type: str) -> set[int]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT tmdb_id FROM library_items WHERE media_type = ? AND tmdb_id IS NOT NULL",
                (media_type,),
            ).fetchall()
            return {int(r["tmdb_id"]) for r in rows}

    def owned_tvdb_ids(self) -> set[int]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT tvdb_id FROM library_items WHERE media_type = 'show' AND tvdb_id IS NOT NULL"
            ).fetchall()
            return {int(r["tvdb_id"]) for r in rows}

    def search_keyword(self, query: str, *, limit: int = 20) -> List[sqlite3.Row]:
        pattern = f"%{query.lower()}%"
        with self.connect() as conn:
            return list(
                conn.execute(
                    """
                    SELECT * FROM library_items
                    WHERE lower(title) LIKE ? OR lower(summary) LIKE ? OR lower(genres) LIKE ?
                    ORDER BY view_count DESC, title
                    LIMIT ?
                    """,
                    (pattern, pattern, pattern, limit),
                ).fetchall()
            )

    def get_embeddings(self) -> List[Tuple[int, List[float]]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT item_id, vector FROM embeddings"
            ).fetchall()
            return [(int(r["item_id"]), json.loads(r["vector"])) for r in rows]

    def add_preference(self, signal_type: str, text: str, **kwargs: Any) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO preference_facts (signal_type, text, weight, tmdb_id, tvdb_id, media_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_type,
                    text,
                    kwargs.get("weight", 1.0),
                    kwargs.get("tmdb_id"),
                    kwargs.get("tvdb_id"),
                    kwargs.get("media_type"),
                    time.time(),
                ),
            )

    def preference_facts(self, limit: int = 50) -> List[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    "SELECT * FROM preference_facts ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            )

    def save_pending_action(self, token: str, action_type: str, payload: Mapping[str, Any], ttl_seconds: int = 600) -> None:
        now = time.time()
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO pending_actions (token, action_type, payload_json, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
                (token, action_type, json.dumps(dict(payload)), now, now + ttl_seconds),
            )

    def pop_pending_action(self, token: str) -> Optional[Mapping[str, Any]]:
        now = time.time()
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM pending_actions WHERE token = ? AND expires_at > ?",
                (token, now),
            ).fetchone()
            if not row:
                return None
            conn.execute("DELETE FROM pending_actions WHERE token = ?", (token,))
            return json.loads(row["payload_json"])

    def set_sync_state(self, key: str, value: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sync_state (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, time.time()),
            )

    def get_sync_state(self, key: str) -> Optional[str]:
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM sync_state WHERE key = ?", (key,)).fetchone()
            return str(row["value"]) if row else None

    def ensure_chat_session(self, session_id: str) -> None:
        now = time.time()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO chat_sessions (id, created_at, updated_at) VALUES (?, ?, ?)
                """,
                (session_id, now, now),
            )

    def save_chat_message(self, session_id: str, message_id: str, role: str, blocks: Iterable[Mapping[str, Any]]) -> None:
        now = time.time()
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO chat_messages (id, session_id, role, blocks_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (message_id, session_id, role, json.dumps(list(blocks)), now),
            )
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )

    def chat_history(self, session_id: str, limit: int = 50) -> List[Mapping[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
            messages = []
            for row in reversed(rows):
                messages.append(
                    {
                        "id": row["id"],
                        "role": row["role"],
                        "blocks": json.loads(row["blocks_json"]),
                        "created_at": row["created_at"],
                    }
                )
            return messages
