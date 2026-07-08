# Product Requirement Document (PRD)

**Project CuratorX: Unified Core Engine & Onboarding Framework**  
**Version 2.7 (Codebase-Anchored Implementation Guide)**

## 1. Product Vision & Value Proposition

CuratorX translates standard media management tools into an intent-aware ecosystem by introducing isolated processing containers called Lenses.

This revision transitions the platform from a flat configuration layout to a step-by-step onboarding wizard. By linking verification events directly to the state engine, validation data (such as library identifiers retrieved from Plex) is immediately mapped to conversational settings, UI choices, and dynamic selection fields.

## 2. Guided Configuration Pipeline (The Multi-Step Wizard)

The single-page view inside `frontend/src/pages/ConfigPage.jsx` is a controlled state machine. The onboarding process uses an interactive step sequence where subsequent parameters remain locked until active verification dependencies are fulfilled.

```
[Step 1: Identity & LLM] ──(Verified)──> [Step 2: Media Core] ──(Sections Parsed)──> [Step 3: App Pipelines]
  ──> [Step 4: Persona] ──> [Step 5: Optional Services] ──> [Main App]
```

### Step 1: Sovereign Identity & BYO LLM Engine

- **Sovereign Personality Input:** Captures `curator_name`, which hooks into the backend setup routine to provide real-time visual variations of the interface voice.
- **OpenAI-Compatible Core Engine Configuration:**
  - `llm_provider`: Selectable menu dropdown (`openai`, `ollama`, `openrouter`, `custom_openai_compatible`).
  - `llm_base_url`: Editable string input (defaults per provider).
  - `llm_api_key`: Masked secret field.
  - `llm_model`: String identifier (e.g., `gpt-4o`, `llama3`, `deepseek-chat`).
- **Onboarding Assistant Context Integration:** When a valid connection is established, a processing window displays hints dynamically using short system instructions.

### Step 2: Media Infrastructure Binding (Dynamic Handshake)

- **Plex Connection Matrix:** `plex_url`, `plex_token`, and **Verify Integration**.
- **Dropdown Selection Mapping:** When `test_plex` returns `ok`, raw inputs collapse and movie/TV section `<select>` dropdowns replace legacy button rows (filtered by `movie` / `show` types).

### Step 3: Automation Framework Linkage (Radarr & Sonarr)

- Card verification with enriched status: e.g. `Connected — Radarr v4.2 | 1,240 Movies Found`.
- Unlocks persona step after both services verify.

### Step 4: Persona

- Behavioral sliders: vocabulary, interaction tone, automation autonomy.

### Step 5: Optional Services

- TMDB, Fanart.tv, Tautulli — skippable before finish.

## 3. Integrated Global Component Viewports

### 3.1 Inline Web Widget State

- **Monospace Entry Lane:** `font-mono` command input with lens prefix (e.g. `⧉ [70s Revenge Studies] > _`).
- **Thoughtstream Feed Window:** Max 320px height, inner scroll, job pulse via `resolveAgentPulse`.

### 3.2 Deep Viewport State

- **Workspace Sidebar (240px):** Lens switcher, integration metrics, job monitor.
- **Context Chat Hub (45%):** Messages scoped to active `lens_id`.
- **Visual Fingerprinting (55%):** Card clusters by narrative themes.

## 4. Technical Database Migrations

LLM connection metadata syncs into `curator_system_config` key-value rows (`llm_provider`, `llm_base_url`, `llm_model`). Additional tables in `curatorx/library/db.py`:

- `service_integrations` — verification status per service
- `curation_lenses` — lens containers
- `curator_persona_metrics` — persona sliders and curator name

## 5. Architectural Codebase Mapping

```
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── api/client.js
│       ├── components/
│       │   ├── TurnstyleViewport.jsx
│       │   └── ChatThread.jsx
│       └── pages/
│           └── ConfigPage.jsx
└── curatorx/
    ├── agent/
    │   ├── curator.py
    │   └── tools.py
    ├── library/
    │   └── db.py
    └── web/
        ├── app.py
        └── setup.py
```
