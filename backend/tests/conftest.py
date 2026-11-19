"""Shared test setup.

Tests run against a disposable Postgres, never production. The migrations use
Postgres-only features (RLS, policies), so SQLite can't stand in for it.

    docker run -d --name vigil-test-pg -e POSTGRES_PASSWORD=test -p 5433:5432 postgres:17
    TEST_DATABASE_URL=postgresql://postgres:test@localhost:5433/postgres pytest
"""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# ── Environment: set before any app module is imported ─────────────────────────

_ALLOWED_DB_HOSTS = {"localhost", "127.0.0.1", "postgres"}

_test_db = os.getenv("TEST_DATABASE_URL")
if not _test_db:
    pytest.exit("TEST_DATABASE_URL is not set; see backend/tests/conftest.py", returncode=2)
if urlparse(_test_db).hostname not in _ALLOWED_DB_HOSTS:
    pytest.exit(f"Refusing to run tests against non-local database host "
                f"{urlparse(_test_db).hostname!r}", returncode=2)

# Never read backend/.env: it may hold production credentials.
import dotenv  # noqa: E402
dotenv.load_dotenv = lambda *a, **k: False

for _var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
             "SENDGRID_API_KEY", "ALERT_SENDER_EMAIL"):
    os.environ.pop(_var, None)
os.environ["DATABASE_URL"]     = _test_db
os.environ["VIGIL_JWT_SECRET"] = "test-secret-not-for-production"
os.environ["DATA_SOURCE"]      = "seed"

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import permissions  # noqa: E402
from database import SessionLocal, engine  # noqa: E402
from main import app  # noqa: E402
from models import User  # noqa: E402
from passwords import hash_password  # noqa: E402
from routers.auth import create_access_token  # noqa: E402
from routers.auth import limiter as auth_limiter  # noqa: E402

# Tables tests write to. roles/permissions/role_permissions come from the
# migrations and are left alone.
_DATA_TABLES = ("refresh_tokens", "auth_events", "audit_log", "alert_log", "anomaly_events", "users")

PASSWORD = "Correct-horse-9"


@pytest.fixture(scope="session", autouse=True)
def _migrated_db():
    """Apply the real Alembic migrations once, exactly as production does."""
    with engine.begin() as conn:
        # Supabase provides this role; the RLS policies are granted to it.
        conn.execute(text(
            "DO $$ BEGIN CREATE ROLE service_role; "
            "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
        ))
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(cfg, "head")


@pytest.fixture(autouse=True)
def _clean_state():
    """Every test starts with empty data tables and no rate-limit history."""
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(_DATA_TABLES)} RESTART IDENTITY CASCADE"))
    permissions.invalidate_cache()
    # Rate limits are per IP and every test client shares one; tests that
    # exercise them turn them back on explicitly.
    app.state.limiter.enabled = False
    auth_limiter.enabled = False
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def make_user(db):
    def _make(role="analyst", email=None, password=PASSWORD):
        user = User(email=email or f"{role}-{os.urandom(3).hex()}@example.com",
                    password_hash=hash_password(password), role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    return _make


def auth_header(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user)}"}


@pytest.fixture
def guest_headers(client):
    res = client.post("/api/v1/auth/guest")
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
