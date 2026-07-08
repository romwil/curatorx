# Docker / Unraid

## Mac (Homebrew)

`brew install docker` installs only the **Docker CLI**. It does not install Compose, Buildx, or a container runtime. Without those, `docker compose up -d --build` fails with errors like `unknown shorthand flag: 'd' in -d` (the CLI treats `compose` as invalid and misparses flags).

Choose **one** runtime:

### Option A — Docker Desktop (GUI)

```bash
brew install --cask docker
open -a Docker
```

Wait until the whale icon in the menu bar is steady, then:

```bash
docker compose version
cd /path/to/mediacurator
cp .env.example .env   # if you have not already
docker compose up -d --build
```

### Option B — Colima (CLI, no Docker Desktop)

```bash
brew install colima docker-compose
colima start
docker context use colima   # if `docker info` still cannot connect
```

Homebrew’s `docker-compose` formula is a **CLI plugin**. Tell the Docker client where to find it (once per user):

```bash
mkdir -p ~/.docker
cat > ~/.docker/config.json << 'JSON'
{
  "cliPluginsExtraDirs": [
    "/opt/homebrew/lib/docker/cli-plugins"
  ]
}
JSON
```

On Intel Macs, use `/usr/local/lib/docker/cli-plugins` instead of `/opt/homebrew/...`.

Verify:

```bash
docker compose version
docker info | head -5
```

Then run MediaCurator:

```bash
cd /path/to/mediacurator
cp .env.example .env   # if you have not already
docker compose up -d --build
```

After reboot, start the VM again: `colima start` (or `brew services start colima`).

Open `http://localhost:8788`.

## Docker Compose (all platforms)

```bash
cp .env.example .env
docker compose up -d --build
```

Open `http://localhost:8788`.

## Unraid

Install from the Community Applications template (`templates/mediacurator.xml`) or add manually:

- **Port:** 8788
- **Config path:** `/mnt/user/appdata/mediacurator/config` → `/config`

Seed optional environment variables for Plex, *arr, TMDB, and LLM keys on first run.

## Data layout

| Path | Contents |
|------|----------|
| `/config/settings.json` | User settings |
| `/config/mediacurator.db` | Library index, chat, preferences, embeddings |

## Resources

- LLM via Ollama: allocate RAM on the Unraid host for your chosen model.
- Library sync: CPU-bound during TMDB enrichment; runs as a background job.
