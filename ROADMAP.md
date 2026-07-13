# ProductStudio AI — Project Roadmap

**Status:** Planning complete, Phase 1 not yet started
**Owner:** Personal project (built on a company laptop, but NOT affiliated with or pushed to any company repo/system)
**Target GitHub:** To be pushed by owner personally once complete — no pushes will be made by the assistant to any git remote, ever, during this project.
**Purpose:** Resume/interview-grade project demonstrating multimodal AI, computer vision, diffusion models, and production backend engineering — for placement interviews.

---

## Ground Rules (Non-negotiable)

1. Nothing from any company app, GitHub org, or company software is touched, referenced, or used in this project.
2. All credentials/API keys used during development are dummy/placeholder values. Real credentials are supplied by the owner only after the project is fully built.
3. No `git push` to any remote is performed by the assistant at any point. The owner pushes to her own personal GitHub herself after reviewing everything.
4. Tech stack stays deliberately scoped to what's listed below — no extra frameworks bolted on just to look impressive. Every technology used must be explainable in a technical interview.

---

## Why These Technologies (quick justification)

| Tech | Why it's here |
|---|---|
| **SAM2** | Real, current computer-vision segmentation model — justifies "product segmentation" and background removal without hand-rolled CV. |
| **SDXL + ControlNet** | Industry-standard open diffusion stack for controllable image generation — justifies "AI product photography" and "diffusion models" resume line. |
| **FastAPI** | Async-native, typed, auto-generates OpenAPI docs — fits a service that talks to a GPU inference backend. |
| **React** | Standard, interview-safe frontend choice for the dashboard/upload UI. |
| **PostgreSQL** | Relational data: users, projects, generation history, metadata — needs real relationships and querying. |
| **Redis** | Caching generation results and prompt-optimization outputs, and backing an async job queue — justifies "responsive image generation" under load. |
| **Docker / Docker Compose** | Standard containerized deployment story; Kubernetes deliberately left optional/excluded unless it earns its place. |
| **OpenCV** | Classical CV for the enhancement pipeline (color correction, sharpening, shadow refinement) — sits alongside the generative side, showing both classical and generative CV. |
| **LLM (prompt optimization + marketing copy)** | One LLM integration reused for two features (prompt refinement and marketing content generation) — avoids stacking multiple AI providers just for variety. |

---

## Realistic Timeline

This is a full platform (CV + diffusion models + full-stack + infra), not a script. Built solo and properly (with real tests, docs, and something that survives interview questioning), this takes **roughly 3–4 weeks of consistent work**, split across the 4 phases below. A single day is enough to plan (this document) and start Phase 1 scaffolding — not to complete the platform.

**GPU cost note:** SAM2 and SDXL+ControlNet inference need a real GPU. Plan is to use a **cloud GPU only during Phase 2 development/testing** (e.g. RunPod/Vast.ai at ~$0.20–0.80/hr), spun up only while actively testing and shut down immediately after — expected total cost for the whole project is roughly **$5–15**, not a recurring bill. Free tiers (Colab/Kaggle GPU) can be used for early experimentation before wiring up the real inference service.

---

## Phase 1 — Foundation (Backend + Frontend Skeleton)

**Goal:** A working, empty-of-AI skeleton that already demonstrates clean backend architecture.

- FastAPI backend: project structure, service layer, repository pattern, environment config, structured logging, centralized error handling, type hints throughout
- PostgreSQL schema: `users`, `projects`, `images`, `generations`, `assets`
- JWT-based authentication APIs
- Image upload API (stores originals, associates with a project)
- React frontend skeleton: routing, auth pages, upload UI, project dashboard shell
- Docker + docker-compose wiring backend + PostgreSQL + Redis (no GPU service yet)
- Auto-generated Swagger/OpenAPI docs

**No AI models in this phase.** Pure backend/frontend plumbing, done properly.

---

## Phase 2 — Core AI Pipeline

**Goal:** The actual computer-vision/generative heart of the resume claims.

- SAM2 integration for product segmentation → background removal → transparent PNG output, with mask editing support
- SDXL + ControlNet integration for photo generation (studio background, lifestyle scene, indoor/outdoor, marketplace-ready), with lighting/angle/scene controls
- Runs as a **separate AI inference service** on the cloud GPU box, called by the FastAPI backend over an internal API — this is what justifies "GPU-accelerated inference" architecturally, not just as a buzzword
- Async job handling (generation takes time) via a queue (Celery or RQ) so the API stays responsive
- Redis caches generation requests/results

---

## Phase 3 — Intelligence Layer

**Goal:** The "smart workflows" layer that turns raw generation into a product.

- LLM-based prompt optimization: refines user prompts, expands product descriptions, generates negative prompts, recommends photography style
- OpenCV-based enhancement pipeline: resolution enhancement, color correction, lighting adjustment, shadow refinement, contrast optimization, sharpening
- LLM-based marketing content generation from image + metadata: titles, descriptions, feature bullets, social captions, SEO keywords
- Image quality assessment: scores sharpness, lighting, composition, background quality, resolution, product visibility — surfaced before download

---

## Phase 4 — Production Polish

**Goal:** What turns a working demo into something "production-ready" on paper and in review.

- React analytics dashboard: generation history, processing status, storage usage, quality scores, recent activity
- Asset management: version comparison, search, organize by project, bulk download
- Pytest suite: auth, upload, generation, prompt optimization, asset management, and integration tests
- Deployment guide, environment configuration docs, architecture + sequence diagrams
- Comprehensive README, final polish pass on error handling and logging

---

## Next Step

Detailed design (PRD, DB schema, API design, folder structure) for **Phase 1** — to be brainstormed and written as its own spec before any code is written.
