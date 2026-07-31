"""
Runs Evidently AI's data drift detection comparing the "reference" data
(what sme-credit-scorer was trained on) against "current" data (simulating
live production traffic a few months later).

If drift is detected on enough features, this automatically:
1. Logs a `drift_score` metric into the registry
2. Moves the model from PRODUCTION -> REVIEW via the same governance API
   we already built — no separate "back door" path, it goes through the
   exact same workflow/state-machine gate a human approver would use.
"""

import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.registry import MLModel
from app.ml.train_model import FEATURES

client = TestClient(app)

# A model is considered "drifted enough to review" if this fraction
# (or more) of its input features show statistically significant drift.
DRIFT_SHARE_THRESHOLD = 0.5


def run_drift_check():
    reference = pd.read_csv("data_train.csv")[FEATURES]
    current = pd.read_csv("data_current.csv")[FEATURES]

    report = Report([DataDriftPreset()])
    result = report.run(reference_data=reference, current_data=current)
    result_dict = result.dict()

    # Pull the overall drift share out of Evidently's result structure.
    # In this Evidently version metric_id isn't populated, so we match by
    # shape instead: the DriftedColumnsCount summary is the one metric whose
    # value is a {"count": ..., "share": ...} dict.
    drift_metric = next(
        m for m in result_dict["metrics"]
        if isinstance(m.get("value"), dict) and "share" in m["value"]
    )
    drift_share = drift_metric["value"]["share"]
    drifted_count = drift_metric["value"]["count"]
    print(f"Raw Evidently result: {drifted_count} of {len(FEATURES)} features drifted (share={drift_share})")

    print(f"\n📊 Drift check: {drift_share:.0%} of features show significant drift "
          f"(threshold: {DRIFT_SHARE_THRESHOLD:.0%})")

    db = SessionLocal()
    sme = db.query(MLModel).filter(MLModel.name == "sme-credit-scorer").first()
    model_id, current_stage = sme.id, sme.stage.value
    db.close()

    # Log the drift score into the registry regardless of outcome
    client.post(
        f"/api/v1/models/{model_id}/metrics",
        json={"metric_name": "drift_share", "metric_value": float(drift_share)},
    )

    if drift_share >= DRIFT_SHARE_THRESHOLD and current_stage == "production":
        print(f"🚨 Drift exceeds threshold — auto-flagging model for review...")
        resp = client.post(
            f"/api/v1/models/{model_id}/approve",
            json={
                "to_stage": "review",
                "approved_by": "drift-monitor-service",
                "comment": (
                    f"Auto-flagged: {drift_share:.0%} of input features show "
                    f"significant drift vs training data (threshold {DRIFT_SHARE_THRESHOLD:.0%})"
                ),
            },
        )
        print(f"   HTTP {resp.status_code}: model stage is now '{resp.json()['stage']}'")
    else:
        print("✅ Drift within acceptable range, no action taken.")

    return drift_share


if __name__ == "__main__":
    run_drift_check()