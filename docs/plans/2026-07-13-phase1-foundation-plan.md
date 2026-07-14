# Phase 1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend + frontend skeleton for ProductStudio AI — auth, projects, image upload, containerized — with no AI models yet.

**Architecture:** FastAPI backend using a layered architecture (API routers → services → repositories → SQLAlchemy models), JWT auth, PostgreSQL via Alembic-migrated schema, local-disk storage behind a swappable `StorageService`. React (Vite + TypeScript) frontend consuming the API via an Axios client with token-based auth guarding routes. Both containerized via Docker Compose alongside Postgres and an as-yet-unused Redis (wired up for Phase 2).

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 16, passlib (bcrypt), python-jose (JWT), pytest + httpx, React 18 + TypeScript (Vite), react-router-dom, axios, Vitest + React Testing Library, Docker / Docker Compose.

## Global Constraints

- No AI models (SAM2/SDXL/ControlNet/LLM) are touched in Phase 1 — out of scope per `docs/specs/2026-07-13-phase1-foundation-design.md`.
- Only `users`, `projects`, `images` tables are created this phase; `generations`/`assets` are added in later phases via new migrations, not stubbed now.
- All secrets in `.env.example` are dummy placeholder values (e.g. `SECRET_KEY=dummy-dev-secret-change-me`) — never real credentials.
- No `git push` to any remote — commits are local only.
- Every route that touches a project or image must enforce that the resource belongs to the requesting user (ownership check in the service layer).

---

### Task 1: Backend Scaffolding & Health Check

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/Dockerfile`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/v1/__init__.py`
- Create: `backend/app/api/v1/router.py`
- Test: `backend/tests/__init__.py`
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Produces: `app.main.app` (the FastAPI instance, used by every later test and by uvicorn); `app.core.config.settings` (a `Settings` instance with `.APP_NAME`, `.DATABASE_URL`, `.SECRET_KEY`, `.ACCESS_TOKEN_EXPIRE_MINUTES`, `.UPLOAD_DIR`); `app.api.v1.router.api_router` (empty `APIRouter`, later tasks call `.include_router(...)` on it).

- [ ] **Step 1: Create the backend directory and dependency file**

Create `backend/requirements.txt`:

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic==2.9.2
pydantic-settings==2.5.2
sqlalchemy==2.0.35
alembic==1.13.3
psycopg2-binary==2.9.10
passlib==1.7.4
bcrypt==4.0.1
python-jose[cryptography]==3.3.0
python-multipart==0.0.9
email-validator==2.2.0
pytest==8.3.3
httpx==0.27.2
```

- [ ] **Step 2: Create a virtual environment and install dependencies**

```bash
cd "backend"
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

Expected: install completes with no errors.

- [ ] **Step 3: Write the failing health check test**

Create `backend/tests/__init__.py` (empty file).

Create `backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient
from app.main import app


def test_health_check_returns_ok():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 4: Run the test to verify it fails**

```bash
cd backend
pytest tests/test_health.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app'` (or similar) — `app.main` doesn't exist yet.

- [ ] **Step 5: Create the config module**

Create `backend/app/__init__.py` (empty file).
Create `backend/app/core/__init__.py` (empty file).

Create `backend/app/core/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "ProductStudio AI"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@db:5432/productstudio"
    SECRET_KEY: str = "dummy-dev-secret-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    UPLOAD_DIR: str = "/data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 15


settings = Settings()
```

- [ ] **Step 6: Create the empty API router aggregator**

Create `backend/app/api/__init__.py` (empty file).
Create `backend/app/api/v1/__init__.py` (empty file).

Create `backend/app/api/v1/router.py`:

```python
from fastapi import APIRouter

api_router = APIRouter()
```

- [ ] **Step 7: Create the FastAPI app with the health endpoint**

Create `backend/app/main.py`:

```python
from fastapi import FastAPI

from app.core.config import settings
from app.api.v1.router import api_router

app = FastAPI(title=settings.APP_NAME)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok"}
```

- [ ] **Step 8: Run the test to verify it passes**

```bash
cd backend
pytest tests/test_health.py -v
```

Expected: PASS (1 passed).

- [ ] **Step 9: Add the Dockerfile and env example**

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create `backend/.env.example`:

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/productstudio
SECRET_KEY=dummy-dev-secret-change-me
ACCESS_TOKEN_EXPIRE_MINUTES=60
UPLOAD_DIR=/data/uploads
MAX_UPLOAD_SIZE_MB=15
```

- [ ] **Step 10: Commit**

```bash
cd ..
git add backend/requirements.txt backend/Dockerfile backend/.env.example backend/app backend/tests
git commit -m "Add FastAPI backend skeleton with health check"
```

---

### Task 2: Database Setup, User Model & Repository

**Files:**
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/core/security.py`
- Create: `backend/app/repositories/__init__.py`
- Create: `backend/app/repositories/user_repository.py`
- Test: `backend/tests/conftest.py`
- Test: `backend/tests/test_user_repository.py`
- Setup: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_create_users_table.py`

**Interfaces:**
- Consumes: `app.core.config.settings` (Task 1).
- Produces: `app.db.base.Base` (declarative base, later models subclass it); `app.db.session.get_db` (FastAPI dependency yielding a `Session`) and `SessionLocal`; `app.models.user.User` (columns: `id`, `email`, `hashed_password`, `full_name`, `created_at`); `app.core.security.hash_password(password: str) -> str`, `verify_password(plain: str, hashed: str) -> bool`, `create_access_token(data: dict, expires_delta: timedelta) -> str`; `app.repositories.user_repository.UserRepository` with `.create(email, hashed_password, full_name) -> User`, `.get_by_email(email) -> User | None`, `.get_by_id(user_id) -> User | None`; test fixtures `db_session` and `client` in `conftest.py` for reuse by all later test files.

- [ ] **Step 1: Create the DB base and session module**

Create `backend/app/db/__init__.py` (empty file).

Create `backend/app/db/base.py`:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

Create `backend/app/db/session.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: Create the User model**

Create `backend/app/models/__init__.py`:

```python
from app.models.user import User  # noqa: F401
```

Create `backend/app/models/user.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 3: Create the security helpers**

Create `backend/app/core/security.py`:

```python
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
```

- [ ] **Step 4: Write the failing repository test**

Create `backend/tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app import models  # noqa: F401  ensures all models register with Base.metadata


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = testing_session_local()
    yield session
    session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _isolate_uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))


@pytest.fixture()
def auth_headers(client):
    def _make(email: str = "owner@example.com", password: str = "StrongPass123"):
        client.post("/api/v1/auth/register", json={"email": email, "password": password})
        response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make
```

Create `backend/app/repositories/__init__.py` (empty file).

Create `backend/tests/test_user_repository.py`:

```python
from app.core.security import hash_password, verify_password
from app.repositories.user_repository import UserRepository


def test_create_and_get_user_by_email(db_session):
    repo = UserRepository(db_session)
    repo.create(email="repo@example.com", hashed_password=hash_password("secret123"), full_name="Repo Test")

    fetched = repo.get_by_email("repo@example.com")
    assert fetched is not None
    assert fetched.email == "repo@example.com"
    assert verify_password("secret123", fetched.hashed_password)


def test_get_by_email_returns_none_when_missing(db_session):
    repo = UserRepository(db_session)
    assert repo.get_by_email("missing@example.com") is None
```

- [ ] **Step 5: Run the test to verify it fails**

```bash
cd backend
pytest tests/test_user_repository.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.repositories.user_repository'`.

- [ ] **Step 6: Implement the UserRepository**

Create `backend/app/repositories/user_repository.py`:

```python
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def create(self, email: str, hashed_password: str, full_name: str | None) -> User:
        user = User(email=email, hashed_password=hashed_password, full_name=full_name)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
```

- [ ] **Step 7: Run the test to verify it passes**

```bash
cd backend
pytest tests/test_user_repository.py -v
```

Expected: PASS (2 passed).

- [ ] **Step 8: Initialize Alembic and add the users migration**

```bash
cd backend
alembic init alembic
```

Edit `backend/alembic/env.py` — add near the top (after existing imports) and replace the `target_metadata = None` line:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from app.db.base import Base
import app.models  # noqa: F401

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
target_metadata = Base.metadata
```

Create `backend/alembic/versions/0001_create_users_table.py`:

```python
"""create users table

Revision ID: 0001
Revises:
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade():
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
```

This migration is verified against real Postgres in Task 6 — tests use `Base.metadata.create_all` against SQLite for speed, not Alembic.

- [ ] **Step 9: Commit**

```bash
cd ..
git add backend/app/db backend/app/models backend/app/core/security.py backend/app/repositories backend/alembic backend/alembic.ini backend/tests
git commit -m "Add DB session, User model, security helpers, and users migration"
```

---

### Task 3: Auth Endpoints (Register, Login, Me)

**Files:**
- Create: `backend/app/core/exceptions.py`
- Create: `backend/app/core/deps.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/user.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/api/v1/auth.py`
- Modify: `backend/app/api/v1/router.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `UserRepository` (Task 2), `hash_password`/`verify_password`/`create_access_token` (Task 2), `settings` (Task 1).
- Produces: `app.core.exceptions.AppError(message, status_code)`, `AuthError`, `NotFoundError`, `ForbiddenError` (used by every later service); `app.core.deps.get_current_user` (FastAPI dependency returning the authenticated `User`, used by every protected route from here on); `AuthService(db).register(email, password, full_name)`, `.authenticate(email, password)`, `.create_token_for_user(user) -> str`.

- [ ] **Step 1: Create the exception hierarchy**

Create `backend/app/core/exceptions.py`:

```python
class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthError(AppError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Not allowed"):
        super().__init__(message, status_code=403)
```

- [ ] **Step 2: Wire the exception handler into the app**

Modify `backend/app/main.py` to:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppError
from app.api.v1.router import api_router

app = FastAPI(title=settings.APP_NAME)
app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(AppError)
def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/health")
def health_check():
    return {"status": "ok"}
```

- [ ] **Step 3: Write the failing auth tests**

Create `backend/tests/test_auth.py`:

```python
def test_register_creates_user(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "seller@example.com", "password": "StrongPass123", "full_name": "Test Seller"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "seller@example.com"
    assert "hashed_password" not in body


def test_register_duplicate_email_fails(client):
    client.post("/api/v1/auth/register", json={"email": "dupe@example.com", "password": "StrongPass123"})
    response = client.post("/api/v1/auth/register", json={"email": "dupe@example.com", "password": "AnotherPass123"})
    assert response.status_code == 400


def test_login_returns_token(client):
    client.post("/api/v1/auth/register", json={"email": "login@example.com", "password": "StrongPass123"})
    response = client.post("/api/v1/auth/login", json={"email": "login@example.com", "password": "StrongPass123"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password_fails(client):
    client.post("/api/v1/auth/register", json={"email": "wrongpass@example.com", "password": "StrongPass123"})
    response = client.post("/api/v1/auth/login", json={"email": "wrongpass@example.com", "password": "WrongOne123"})
    assert response.status_code == 401


def test_me_requires_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user(client):
    client.post("/api/v1/auth/register", json={"email": "me@example.com", "password": "StrongPass123"})
    login_response = client.post("/api/v1/auth/login", json={"email": "me@example.com", "password": "StrongPass123"})
    token = login_response.json()["access_token"]
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"
```

- [ ] **Step 4: Run the tests to verify they fail**

```bash
cd backend
pytest tests/test_auth.py -v
```

Expected: FAIL — no `/api/v1/auth/register` route exists yet (404s).

- [ ] **Step 5: Create schemas, deps, and the auth service**

Create `backend/app/schemas/__init__.py` (empty file).

Create `backend/app/schemas/user.py`:

```python
from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

Create `backend/app/core/deps.py`:

```python
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthError
from app.db.session import get_db
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise AuthError("Invalid token")
    except JWTError:
        raise AuthError("Invalid token")

    user = UserRepository(db).get_by_id(int(user_id))
    if user is None:
        raise AuthError("User not found")
    return user
```

Create `backend/app/services/__init__.py` (empty file).

Create `backend/app/services/auth_service.py`:

```python
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError, AuthError
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def register(self, email: str, password: str, full_name: str | None):
        if self.repo.get_by_email(email):
            raise AppError("Email already registered", status_code=400)
        return self.repo.create(email, hash_password(password), full_name)

    def authenticate(self, email: str, password: str):
        user = self.repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise AuthError("Invalid email or password")
        return user

    def create_token_for_user(self, user) -> str:
        return create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
```

`register` raises a plain `AppError` with status 400 for the duplicate-email case (matching `test_register_duplicate_email_fails`); `authenticate` raises `AuthError` (status 401) for bad credentials (matching `test_login_wrong_password_fails`).

- [ ] **Step 6: Create the auth router**

Create `backend/app/api/v1/auth.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.user import Token, UserCreate, UserLogin, UserOut
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.register(payload.email, payload.password, payload.full_name)


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    service = AuthService(db)
    user = service.authenticate(payload.email, payload.password)
    token = service.create_token_for_user(user)
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user=Depends(get_current_user)):
    return current_user
```

Modify `backend/app/api/v1/router.py`:

```python
from fastapi import APIRouter

from app.api.v1 import auth

api_router = APIRouter()
api_router.include_router(auth.router)
```

- [ ] **Step 7: Run the tests to verify they pass**

```bash
cd backend
pytest tests/test_auth.py -v
```

Expected: PASS (6 passed).

- [ ] **Step 8: Run the full test suite to check for regressions**

```bash
cd backend
pytest -v
```

Expected: all tests pass (health check, user repository, auth).

- [ ] **Step 9: Commit**

```bash
cd ..
git add backend/app/core/exceptions.py backend/app/core/deps.py backend/app/schemas backend/app/services backend/app/api/v1/auth.py backend/app/api/v1/router.py backend/app/main.py backend/tests/test_auth.py
git commit -m "Add JWT auth: register, login, and me endpoints"
```

---

### Task 4: Project Model & Ownership-Enforced CRUD

**Files:**
- Create: `backend/app/models/project.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/repositories/project_repository.py`
- Create: `backend/app/schemas/project.py`
- Create: `backend/app/services/project_service.py`
- Create: `backend/app/api/v1/projects.py`
- Modify: `backend/app/api/v1/router.py`
- Create: `backend/alembic/versions/0002_create_projects_table.py`
- Test: `backend/tests/test_projects.py`

**Interfaces:**
- Consumes: `get_current_user`, `AppError`/`NotFoundError`/`ForbiddenError` (Task 3), `auth_headers` fixture (Task 2).
- Produces: `ProjectService(db).create(user_id, name, description)`, `.list_for_user(user_id)`, `.get_owned(user_id, project_id)` (raises `NotFoundError`/`ForbiddenError`), `.update(...)`, `.delete(...)` — `ImageService` in Task 5 calls `ProjectService(db).get_owned(...)` directly to enforce that an image's project belongs to the requesting user.

- [ ] **Step 1: Create the Project model**

Create `backend/app/models/project.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

Modify `backend/app/models/__init__.py`:

```python
from app.models.user import User  # noqa: F401
from app.models.project import Project  # noqa: F401
```

- [ ] **Step 2: Write the failing project tests**

Create `backend/tests/test_projects.py`:

```python
def test_create_project(client, auth_headers):
    headers = auth_headers()
    response = client.post("/api/v1/projects", json={"name": "Summer Sneakers"}, headers=headers)
    assert response.status_code == 201
    assert response.json()["name"] == "Summer Sneakers"


def test_list_projects_only_returns_own(client, auth_headers):
    headers_a = auth_headers("a@example.com", "StrongPass123")
    headers_b = auth_headers("b@example.com", "StrongPass123")
    client.post("/api/v1/projects", json={"name": "A's project"}, headers=headers_a)
    client.post("/api/v1/projects", json={"name": "B's project"}, headers=headers_b)

    response = client.get("/api/v1/projects", headers=headers_a)
    names = [p["name"] for p in response.json()]
    assert names == ["A's project"]


def test_get_other_users_project_is_forbidden(client, auth_headers):
    headers_a = auth_headers("owner2@example.com", "StrongPass123")
    headers_b = auth_headers("intruder@example.com", "StrongPass123")
    created = client.post("/api/v1/projects", json={"name": "Private"}, headers=headers_a).json()

    response = client.get(f"/api/v1/projects/{created['id']}", headers=headers_b)
    assert response.status_code == 403


def test_get_missing_project_is_404(client, auth_headers):
    headers = auth_headers("missing@example.com", "StrongPass123")
    response = client.get("/api/v1/projects/9999", headers=headers)
    assert response.status_code == 404


def test_update_project(client, auth_headers):
    headers = auth_headers("updater@example.com", "StrongPass123")
    created = client.post("/api/v1/projects", json={"name": "Old Name"}, headers=headers).json()
    response = client.patch(f"/api/v1/projects/{created['id']}", json={"name": "New Name"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


def test_delete_project(client, auth_headers):
    headers = auth_headers("deleter@example.com", "StrongPass123")
    created = client.post("/api/v1/projects", json={"name": "Temp"}, headers=headers).json()
    response = client.delete(f"/api/v1/projects/{created['id']}", headers=headers)
    assert response.status_code == 204
    get_response = client.get(f"/api/v1/projects/{created['id']}", headers=headers)
    assert get_response.status_code == 404
```

- [ ] **Step 3: Run the tests to verify they fail**

```bash
cd backend
pytest tests/test_projects.py -v
```

Expected: FAIL — `/api/v1/projects` doesn't exist yet (404s).

- [ ] **Step 4: Implement the repository, schemas, and service**

Create `backend/app/repositories/project_repository.py`:

```python
from sqlalchemy.orm import Session

from app.models.project import Project


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, name: str, description: str | None) -> Project:
        project = Project(user_id=user_id, name=name, description=description)
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get_by_id(self, project_id: int) -> Project | None:
        return self.db.query(Project).filter(Project.id == project_id).first()

    def list_for_user(self, user_id: int) -> list[Project]:
        return self.db.query(Project).filter(Project.user_id == user_id).all()

    def update(self, project: Project, name: str | None, description: str | None) -> Project:
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        self.db.commit()
        self.db.refresh(project)
        return project

    def delete(self, project: Project) -> None:
        self.db.delete(project)
        self.db.commit()
```

Create `backend/app/schemas/project.py`:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime
```

Create `backend/app/services/project_service.py`:

```python
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.repositories.project_repository import ProjectRepository


class ProjectService:
    def __init__(self, db: Session):
        self.repo = ProjectRepository(db)

    def create(self, user_id: int, name: str, description: str | None):
        return self.repo.create(user_id, name, description)

    def list_for_user(self, user_id: int):
        return self.repo.list_for_user(user_id)

    def get_owned(self, user_id: int, project_id: int):
        project = self.repo.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project not found")
        if project.user_id != user_id:
            raise ForbiddenError("You do not have access to this project")
        return project

    def update(self, user_id: int, project_id: int, name: str | None, description: str | None):
        project = self.get_owned(user_id, project_id)
        return self.repo.update(project, name, description)

    def delete(self, user_id: int, project_id: int):
        project = self.get_owned(user_id, project_id)
        self.repo.delete(project)
```

- [ ] **Step 5: Create the projects router**

Create `backend/app/api/v1/projects.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    payload: ProjectCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    return ProjectService(db).create(current_user.id, payload.name, payload.description)


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return ProjectService(db).list_for_user(current_user.id)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    return ProjectService(db).get_owned(current_user.id, project_id)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ProjectService(db).update(current_user.id, project_id, payload.name, payload.description)


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    ProjectService(db).delete(current_user.id, project_id)
```

Modify `backend/app/api/v1/router.py`:

```python
from fastapi import APIRouter

from app.api.v1 import auth, projects

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(projects.router)
```

- [ ] **Step 6: Run the tests to verify they pass**

```bash
cd backend
pytest tests/test_projects.py -v
```

Expected: PASS (6 passed).

- [ ] **Step 7: Add the projects migration**

Create `backend/alembic/versions/0002_create_projects_table.py`:

```python
"""create projects table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("projects")
```

- [ ] **Step 8: Run the full suite and commit**

```bash
cd backend
pytest -v
```

Expected: all tests pass.

```bash
cd ..
git add backend/app/models backend/app/repositories/project_repository.py backend/app/schemas/project.py backend/app/services/project_service.py backend/app/api/v1/projects.py backend/app/api/v1/router.py backend/alembic/versions/0002_create_projects_table.py backend/tests/test_projects.py
git commit -m "Add project model, ownership-enforced CRUD, and migration"
```

---

### Task 5: Image Model, Storage Service & Upload Endpoints

**Files:**
- Create: `backend/app/models/image.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/services/storage_service.py`
- Create: `backend/app/repositories/image_repository.py`
- Create: `backend/app/schemas/image.py`
- Create: `backend/app/services/image_service.py`
- Create: `backend/app/api/v1/images.py`
- Modify: `backend/app/api/v1/router.py`
- Create: `backend/alembic/versions/0003_create_images_table.py`
- Test: `backend/tests/test_images.py`

**Interfaces:**
- Consumes: `ProjectService(db).get_owned(user_id, project_id)` (Task 4), `AppError`/`NotFoundError` (Task 3), `_isolate_uploads` autouse fixture (Task 2, redirects `settings.UPLOAD_DIR` to a temp dir during tests).
- Produces: `StorageService(base_dir=None).save(project_id, filename, content) -> str`, `.delete(storage_path) -> None` (Phase 2's enhancement pipeline will read files via this same service); `ImageService(db).upload(...)`, `.list_for_project(...)`, `.get_owned(...)`, `.delete(...)`.

- [ ] **Step 1: Create the Image model**

Create `backend/app/models/image.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

Modify `backend/app/models/__init__.py`:

```python
from app.models.user import User  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.image import Image  # noqa: F401
```

- [ ] **Step 2: Write the failing image tests**

Create `backend/tests/test_images.py`:

```python
import io


def test_upload_image(client, auth_headers):
    headers = auth_headers("uploader@example.com", "StrongPass123")
    project = client.post("/api/v1/projects", json={"name": "Shoes"}, headers=headers).json()

    file_content = b"fake-image-bytes"
    response = client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("sneaker.png", io.BytesIO(file_content), "image/png")},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "sneaker.png"
    assert body["size_bytes"] == len(file_content)


def test_upload_rejects_unsupported_content_type(client, auth_headers):
    headers = auth_headers("badtype@example.com", "StrongPass123")
    project = client.post("/api/v1/projects", json={"name": "Shoes"}, headers=headers).json()

    response = client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("doc.pdf", io.BytesIO(b"not an image"), "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 415


def test_list_images_for_project(client, auth_headers):
    headers = auth_headers("lister@example.com", "StrongPass123")
    project = client.post("/api/v1/projects", json={"name": "Bags"}, headers=headers).json()
    client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("bag.jpg", io.BytesIO(b"data"), "image/jpeg")},
        headers=headers,
    )

    response = client.get(f"/api/v1/projects/{project['id']}/images", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_delete_image(client, auth_headers):
    headers = auth_headers("imgdeleter@example.com", "StrongPass123")
    project = client.post("/api/v1/projects", json={"name": "Hats"}, headers=headers).json()
    uploaded = client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("hat.jpeg", io.BytesIO(b"data"), "image/jpeg")},
        headers=headers,
    ).json()

    response = client.delete(f"/api/v1/images/{uploaded['id']}", headers=headers)
    assert response.status_code == 204

    get_response = client.get(f"/api/v1/images/{uploaded['id']}", headers=headers)
    assert get_response.status_code == 404


def test_cannot_access_other_users_image(client, auth_headers):
    headers_a = auth_headers("imgowner@example.com", "StrongPass123")
    headers_b = auth_headers("imgintruder@example.com", "StrongPass123")
    project = client.post("/api/v1/projects", json={"name": "Watches"}, headers=headers_a).json()
    uploaded = client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("watch.png", io.BytesIO(b"data"), "image/png")},
        headers=headers_a,
    ).json()

    response = client.get(f"/api/v1/images/{uploaded['id']}", headers=headers_b)
    assert response.status_code == 403
```

- [ ] **Step 3: Run the tests to verify they fail**

```bash
cd backend
pytest tests/test_images.py -v
```

Expected: FAIL — `/api/v1/projects/{id}/images` doesn't exist yet (404s).

- [ ] **Step 4: Implement the storage service, repository, schema, and service**

Create `backend/app/services/storage_service.py`:

```python
import uuid
from pathlib import Path

from app.core.config import settings


class StorageService:
    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR)

    def save(self, project_id: int, filename: str, content: bytes) -> str:
        project_dir = self.base_dir / str(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        extension = Path(filename).suffix
        stored_name = f"{uuid.uuid4().hex}{extension}"
        destination = project_dir / stored_name
        destination.write_bytes(content)
        return str(destination)

    def delete(self, storage_path: str) -> None:
        path = Path(storage_path)
        if path.exists():
            path.unlink()
```

Create `backend/app/repositories/image_repository.py`:

```python
from sqlalchemy.orm import Session

from app.models.image import Image


class ImageRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self, project_id: int, original_filename: str, storage_path: str, content_type: str, size_bytes: int
    ) -> Image:
        image = Image(
            project_id=project_id,
            original_filename=original_filename,
            storage_path=storage_path,
            content_type=content_type,
            size_bytes=size_bytes,
        )
        self.db.add(image)
        self.db.commit()
        self.db.refresh(image)
        return image

    def get_by_id(self, image_id: int) -> Image | None:
        return self.db.query(Image).filter(Image.id == image_id).first()

    def list_for_project(self, project_id: int) -> list[Image]:
        return self.db.query(Image).filter(Image.project_id == project_id).all()

    def delete(self, image: Image) -> None:
        self.db.delete(image)
        self.db.commit()
```

Create `backend/app/schemas/image.py`:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime
```

Create `backend/app/services/image_service.py`:

```python
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, NotFoundError
from app.repositories.image_repository import ImageRepository
from app.services.project_service import ProjectService
from app.services.storage_service import StorageService

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_SIZE_BYTES = 15 * 1024 * 1024


class ImageService:
    def __init__(self, db: Session, storage: StorageService | None = None):
        self.db = db
        self.repo = ImageRepository(db)
        self.projects = ProjectService(db)
        self.storage = storage or StorageService()

    def upload(self, user_id: int, project_id: int, filename: str, content_type: str, content: bytes):
        self.projects.get_owned(user_id, project_id)

        if content_type not in ALLOWED_CONTENT_TYPES:
            raise AppError(f"Unsupported file type: {content_type}", status_code=415)
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            raise AppError("File exceeds maximum upload size of 15MB", status_code=413)

        storage_path = self.storage.save(project_id, filename, content)
        return self.repo.create(project_id, filename, storage_path, content_type, len(content))

    def list_for_project(self, user_id: int, project_id: int):
        self.projects.get_owned(user_id, project_id)
        return self.repo.list_for_project(project_id)

    def get_owned(self, user_id: int, image_id: int):
        image = self.repo.get_by_id(image_id)
        if image is None:
            raise NotFoundError("Image not found")
        self.projects.get_owned(user_id, image.project_id)
        return image

    def delete(self, user_id: int, image_id: int):
        image = self.get_owned(user_id, image_id)
        self.storage.delete(image.storage_path)
        self.repo.delete(image)
```

- [ ] **Step 5: Create the images router**

Create `backend/app/api/v1/images.py`:

```python
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.image import ImageOut
from app.services.image_service import ImageService

router = APIRouter(tags=["images"])


@router.post("/projects/{project_id}/images", response_model=ImageOut, status_code=201)
async def upload_image(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    content = await file.read()
    return ImageService(db).upload(current_user.id, project_id, file.filename, file.content_type, content)


@router.get("/projects/{project_id}/images", response_model=list[ImageOut])
def list_images(
    project_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    return ImageService(db).list_for_project(current_user.id, project_id)


@router.get("/images/{image_id}", response_model=ImageOut)
def get_image(image_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return ImageService(db).get_owned(current_user.id, image_id)


@router.delete("/images/{image_id}", status_code=204)
def delete_image(image_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    ImageService(db).delete(current_user.id, image_id)
```

Modify `backend/app/api/v1/router.py`:

```python
from fastapi import APIRouter

from app.api.v1 import auth, images, projects

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(images.router)
```

- [ ] **Step 6: Run the tests to verify they pass**

```bash
cd backend
pytest tests/test_images.py -v
```

Expected: PASS (5 passed).

- [ ] **Step 7: Add the images migration**

Create `backend/alembic/versions/0003_create_images_table.py`:

```python
"""create images table

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("storage_path", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("images")
```

- [ ] **Step 8: Run the full backend suite and commit**

```bash
cd backend
pytest -v
```

Expected: all tests pass (health, user repository, auth, projects, images).

```bash
cd ..
git add backend/app/models/image.py backend/app/models/__init__.py backend/app/services/storage_service.py backend/app/services/image_service.py backend/app/repositories/image_repository.py backend/app/schemas/image.py backend/app/api/v1/images.py backend/app/api/v1/router.py backend/alembic/versions/0003_create_images_table.py backend/tests/test_images.py
git commit -m "Add image model, storage service, and upload/list/delete endpoints"
```

---

### Task 6: Docker Compose (Backend + Postgres + Redis)

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`

**Interfaces:**
- Consumes: `backend/Dockerfile` (Task 1), `backend/alembic` migrations (Tasks 2/4/5).
- Produces: a `db` service (Postgres, port 5432) and `redis` service (port 6379, unused by code until Phase 2) that Task 7's `frontend` service and Phase 2's AI inference service will both depend on.

- [ ] **Step 1: Create the root docker-compose file**

Create `docker-compose.yml` (repo root):

```yaml
services:
  db:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-productstudio}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    restart: unless-stopped
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    restart: unless-stopped
    env_file:
      - .env
    depends_on:
      - db
      - redis
    volumes:
      - uploads_data:/data/uploads
    ports:
      - "8000:8000"

volumes:
  postgres_data:
  uploads_data:
```

- [ ] **Step 2: Create the root env example**

Create `.env.example` (repo root):

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/productstudio
SECRET_KEY=dummy-dev-secret-change-me
ACCESS_TOKEN_EXPIRE_MINUTES=60
UPLOAD_DIR=/data/uploads
MAX_UPLOAD_SIZE_MB=15
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=productstudio
```

Copy it to a real (still dummy-valued) `.env` for local use:

```bash
cp .env.example .env
```

- [ ] **Step 3: Build and start the stack**

```bash
docker compose up --build -d db redis backend
```

Expected: three containers running (`docker compose ps` shows `db`, `redis`, `backend` all `Up`).

- [ ] **Step 4: Run Alembic migrations against the real Postgres container**

```bash
docker compose exec backend alembic upgrade head
```

Expected: output shows migrations `0001`, `0002`, `0003` applied in order, no errors.

- [ ] **Step 5: Verify the backend is reachable and functional end-to-end**

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/auth/register -H "Content-Type: application/json" -d "{\"email\":\"smoke@example.com\",\"password\":\"StrongPass123\"}"
```

Expected: `{"status":"ok"}` from the first call; a `201` with the created user JSON from the second.

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "Add Docker Compose for backend, Postgres, and Redis"
```

(`.env` itself is not committed — add it to a new root `.gitignore` in this step if one doesn't already exist:)

Create `.gitignore` (repo root) if it does not already exist:

```
.env
backend/venv/
backend/__pycache__/
backend/**/__pycache__/
frontend/node_modules/
frontend/dist/
```

```bash
git add .gitignore
git commit -m "Add root gitignore for env files and build artifacts"
```

---

### Task 7: Frontend Skeleton (React + Auth + Dashboard + Upload)

**Files:**
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`
- Create: `frontend/Dockerfile`
- Create: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/setupTests.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/store/AuthContext.tsx`
- Create: `frontend/src/routes/ProtectedRoute.tsx`
- Create: `frontend/src/pages/Login.tsx`, `frontend/src/pages/Register.tsx`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/ProjectDetail.tsx`
- Test: `frontend/src/routes/ProtectedRoute.test.tsx`
- Modify: `docker-compose.yml`

**Interfaces:**
- Consumes: backend API from Task 3/4/5 (`/api/v1/auth/*`, `/api/v1/projects*`, `/api/v1/projects/{id}/images`).
- Produces: `useAuth()` hook (`{ token, login(token), logout() }`) used by every page; `client` (configured axios instance) used by every page for API calls.

- [ ] **Step 1: Scaffold the Vite React TypeScript project**

```bash
cd ..
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-router-dom axios
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

- [ ] **Step 2: Configure Vitest**

Modify `frontend/vite.config.ts`:

```typescript
/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: "./src/setupTests.ts",
  },
});
```

Create `frontend/src/setupTests.ts`:

```typescript
import "@testing-library/jest-dom";
```

Modify `frontend/package.json` `scripts` section to add:

```json
"test": "vitest run"
```

- [ ] **Step 3: Create the API client**

Create `frontend/src/api/client.ts`:

```typescript
import axios from "axios";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1",
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default client;
```

- [ ] **Step 4: Create the auth context**

Create `frontend/src/store/AuthContext.tsx`:

```tsx
import { createContext, ReactNode, useContext, useState } from "react";

interface AuthContextValue {
  token: string | null;
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(localStorage.getItem("access_token"));

  const login = (newToken: string) => {
    localStorage.setItem("access_token", newToken);
    setToken(newToken);
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    setToken(null);
  };

  return <AuthContext.Provider value={{ token, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
```

- [ ] **Step 5: Write the failing ProtectedRoute test**

Create `frontend/src/routes/ProtectedRoute.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AuthProvider } from "../store/AuthContext";
import { ProtectedRoute } from "./ProtectedRoute";

function renderProtected() {
  return render(
    <MemoryRouter initialEntries={["/dashboard"]}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<div>Dashboard Page</div>} />
          </Route>
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("ProtectedRoute", () => {
  it("redirects to login when there is no token", () => {
    localStorage.removeItem("access_token");
    renderProtected();
    expect(screen.getByText("Login Page")).toBeInTheDocument();
  });

  it("renders the protected content when a token exists", () => {
    localStorage.setItem("access_token", "fake-token");
    renderProtected();
    expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
  });
});
```

- [ ] **Step 6: Run the test to verify it fails**

```bash
cd frontend
npm run test
```

Expected: FAIL — `./ProtectedRoute` has no exported member `ProtectedRoute` yet.

- [ ] **Step 7: Implement ProtectedRoute**

Create `frontend/src/routes/ProtectedRoute.tsx`:

```tsx
import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "../store/AuthContext";

export function ProtectedRoute() {
  const { token } = useAuth();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}
```

- [ ] **Step 8: Run the test to verify it passes**

```bash
cd frontend
npm run test
```

Expected: PASS (2 passed).

- [ ] **Step 9: Create the Login, Register, Dashboard, and ProjectDetail pages**

Create `frontend/src/pages/Login.tsx`:

```tsx
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import client from "../api/client";
import { useAuth } from "../store/AuthContext";

export function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const response = await client.post("/auth/login", { email, password });
      login(response.data.access_token);
      navigate("/dashboard");
    } catch {
      setError("Invalid email or password");
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h1>Log in</h1>
      <label htmlFor="email">Email</label>
      <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <label htmlFor="password">Password</label>
      <input
        id="password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      {error && <p role="alert">{error}</p>}
      <button type="submit">Log in</button>
    </form>
  );
}
```

Create `frontend/src/pages/Register.tsx`:

```tsx
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import client from "../api/client";

export function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await client.post("/auth/register", { email, password });
      navigate("/login");
    } catch {
      setError("Could not register. Email may already be in use.");
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h1>Create account</h1>
      <label htmlFor="email">Email</label>
      <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <label htmlFor="password">Password</label>
      <input
        id="password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      {error && <p role="alert">{error}</p>}
      <button type="submit">Register</button>
    </form>
  );
}
```

Create `frontend/src/pages/Dashboard.tsx`:

```tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import client from "../api/client";

interface Project {
  id: number;
  name: string;
  description: string | null;
}

export function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");

  useEffect(() => {
    client.get<Project[]>("/projects").then((response) => setProjects(response.data));
  }, []);

  async function handleCreate() {
    const response = await client.post<Project>("/projects", { name });
    setProjects((prev) => [...prev, response.data]);
    setName("");
  }

  return (
    <div>
      <h1>Your Projects</h1>
      <input value={name} onChange={(e) => setName(e.target.value)} placeholder="New project name" />
      <button onClick={handleCreate}>Create Project</button>
      <ul>
        {projects.map((project) => (
          <li key={project.id}>
            <Link to={`/projects/${project.id}`}>{project.name}</Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

Create `frontend/src/pages/ProjectDetail.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import client from "../api/client";

interface ImageAsset {
  id: number;
  original_filename: string;
  uploaded_at: string;
}

export function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const [images, setImages] = useState<ImageAsset[]>([]);
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    client.get<ImageAsset[]>(`/projects/${id}/images`).then((response) => setImages(response.data));
  }, [id]);

  async function handleUpload() {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    const response = await client.post<ImageAsset>(`/projects/${id}/images`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    setImages((prev) => [...prev, response.data]);
    setFile(null);
  }

  return (
    <div>
      <h1>Project Images</h1>
      <input
        type="file"
        accept="image/png,image/jpeg,image/webp"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />
      <button onClick={handleUpload} disabled={!file}>
        Upload
      </button>
      <ul>
        {images.map((image) => (
          <li key={image.id}>{image.original_filename}</li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 10: Wire routing in App.tsx**

Modify `frontend/src/App.tsx`:

```tsx
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
import { ProjectDetail } from "./pages/ProjectDetail";
import { Register } from "./pages/Register";
import { ProtectedRoute } from "./routes/ProtectedRoute";
import { AuthProvider } from "./store/AuthContext";

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/projects/:id" element={<ProjectDetail />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
```

Modify `frontend/src/main.tsx` to render `<App />` (Vite's default template already does this via `<App />` from `./App` — update the import if the default template used a default export):

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

- [ ] **Step 11: Run the full frontend test suite**

```bash
cd frontend
npm run test
```

Expected: all tests pass (2 passed).

- [ ] **Step 12: Add the frontend Dockerfile and wire it into Compose**

Create `frontend/Dockerfile`:

```dockerfile
FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

Modify `docker-compose.yml` — add this service alongside `db`, `redis`, `backend`:

```yaml
  frontend:
    build: ./frontend
    restart: unless-stopped
    depends_on:
      - backend
    ports:
      - "5173:5173"
```

- [ ] **Step 13: Full-stack verification**

```bash
docker compose up --build -d
```

Expected: `docker compose ps` shows `db`, `redis`, `backend`, `frontend` all `Up`.

Open `http://localhost:5173` in a browser, register a new account, log in, create a project, and upload a `.png`/`.jpg` file — confirm it appears in the project's image list.

- [ ] **Step 14: Commit**

```bash
git add frontend docker-compose.yml
git commit -m "Add React frontend skeleton with auth, dashboard, and image upload"
```

---

## Definition of Done for Phase 1

- `pytest -v` in `backend/` passes with 0 failures.
- `npm run test` in `frontend/` passes with 0 failures.
- `docker compose up --build` brings up `db`, `redis`, `backend`, `frontend` cleanly.
- `alembic upgrade head` runs cleanly against the Postgres container.
- Manual walkthrough in the browser: register → login → create project → upload image → see it listed.
- No AI models, no real credentials, nothing pushed to any remote.
