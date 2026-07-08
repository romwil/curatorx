# End-to-end UI testing

CuratorX uses [Playwright](https://playwright.dev/) for browser tests against the full stack (FastAPI + built React SPA).

## Quick start

From the repo root with Python dependencies installed (`pip install -e ".[web]"`):

```bash
bash scripts/run-e2e.sh
```

Or step by step:

```bash
cd frontend && npm install && npm run build && cd ..
npm install
npx playwright install chromium
npm run test:e2e
```

Tests start a temporary CuratorX server on **http://127.0.0.1:8788** (override with `E2E_PORT`).

If you already have Docker running on port 8788, Playwright reuses it locally (`reuseExistingServer`).

## What is covered

| Suite | UI mode |
|-------|---------|
| `e2e/chat.spec.ts` | Turnstyle compact + Immersive viewport |
| `e2e/setup-banner.spec.ts` | Incomplete setup banner on `/` |
| `e2e/config-wizard.spec.ts` | 3-step onboarding wizard |
| `e2e/config-maintenance.spec.ts` | Maintenance dashboard |

**21 tests** mock `/api/chat`, `/api/setup/test/*`, and `/api/plex/sections` so CI passes without Anthropic or Plex credentials.

## Live integration (optional)

Against a real Docker stack with credentials configured:

```bash
docker compose up -d
E2E_MOCK_APIS=0 npm run test:e2e:live
```

## CI / full test suite

GitHub Actions runs Python unit tests, frontend build, and Playwright E2E on every push/PR to `main`.

Run the same locally:

```bash
npm test
```

This executes `python -m unittest discover`, `frontend` production build, and Playwright.

## Maintenance

- Prefer `data-testid` attributes for stable selectors (see components under `frontend/src/`).
- Shared mocks live in `e2e/fixtures/api-mocks.ts`.
- Page helpers: `e2e/fixtures/helpers.ts`, `e2e/fixtures/selectors.ts`.
