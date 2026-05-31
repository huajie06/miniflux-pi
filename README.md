# miniflux-pi

Self-hosted RSS reader running Miniflux + PostgreSQL on a Raspberry Pi 4.

Remote: `git@github.com:huajie06/miniflux-pi.git`

## Design

```
Mac (dev)                          Pi (prod)
──────────                         ──────────
~/repos/miniflux-local/            ~/repos/miniflux/          (app code)
                                    ~/services/miniflux/      (postgres data)
```

- **App**: Miniflux container (Go binary, port 8080)
- **Database**: PostgreSQL 16 Alpine, data persists outside git repo
- **Import**: Python script reads `rss-feed.yaml` and pushes to Miniflux via API

Categories defined in `rss-feed.yaml`: tech, markets, economy, central-bank, politics, china, asia, world, government, macro.

## Deploy

### First time

```bash
# Copy to Pi
rsync -avz . pi@192.168.68.168:~/repos/miniflux/

# On Pi
cd ~/repos/miniflux
mkdir -p ~/services/miniflux

cp .env.example .env
cp docker-compose.yml.example docker-compose.yml
vi .env                          # set real passwords + MINIFLUX_API_KEY
vi docker-compose.yml            # set same passwords

docker compose up -d
```

Open `http://192.168.68.168:8080/unread` — log in with admin credentials from `.env`.

### Import feeds

1. Create API key in Miniflux UI: Settings → API Keys → Create
2. Add key to `.env`: `MINIFLUX_API_KEY=<key>`
3. Run:

```bash
uv run import-feeds.py
```

Script is idempotent — skips existing feeds, creates missing categories.

###日常运维

```bash
# Update
docker compose pull && docker compose up -d

# Backup
docker exec miniflux-postgres pg_dump -U miniflux miniflux > ~/services/miniflux/backup-$(date +%Y-%m-%d).sql
```

## Files

| File | Purpose |
|------|---------|
| `docker-compose.yml.example` | Container config template (copy to `.yml`, fill in passwords) |
| `.env.example` | Secrets template (copy to `.env`, fill in values) |
| `rss-feed.yaml` | Feed definitions (name, url, category, enabled) |
| `import-feeds.py` | Reads yaml → creates categories + feeds via Miniflux API |
| `pyproject.toml` | Python deps (miniflux, pyyaml) |
| `plan.md` | Detailed deployment plan |
