"""Authentication boundary tests.

Most governance tests explicitly disable external auth so they can exercise
the state machine in isolation. These tests turn the boundary back on and
prove unauthenticated callers and over-privileged monitors are rejected.
"""

from app import auth
from tests.conftest import API


def test_api_rejects_missing_credentials(client, monkeypatch):
    monkeypatch.setattr(auth, "AUTH_DISABLED", False)
    response = client.get(f"{API}/models")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_monitor_can_demote_but_cannot_promote_or_kill(
    client, register, score, promote, monkeypatch
):
    model = register()
    score(model["id"], 9.0)
    promote(model["id"], "review")
    promote(model["id"], "production")

    monkeypatch.setattr(auth, "AUTH_DISABLED", False)
    monkeypatch.setattr(auth, "MONITOR_API_KEY", "test-monitor-key")
    headers = {"X-API-Key": "test-monitor-key"}

    demote = client.post(
        f"{API}/models/{model['id']}/approve",
        headers=headers,
        json={"to_stage": "review", "comment": "Drift threshold exceeded"},
    )
    assert demote.status_code == 200

    history = client.get(
        f"{API}/models/{model['id']}/history", headers=headers
    ).json()
    assert history[-1]["approved_by"] == auth.MONITOR_ACTOR

    promote_attempt = client.post(
        f"{API}/models/{model['id']}/approve",
        headers=headers,
        json={"to_stage": "production"},
    )
    assert promote_attempt.status_code == 403

    kill_attempt = client.post(
        f"{API}/models/{model['id']}/kill-switch",
        headers=headers,
        params={"reason": "test"},
    )
    assert kill_attempt.status_code == 403
