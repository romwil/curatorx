# CuratorX — Data Model

Reference for persistent storage: SQLite tables, settings fields, and Pydantic schemas. Schema definitions live in `curatorx/library/db.py` and `curatorx/models/schemas.py`.

---

## Storage layout

| Path | Format | Contents |
|------|--------|----------|
| `{DATA_DIR}/curatorx.db` | SQLite 3 | Library, embeddings, chat (lens-scoped), persona, lenses, preferences |
| `{DATA_DIR}/settings.json` | JSON | Connection settings and secrets |

Default `DATA_DIR`: `/config` in Docker, `./config` in local dev.

---

## SQLite schema

### Core library (Phase 1)

#### `library_items`

Canonical Plex index enriched during sync.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Internal row ID |
| `rating_key` | TEXT UNIQUE | Plex rating key |
| `media_type` | TEXT | `movie` or `show` |
| `title` | TEXT | Display title |
| `year` | INTEGER | Release / first air year |
| `summary` | TEXT | Overview |
| `genres` | TEXT | JSON array |
| `cast` / `directors` / `keywords` | TEXT | JSON arrays |
| `tmdb_id` / `tvdb_id` / `imdb_id` | | External IDs |
| `poster_url` / `backdrop_url` | TEXT | Art URLs |
| `view_count` | INTEGER | Plex plays |
| `last_viewed_at` | INTEGER | Unix timestamp |
| `file_size` | INTEGER | Bytes on disk |
| `in_radarr` / `in_sonarr` | INTEGER | 0/1 queue flags |
| `updated_at` | REAL | Last upsert |

**Indexes:** `tmdb_id`, `tvdb_id`, `media_type`.

#### `embeddings`

| Column | Type | Description |
|--------|------|-------------|
| `item_id` | INTEGER PK FK | References `library_items.id` |
| `vector` | TEXT | JSON float array (384-dim hash or provider length) |

#### `preference_facts`

Taste signals for agent context and purge scoring.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | |
| `signal_type` | TEXT | `explicit`, `positive`, `negative`, `add`, `dismiss` |
| `text` | TEXT | Natural language description |
| `weight` | REAL | Signed weight |
| `tmdb_id` / `tvdb_id` / `media_type` | | Optional title scope |
| `created_at` | REAL | Unix timestamp |

#### `chat_sessions`

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | Session UUID |
| `created_at` / `updated_at` | REAL | |
| **`lens_id`** | TEXT | **Curation lens scope** (default `general`) |

#### `chat_messages`

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | Message UUID |
| `session_id` | TEXT FK | References `chat_sessions.id` |
| `role` | TEXT | `user`, `assistant`, `system` |
| `blocks_json` | TEXT | JSON message blocks |
| `created_at` | REAL | |
| **`lens_id`** | TEXT | **Lens filter for history queries** (default `general`) |

Chat history API and agent context load messages filtered by `lens_id` so lenses remain isolated within a session.

#### `pending_actions`

Confirmation-gated *arr operations (10-minute TTL).

| Column | Type | Description |
|--------|------|-------------|
| `token` | TEXT PK | UUID hex |
| `action_type` | TEXT | `add_radarr`, `add_sonarr`, `remove_arr` |
| `payload_json` | TEXT | Action-specific JSON |
| `created_at` / `expires_at` | REAL | |

#### `sync_state`

Key-value job metadata (e.g. `last_sync` JSON with item/embedding counts).

---

### PRD cognitive tables (Phase 1)

From [curatorx_prd.md](curatorx_prd.md):

#### `curator_system_config`

| Column | Type | Description |
|--------|------|-------------|
| `config_key` | TEXT PK | e.g. `active_lens_id`, `curator_name` |
| `config_value` | TEXT | |
| `updated_at` | DATETIME | |

#### `service_integrations`

| Column | Type | Description |
|--------|------|-------------|
| `service_name` | TEXT PK | `plex`, `radarr`, `sonarr`, `tmdb`, … |
| `base_url` | TEXT | |
| `api_token_encrypted` | TEXT | Reserved for encrypted storage |
| `connection_status` | TEXT | `unverified`, `verified`, `error` |
| `last_tested_at` | DATETIME | |

#### `curator_persona_metrics`

| Column | Type | Description |
|--------|------|-------------|
| `metric_id` | TEXT PK | Default `current_profile` |
| `curator_name` | TEXT | Display name (default `Curator`) |
| `val_bro_prof` | REAL | Vocabulary: bro (0) → professorial (1) |
| `val_dipl_snark` | REAL | Tone: diplomatic (0) → snarky (1) |
| `val_pass_auto` | REAL | Autonomy: passive (0) → autonomous (1) |
| `last_modified` | DATETIME | |

#### `curation_lenses`

| Column | Type | Description |
|--------|------|-------------|
| `lens_id` | TEXT PK | e.g. `general`, `directors` |
| `lens_name` | TEXT | Display name |
| `description` | TEXT | Optional |
| `created_at` | DATETIME | |

Seeded on init: **`general`** lens.

#### `lens_taste_profile`

| Column | Type | Description |
|--------|------|-------------|
| `lens_id` | TEXT FK | References `curation_lenses` |
| `cluster_tag` | TEXT | Taste cluster identifier |
| `weight` | REAL | Default 1.0 |
| `explicit_lock` | INTEGER | 1 = block automatic telemetry updates |
| `last_updated` | DATETIME | |

**Primary key:** `(lens_id, cluster_tag)`.

#### `interaction_telemetry`

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | |
| `title_id` | TEXT | Library or external title reference |
| `lens_id` | TEXT FK | Lens context |
| `source` | TEXT | `chat_thread`, `tautulli_webhook`, `widget_input`, … |
| `event_type` | TEXT | `watch_complete`, `deep_query`, … |
| `watch_duration_seconds` | INTEGER | |
| `completion_percentage` | REAL | |
| `timestamp` | DATETIME | |

#### `agent_blueprints`

| Column | Type | Description |
|--------|------|-------------|
| `blueprint_id` | TEXT PK | |
| `name` | TEXT | e.g. Midnight Scavenger |
| `cron_schedule` | TEXT | Crontab string |
| `active_lens_id` | TEXT FK | Lens context for scheduled runs |
| `instructions_json` | TEXT | Serialized agent instructions |
| `is_enabled` | INTEGER | 0/1 |
| `last_run_status` / `last_run_timestamp` | | Job telemetry |

---

## Settings model

Python dataclass `Settings` in `curatorx/config_store.py`, persisted as `settings.json`. Environment variables override file values.

See [CONFIGURATION.md](CONFIGURATION.md) for the full field list. Secret fields are masked on `GET /api/settings` with `{field}_set` booleans.

Persona sliders and curator name are **not** in `settings.json` — they live in `curator_persona_metrics` and `curator_system_config`.

---

## Pydantic schemas

Defined in `curatorx/models/schemas.py`.

### Lens and persona

| Model | Key fields |
|-------|------------|
| `Lens` | `lens_id`, `lens_name`, `description`, `created_at` |
| `LensCreate` | `lens_id`, `lens_name`, `description` |
| `ActiveLensUpdate` | `lens_id` |
| `PersonaMetrics` | `curator_name`, `val_bro_prof`, `val_dipl_snark`, `val_pass_auto` |

### Chat (lens-aware)

| Model | Key fields |
|-------|------------|
| `ChatRequest` | `message`, `session_id`, **`lens_id`** (optional) |
| `ChatMessage` | `id`, `role`, `blocks`, **`lens_id`** |
| `ChatMessageBlock` | `type`, `content`, `items`, `action`, `payload` |

### Titles and actions

| Model | Purpose |
|-------|---------|
| `TitleCard` / `TitleDetail` | Card and detail page payloads |
| `PreferenceSignal` | Taste signals; optional `lens_id` |
| `ActionConfirmRequest` | Confirmation token execution |

---

## Entity relationships

```mermaid
erDiagram
    curation_lenses ||--o{ chat_sessions : scopes
    curation_lenses ||--o{ chat_messages : filters
    curation_lenses ||--o{ lens_taste_profile : weights
    curation_lenses ||--o{ interaction_telemetry : tracks
    curation_lenses ||--o{ agent_blueprints : schedules
    library_items ||--o| embeddings : has
    chat_sessions ||--o{ chat_messages : contains
    curation_lenses {
        text lens_id PK
        text lens_name
    }
    chat_messages {
        text id PK
        text session_id FK
        text lens_id
    }
    lens_taste_profile {
        text lens_id FK
        text cluster_tag
        real weight
    }
    curator_persona_metrics {
        text metric_id PK
        text curator_name
    }
```

---

## Related documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — sync and chat data flows
- [DESIGN.md](DESIGN.md) — block schema and API usage
- [curatorx_prd.md](curatorx_prd.md) — product source spec
