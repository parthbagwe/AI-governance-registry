"""
Shared test setup.

The environment variables have to be set *before* anything under `app` is
imported, because `app/database.py` reads DATABASE_URL and builds its engine at
module scope. pytest loads conftest first, which is what makes this ordering
work — put these lines anywhere else and the tests quietly run against
governance.db, the real development database. That failure mode is silent and
destructive, which is why it's called out here rather than assumed.
"""

import os
import tempfile
from pathlib import Path

TEST_DB = Path(tempfile.gettempdir()) / "ai_governance_registry_test.db"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["SKIP_BOOTSTRAP_SEED"] = "1"
# Left unset deliberately: monitors and scripts must talk to the in-process app
# during tests, never to a deployed instance.
os.environ.pop("REGISTRY_API_URL", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

API = "/api/v1"


@pytest.fixture(autouse=True)
def fresh_database():
    """
    Every test gets an empty registry.

    Autouse and function-scoped on purpose. Governance state is cumulative — a
    model promoted in one test would still be in production for the next, and
    tests that pass only in a particular order are worse than no tests, because
    they teach you to trust a green run that isn't checking what you think.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def register(client):
    """Registers a model and returns its JSON, failing loudly if it didn't."""

    def _register(**overrides):
        payload = {
            "name": "test-model",
            "version": "v1.0.0",
            "model_type": "traditional_ml",
            "use_case": "Testing",
            "owner": "test-team",
            "risk_tier": "medium",
        }
        payload.update(overrides)
        resp = client.post(f"{API}/models", json=payload)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _register


@pytest.fixture
def score(client):
    """Sets all five scorecard dimensions to the same value."""

    def _score(model_id: str, value: float):
        resp = client.patch(
            f"{API}/models/{model_id}/scores",
            json={
                "efficiency_score": value,
                "adoption_score": value,
                "input_quality_score": value,
                "cost_reduction_score": value,
                "revenue_impact_score": value,
            },
        )
        assert resp.status_code == 200, resp.text
        return resp.json()

    return _score


@pytest.fixture
def promote(client):
    """Moves a model to a stage, returning the raw response so the caller can
    assert on failures as well as successes."""

    def _promote(model_id: str, to_stage: str, by: str = "tester", comment: str | None = None):
        return client.post(
            f"{API}/models/{model_id}/approve",
            json={"to_stage": to_stage, "approved_by": by, "comment": comment},
        )

    return _promote
