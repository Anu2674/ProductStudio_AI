# Phase 1 — Foundation Design

**Date:** 2026-07-13
**Status:** Approved
**Scope:** Backend + frontend skeleton, auth, project/image CRUD, Docker. No AI models in this phase.

---

## Folder Structure

```
ProductStudio AI/
├── ROADMAP.md
├── docs/specs/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/                # config, logging, security, exceptions
│   │   ├── api/v1/               # routers: auth, projects, images
│   │   ├── models/               # SQLAlchemy models
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   ├── repositories/         # DB access layer (repository pattern)
│   │   ├── services/             # business logic (service layer)
│   │   ├── db/                   # session, base
│   │   └── tests/
│   ├── alembic/                  # migrations
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/{pages,components,api,store,routes}/
│   ├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Database Schema (Phase 1)

Only tables needed for this phase's features are created now. `generations` and `assets` tables are added via new Alembic migrations in Phase 2/3, not stubbed out empty ahead of time.

- **users**: `id`, `email` (unique), `hashed_password`, `full_name`, `created_at`
- **projects**: `id`, `user_id` (FK → users), `name`, `description`, `created_at`, `updated_at`
- **images**: `id`, `project_id` (FK → projects), `original_filename`, `storage_path`, `content_type`, `size_bytes`, `uploaded_at`

## Storage

Local disk volume at `/data/uploads/{project_id}/{image_id}.ext`, accessed only through a `StorageService` interface (`save`, `get_path`, `delete`). This lets Phase 2 swap in S3/MinIO-compatible storage later without changing any caller.

## APIs (Phase 1)

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login` → JWT access token
- `GET /api/v1/auth/me`
- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `GET /api/v1/projects/{id}`
- `PATCH /api/v1/projects/{id}`
- `DELETE /api/v1/projects/{id}`
- `POST /api/v1/projects/{id}/images` (upload)
- `GET /api/v1/projects/{id}/images`
- `GET /api/v1/images/{id}`
- `DELETE /api/v1/images/{id}`

All protected routes require a valid JWT via a FastAPI dependency guard. Ownership checks (a user can only access their own projects/images) enforced in the service layer.

## Auth

JWT access tokens (python-jose), bcrypt password hashing (passlib). No refresh tokens in Phase 1 — access token expiry is generous enough for demo purposes; refresh flow can be added later if needed (not required for the resume claims).

## Docker Compose (Phase 1 services)

- `backend` — FastAPI app
- `frontend` — React app
- `db` — PostgreSQL
- `redis` — stood up now per the roadmap's infra plan, but unused by any code until Phase 2 caching lands

## Testing (Phase 1)

Pytest coverage for: auth (register/login/me, invalid credentials, duplicate email), projects CRUD (including ownership enforcement), image upload (valid/invalid file types, size limits), using a test database fixture (SQLite in-memory or a dedicated test Postgres schema).

## Out of Scope for Phase 1

SAM2, SDXL/ControlNet, prompt optimization, enhancement pipeline, marketing content generation, quality assessment, analytics dashboard data, asset versioning — all deferred to Phases 2–4 per `ROADMAP.md`.
