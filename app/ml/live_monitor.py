"""
The live monitoring loop — the thing that makes this registry self-updating.

Every run:
  1. Pulls a fresh batch of transactions from the live feed. Not a replay:
     these transactions did not exist the last time this ran.
  2. Scores them with the deployed anomaly model.
  3. Logs the real observed metrics into the registry via the API.
  4. Runs Evidently drift detection against the baseline the model was
     trained on, and logs that too.
  5. If enough features have drifted and the model is live, demotes it back
     to review — through the same /approve endpoint a human reviewer uses,
     with no special bypass.

Step 5 is the one that matters. An automated actor and a human reviewer go
through the identical door, hit the identical state machine, and leave the
identical kind of audit record. The only difference is the name on it.

Run it once by hand, or on a schedule:
    Windows : Task Scheduler -> python -m app.ml.live_monitor
    Linux   : */30 * * * * cd /path && python -m app.ml.live_monitor
"""

import pickle
from datetime import datetime

import numpy as np
import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.registry import MLModel
from app.ml.live_feed import FEATURES, snapshot
from app.ml.train_live_model import BASELINE_PATH, MODEL_PATH

client = TestClient(app)

MODEL_NAME = "payment-anomaly-monitor"

# Share of features that must drift before the model is pulled back for review.
DRIFT_SHARE_THRESHOLD = 0.5

# How much live traffic to sample per run. ~25 seconds of polling — enough for
# a stable read without leaning on a free public API harder than necessary.
POLLS_PER_RUN = 20


def _measure_drift(reference: pd.DataFrame, current: pd.DataFrame) -> tuple[float, int]:
    """
    Returns (share_of_features_drifted, count). Uses the same result-shape
    matching as drift_check.py: this Evidently version leaves metric_id
    unpopulated, so the summary metric is identified by being the one whose
    value is a {count, share} dict rather than by name.
    """
    report = Report([DataDriftPreset()])
    result = report.run(reference_data=reference[FEATURES], current_data=current[FEATURES])
    summary = next(
        m for m in result.dict()["metrics"]
        if isinstance(m.get("value"), dict) and "share" in m["value"]
    )
    return float(summary["value"]["share"]), int(summary["value"]["count"])


def run():
    print(f"🕐 Live monitoring run — {datetime.now():%Y-%m-%d %H:%M:%S}\n")

    db = SessionLocal()
    record = db.query(MLModel).filter(MLModel.name == MODEL_NAME).first()
    if record is None:
        db.close()
        raise RuntimeError(
            f"{MODEL_NAME} isn't registered yet. "
            f"Run: python -m app.ml.register_live_model"
        )
    model_id, stage = record.id, record.stage.value
    db.close()

    with open(MODEL_PATH, "rb") as f:
        detector = pickle.load(f)
    baseline = pd.read_csv(BASELINE_PATH)

    # 1. Genuinely new data — fetched now, never seen before.
    current = snapshot(polls=POLLS_PER_RUN)

    # 2. Score it.
    scores = -detector.score_samples(current[FEATURES])
    flagged = detector.predict(current[FEATURES]) == -1

    observed = {
        "anomaly_rate": float(flagged.mean()),
        "mean_anomaly_score": float(np.mean(scores)),
        "p99_anomaly_score": float(np.percentile(scores, 99)),
        "live_batch_size": float(len(current)),
    }

    print(f"\n📊 This batch: {len(current)} transactions, "
          f"{int(flagged.sum())} flagged ({observed['anomaly_rate']:.1%})")

    if flagged.any():
        top = current.loc[flagged].copy()
        top["anomaly_score"] = scores[flagged]
        print("\n🚩 Flagged for review:")
        for _, row in top.nlargest(min(5, len(top)), "anomaly_score").iterrows():
            print(
                f"   {row['txid'][:16]}…  "
                f"value={row['value']:>14,.0f}  "
                f"fee={row['fee']:>9,.0f}  "
                f"fee/value={row['fee_ratio_bps']:>9,.0f}bps"
            )

    # 3. Everything goes into the registry through the API, not a side channel.
    for name, value in observed.items():
        client.post(
            f"/api/v1/models/{model_id}/metrics",
            json={"metric_name": name, "metric_value": value},
        )

    # 4. Has live traffic moved away from what the model was trained on?
    drift_share, drifted_count = _measure_drift(baseline, current)
    client.post(
        f"/api/v1/models/{model_id}/metrics",
        json={"metric_name": "drift_share", "metric_value": drift_share},
    )
    print(f"\n📉 Drift vs baseline: {drifted_count}/{len(FEATURES)} features shifted "
          f"({drift_share:.0%}, threshold {DRIFT_SHARE_THRESHOLD:.0%})")

    # 5. Act on it — via the same gate a person would use.
    if drift_share >= DRIFT_SHARE_THRESHOLD and stage == "production":
        print("\n🚨 Drift over threshold on a live model — pulling it back for review.")
        resp = client.post(
            f"/api/v1/models/{model_id}/approve",
            json={
                "to_stage": "review",
                "approved_by": "live-monitor-service",
                "comment": (
                    f"Auto-demoted from live: {drift_share:.0%} of input features "
                    f"({drifted_count}/{len(FEATURES)}) have shifted away from the "
                    f"training baseline. Observed anomaly rate this batch was "
                    f"{observed['anomaly_rate']:.1%} across {len(current)} live "
                    f"transactions. Retrain against current traffic before "
                    f"returning this model to production."
                ),
            },
        )
        print(f"   HTTP {resp.status_code} — stage is now '{resp.json().get('stage')}'")
    elif drift_share >= DRIFT_SHARE_THRESHOLD:
        print(f"\n⚠️  Drift over threshold, but the model is '{stage}', not live — "
              f"nothing to demote. Logged for the reviewer to weigh.")
    else:
        print("\n✅ Live traffic still resembles the training baseline. No action.")

    print("\n   Refresh the dashboard — the new measurements are already there.")
    return observed, drift_share


if __name__ == "__main__":
    run()
