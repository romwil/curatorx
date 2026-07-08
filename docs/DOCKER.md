# CuratorX — Docker / Unraid

Deploy CuratorX as a single container with a persistent `/config` volume for `settings.json` and `curatorx.db`.

---

## Mac (Homebrew)

`brew install docker` installs only the **Docker CLI**. It does not install Compose, Buildx, or a container runtime. Without those, `docker compose up -d --build` fails with errors like `unknown shorthand flag: 'd' in -d`.

Choose **one** runtime:

### Option A — Docker Desktop (GUI)

```bash
brew install --cask docker
open -a Docker
```

Wait until the whale icon in the menu bar is steady, then:

```bash
docker compose version
cd /path/to/curatorx
cp .env.example .env
docker compose up -d --build
```

### Option B — Colima (CLI, no Docker Desktop)

```bash
brew install colima docker-compose
colima start
docker context use colima
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

Then run CuratorX:

```bash
cd /path/to/curatorx
cp .env.example .env
docker compose up -d --build
```

After reboot: `colima start` (or `brew services start colima`).

Open **http://localhost:8788**.

---

## Docker Compose (all platforms)

```bash
git clone https://github.com/romwil/curatorx.git
cd curatorx
cp .env.example .env
docker compose up -d --build
```

Open **http://localhost:8788**.

Environment variables in `.env` seed first-run settings (Plex, *arr, TMDB, LLM). See [CONFIGURATION.md](CONFIGURATION.md).

---

## Unraid

Install from the Community Applications template (`templates/curatorx.xml` or `unraid/curatorx.xml`) or add manually:

| Setting | Value |
|---------|-------|
| **Port** | 8788 |
| **Config path** | `/mnt/user/appdata/curatorx/config` → `/config` |
| **Image** | Build from repo `Dockerfile` or published image when available |

### Ollama on the Unraid host

Point CuratorX at the host LLM:

```
LLM_PROVIDER=ollama
LLM_BASE_URL=http://host.docker.internal:11434/v1
```

Or use the host LAN IP if `host.docker.internal` is unavailable.

---

## Data layout

| Path | Contents |
|------|----------|
| `/config/settings.json` | Connection settings, LLM config, onboarding flags |
| `/config/curatorx.db` | Library index, embeddings, chat (with `lens_id`), persona, lenses |

Back up the entire `/config` directory before upgrades.

---

## Resources

- **LLM via Ollama** — allocate RAM on the host for your chosen model.
- **Library sync** — CPU/network-bound during TMDB enrichment; runs as a background job.
- **Embeddings** — optional cloud embedding API; hash fallback works offline.

---

## Related documentation

- [ONBOARDING.md](ONBOARDING.md) — first-run wizard
- [ARCHITECTURE.md](ARCHITECTURE.md) — deployment diagram
