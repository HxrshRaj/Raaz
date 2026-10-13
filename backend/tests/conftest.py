from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="raaz-test-"))
os.environ.update(
    RAAZ_ENV="test",
    # CI's PostgreSQL job sets RAAZ_TEST_DATABASE_URL; locally tests use an isolated throwaway SQLite file.
    RAAZ_DATABASE_URL=os.environ.get("RAAZ_TEST_DATABASE_URL") or f"sqlite:///{(_TMP / 'test.db').as_posix()}",
    RAAZ_RATE_LIMIT_PER_MIN="100000",
    RAAZ_LLM_RATE_LIMIT_PER_MIN="100000",
    RAAZ_AGENT_RUNS_PER_HOUR="100000",
    RAAZ_LLM_PROVIDER="none",
    RAAZ_ARTIFACTS_DIR=(_TMP / "artifacts").as_posix(),
    RAAZ_JWT_SECRET="test-secret-test-secret-test-secret-123",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.ratelimit import reset_limiter  # noqa: E402
from tests.helpers import Player  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _fresh_limiter():
    reset_limiter()
    yield


@pytest.fixture
def player(client) -> Player:
    p = Player(client)
    p.start()
    return p
