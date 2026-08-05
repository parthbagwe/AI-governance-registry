"""
Intraday monitoring loop — run it repeatedly and watch the registry fill up.

This is the one that answers "how do I know it's actually live?" with a number
rather than an assurance. Every run reports how many of the bars it just
fetched did not exist in the training baseline. Run it twice a minute apart and
that count goes up. Run it against a replayed file and it would be zero,
forever.

Each run:
  1. Fetches the latest 1-minute bars from the market.
  2. Reports how many are genuinely new since the baseline was captured.
  3. Scores them and logs the observed metrics to the registry.
  4. Runs drift detection against the baseline.
  5. Demotes the model if it's live and the regime has moved — through the
     same /approve endpoint a human uses, with no bypass.

Cheap to run: one API credit per invocation, against a free tier of 800/day.
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
from app.ml.intraday_feed import BASELINE_PATH, DRIFT_FEATURES, FEATURES, snapshot
from app.ml.train_intraday_model import MODEL_PATH

client = TestClient(app)

MODEL_NAME = "fx-intraday-monitor"

DRIFT_SHARE_THRESHOLD = 0.5

# Bars pulled per run. Enough context for the rolling range feature to be
# meaningful, small enough to stay light on a free API tier.
BARS_PER_RUN = 200


def _measure_drift(reference: pd.DataFrame, current: pd.DataFrame) -> tuple[float, int]:
    """
    Returns (share_of_features_drifted, count).

    Measured on DRIFT_FEATURES, not FEATURES — the clock is excluded on
    purpose. A monitored window covers a few hours and the baseline covers a
    full day, so the time-of-day features differ between them by construction,
    on every run, forever. Letting them count would mean permanently reporting
    drift because time passed.

    Same result-shape matching as the other monitors: this Evidently version
    leaves metric_id unpopulated, so the summary metric is found by being the
    one whose value is a {count, share} dict.
    """
    report = Report([DataDriftPreset()])
    result = report.run(
        reference_data=reference[DRIFT_FEATURES],
        current_data=current[DRIFT_FEATURES],
    )
    summary = next(
        m for m in result.dict()["metrics"]
        if isinstance(m.get("value"), dict) and "share" in m["value"]
    )
    return float(summary["value"]["share"]), int(summary["value"]["count"])


def run():
    print(f"🕐 Intraday monitoring run — {datetime.now():%Y-%m-%d %H:%M:%S}\n")

    db = SessionLocal()
    record = db.query(MLModel).filter(MLModel.name == MODEL_NAME).first()
    if record is None:
        db.close()
        raise RuntimeError(
            f"{MODEL_NAME} isn't registered yet. "
            f"Run: python -m app.ml.register_intraday_model"
        )
    model_id, stage = record.id, record.stage.value
    db.close()

    with open(MODEL_PATH, "rb") as f:
        detector = pickle.load(f)
    baseline = pd.read_csv(BASELINE_PATH)

    # 1. Fetch.
    current = snapshot(outputsize=BARS_PER_RUN)

    # 2. Liveness, as a number. Bars are identified by their timestamp, so
    # "new" means a minute that had not happened when the baseline was taken.
    seen = set(baseline["observed_at"])
    fresh = current[~current["observed_at"].isin(seen)]
    newest = current["observed_at"].iloc[-1]

    print(f"\n🔴 {len(fresh)} of {len(current)} bars are new since the baseline "
          f"was captured.")
    print(f"   Most recent bar: {newest} UTC at {current['close'].iloc[-1]:.5f}")
    if len(fresh) == 0:
        print("   (Zero is expected if you just built the baseline — wait a few")
        print("    minutes and run again to watch this climb.)")

    # 3. Score.
    scores = -detector.score_samples(current[FEATURES])
    flagged = detector.predict(current[FEATURES]) == -1

    observed = {
        "anomaly_rate": float(flagged.mean()),
        "mean_anomaly_score": float(np.mean(scores)),
        "p99_anomaly_score": float(np.percentile(scores, 99)),
        "live_window_bars": float(len(current)),
        "new_bars_since_baseline": float(len(fresh)),
        "latest_price": float(current["close"].iloc[-1]),
    }

    print(f"\n📊 {len(current)} bars scored, {int(flagged.sum())} flagged "
          f"({observed['anomaly_rate']:.1%})")

    if flagged.any():
        top = current.loc[flagged].copy()
        top["anomaly_score"] = scores[flagged]
        print("\n🚩 Minutes worth a second look:")
        for _, row in top.nlargest(min(5, len(top)), "anomaly_score").iterrows():
            kind = "wick" if row["body_ratio"] < 0.35 else "directional"
            print(
                f"   {row['observed_at']} UTC  "
                f"move {row['return_bps']:>+7.2f}bps  "
                f"range {row['range_bps']:>6.2f}bps  "
                f"({row['range_vs_recent']:>5.1f}× recent)  {kind}"
            )

    # 4. Log everything through the API, not a side channel.
    for name, value in observed.items():
        client.post(
            f"/api/v1/models/{model_id}/metrics",
            json={"metric_name": name, "metric_value": value},
        )

    drift_share, drifted_count = _measure_drift(baseline, current)
    client.post(
        f"/api/v1/models/{model_id}/metrics",
        json={"metric_name": "drift_share", "metric_value": drift_share},
    )
    print(f"\n📉 Drift vs baseline: {drifted_count}/{len(DRIFT_FEATURES)} market "
          f"features shifted ({drift_share:.0%}, threshold {DRIFT_SHARE_THRESHOLD:.0%})")

    # Honest caveat, printed rather than buried: FX has strong intraday
    # seasonality. A window drawn entirely from the quiet Asian session will
    # look different from a baseline spanning London and New York too, and
    # that difference is the clock, not a regime change. The model handles
    # this — it has the time features — but this comparison doesn't yet.
    # Restricting the baseline to matching hours is the outstanding fix.
    if len(current) < 0.4 * len(baseline):
        print("   ⚠️  This window is much shorter than the baseline, so some of")
        print("       the reported drift is session composition rather than a")
        print("       genuine regime change. Read it with that in mind.")

    # 5. Act, through the same gate a person would use.
    if drift_share >= DRIFT_SHARE_THRESHOLD and stage == "production":
        print("\n🚨 Drift over threshold on a live model — pulling it back for review.")
        resp = client.post(
            f"/api/v1/models/{model_id}/approve",
            json={
                "to_stage": "review",
                "approved_by": "intraday-monitor-service",
                "comment": (
                    f"Auto-demoted from live: {drift_share:.0%} of market features "
                    f"({drifted_count}/{len(DRIFT_FEATURES)}) have shifted away from "
                    f"the training baseline, indicating the intraday volatility regime "
                    f"has changed. Observed anomaly rate was "
                    f"{observed['anomaly_rate']:.1%} across {len(current)} bars "
                    f"ending {newest} UTC. Retrain on current market conditions "
                    f"before returning this model to production."
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
    print("   Run this again in a few minutes and watch the new-bar count climb.")
    return observed, drift_share


if __name__ == "__main__":
    run()
