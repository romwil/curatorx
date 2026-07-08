Here is the consolidated, production-ready Unified Product Requirement Document (PRD). This version has been refactored specifically for your existing repository pattern. It shifts the "Turnstyle Widget" from a standalone desktop concept into an integrated overlay framework that streams out of your running web container, and explicitly maps out where each architectural enhancement hooks into your actual backend and frontend file structure.

Product Requirement Document (PRD)
Project CuratorX: The Intent-Aware Media Ecosystem
Version 2.5 (Production & Codebase-Anchored Implementation Guide)

1. Product Vision & Value Proposition

CuratorX transforms traditional self-hosted media automation from a reactive, rule-based request downloader into an intent-aware, context-isolated curation companion. Modern media setups suffer from monolithic profile bias; they treat user telemetry as a single flat history timeline, leading to context contamination where a casual, late-night background watch shifts recommendations or automated grabs away from intentional discovery goals.

CuratorX solves this by injecting high-dimensional vector curation sandboxed inside cognitive boundaries, delivered through a standard container application. The browser experience dynamically telescopes between a zero-friction, fast-access overlay interface (The Turnstyle Widget state) and a deep immersive hub, powered by autonomous background workers synchronized with the local homelab architecture.

1. Core Subsystems & Cognitive Architecture

2.1 Curation Lenses (The Anti-Monolith Framework)
The engine completely discards global taste averaging. All user conversations, data telemetry, and media evaluation loops must be strictly sandboxed within explicit execution containers identified by a mandatory lens_id.

Lens Isolation Engine: Execution contexts act as hard algorithmic walls protecting distinct mental paradigms (e.g., Cinematography & Director Studies, 70s Exploitation, Homesteading & Craft Production).

Asymmetric Signal Weighting: Ingestion pipelines process implicit telemetry (watch completions) and explicit interactions (text chat) with varying mathematical modifiers depending on the operational rules of the active Lens.

Cross-Contamination Firewall: Telemetry generated under a designated casual lens cannot alter or drift vector dimensions or taste weights belonging to an academic or highly curated study Lens unless explicit bridge authorization is given by the user.

2.2 Sovereign Identity Configuration & Dynamic Persona Tuning
The agent companion is fluidly customized by the host user. It updates its behavioral characteristics and application branding without requiring redeploys or service restarts.

Dynamic Identity Prompting: During the launch sequence, specifying the agent's name triggers a centralized state rewrite that cascades across LLM system prompts, application titles, and interface greetings globally.

Behavioral Sliders: Tone control maps human personas to floating-point metrics (0.0 to 1.0) recorded in the system database:

Vocabulary Density: Bro (0.0) to Professorial (1.0)

Interaction Friction: Diplomatic (0.0) to Snarky (1.0)

Automation Autonomy: Passive (0.0) to Autonomous (1.0)

Hot-Reload Prompt Compilation: The LLM compilation loop intercepts conversational payloads and prepends a structured system context constructed on the fly by reading these configuration and metric tables.

1. Integrated UI/UX Layout Strategy

The entire user interface is served from the central Vite/React single-page application. Instead of forcing a hard platform separation, the interface toggles smoothly between two primary operational view states.

3.1 The Web-Delivered "Turnstyle" Widget State
Designed to load instantly inside the browser view with minimal layout friction, functioning as a lightweight keyboard-driven lane.

The Command Lane: A centered, borderless text input field adopting an unstyled high-contrast monospace typeface (font-mono). It automatically grabs browser focus state on initialization. A persistent visual prefix indicates the current active Lens (e.g., ⧉ [Director Studies] > _). It handles shorthand terminal piping or raw natural language intents.

The Thoughtstream Feed: A minimal, high-density dashboard vertical stack appearing beneath the input line. It restricts overall vertical displacement to a maximum height of 320px with internal overflow scroll containment. It registers background engine processing events with clear activity icons and relative timestamps (e.g., Syncing Plex... 2m ago).

Fluid Scaling Trigger: Executing a core hotkey combination, typing a generic expansion token, or clicking the view card transitions the compact presentation layer smoothly into the full screen viewport using CSS transition frameworks.

3.2 The Immersive Viewport State
The deep-dive analytical view maximizing layout workspace efficiency.

Sidebar Matrix Layout (240px Fixed Width): Contains persistent lens switches, integrations status arrays, configuration portals, and automation diagnostics.

The Conversational Context Sandbox (Left Pane - 45% Space): Dedicated historical message thread logging associated only with the active lens_id, complete with a bottom-docked input tray.

Visual Fingerprinting Array (Right Pane - 55% Space): Replaces basic table rows with organic clusters. Media items are organized visually by narrative tropes, stylistic properties, and directorial fingerprints. Clicking titles executes local streaming via backend integrations.

1. Technical Database Migrations

To add cognitive separation, metadata validation states, and slider parameters to the existing application database tier, integrate the following structures into mediacurator/library/db.py:

SQL
-- Core Configuration & Fluid Environment Strings
CREATE TABLE IF NOT EXISTS curator_system_config (
    config_key TEXT PRIMARY KEY,
    config_value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Real-time Validation States for External Services
CREATE TABLE IF NOT EXISTS service_integrations (
    service_name TEXT PRIMARY KEY, -- 'plex', 'radarr', 'sonarr', 'tmdb'
    base_url TEXT,
    api_token_encrypted TEXT,
    connection_status TEXT DEFAULT 'unverified',
    last_tested_at DATETIME
);

-- Dynamic System Persona Tuning Coordinates
CREATE TABLE IF NOT EXISTS curator_persona_metrics (
    metric_id TEXT PRIMARY KEY DEFAULT 'current_profile',
    curator_name TEXT DEFAULT 'Curator',
    val_bro_prof REAL DEFAULT 0.5,
    val_dipl_snark REAL DEFAULT 0.5,
    val_pass_auto REAL DEFAULT 0.5,
    last_modified DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Isolated Cognitive Walls for Media Contexts
CREATE TABLE IF NOT EXISTS curation_lenses (
    lens_id TEXT PRIMARY KEY,
    lens_name TEXT NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Taste Vectors Separated strictly by Active Lens Mapping
CREATE TABLE IF NOT EXISTS lens_taste_profile (
    lens_id TEXT NOT NULL,
    cluster_tag TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    explicit_lock INTEGER DEFAULT 0, -- 1 blocks automatic telemetry updates
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (lens_id, cluster_tag),
    FOREIGN KEY (lens_id) REFERENCES curation_lenses(lens_id)
);

-- Deep Telemetry Tracking with Context Identification
CREATE TABLE IF NOT EXISTS interaction_telemetry (
    id TEXT PRIMARY KEY,
    title_id TEXT NOT NULL,
    lens_id TEXT NOT NULL,
    source TEXT NOT NULL,          -- 'chat_thread', 'tautulli_webhook', 'widget_input'
    event_type TEXT NOT NULL,      -- 'watch_abandoned', 'watch_complete', 'deep_query'
    watch_duration_seconds INTEGER DEFAULT 0,
    completion_percentage REAL DEFAULT 0.0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lens_id) REFERENCES curation_lenses(lens_id)
);

-- Automated Task Blueprints for Engine Schedules
CREATE TABLE IF NOT EXISTS agent_blueprints (
    blueprint_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cron_schedule TEXT NOT NULL,   -- Crontab notation string
    active_lens_id TEXT,
    instructions_json TEXT,        -- Serialized instructions dictionary
    is_enabled INTEGER DEFAULT 1,
    last_run_status TEXT,
    last_run_timestamp DATETIME,
    FOREIGN KEY (active_lens_id) REFERENCES curation_lenses(lens_id)
);
5. Architectural Codebase Mapping for Cursor
When generating code files, modifying logic patterns, or linking API responses, target these exact modules inside your repository:

├── frontend/
│   └── src/
│       ├── App.jsx                       <- Global application view state, scaling transitions
│       ├── api/client.js                 <- Integration test handshakes & dynamic configuration routes
│       ├── components/
│       │   ├── TurnstyleViewport.jsx     <- Monospace command line widget view overlay implementation
│       │   └── ChatThread.jsx            <- Isolated chat interface bound tightly to active LensID
│       └── pages/
│           └── ConfigPage.jsx            <- Onboarding wizard cards & interactive behavior slider matrix
└── mediacurator/
    ├── agent/
    │   ├── curator.py                    <- System prompt interpolation via persona metric rows
    │   └── tools.py                      <- Context-aware tool calls and automation piping
    ├── connectors/
    │   ├── plex.py, radarr.py, sonarr.py <- Active infrastructure handshakes & payload validation
    │   └── tmdb.py                       <- Extended cluster metadata parsing loops
    ├── library/
    │   └── db.py                         <- Migration steps, SQLite schema mounts, isolation query filters
    ├── models/
    │   └── schemas.py                    <- Pydantic validation structures matching the lens/metric tables
    └── web/
        ├── app.py                        <- FastAPI core routing engine, handling lens context handshakes
        └── jobs.py                       <- Asynchronous orchestration layer for scheduling agent workflows
6. Scheduled Autonomous Workers & Tactical Blueprints
Background operations are registered directly in the web execution tier (mediacurator/web/jobs.py) and must leverage client configurations stored in the database.

Blueprint 1: The Midnight Scavenger (Obscure Ingestion Engine)

Trigger: Scheduled cron configuration (Default: Daily at 02:00).

Logic: Extracts tags with higher mathematical weight allocations from lens_taste_profile tied to active historical lenses. Searches index connections for rare alternate variants or preservation remasters.

Action: Dispatches matching content identifiers straight into setup downstream download services (*arr) and updates the user widget interface feed.

Blueprint 2: The Library Compactor (Optimization Engine)

Trigger: Scheduled weekly loop intervals.

Logic: Audits files on connected hardware. Removes broken paths, builds missing vectors against metadata index utilities, and flags stale context tracking items for storage archival.

Blueprint 3: The Promptable Pipeline (Dynamic Execution Engine)

Trigger: Event-driven intent phrases intercepted via chat strings.

Logic: Evaluates natural conditional statements configured via prompt inputs (e.g., "Every Thursday check for movies matching director profile criteria").

1. Strategic Verification & Onboarding Logic

To safely move past rigid parameter setups, the setup pipeline in frontend/src/pages/ConfigPage.jsx and mediacurator/web/setup.py applies a real-time validation pattern.

Sovereign Identity Setup: Updates curator_system_config immediately on text mutation. A backend lookup mirrors back dynamic copy adjustments right below the input line.

Asynchronous Service Handshakes: Input configuration cards do not accept passive user updates. Modifying coordinate blocks triggers a route challenge inside mediacurator/web/app.py:

The card enters a read-only loading state while testing live network paths.

Success States: Sets data rows to verified, returns item summaries (e.g., Connected: Found 1,420 Movies), and shifts borders to border-emerald-500.

Error Handlers: Logs explicitly captured failure blocks instead of raw technical trace paths, turning common failures (HTTP 401, Connection Timeouts) into useful interface guidance blocks.

1. System Status Tokens & Visual Feedback States

Lens Activation Token (.lens-active): Tracked contextually inside the main React view tier. Changing the active identity token changes minor layout color properties and component theme highlights, providing immediate visual verification that search spaces and analytics are completely separated.

The Content Lock Toggle (.explicit-lock): Functional interaction switches mapped beside specific cluster groups or media vectors. Setting this metric to 1 preserves value configurations from experiencing variance shifts during ambient user watching trends.

The Job Monitor State (.agent-pulse): Inline tracking dot rendered inside the widget navigation framework. It queries jobs executed in the core runtime loop (jobs.py):

idle: Standard low-contrast styling (slate-800).

running: Pulsing color theme configuration (animate-pulse text-sky-400).

error: Persistent warning configuration (text-rose-500), where direct clicks reveal target failure logs inside diagnostics views.