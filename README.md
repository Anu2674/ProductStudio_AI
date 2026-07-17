# ProductStudio AI

A production-oriented AI product photography platform: e-commerce sellers upload a product photo and get automatic background removal, AI-generated studio/lifestyle photography, OpenCV-based image enhancement, automated quality scoring, and marketing copy generation.

Built as a full-stack, multi-service system (FastAPI + React + PostgreSQL + Redis + a GPU-backed inference microservice) to demonstrate production backend engineering and applied computer vision, not just a model demo.

## What it does

1. Upload one or more product photos into a project.
2. Remove the background with **SAM2** (segmentation) to get a clean, transparent cutout.
3. Generate a new studio/lifestyle/outdoor scene around the product with **SDXL + ControlNet** (Canny-edge conditioning preserves the product's shape while the background, lighting, and scene change).
4. Every generated photo is automatically run through an **OpenCV enhancement pipeline** (white balance, CLAHE lighting/contrast correction, sharpening) and scored across 7 quality dimensions (sharpness, lighting, contrast, resolution, background cleanliness, product visibility, composition) before it's ever shown as "done."
5. Generate marketing copy (title, description, feature bullets, social caption, SEO keywords) from the product image and metadata.
6. Track everything — generation history, quality trends, storage usage — on a per-project analytics dashboard, and bulk-download finished assets as a zip.

## Architecture

```
                      ┌──────────────────────┐
                      │   React Frontend      │  (Vite + TS, JWT auth)
                      └──────────┬────────────┘
                                 │ REST (JSON)
                      ┌──────────▼────────────┐
                      │   FastAPI Backend      │  service layer / repository pattern
                      │  auth, projects, images│
                      │  generations, marketing│
                      │  analytics             │
                      └───┬───────────┬────────┘
                          │           │
              ┌───────────▼──┐   ┌────▼─────────┐
              │  PostgreSQL   │   │    Redis      │  RQ job queue + (future) caching
              └───────────────┘   └───┬───────────┘
                                       │ enqueues
                                ┌──────▼───────────┐
                                │   RQ Worker        │  process_generation job:
                                │  (backend image)   │  enhance + assess quality
                                └──────┬─────────────┘
                                       │ HTTP
                                ┌──────▼───────────────┐
                                │   AI Inference Service │  separate microservice,
                                │   (GPU box)            │  SAM2 + SDXL/ControlNet
                                └────────────────────────┘
```

**Why this shape:**
- The **AI inference service is a separate deployable** from the backend so the GPU-hungry SAM2/SDXL code can be scaled and deployed independently of the API — the backend talks to it over plain HTTP, never imports it directly.
- **Redis + RQ** decouple the slow part (image generation, seconds-to-minutes) from the request/response cycle. The API returns `202 Accepted` immediately with a `pending` generation record; the worker processes it asynchronously and the frontend polls for status.
- **PostgreSQL** holds everything relational and durable: users, projects, images, generations, marketing content, and their ownership relationships.
- **Local disk storage is abstracted behind `StorageService`** so it can be swapped for S3/MinIO later without touching any calling code.

## Request lifecycle: generating a photo

```
User                Frontend            Backend API           Redis/RQ           Worker              AI Service
 │  click "Generate"    │                    │                    │                 │                    │
 ├──────────────────────▶                    │                    │                 │                    │
 │                       │  POST .../generate │                    │                 │                    │
 │                       ├───────────────────▶│                    │                 │                    │
 │                       │                    │ build prompt       │                 │                    │
 │                       │                    │ create Generation  │                 │                    │
 │                       │                    │ (status=pending)   │                 │                    │
 │                       │                    │  enqueue(job) ─────▶                 │                    │
 │                       │  202 + generation  │                    │                 │                    │
 │                       ◀────────────────────┤                    │                 │                    │
 │                       │                    │                    │ dequeue         │                    │
 │                       │                    │                    ├────────────────▶│                    │
 │                       │                    │                    │                 │ mark processing    │
 │                       │                    │                    │                 │  POST /generate ───▶
 │                       │                    │                    │                 │                    │ SAM2/SDXL run
 │                       │                    │                    │                 │  PNG bytes  ◀───────┤
 │                       │                    │                    │                 │ enhance (OpenCV)    │
 │                       │                    │                    │                 │ assess quality       │
 │                       │                    │                    │                 │ save file, mark      │
 │                       │                    │                    │                 │  completed           │
 │  poll GET .../{id}    │                    │                    │                 │                    │
 ├───────────────────────▶───────────────────▶│  (reads DB row) ◀──────────────────────────────────────────┤
 │  status=completed +   │                    │                    │                 │                    │
 │  quality_score        │                    │                    │                 │                    │
 ◀───────────────────────┴────────────────────┘                    │                 │                    │
```

## Why each piece of the stack is here

| Technology | Why |
|---|---|
| **FastAPI** | Async-native, typed, auto-generates OpenAPI docs; natural fit for a service that also talks to a GPU inference backend over HTTP. |
| **React (Vite + TS)** | Standard SPA choice for the upload/dashboard/analytics UI. |
| **PostgreSQL** | Real relational data — users own projects, projects own images and generations, everything needs joins and referential integrity. |
| **Redis + RQ** | Backs the async job queue for slow generation work, keeping the API responsive; positioned to also back response caching later. |
| **SAM2** | Real, current segmentation model for automatic background removal — not hand-rolled thresholding. |
| **SDXL + ControlNet** | Open, controllable diffusion stack; Canny-edge conditioning keeps the product's silhouette intact while regenerating the scene around it. |
| **OpenCV** | Classical CV for the enhancement pipeline and the 7-metric quality scorer — shows both classical and generative computer vision in one project. |
| **Docker Compose** | Standard local/single-host deployment story; Kubernetes deliberately left out since it wouldn't earn its place at this scale. |

## Project layout

```
ProductStudio AI/
├── backend/          FastAPI app (auth, projects, images, generations, marketing content, analytics)
│   ├── app/
│   │   ├── api/v1/        route handlers
│   │   ├── core/           config, security, logging, exceptions, deps
│   │   ├── models/         SQLAlchemy models
│   │   ├── schemas/        Pydantic request/response schemas
│   │   ├── repositories/   DB access layer
│   │   ├── services/       business logic (incl. OpenCV enhancement/quality assessment)
│   │   └── jobs/           RQ background job(s)
│   ├── alembic/            versioned migrations
│   └── tests/              pytest suite (43 tests)
├── ai-service/       Separate FastAPI microservice: SAM2 + SDXL/ControlNet pipelines
├── frontend/         React (Vite + TS): auth, dashboard, project detail, analytics
├── docs/
│   ├── specs/              Phase 1 design spec
│   └── plans/              Phase 1 implementation plan
├── docker-compose.yml
├── ROADMAP.md              4-phase build roadmap
└── DEPLOYMENT.md           local/production deployment guide
```

## Running it locally

See [DEPLOYMENT.md](DEPLOYMENT.md) for the full guide (env vars, Docker Compose, GPU box notes). Quick version:

```bash
cp .env.example .env
docker compose up --build
```

Backend: http://localhost:8001 (Swagger UI at `/docs`). Frontend: http://localhost:5174.

## Testing

- **Backend:** `cd backend && pytest -v` — 43 tests covering auth, project/image/generation CRUD and ownership enforcement, the OpenCV enhancement and quality-assessment services, the async worker job, marketing content generation, asset downloads, analytics, and one full end-to-end integration test.
- **Frontend:** `cd frontend && npm run test` — Vitest + React Testing Library, covering auth-gated routing.

## Status

All 4 planned phases are complete — see [ROADMAP.md](ROADMAP.md) for the phase breakdown. The AI inference service (SAM2/SDXL) is implemented and tested at the API/orchestration layer with a fake pipeline (no GPU in this dev environment); real model execution is intended to run on a cloud GPU box per the deployment guide.
