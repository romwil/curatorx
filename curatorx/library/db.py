"""SQLite database for library index, chat, preferences, lenses, and embeddings."""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, List, Mapping, Optional, Sequence, Tuple

DEFAULT_LENS_ID = "general"
DEFAULT_CONTEXT_HASH = "general"
DEFAULT_PERSONA_ID = "current_profile"
ACTIVE_LENS_CONFIG_KEY = "active_lens_id"
ACTIVE_CONTEXT_CONFIG_KEY = "active_context_hash"
CURATOR_NAME_CONFIG_KEY = "curator_name"

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
    updated_at REAL NOT NULL,
    lens_id TEXT NOT NULL DEFAULT 'general',
    thread_title TEXT DEFAULT 'New conversation',
    context_hash TEXT DEFAULT 'general'
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    blocks_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    lens_id TEXT NOT NULL DEFAULT 'general',
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

CREATE TABLE IF NOT EXISTS curator_system_config (
    config_key TEXT PRIMARY KEY,
    config_value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS service_integrations (
    service_name TEXT PRIMARY KEY,
    base_url TEXT,
    api_token_encrypted TEXT,
    connection_status TEXT DEFAULT 'unverified',
    last_tested_at DATETIME,
    certified INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS curator_persona_metrics (
    metric_id TEXT PRIMARY KEY DEFAULT 'current_profile',
    curator_name TEXT DEFAULT 'Curator',
    persona_identity TEXT DEFAULT '',
    val_bro_prof REAL DEFAULT 0.5,
    val_dipl_snark REAL DEFAULT 0.5,
    val_pass_auto REAL DEFAULT 0.5,
    persona_preset_id TEXT,
    persona_prompt_override TEXT,
    last_modified DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS curation_lenses (
    lens_id TEXT PRIMARY KEY,
    lens_name TEXT NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lens_taste_profile (
    lens_id TEXT NOT NULL,
    cluster_tag TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    explicit_lock INTEGER DEFAULT 0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (lens_id, cluster_tag),
    FOREIGN KEY (lens_id) REFERENCES curation_lenses(lens_id)
);

CREATE TABLE IF NOT EXISTS interaction_telemetry (
    id TEXT PRIMARY KEY,
    title_id TEXT NOT NULL,
    lens_id TEXT NOT NULL,
    source TEXT NOT NULL,
    event_type TEXT NOT NULL,
    watch_duration_seconds INTEGER DEFAULT 0,
    completion_percentage REAL DEFAULT 0.0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lens_id) REFERENCES curation_lenses(lens_id)
);

CREATE TABLE IF NOT EXISTS agent_blueprints (
    blueprint_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cron_schedule TEXT NOT NULL,
    active_lens_id TEXT,
    instructions_json TEXT,
    is_enabled INTEGER DEFAULT 1,
    last_run_status TEXT,
    last_run_timestamp DATETIME,
    FOREIGN KEY (active_lens_id) REFERENCES curation_lenses(lens_id)
);

CREATE TABLE IF NOT EXISTS derived_contexts (
    context_hash TEXT PRIMARY KEY,
    inferred_label TEXT DEFAULT 'General Exploration',
    thematic_centroid_json TEXT,
    interaction_density INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_active_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_telemetry_stream (
    id TEXT PRIMARY KEY,
    media_node_id TEXT,
    associated_context_hash TEXT,
    event_class TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (associated_context_hash) REFERENCES derived_contexts(context_hash)
);

CREATE VIEW IF NOT EXISTS integration_profiles AS
SELECT
    service_name AS service_id,
    base_url AS endpoint_url,
    api_token_encrypted AS credential_encrypted,
    connection_status AS verification_state,
    last_tested_at AS synchronized_at
FROM service_integrations;
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            self._migrate_chat_lens_columns(conn)
            self._migrate_chat_thread_columns(conn)
            self._migrate_service_integrations_certified(conn)
            self._migrate_phase3_tables(conn)
            self._migrate_persona_columns(conn)
            self._seed_defaults(conn)

    def _table_columns(self, conn: sqlite3.Connection, table: str) -> set[str]:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {str(row["name"]) for row in rows}

    def _migrate_chat_lens_columns(self, conn: sqlite3.Connection) -> None:
        session_cols = self._table_columns(conn, "chat_sessions")
        if "lens_id" not in session_cols:
            conn.execute(
                f"ALTER TABLE chat_sessions ADD COLUMN lens_id TEXT NOT NULL DEFAULT '{DEFAULT_LENS_ID}'"
            )
        message_cols = self._table_columns(conn, "chat_messages")
        if "lens_id" not in message_cols:
            conn.execute(
                f"ALTER TABLE chat_messages ADD COLUMN lens_id TEXT NOT NULL DEFAULT '{DEFAULT_LENS_ID}'"
            )
        conn.execute(
            "UPDATE chat_sessions SET lens_id = ? WHERE lens_id IS NULL OR lens_id = ''",
            (DEFAULT_LENS_ID,),
        )
        conn.execute(
            "UPDATE chat_messages SET lens_id = ? WHERE lens_id IS NULL OR lens_id = ''",
            (DEFAULT_LENS_ID,),
        )

    def _migrate_chat_thread_columns(self, conn: sqlite3.Connection) -> None:
        session_cols = self._table_columns(conn, "chat_sessions")
        if "thread_title" not in session_cols:
            conn.execute(
                "ALTER TABLE chat_sessions ADD COLUMN thread_title TEXT DEFAULT 'New conversation'"
            )
        if "context_hash" not in session_cols:
            conn.execute(
                f"ALTER TABLE chat_sessions ADD COLUMN context_hash TEXT DEFAULT '{DEFAULT_CONTEXT_HASH}'"
            )
        conn.execute(
            "UPDATE chat_sessions SET thread_title = 'New conversation' WHERE thread_title IS NULL OR thread_title = ''"
        )
        conn.execute(
            "UPDATE chat_sessions SET context_hash = ? WHERE context_hash IS NULL OR context_hash = ''",
            (DEFAULT_CONTEXT_HASH,),
        )

    def _migrate_service_integrations_certified(self, conn: sqlite3.Connection) -> None:
        cols = self._table_columns(conn, "service_integrations")
        if "certified" not in cols:
            conn.execute(
                "ALTER TABLE service_integrations ADD COLUMN certified INTEGER DEFAULT 0"
            )
            conn.execute(
                """
                UPDATE service_integrations
                SET certified = 1
                WHERE connection_status = 'verified'
                """
            )

    def _migrate_persona_columns(self, conn: sqlite3.Connection) -> None:
        cols = self._table_columns(conn, "curator_persona_metrics")
        if "persona_identity" not in cols:
            conn.execute(
                "ALTER TABLE curator_persona_metrics ADD COLUMN persona_identity TEXT DEFAULT ''"
            )
        if "persona_preset_id" not in cols:
            conn.execute(
                "ALTER TABLE curator_persona_metrics ADD COLUMN persona_preset_id TEXT"
            )
        if "persona_prompt_override" not in cols:
            conn.execute(
                "ALTER TABLE curator_persona_metrics ADD COLUMN persona_prompt_override TEXT"
            )

    def _migrate_phase3_tables(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS derived_contexts (
                context_hash TEXT PRIMARY KEY,
                inferred_label TEXT DEFAULT 'General Exploration',
                thematic_centroid_json TEXT,
                interaction_density INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_active_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS system_telemetry_stream (
                id TEXT PRIMARY KEY,
                media_node_id TEXT,
                associated_context_hash TEXT,
                event_class TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (associated_context_hash) REFERENCES derived_contexts(context_hash)
            );

            CREATE VIEW IF NOT EXISTS integration_profiles AS
            SELECT
                service_name AS service_id,
                base_url AS endpoint_url,
                api_token_encrypted AS credential_encrypted,
                connection_status AS verification_state,
                last_tested_at AS synchronized_at
            FROM service_integrations;
            """
        )

    def _seed_defaults(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT OR IGNORE INTO curation_lenses (lens_id, lens_name, description)
            VALUES (?, 'General', 'Default curation lens for general conversation and discovery.')
            """,
            (DEFAULT_LENS_ID,),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO derived_contexts (
                context_hash, inferred_label, thematic_centroid_json, interaction_density
            ) VALUES (?, 'General Exploration', NULL, 1)
            """,
            (DEFAULT_CONTEXT_HASH,),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO curator_system_config (config_key, config_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (ACTIVE_CONTEXT_CONFIG_KEY, DEFAULT_CONTEXT_HASH),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO curator_persona_metrics (
                metric_id, curator_name, val_bro_prof, val_dipl_snark, val_pass_auto
            ) VALUES (?, 'Curator', 0.5, 0.5, 0.5)
            """,
            (DEFAULT_PERSONA_ID,),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO curator_system_config (config_key, config_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (ACTIVE_LENS_CONFIG_KEY, DEFAULT_LENS_ID),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO curator_system_config (config_key, config_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (CURATOR_NAME_CONFIG_KEY, "Curator"),
        )

    def ensure_seed_data(self) -> None:
        with self.connect() as conn:
            self._seed_defaults(conn)

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

    # --- System config ---

    def get_config(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT config_value FROM curator_system_config WHERE config_key = ?",
                (key,),
            ).fetchone()
            if not row:
                return default
            return str(row["config_value"])

    def set_config(self, key: str, value: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO curator_system_config (config_key, config_value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(config_key) DO UPDATE SET
                    config_value=excluded.config_value,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (key, value),
            )

    def get_all_config(self) -> Dict[str, str]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT config_key, config_value FROM curator_system_config ORDER BY config_key"
            ).fetchall()
            return {str(r["config_key"]): str(r["config_value"]) for r in rows}

    def sync_llm_config(
        self,
        *,
        llm_provider: str,
        llm_base_url: str,
        llm_model: str,
    ) -> None:
        self.set_config("llm_provider", llm_provider)
        self.set_config("llm_base_url", llm_base_url)
        self.set_config("llm_model", llm_model)

    # --- Service integrations ---

    def upsert_service_integration(
        self,
        service_name: str,
        *,
        base_url: str = "",
        api_token_encrypted: str = "",
        connection_status: str = "unverified",
        last_tested_at: Optional[str] = None,
        certified: Optional[int] = None,
    ) -> None:
        tested_at = last_tested_at or time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        certified_value = 0 if certified is None else int(bool(certified))
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO service_integrations (
                    service_name, base_url, api_token_encrypted, connection_status,
                    last_tested_at, certified
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(service_name) DO UPDATE SET
                    base_url=excluded.base_url,
                    api_token_encrypted=excluded.api_token_encrypted,
                    connection_status=excluded.connection_status,
                    last_tested_at=excluded.last_tested_at,
                    certified=excluded.certified
                """,
                (
                    service_name,
                    base_url,
                    api_token_encrypted,
                    connection_status,
                    tested_at,
                    certified_value,
                ),
            )

    def invalidate_service_certification(self, service_name: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE service_integrations
                SET certified = 0, connection_status = 'unverified'
                WHERE service_name = ?
                """,
                (service_name,),
            )

    def get_service_integration(self, service_name: str) -> Optional[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM service_integrations WHERE service_name = ?",
                (service_name,),
            ).fetchone()

    def get_service_integrations(self) -> List[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    "SELECT * FROM service_integrations ORDER BY service_name ASC"
                ).fetchall()
            )

    def get_active_lens_id(self) -> str:
        return self.get_config(ACTIVE_LENS_CONFIG_KEY, DEFAULT_LENS_ID) or DEFAULT_LENS_ID

    def set_active_lens_id(self, lens_id: str) -> None:
        if not self.get_lens(lens_id):
            raise ValueError(f"Unknown lens_id: {lens_id}")
        self.set_config(ACTIVE_LENS_CONFIG_KEY, lens_id)

    # --- Derived contexts (Phase 3) ---

    def get_derived_context(self, context_hash: str) -> Optional[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM derived_contexts WHERE context_hash = ?",
                (context_hash,),
            ).fetchone()

    def get_active_derived_context(self) -> sqlite3.Row:
        active_hash = self.get_config(ACTIVE_CONTEXT_CONFIG_KEY, DEFAULT_CONTEXT_HASH) or DEFAULT_CONTEXT_HASH
        row = self.get_derived_context(active_hash)
        if row:
            return row
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO derived_contexts (
                    context_hash, inferred_label, thematic_centroid_json, interaction_density
                ) VALUES (?, 'General Exploration', NULL, 1)
                """,
                (DEFAULT_CONTEXT_HASH,),
            )
        row = self.get_derived_context(DEFAULT_CONTEXT_HASH)
        assert row is not None
        return row

    # --- Persona ---

    def get_persona(self, metric_id: str = DEFAULT_PERSONA_ID) -> Optional[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM curator_persona_metrics WHERE metric_id = ?",
                (metric_id,),
            ).fetchone()

    def upsert_persona(
        self,
        *,
        metric_id: str = DEFAULT_PERSONA_ID,
        curator_name: Optional[str] = None,
        persona_identity: Optional[str] = None,
        val_bro_prof: Optional[float] = None,
        val_dipl_snark: Optional[float] = None,
        val_pass_auto: Optional[float] = None,
        persona_preset_id: Optional[str] = ...,  # type: ignore[assignment]
        persona_prompt_override: Optional[str] = ...,  # type: ignore[assignment]
        clear_persona_override: bool = False,
    ) -> sqlite3.Row:
        current = self.get_persona(metric_id)
        name = curator_name if curator_name is not None else (current["curator_name"] if current else "Curator")
        identity = (
            persona_identity
            if persona_identity is not None
            else (str(current["persona_identity"] or "") if current and "persona_identity" in current.keys() else "")
        )
        bro = val_bro_prof if val_bro_prof is not None else (float(current["val_bro_prof"]) if current else 0.5)
        snark = val_dipl_snark if val_dipl_snark is not None else (float(current["val_dipl_snark"]) if current else 0.5)
        auto = val_pass_auto if val_pass_auto is not None else (float(current["val_pass_auto"]) if current else 0.5)

        if persona_preset_id is ...:
            preset_id = str(current["persona_preset_id"] or "") if current and "persona_preset_id" in current.keys() else None
            preset_id = preset_id or None
        else:
            preset_id = persona_preset_id

        if clear_persona_override:
            override = None
        elif persona_prompt_override is ...:
            override = (
                str(current["persona_prompt_override"])
                if current and current["persona_prompt_override"] is not None
                else None
            )
        else:
            override = persona_prompt_override

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO curator_persona_metrics (
                    metric_id, curator_name, persona_identity, val_bro_prof, val_dipl_snark,
                    val_pass_auto, persona_preset_id, persona_prompt_override, last_modified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(metric_id) DO UPDATE SET
                    curator_name=excluded.curator_name,
                    persona_identity=excluded.persona_identity,
                    val_bro_prof=excluded.val_bro_prof,
                    val_dipl_snark=excluded.val_dipl_snark,
                    val_pass_auto=excluded.val_pass_auto,
                    persona_preset_id=excluded.persona_preset_id,
                    persona_prompt_override=excluded.persona_prompt_override,
                    last_modified=CURRENT_TIMESTAMP
                """,
                (metric_id, name, identity, bro, snark, auto, preset_id, override),
            )
        if curator_name is not None:
            self.set_config(CURATOR_NAME_CONFIG_KEY, name)
        persona = self.get_persona(metric_id)
        assert persona is not None
        return persona

    # --- Lenses ---

    def list_lenses(self) -> List[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    "SELECT * FROM curation_lenses ORDER BY created_at ASC, lens_name ASC"
                ).fetchall()
            )

    def get_lens(self, lens_id: str) -> Optional[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM curation_lenses WHERE lens_id = ?",
                (lens_id,),
            ).fetchone()

    def create_lens(self, lens_id: str, lens_name: str, description: str = "") -> sqlite3.Row:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO curation_lenses (lens_id, lens_name, description)
                VALUES (?, ?, ?)
                """,
                (lens_id, lens_name, description),
            )
        lens = self.get_lens(lens_id)
        assert lens is not None
        return lens

    def update_lens(
        self,
        lens_id: str,
        *,
        lens_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> sqlite3.Row:
        current = self.get_lens(lens_id)
        if not current:
            raise ValueError(f"Unknown lens_id: {lens_id}")
        name = lens_name if lens_name is not None else current["lens_name"]
        desc = description if description is not None else (current["description"] or "")
        with self.connect() as conn:
            conn.execute(
                "UPDATE curation_lenses SET lens_name = ?, description = ? WHERE lens_id = ?",
                (name, desc, lens_id),
            )
        lens = self.get_lens(lens_id)
        assert lens is not None
        return lens

    # --- Lens taste profile ---

    def get_lens_taste_profile(self, lens_id: str) -> List[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    """
                    SELECT * FROM lens_taste_profile
                    WHERE lens_id = ?
                    ORDER BY weight DESC, cluster_tag ASC
                    """,
                    (lens_id,),
                ).fetchall()
            )

    def set_lens_taste_weight(
        self,
        lens_id: str,
        cluster_tag: str,
        weight: float,
        *,
        explicit_lock: Optional[bool] = None,
        respect_lock: bool = True,
    ) -> None:
        if not self.get_lens(lens_id):
            raise ValueError(f"Unknown lens_id: {lens_id}")
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT * FROM lens_taste_profile WHERE lens_id = ? AND cluster_tag = ?",
                (lens_id, cluster_tag),
            ).fetchone()
            if existing and respect_lock and int(existing["explicit_lock"]) == 1 and explicit_lock is None:
                return
            lock_value = (
                int(bool(explicit_lock))
                if explicit_lock is not None
                else (int(existing["explicit_lock"]) if existing else 0)
            )
            conn.execute(
                """
                INSERT INTO lens_taste_profile (lens_id, cluster_tag, weight, explicit_lock, last_updated)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(lens_id, cluster_tag) DO UPDATE SET
                    weight=excluded.weight,
                    explicit_lock=excluded.explicit_lock,
                    last_updated=CURRENT_TIMESTAMP
                """,
                (lens_id, cluster_tag, weight, lock_value),
            )

    # --- Chat (lens-scoped) ---

    DEFAULT_THREAD_TITLE = "New conversation"

    def _preview_from_blocks(self, blocks_json: Optional[str]) -> str:
        if not blocks_json:
            return ""
        try:
            blocks = json.loads(blocks_json)
        except json.JSONDecodeError:
            return ""
        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                content = str(block.get("content") or "").strip()
                if content:
                    return content[:120]
        return ""

    def _row_to_thread_summary(self, row: sqlite3.Row, *, message_count: int = 0, preview: str = "") -> Dict[str, Any]:
        return {
            "id": str(row["id"]),
            "thread_title": str(row["thread_title"] or self.DEFAULT_THREAD_TITLE),
            "context_hash": str(row["context_hash"] or DEFAULT_CONTEXT_HASH),
            "lens_id": str(row["lens_id"] or DEFAULT_LENS_ID),
            "created_at": float(row["created_at"]),
            "updated_at": float(row["updated_at"]),
            "message_count": message_count,
            "preview": preview,
        }

    def create_chat_thread(
        self,
        session_id: str,
        *,
        lens_id: str = DEFAULT_LENS_ID,
        context_hash: str = DEFAULT_CONTEXT_HASH,
        thread_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = time.time()
        resolved_lens = lens_id or DEFAULT_LENS_ID
        resolved_context = context_hash or DEFAULT_CONTEXT_HASH
        title = (thread_title or self.DEFAULT_THREAD_TITLE).strip() or self.DEFAULT_THREAD_TITLE
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_sessions (
                    id, created_at, updated_at, lens_id, thread_title, context_hash
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, now, now, resolved_lens, title, resolved_context),
            )
            row = conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
        assert row is not None
        return self._row_to_thread_summary(row)

    def get_chat_thread(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
            if not row:
                return None
            count_row = conn.execute(
                "SELECT COUNT(*) AS count FROM chat_messages WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            last_row = conn.execute(
                """
                SELECT blocks_json FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        preview = self._preview_from_blocks(last_row["blocks_json"] if last_row else None)
        return self._row_to_thread_summary(
            row,
            message_count=int(count_row["count"]) if count_row else 0,
            preview=preview,
        )

    def list_chat_threads(self, *, limit: int = 50) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    s.*,
                    COUNT(m.id) AS message_count,
                    (
                        SELECT blocks_json FROM chat_messages
                        WHERE session_id = s.id
                        ORDER BY created_at DESC
                        LIMIT 1
                    ) AS last_blocks_json
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON m.session_id = s.id
                GROUP BY s.id
                ORDER BY s.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        threads: List[Dict[str, Any]] = []
        for row in rows:
            preview = self._preview_from_blocks(row["last_blocks_json"])
            threads.append(
                self._row_to_thread_summary(
                    row,
                    message_count=int(row["message_count"] or 0),
                    preview=preview,
                )
            )
        return threads

    def update_thread_title(self, session_id: str, thread_title: str) -> Dict[str, Any]:
        title = thread_title.strip()
        if not title:
            raise ValueError("thread_title is required")
        now = time.time()
        with self.connect() as conn:
            existing = conn.execute("SELECT id FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
            if not existing:
                raise ValueError(f"Unknown session_id: {session_id}")
            conn.execute(
                "UPDATE chat_sessions SET thread_title = ?, updated_at = ? WHERE id = ?",
                (title, now, session_id),
            )
        thread = self.get_chat_thread(session_id)
        assert thread is not None
        return thread

    def maybe_auto_title_thread(self, session_id: str, first_message: str) -> None:
        text = first_message.strip()
        if not text:
            return
        title = text[:60] + ("…" if len(text) > 60 else "")
        with self.connect() as conn:
            row = conn.execute(
                "SELECT thread_title FROM chat_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if not row:
                return
            current = str(row["thread_title"] or self.DEFAULT_THREAD_TITLE)
            if current != self.DEFAULT_THREAD_TITLE:
                return
            conn.execute(
                "UPDATE chat_sessions SET thread_title = ? WHERE id = ?",
                (title, session_id),
            )

    def delete_chat_thread(self, session_id: str) -> bool:
        with self.connect() as conn:
            row = conn.execute("SELECT id FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
            if not row:
                return False
            conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            return True

    def ensure_chat_session(
        self,
        session_id: str,
        lens_id: str = DEFAULT_LENS_ID,
        *,
        context_hash: str = DEFAULT_CONTEXT_HASH,
    ) -> None:
        now = time.time()
        resolved = lens_id or DEFAULT_LENS_ID
        resolved_context = context_hash or DEFAULT_CONTEXT_HASH
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO chat_sessions (
                    id, created_at, updated_at, lens_id, thread_title, context_hash
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, now, now, resolved, self.DEFAULT_THREAD_TITLE, resolved_context),
            )
            conn.execute(
                """
                UPDATE chat_sessions
                SET lens_id = ?, updated_at = ?, context_hash = COALESCE(context_hash, ?)
                WHERE id = ?
                """,
                (resolved, now, resolved_context, session_id),
            )

    def save_chat_message(
        self,
        session_id: str,
        message_id: str,
        role: str,
        blocks: Iterable[Mapping[str, Any]],
        lens_id: str = DEFAULT_LENS_ID,
    ) -> None:
        now = time.time()
        resolved = lens_id or DEFAULT_LENS_ID
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_messages (id, session_id, role, blocks_json, created_at, lens_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (message_id, session_id, role, json.dumps(list(blocks)), now, resolved),
            )
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ?, lens_id = ? WHERE id = ?",
                (now, resolved, session_id),
            )

    def chat_history(
        self,
        session_id: str,
        limit: int = 50,
        lens_id: Optional[str] = None,
    ) -> List[Mapping[str, Any]]:
        with self.connect() as conn:
            if lens_id:
                rows = conn.execute(
                    """
                    SELECT * FROM chat_messages
                    WHERE session_id = ? AND lens_id = ?
                    ORDER BY created_at DESC LIMIT ?
                    """,
                    (session_id, lens_id, limit),
                ).fetchall()
            else:
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
                        "lens_id": row["lens_id"] if "lens_id" in row.keys() else DEFAULT_LENS_ID,
                    }
                )
            return messages
