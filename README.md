# ProductStudio AI

An AI-powered product photography platform for e-commerce sellers: upload a raw product photo and get an automatic background removal, an AI-regenerated studio or lifestyle scene, automated image quality scoring, and generated marketing copy — all through a full-stack, multi-service application.

Built to demonstrate production backend engineering and applied computer vision together: a typed FastAPI service layer, an async job queue, and a dedicated GPU inference microservice running real segmentation and diffusion models, not a mockup.

## What it does

1. Upload one or more product photos into a project.
2. Segment the product foreground with **SAM2** (Meta's Segment Anything Model 2) to get a clean, transparent cutout.
3. Regenerate the background from a text prompt with **SDXL inpainting + ControlNet**: the SAM2 mask is used as the inpaint mask so the product region is never repainted, Canny-edge ControlNet conditioning keeps the diffusion from hallucinating structure across the product silhouette, and the product pixels are composited back from the original so they stay pixel-faithful.
4. Every generated photo automatically runs through an **OpenCV enhancement pipeline** (white balance, CLAHE lighting/contrast correction, sharpening) and is scored across 7 quality dimensions (sharpness, lighting, contrast, resolution, background cleanliness, product visibility, composition) before it's shown as done.
5. Generate marketing copy (title, description, feature bullets, social caption, SEO keywords) from the product image and metadata.
6. Track generation history, quality trends, and storage usage on a per-project analytics dashboard, and bulk-download finished assets as a zip.

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
              │  PostgreSQL   │   │    Redis      │  async job queue
              └───────────────┘   └───┬───────────┘
                                       │ enqueues
                                ┌──────▼───────────┐
                                │   Worker            │  process_generation job:
                                │  (backend image)   │  enhance + assess quality
                                └──────┬─────────────┘
                                       │ HTTP
                                ┌──────▼───────────────┐
                                │   AI Inference Service │  separate microservice,
                                │   (GPU box)            │  SAM2 + SDXL / ControlNet
                                └────────────────────────┘
```

**Why this shape:**
- The **AI inference service is a separate deployable** from the backend so the GPU-hungry SAM2/SDXL code can be scaled and deployed independently of the API — the backend talks to it over plain HTTP, never imports it directly.
- **Redis-backed async processing** decouples the slow part (image generation, seconds-to-minutes) from the request/response cycle.
- **PostgreSQL** holds everything relational and durable: users, projects, images, generations, marketing content, and their ownership relationships.
- **Local disk storage is abstracted behind `StorageService`** so it can be swapped for S3/MinIO later without touching any calling code.

## Why each piece of the stack is here

| Technology | Why |
|---|---|
| **FastAPI** | Async-native, typed, auto-generates OpenAPI docs; a natural fit for a service that also talks to a GPU inference backend over HTTP. |
| **React (Vite + TS)** | Standard SPA choice for the upload/dashboard/analytics UI. |
| **PostgreSQL** | Real relational data — users own projects, projects own images and generations, everything needs joins and referential integrity. |
| **Redis** | Backs the async job queue for slow generation work, keeping the API responsive. |
| **SAM2** | A real, current segmentation model (`segment-anything-2`) for automatic product foreground extraction — not hand-rolled thresholding. |
| **SDXL inpainting + ControlNet** | An open, controllable diffusion stack. Inpainting confines regeneration to the background via the SAM2 mask; Canny-edge ControlNet conditioning keeps the product silhouette intact. |
| **OpenCV** | Classical CV for the enhancement pipeline and the 7-metric quality scorer, alongside the generative pipeline. |
| **Docker Compose** | Standard local/single-host deployment story. |

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
│   │   └── jobs/           background job(s)
│   ├── alembic/            versioned migrations
│   └── tests/              pytest suite (43 tests)
├── ai-service/       Separate FastAPI microservice: SAM2 + SDXL-inpaint/ControlNet pipelines
│   └── app/pipelines/     sam2_pipeline.py, sdxl_inpaint_pipeline.py
├── notebooks/        Colab notebook to run the real pipeline on a free GPU
├── frontend/         React (Vite + TS): auth, dashboard, project detail, analytics
├── docker-compose.yml
└── ROADMAP.md
```

## Running it locally

```bash
cp .env.example .env
docker compose up --build
```

Backend: http://localhost:8001 (Swagger UI at `/docs`). Frontend: http://localhost:5174.

See [DEPLOYMENT.md](DEPLOYMENT.md) for the full deployment guide.

## Testing

- **Backend:** `cd backend && pytest -v` — 43 tests covering auth, project/image/generation CRUD and ownership enforcement, the OpenCV enhancement and quality-assessment services, the async worker job, marketing content generation, asset downloads, analytics, and one full end-to-end integration test.
- **AI service:** `cd ai-service && pytest -v` — 15 tests covering the segmentation and generation pipelines.
- **Frontend:** `cd frontend && npm run test` — Vitest + React Testing Library, covering auth-gated routing.

## AI pipeline

The inference service supports two modes via `PIPELINE_MODE`:

- **`mock`** — a lightweight image-processing fallback used for local development and CI without a GPU.
- **`real`** — the full SAM2 segmentation + SDXL inpainting / ControlNet generation pipeline. Needs a CUDA GPU with ~10–12 GB VRAM (a Colab T4 works; `LOW_VRAM=true` trades speed for VRAM on smaller GPUs).

## Evaluation results

Measured on a Tesla T4 GPU against 19 real product photos with hand-labelled segmentation ground truth and real text prompts.

| Metric | Result | What it measures |
|---|---|---|
| Segmentation IoU (median) | **0.74** | SAM2 mask accuracy vs. hand-labelled ground truth |
| CLIP score | **29.1** | text-prompt alignment of the generated background |
| Product SSIM | **0.98** | product preserved unchanged while the background regenerates |
| Product LPIPS | **0.04** | perceptual distortion on the product region (near zero) |
| Generation latency | **24.5 s/image** | SDXL inpaint + ControlNet, Tesla T4, warm |

## Status

Full-stack platform (auth, projects, images, async job processing, Postgres, Docker, OpenCV enhancement/quality scoring, frontend) is complete and working. The SAM2 + SDXL-inpaint + ControlNet pipeline is implemented, wired in behind `PIPELINE_MODE=real`, and evaluated end to end on a real GPU run — see Evaluation results above.
