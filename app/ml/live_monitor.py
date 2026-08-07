"""
The live monitoring loop — what makes this registry self-updating rather than
a static snapshot.

Every run:
  1. Pulls the most recent window of real ECB rates. Not a replay: each new
     business day adds an observation that did not exist before.
  2. Scores those days with the deployed anomaly model.
  3. Logs the real observed metrics into the registry through the API.
  4. Runs Evidently drift detection against the baseline period the model was
     trained on — i.e. "does the current market regime still resemble the one
     this model learned?"
  5. If enough features have drifted and the model is live, demotes it back to
     review through the same /approve endpoint a human reviewer uses.

Step 5 is the one that matters. An automated actor and a human reviewer go
through the identical door, hit the identical state machine, and leave the
identical kind of audit record. The only difference is the name on it.

Run once by hand, or on a schedule:
    Windows : Task Scheduler -> python -m app.ml.live_monitor
    Linux   : 30 6 * * 1-5 cd /path && python -m app.ml.live_monitor
"""

import pickle
from datetime import datetime

import numpy as np
import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset
from app.ml.live_feed import FEATURES, current_window, snapshot
from app.ml.registry_client import describe_target, fetch_model, get_client
from app.ml.train_live_model import BASELINE_PATH, MODEL_PATH

client = get_client()

MODEL_NAME = "fx-exposure-monitor"

# Share of features that must drift before a live model is pulled back.
DRIFT_SHARE_THRESHOLD = 0.5


def _measure_drift(reference: pd.DataFrame, current: pd.DataFrame) -> tuple[float, int]:
    """
    Returns (share_of_features_drifted, count).

    Uses the same result-shape matching as drift_check.py: this Evidently
    version leaves metric_id unpopulated, so the summary metric is identified
    by being the one whose value is a {count, share} dict rather than by name.
    """
    report = Report([DataDriftPreset()])
    result = report.run(
        reference_data=reference[FEATURES],
        current_data=current[FEATURES],
    )
    summary = next(
        m for m in result.dict()["metrics"]
        if isinstance(m.get("value"), dict) and "share" in m["value"]
    )
    return float(summary["value"]["share"]), int(summary["value"]["count"])


def run():
    print(f"🕐 Live FX monitoring run — {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"📕 Registry: {describe_target()}\n")

    # Read the model's current stage back through the API rather than the DB,
    # so this behaves identically whether the registry is local or deployed.
    record = fetch_model(client, MODEL_NAME)
    if record is None:
        raise RuntimeError(
            f"{MODEL_NAME} isn't registered on {describe_target()}. "
            f"Run: python -m app.ml.register_live_model"
        )
    model_id, stage = record["id"], record["stage"]

    with open(MODEL_PATH, "rb") as f:
        detector = pickle.load(f)
    baseline = pd.read_csv(BASELINE_PATH)

    # 1. Genuinely current data — fetched now, and it grows every business day.
    start, end = current_window()
    current = snapshot(start, end)

    # 2. Score it.
    scores = -detector.score_samples(current[FEATURES])
    flagged = detector.predict(current[FEATURES]) == -1

    observed = {
        "anomaly_rate": float(flagged.mean()),
        "mean_anomaly_score": float(np.mean(scores)),
        "p99_anomaly_score": float(np.percentile(scores, 99)),
        "live_window_days": float(len(current)),
    }

    print(f"\n📊 Window {start} → {end}: {len(current)} trading days, "
          f"{int(flagged.sum())} flagged ({observed['anomaly_rate']:.1%})")

    if flagged.any():
        top = current.loc[flagged].copy()
        top["anomaly_score"] = scores[flagged]
        print("\n🚩 Days a treasury desk would want to look at:")
        for _, row in top.nlargest(min(5, len(top)), "anomaly_score").iterrows():
            print(
                f"   {row['observed_on']}  "
                f"worst mover {row['max_abs_move']:>6.2f}%  "
                f"USD/INR {row['usd_move']:>+6.2f}%  "
                f"{int(row['n_material_moves'])} material moves"
            )

    # 3. Everything goes into the registry through the API, not a side channel.
    for name, value in observed.items():
        client.post(
            f"/api/v1/models/{model_id}/metrics",
            json={"metric_name": name, "metric_value": value},
        )

    # 4. Has the market regime moved away from what the model learned?
    drift_share, drifted_count = _measure_drift(baseline, current)
    client.post(
        f"/api/v1/models/{model_id}/metrics",
        json={"metric_name": "drift_share", "metric_value": drift_share},
    )
    print(f"\n📉 Regime drift vs baseline: {drifted_count}/{len(FEATURES)} features "
          f"shifted ({drift_share:.0%}, threshold {DRIFT_SHARE_THRESHOLD:.0%})")

    # 5. Act on it — through the same gate a person would use.
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
                    f"training baseline, indicating the market regime has changed. "
                    f"Observed anomaly rate over {start} to {end} was "
                    f"{observed['anomaly_rate']:.1%} across {len(current)} trading "
                    f"days. Retrain on recent data before returning to production."
                ),
            },
        )
        print(f"   HTTP {resp.status_code} — stage is now '{resp.json().get('stage')}'")
    elif drift_share >= DRIFT_SHARE_THRESHOLD:
        print(f"\n⚠️  Drift over threshold, but the model is '{stage}', not live — "
              f"nothing to demote. Logged for whoever reviews it.")
    else:
        print("\n✅ Current market still resembles the training baseline. No action.")

    print("\n   Refresh the dashboard — the new measurements are already there.")
    return observed, drift_share


if __name__ == "__main__":
    run()
