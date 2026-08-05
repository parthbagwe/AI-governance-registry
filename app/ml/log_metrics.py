"""
Logs sme-credit-scorer's real training metrics into the registry.

The seeded metrics for this model are synthetic — a plausible-looking accuracy
curve with a drop injected at the end, so there's something for the drift
monitor to catch on a fresh install. This script writes the *actual* numbers
the XGBoost model scored, prefixed `real_` so the two can never be confused on
a chart or in a conversation.

That prefix matters more than it looks. A governance registry whose metrics
might be real or might be illustrative, with no way to tell which, is worse
than one with no metrics at all — it invites confident decisions from numbers
nobody can vouch for.

Run AFTER train_model.py (it needs data_train.csv to exist).
"""

from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.registry import MLModel
from app.ml.train_model import train

client = TestClient(app)

MODEL_NAME = "sme-credit-scorer"


def log_real_metrics():
    db = SessionLocal()
    record = db.query(MLModel).filter(MLModel.name == MODEL_NAME).first()
    if record is None:
        db.close()
        raise RuntimeError(
            f"{MODEL_NAME} isn't in the registry. Run: python seed.py"
        )
    model_id = record.id
    db.close()

    _, metrics = train()

    print()
    for name, value in metrics.items():
        resp = client.post(
            f"/api/v1/models/{model_id}/metrics",
            json={"metric_name": f"real_{name}", "metric_value": float(value)},
        )
        if resp.status_code != 201:
            raise RuntimeError(f"Failed to log real_{name}: HTTP {resp.status_code} {resp.text}")
        print(f"  logged real_{name} = {value:.4f}")

    print(f"\n✅ Real training metrics recorded against {MODEL_NAME}.")
    print("   They sit alongside the seeded synthetic history in the chart —")
    print("   the `real_` prefix is what tells them apart.")
    return metrics


if __name__ == "__main__":
    log_real_metrics()
