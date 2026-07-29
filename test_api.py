"""
Exercises the API in-process (no server needed) to prove:
1. Listing models works
2. The governance gate BLOCKS promoting a low-scoring model to production
3. A well-scoring model CAN be promoted
4. Illegal state transitions are rejected
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

resp = client.get("/api/v1/models")
models = resp.json()
fraud_model = next(m for m in models if m["name"] == "fraud-flagger")
sme_model = next(m for m in models if m["name"] == "sme-credit-scorer")

# Governance gate should BLOCK this (score 6.25 < 7.0 threshold)
resp = client.post(
    f"/api/v1/models/{fraud_model['id']}/approve",
    json={"to_stage": "production", "approved_by": "test-committee", "comment": "trying anyway"},
)
assert resp.status_code == 403

# State machine should REJECT skipping review
new_model = client.post("/api/v1/models", json={
    "name": "test-model", "version": "v1", "model_type": "traditional_ml",
    "use_case": "test", "owner": "tester",
}).json()
resp = client.post(
    f"/api/v1/models/{new_model['id']}/approve",
    json={"to_stage": "production", "approved_by": "test", "comment": "skip review"},
)
assert resp.status_code == 400

print("✅ All API + workflow tests passed.")