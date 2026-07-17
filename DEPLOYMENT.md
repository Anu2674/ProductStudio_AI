# Deployment Guide

## Local development (Docker Compose)

Prerequisites: Docker Desktop.

```bash
cp .env.example .env
docker compose up --build -d db redis backend frontend
```

This brings up 4 services:

| Service | Container port | Host port (this repo's default) | Notes |
|---|---|---|---|
| `db` (Postgres 16) | 5432 | 5434 | Remapped because 5432 is commonly already in use on dev machines |
| `redis` | 6379 | 6381 | Remapped for the same reason |
| `backend` (FastAPI) | 8000 | 8001 | Swagger UI at `/docs` |
| `frontend` (React dev server) | 5173 | 5174 | |

If your machine has nothing else bound to the standard ports, feel free to change these back to `5432:5432` / `6379:6379` / `8000:8000` / `5173:5173` in `docker-compose.yml`.

Run migrations once the containers are up:

```bash
docker compose exec backend alembic upgrade head
```

Verify:

```bash
curl http://localhost:8001/health
```

Then open http://localhost:5174 and register a user through the UI.

## Environment variables

Copy `.env.example` to `.env` at the repo root — this is consumed by `docker-compose.yml` and passed into the `backend` and `worker` containers.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy connection string for Postgres |
| `SECRET_KEY` | JWT signing secret — **replace the dummy value before any real deployment** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token lifetime |
| `UPLOAD_DIR` | Where uploaded images and generation results are stored (mounted as a Docker volume) |
| `MAX_UPLOAD_SIZE_MB` | Upload size limit enforced by the image service |
| `REDIS_URL` | Used both for the RQ job queue and by the worker |
| `AI_SERVICE_URL` | Where the backend reaches the AI inference microservice |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Postgres container credentials |

`ai-service/.env.example` holds a separate set of variables (model checkpoint paths, device) for the inference microservice — see below.

## The AI inference service (SAM2 + SDXL/ControlNet) — GPU required

`ai-service/` is a **separate deployable** from the main backend. It is not started by the default `docker compose up` command above because it declares a GPU device reservation (`deploy.resources.reservations.devices` in `docker-compose.yml`) and needs an NVIDIA GPU + the NVIDIA Container Toolkit on the host.

**This dev machine has no GPU.** The service's API layer (FastAPI routes, request/response contracts) is fully implemented and unit-tested with a fake pipeline standing in for the real models. The real SAM2/SDXL model-loading code exists in `ai-service/app/pipelines/` but has not been exercised end-to-end locally.

To actually run it:

1. Provision a machine with an NVIDIA GPU (8GB+ VRAM) and the NVIDIA Container Toolkit — e.g. a RunPod or Vast.ai on-demand GPU instance (~$0.20–0.80/hr for something like an RTX 3090/4090).
2. Copy `ai-service/.env.example` to `ai-service/.env` and set the real model paths / HuggingFace model IDs.
3. `docker compose up --build ai-service` on that machine (or add it to the same compose stack if the whole thing is deployed together on a GPU host).
4. Point the backend's `AI_SERVICE_URL` at that machine's address.
5. Shut the GPU instance down when not actively testing/demoing — this is the only part of the stack with a meaningful ongoing cost.

## Production deployment notes

- Put `backend`, `worker`, `db`, `redis`, and `frontend` behind a reverse proxy (e.g. Nginx or a cloud load balancer) with TLS termination — none of that is configured in this repo's Compose file, which is dev-oriented.
- Set a real, secret `SECRET_KEY` and rotate it if it's ever exposed.
- Point `UPLOAD_DIR` at a persistent volume (or migrate `StorageService` to S3/MinIO — it's already abstracted behind that interface for exactly this reason).
- Run `alembic upgrade head` as a release step, not manually, in any real deployment pipeline.
- The `worker` service (RQ) must run continuously — it is a long-running process (`rq worker`), not something that starts and stops per request.
