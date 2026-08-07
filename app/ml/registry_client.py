"""
One client, two destinations.

Until now every monitoring script talked to the registry through FastAPI's
in-process TestClient. That was fine while everything lived on one laptop, but
it quietly assumed the API and the monitor were the same process — which stops
being true the moment the API is deployed.

So: if REGISTRY_API_URL is set, calls go over real HTTP to the deployed
service. If it isn't, they run in-process exactly as before.

What deliberately does *not* change is the surface. Both paths speak the same
REST endpoints, hit the same state machine, and get the same 403 when a
promotion is refused. A monitor running on a laptop against a Render instance
has no more authority than one running locally — which is the same principle
the governance gate rests on: no actor gets a private door.
"""

import os
from typing import Any

REGISTRY_API_URL = os.getenv("REGISTRY_API_URL", "").rstrip("/")

# Where the versioned routes live, relative to the service root.
API_PREFIX = "/api/v1"


class _RemoteClient:
    """
    Minimal stand-in for TestClient over real HTTP.

    Only `get` and `post` are implemented, because that's all the monitors
    use. The returned object exposes `.status_code`, `.json()` and `.text`,
    so calling code doesn't need to know which transport it got.
    """

    def __init__(self, base_url: str):
        import requests  # imported here so the API image needn't ship it

        self._requests = requests
        self.base_url = base_url

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def get(self, path: str, **kwargs: Any):
        return self._requests.get(self._url(path), timeout=30, **kwargs)

    def post(self, path: str, **kwargs: Any):
        return self._requests.post(self._url(path), timeout=60, **kwargs)


def get_client():
    """
    Returns a client whose paths are relative to the service root, so callers
    keep writing `/api/v1/models/...` exactly as they did before.
    """
    if REGISTRY_API_URL:
        return _RemoteClient(REGISTRY_API_URL)

    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app)


def describe_target() -> str:
    """Human-readable description of where this run will write. Printed by the
    monitors, because 'which registry did I just update?' should never be a
    question you have to reason about."""
    return REGISTRY_API_URL or "local in-process API (governance.db)"


def get_session():
    """
    Direct DB session, for the few places that genuinely need one — writing
    lineage rows, and looking up a model's current stage.

    This only works when the database is reachable from wherever the script is
    running. Against a deployed registry it will hit the local SQLite file, not
    production, which is why the callers that need a model's stage read it back
    through the API instead.
    """
    from app.database import SessionLocal

    return SessionLocal()


def fetch_model(client, name: str) -> dict | None:
    """
    Look a model up by name through the API rather than the DB, so it works
    identically whether the registry is local or remote.
    """
    resp = client.get(f"{API_PREFIX}/models")
    if resp.status_code != 200:
        raise RuntimeError(
            f"Could not list models from {describe_target()}: "
            f"HTTP {resp.status_code} {resp.text}"
        )
    return next((m for m in resp.json() if m["name"] == name), None)
