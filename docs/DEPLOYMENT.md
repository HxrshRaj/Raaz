# Deployment guide

> **Status:** no deployment was performed by the author. Nothing here claims a running public instance. Commands are
> provided to be run by you, and the Compose/Docker/CI files were **authored but not executed** in the build
> environment (no Docker engine, PostgreSQL or Redis was available). `docker compose config` parses.

## Topology

```
Internet → TLS terminator / reverse proxy → web (nginx: static SPA + /api proxy) → api (uvicorn) → PostgreSQL
                                                                             └──→ Redis (optional, rate limits)
```

`docker-compose.yml` provides `db` (postgres:16), `redis` (7), `api` (backend image; runs `alembic upgrade head`
then uvicorn with graceful shutdown) and `web` (nginx serving the Vite build and proxying `/api/`). The web port
(8080) is the only published port.

## First deployment

```bash
cp .env.example .env
#  set POSTGRES_PASSWORD, RAAZ_JWT_SECRET (>= 32 random chars; the API refuses to start in prod otherwise),
#  RAAZ_CORS_ORIGINS=https://your.domain, and optionally an LLM provider + key
docker compose up --build -d
docker compose exec api python -m app.cli train-ml     # optional: enables lead ranking & note tags (about 25 s)
```

* **Migrations** run automatically on API start (`alembic upgrade head`). To run them separately:
  `docker compose run --rm api alembic upgrade head`.
* **Seeding:** the public catalog and RAG corpus seed themselves at startup (idempotent); `python -m app.cli seed` does
  the same on demand. There are no default accounts.
* **Health:** `GET /health` (liveness), `GET /ready` (DB check) — used by the container healthcheck.
* **Graceful shutdown:** uvicorn `--timeout-graceful-shutdown 20`, Compose `stop_grace_period: 30s`, and the job pool is
  shut down on application shutdown.
* **Without PyTorch:** build with `INSTALL_ML=0`; the PyTorch model is simply unavailable, everything else works.
* **Client IPs:** the API runs with `--proxy-headers --forwarded-allow-ips '*'` because only the nginx container can
  reach it. If you publish the API port directly, restrict `--forwarded-allow-ips` to your proxy, or per-IP rate limits
  can be spoofed.

## Configuration

All settings are `RAAZ_*` environment variables (see `.env.example`). Production specifics: `RAAZ_ENV=prod` disables
the OpenAPI docs and the ML workbench (unless enabled explicitly) and enforces a strong JWT secret. Terminate TLS at your
proxy and add a Content-Security-Policy there. Set `RAAZ_METRICS_TOKEN` or keep `/metrics` internal.

## Persistence and backups

| Data | Where | Backup |
|---|---|---|
| Players, investigations, dialogue, boards, accusations | PostgreSQL volume `pgdata` | scheduled `pg_dump`; test restores. A Docker volume is not a backup |
| ML artifacts | volume `artifacts` | reproducible via `train-ml`; no need to back up |
| Nothing else is stateful | – | – |

## Scaling notes

One API process is the intended starting point. For several replicas: use PostgreSQL (done), Redis for the shared rate
limiter (`RAAZ_REDIS_URL`), and move `jobs.submit` to Celery/RQ if agent runs must survive restarts or scale separately
(runs in flight when a process dies stay `running`). See [ARCHITECTURE.md](ARCHITECTURE.md).

## Releases

No release, package publication, tag or push has been made, and none should happen without the owner's explicit
authorization. CI (`.github/workflows/ci.yml`) validates tests, types, migrations on PostgreSQL, the frontend build and
image builds, but pushes nothing.
