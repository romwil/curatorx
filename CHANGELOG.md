# Changelog

All notable changes to CuratorX are documented in this file.

## [1.0.0] — 2026-07-12

Community Applications–ready release: single chat workspace, durable library sync jobs, and Unraid/Docker Hub images.

### Added
- Durable job state under `DATA_DIR/jobs_state.json` — sync jobs survive process/container restarts; interrupted `running`/`queued` jobs are marked failed with a clear recovery message
- In-repo wiki under [`docs/wiki/`](docs/wiki/) (Home, Installation, Unraid, Configuration, Library Sync, Multi-User, Seerr, Troubleshooting, FAQ)
- Canonical [`docs/FAQ.md`](docs/FAQ.md)
- Multi-arch Docker Hub tags: `romwil/curatorx:1.0.0`, `:1.0`, `:latest` (amd64 + arm64)

### Changed
- Status dock prefers live sync phase / counts / `%` over persona flavor text
- `/sync` slash command uses a friendly “Library sync queued…” message (no raw job ids)
- FastAPI startup migrated to lifespan context manager
- Documentation rewritten for the **single workspace** product (removed dual Turnstyle/Immersive and Phase shipping language)

### Fixed
- Restart no longer leaves the UI believing a sync is still running with no recovery path

## [0.1.0] — prior

Initial public redesign: chat workspace, Seerr connector hooks, optional multi-user auth, reviews, and Unraid template.
