# Implementation plan for running **Miniflux + PostgreSQL on your Raspberry Pi 4 microSD**, with a future path to move PostgreSQL to Synology.

## Background

- **dev env**: development is done on a Mac
- **deployment: will be on a Raspberry Pi on the same LAN.

**Target Setup**

```text
Raspberry Pi 4
  Docker
  Docker Compose
  Miniflux container
  PostgreSQL container
  Persistent Postgres volume on microSD
  Optional reverse proxy later

Synology
  Backup destination now
  Possible PostgreSQL host later
```

**Phase 1: Prepare The Pi**

1. Create a dedicated directory:

```bash
mkdir -p ~/services/miniflux
cd ~/services/miniflux
```

I’d keep Miniflux under a clear service folder so it’s easy to back up, move, or inspect later.

**Phase 2: Create Docker Compose Setup**

Use a `docker-compose.yml` with two services:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: miniflux-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: miniflux
      POSTGRES_PASSWORD: miniflux
      POSTGRES_DB: miniflux
    volumes:
      - ./postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U miniflux -d miniflux"]
      interval: 10s
      timeout: 5s
      retries: 5

  miniflux:
    image: miniflux/miniflux:latest
    container_name: miniflux
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "8080:8080"
    environment:
      DATABASE_URL: postgres://miniflux:change-this-password@postgres/miniflux?sslmode=disable
      RUN_MIGRATIONS: 1
      CREATE_ADMIN: 1
      ADMIN_USERNAME: admin
      ADMIN_PASSWORD: change-this-admin-password

      POLLING_FREQUENCY: 60
      BATCH_SIZE: 20
      WORKER_POOL_SIZE: 4
      DATABASE_MAX_CONNS: 5
      DATABASE_MIN_CONNS: 1
      CLEANUP_ARCHIVE_READ_DAYS: 30
      CLEANUP_ARCHIVE_UNREAD_DAYS: 90
```

I would eventually pin image versions instead of using `latest`, but for the very first test this is okay. After confirming it works, switch to explicit versions.

**Phase 3: First Startup**

From the Miniflux directory:

```bash
docker compose up -d
docker compose logs -f
```

Then open:

```text
http://pi-ip-address:8080
```

Log in with the admin username/password from the compose file.

After first successful startup, you can remove or set these to `0`:

```yaml
RUN_MIGRATIONS: 1
CREATE_ADMIN: 1
```

Leaving `RUN_MIGRATIONS: 1` is usually fine for upgrades, but `CREATE_ADMIN` is only needed for initial admin creation.

**Phase 4: Basic Hardening**

1. Change all default passwords before starting.
2. Keep Postgres unexposed to the LAN. In the compose above, only Miniflux exposes a port; Postgres does not.
3. Use a strong admin password.
4. Do not expose Miniflux publicly until you add HTTPS/auth strategy via reverse proxy or VPN.
5. If you already use Tailscale/WireGuard, access it through that first.

For LAN-only usage, this is enough to begin.

**Phase 5: Resource Settings**

Start conservative:

```yaml
POLLING_FREQUENCY: 60
BATCH_SIZE: 20
WORKER_POOL_SIZE: 4
DATABASE_MAX_CONNS: 5
CLEANUP_ARCHIVE_READ_DAYS: 30
CLEANUP_ARCHIVE_UNREAD_DAYS: 90
```

After a week, adjust based on behavior:

```text
Feeds feel stale:
  Increase BATCH_SIZE to 50

CPU spikes or Pi feels busy:
  Lower WORKER_POOL_SIZE to 2

You want more article history:
  Increase CLEANUP_ARCHIVE_READ_DAYS to 90 or 180

You use unread as a long-term queue:
  Increase CLEANUP_ARCHIVE_UNREAD_DAYS to 180 or -1
```

**Phase 6: Backups To Synology**. Will come back later, not today.

This is the most important part because you’re using microSD storage.

Create a backup script on the Pi:

```bash
mkdir -p ~/backups/miniflux
```

Example backup command:

```bash
docker exec miniflux-postgres pg_dump -U miniflux miniflux > ~/backups/miniflux/miniflux-$(date +%Y-%m-%d).sql
```

Then copy that to Synology. Options:

```text
rsync over SSH
Synology shared folder mounted on the Pi
Synology Drive
manual copy at first
```

A simple cron schedule:

```bash
crontab -e
```

Run nightly, for example:

```cron
30 3 * * * docker exec miniflux-postgres pg_dump -U miniflux miniflux > /home/pi/backups/miniflux/miniflux-$(date +\%Y-\%m-\%d).sql
```

If you mount a Synology folder, write the backup there directly or `rsync` it after creation.

**Phase 7: Maintenance Routine**

Weekly or monthly:

```bash
docker compose pull
docker compose up -d
docker image prune
```

Before upgrading Miniflux/Postgres, take a backup:

```bash
docker exec miniflux-postgres pg_dump -U miniflux miniflux > ~/backups/miniflux/pre-upgrade.sql
```

For Postgres major upgrades, be more careful. Do not casually jump from `postgres:16` to `postgres:17` without a dump/restore plan.

**Phase 8: Future Migration To Synology PostgreSQL**

When you’re ready:

1. Stop Miniflux on the Pi:

```bash
docker compose stop miniflux
```

2. Dump the Pi database:

```bash
docker exec miniflux-postgres pg_dump -U miniflux miniflux > miniflux-migration.sql
```

3. Start PostgreSQL on Synology.
4. Create a `miniflux` database/user on Synology.
5. Restore the dump into Synology Postgres.
6. Change Pi Miniflux `DATABASE_URL`:

```yaml
DATABASE_URL: postgres://miniflux:password@synology-lan-ip:5432/miniflux?sslmode=disable
```

7. Start Miniflux again:

```bash
docker compose up -d miniflux
```

8. Once verified, stop/remove the old Pi Postgres container, but keep the old data directory for a while.

**My Recommended Order**

1. Install Docker/Compose if needed.
2. Create the compose file.
3. Start Miniflux locally.
4. Import/add feeds.
5. Set up Synology backup within the first day.
6. Run it for a few weeks.
7. Tune polling/history only if needed.
8. Revisit Synology-hosted Postgres after you know Miniflux is worth keeping.

The key thing: don’t over-engineer the first version. Local Postgres on microSD plus real backups is a totally reasonable trial setup.