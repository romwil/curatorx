# CuratorX — Design Document

Product principles, dual UI modes, lens isolation UX, agent behavior, and API design for CuratorX Phase 1. Items marked **Future** are planned but not fully shipped.

---

## Product principles

1. **Intent-aware, not averaged** — Taste lives in **curation lenses**, not one global profile. Casual watches must not poison curated study lanes.

2. **Chat-first** — The curator conversation is the primary loop. Settings, sync, and title detail support the chat.

3. **Telescope, don't navigate** — **Turnstyle** handles quick intents; **Immersive** expands for deep work. Same SPA, smooth CSS transitions.

4. **Explain the “why”** — Every title card carries a `recommendation_reason`.

5. **Sovereign identity** — Name your curator; tune persona sliders without redeploying.

6. **Confirm before changing the fleet** — Radarr/Sonarr mutations always require explicit confirmation.

7. **Bring your own provider** — LLM and embeddings are configurable; Ollama on the homelab is first-class.

8. **Homelab pragmatism** — Single container, SQLite, no mandatory cloud beyond TMDB and your chosen LLM.

---

## Dual UI: Turnstyle vs Immersive

CuratorX serves both modes from one React application (`frontend/src/App.jsx`).

### Turnstyle widget state

Designed for **zero-friction intent entry**:

| Element | Behavior |
|---------|----------|
| **Command lane** | Centered borderless input, `font-mono`, auto-focus on load |
| **Lens prefix** | Persistent active lens indicator, e.g. `⧉ [General] > _` |
| **Thoughtstream feed** | Vertical activity log (sync, jobs) max ~320px, internal scroll |
| **Expansion triggers** | Hotkey, `/expand` token, or viewport card click |

Turnstyle is the default entry point for homelab users who want “ask one thing and go.”

### Immersive viewport state

Designed for **deep analytical curation**:

| Region | Width | Contents |
|--------|-------|----------|
| **Sidebar** | 240px fixed | Lens switcher, integration status, settings, job pulse (`.agent-pulse`) |
| **Chat sandbox** | ~45% | Message thread **filtered by active `lens_id`** |
| **Visual array** | ~55% | Title card clusters by trope, genre, or fingerprint |

### Visual state tokens

| Token | Meaning |
|-------|---------|
| `.lens-active` | Active lens — theme accent shift for at-a-glance context verification |
| `.explicit-lock` | Taste cluster locked against telemetry drift |
| `.agent-pulse` | Background job state: idle / running / error |

---

## Lens isolation UX

### User mental model

A **lens** is a taste sandbox — like separate playlists for “comfort rewatch” vs “director study.” Switching lenses changes:

- Which chat messages appear in history
- Which taste weights apply (`lens_taste_profile`)
- Which telemetry bucket receives future events (**Future** full ingestion)

### Default and custom lenses

- **`general`** — seeded at install; default active lens.
- **Custom lenses** — created in Settings or `POST /api/lenses` with URL-safe `lens_id`.

### Cross-contamination firewall

Watch completions and chat signals under lens A do not update taste weights for lens B unless:

- The user explicitly bridges contexts (**Future**), or
- A cluster has `explicit_lock = 0` and shared global preference facts apply (global `preference_facts` remain cross-lens today).

### API contract

```json
POST /api/chat
{
  "message": "Find neo-noir gaps",
  "session_id": "optional-uuid",
  "lens_id": "general"
}
```

Response includes `lens_id` on the assistant message. History queries use the same filter server-side.

---

## Persona tuning UX

Configured in **Settings** (`/config`) and stored in `curator_persona_metrics`:

| Slider | Field | Low (0.0) | High (1.0) |
|--------|-------|-----------|------------|
| Vocabulary | `val_bro_prof` | Bro | Professorial |
| Tone | `val_dipl_snark` | Diplomatic | Snarky |
| Autonomy | `val_pass_auto` | Passive | Autonomous |

**Curator name** updates greetings, page title, and LLM system prompt via `build_system_prompt()` — no container restart required.

---

## User journeys

### Onboarding

```mermaid
flowchart TD
    Start[Open :8788] --> Config[/config]
    Config --> Plex[Test Plex sections]
    Config --> Persona[Name curator + sliders]
    Config --> LLM[Configure BYOP or Ollama]
    Config --> Save[Save settings]
    Save --> Chat[Chat /]
    Chat --> Lens[Confirm active lens]
    Chat --> Sync[Sync library]
    Sync --> Ready[Curate]
```

### Genre exploration (lens-scoped)

1. User selects **Director Studies** lens (or stays on `general`).
2. Sends: "Explore neo-noir based on what I love."
3. Agent calls `explore_genre` / `search_library` with lens-aware preference context.
4. Cards appear inline; user expands via Turnstyle viewport or Immersive array.
5. Dismissals record preference signals; adds go through confirmation flow.

### Gap finding, watch tonight, purge

Same tool flows as Phase 0 — see agent catalog below. Purge remains advisory; *arr remove requires confirmation.

---

## UI design system

Dark **cinematic dashboard** in `frontend/src/styles.css`:

| Token | Value | Usage |
|-------|-------|-------|
| `--bg` | `#0b0d12` | Page background |
| `--surface` | `#141925` | Cards, panels |
| `--accent` | `#6ea8ff` | Links, buttons |
| `--radius` | `16px` | Containers |

Typography: **Inter** with system fallback; Turnstyle command lane uses monospace.

---

## Message block schema

Defined in `curatorx/models/schemas.py`.

| `type` | Fields | Purpose |
|--------|--------|---------|
| `text` | `content` | Prose reply |
| `title_cards` | `items: TitleCard[]` | Inline posters |
| `action_prompt` | `action`, `payload` | UI actions (`open_viewport`) |

Assistant messages may include **`lens_id`** at the message level for client state sync.

---

## Agent tool catalog

Registered in `curatorx/agent/tools.py`. System prompt includes persona metrics and lens-scoped `preference_context()`.

| Tool | Purpose |
|------|---------|
| `search_library` | Semantic + keyword search over owned titles |
| `find_collection_gaps` | TMDB discover minus owned IDs |
| `recommend_hidden_gems` | High-rated TMDB titles not owned |
| `suggest_purge_candidates` | Large, unwatched, low-taste items |
| `remember_preference` | Save explicit taste fact |
| `add_to_radarr` / `add_to_sonarr` | Return confirmation token |
| `remove_from_arr` | Return confirmation token |
| `get_title_detail` | Deep dive on one title |
| `explore_genre` | Genre browse with optional missing titles |
| `what_to_watch_tonight` | Low view-count or mood search |
| `analyze_watch_patterns` | Library habit stats |

### Fallback agent (no LLM)

Keyword routing to tools when no provider is configured — same heuristics as Phase 0.

---

## BYOP LLM providers

Implemented in `curatorx/agent/providers/__init__.py`:

| Provider | Protocol |
|----------|----------|
| `openai_compatible` | OpenAI-compatible chat completions |
| `ollama` | Same protocol; default `localhost:11434` |
| `anthropic` | Anthropic Messages API |

Embeddings: OpenAI-compatible or deterministic hash fallback.

---

## Confirmation token pattern

Unchanged: propose → token (600s TTL) → confirm → execute. See [ARCHITECTURE.md](ARCHITECTURE.md).

---

## API surface (Phase 1 additions)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/lenses` | List lenses |
| GET | `/api/lenses/active` | Active lens |
| PUT | `/api/lenses/active` | Set active lens |
| POST | `/api/lenses` | Create lens |
| PUT | `/api/lenses/{lens_id}` | Update lens |
| GET | `/api/persona` | Persona metrics |
| PUT | `/api/persona` | Update persona |
| GET | `/api/system-config` | Config key-values |
| PUT | `/api/system-config` | Update config |

Chat endpoints accept optional **`lens_id`**. Full list in [WEB_UI.md](WEB_UI.md).

---

## Related documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — system context and data flows
- [DATA_MODEL.md](DATA_MODEL.md) — schema reference
- [curatorx_prd.md](curatorx_prd.md) — source PRD
