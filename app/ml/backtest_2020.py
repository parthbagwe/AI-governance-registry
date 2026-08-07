"""
A real model, real data, and the month it stopped working.

Everything else in this registry demonstrates governance on data that happens
to be well-behaved. This reconstructs the case governance actually exists for:
a model that passed review, went live, and was then invalidated by the world
changing underneath it.

No simulation and no injected drift. Real ECB reference rates, 2018 to 2021.
The model is trained on 2018-2019 — a genuinely calm stretch for FX — promoted
to production in January 2020 on metrics that were, at the time, perfectly
good. Then it is walked forward month by month through 2020 and scored on data
it has never seen.

In March 2020 it breaks. Not gradually: the anomaly rate goes from a couple of
percent to a large fraction of all trading days, because a model whose notion
of "normal" was built in 2019 has nothing sensible to say about the pandemic
crash. The registry catches it on real dates, from real numbers, and pulls it
back for review.

This is registered as **v0.9.0** of fx-exposure-monitor — the same model name
as the version running today, a different version. That's the (name, version)
key doing exactly what it exists for: one model, two versions, one retired
after it failed and one live now, both on the record with their own histories.

Run:  python -m app.ml.backtest_2020
"""

from datetime import date, datetime

import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset
from sklearn.ensemble import IsolationForest

from app.ml.live_feed import FEATURES, engineer_features, fetch_rates
from app.ml.registry_client import describe_target, get_client

client = get_client()

MODEL_NAME = "fx-exposure-monitor"
VERSION = "v0.9.0"

# Training window: two years of unremarkable FX. This is what the model
# believed "normal" looked like.
TRAIN_START = date(2018, 1, 1)
TRAIN_END = date(2019, 12, 31)

# Evaluation window: walked forward a month at a time, none of it seen in
# training. Runs past the crash so the recovery is visible too.
TEST_START = date(2020, 1, 1)
TEST_END = date(2021, 6, 30)

CONTAMINATION = 0.02
DRIFT_SHARE_THRESHOLD = 0.5

# Above this share of days flagged in a single month, the model isn't
# detecting anomalies any more — it's failing to describe the market at all.
BROKEN_ANOMALY_RATE = 0.25


def _month_ends(start: date, end: date) -> list[pd.Timestamp]:
    return list(pd.date_range(start, end, freq="ME"))


def _measure_drift(reference: pd.DataFrame, current: pd.DataFrame) -> tuple[float, int]:
    """Share of features whose distribution has shifted. Same result-shape
    matching as the other monitors — this Evidently version leaves metric_id
    unpopulated, so the summary metric is the one whose value is a
    {count, share} dict."""
    report = Report([DataDriftPreset()])
    result = report.run(reference_data=reference[FEATURES], current_data=current[FEATURES])
    summary = next(
        m for m in result.dict()["metrics"]
        if isinstance(m.get("value"), dict) and "share" in m["value"]
    )
    return float(summary["value"]["share"]), int(summary["value"]["count"])


def _log(model_id: str, name: str, value: float, when: datetime) -> None:
    """Metrics are backfilled to the date they describe — that's what makes the
    chart tell the story rather than showing eighteen months of history
    collapsed into one timestamp."""
    resp = client.post(
        f"/api/v1/models/{model_id}/metrics",
        json={
            "metric_name": name,
            "metric_value": float(value),
            "recorded_at": when.isoformat(),
        },
    )
    if resp.status_code != 201:
        raise RuntimeError(f"Failed to log {name}: HTTP {resp.status_code} {resp.text}")


def _reset_scenario(model_id: str) -> None:
    """
    Clears this version's metrics and events so the backtest can be re-run
    without stacking duplicates.

    Deleting audit events is exactly the thing this project argues against, so
    the boundary matters: this runs against one specific scenario version,
    from a local script, over a direct DB connection. The API exposes no
    delete for either table, and nothing reachable over HTTP can do this. A
    scenario you can rebuild is not the same as a record you can rewrite.
    """
    from app.database import SessionLocal
    from app.models.registry import ApprovalEvent, ModelMetric

    db = SessionLocal()
    try:
        events = db.query(ApprovalEvent).filter(ApprovalEvent.model_id == model_id).delete()
        metrics = db.query(ModelMetric).filter(ModelMetric.model_id == model_id).delete()
        db.commit()
        if events or metrics:
            print(f"   cleared {events} prior event(s) and {metrics} metric(s) — rebuilding.")
    finally:
        db.close()


def _record_history(model_id: str, events: list[dict]) -> None:
    """
    Writes the historical lifecycle straight to the database.

    Not through the API, on purpose. The API has no way to backdate an
    approval, and it shouldn't — an audit trail whose timestamps can be chosen
    isn't an audit trail. But this script isn't *operating* the registry, it's
    *constructing a past scenario*, which is the same thing seed.py does. The
    distinction is worth keeping sharp: the live system can't rewrite history,
    and the scenario builder isn't part of the live system.
    """
    from app.database import SessionLocal
    from app.models.registry import ApprovalEvent, MLModel, ModelStage

    db = SessionLocal()
    try:
        for e in events:
            db.add(ApprovalEvent(
                model_id=model_id,
                from_stage=e["from"],
                to_stage=e["to"],
                approved_by=e["by"],
                comment=e["comment"],
                created_at=e["at"],
            ))
        final = events[-1]["to"]
        db.query(MLModel).filter(MLModel.id == model_id).update({"stage": final})
        db.commit()
    finally:
        db.close()


def run():
    print(f"📕 Registry: {describe_target()}\n")
    print("Pulling real ECB reference rates, 2018 → 2021…")

    rates = fetch_rates(TRAIN_START, TEST_END, quiet=True)
    features = engineer_features(rates)
    features["observed_on"] = pd.to_datetime(features["observed_on"])

    train = features[features["observed_on"] <= pd.Timestamp(TRAIN_END)]
    print(f"✅ {len(features)} business days total; {len(train)} in the training window.\n")

    # ---- Train on 2018-2019 only -------------------------------------------
    detector = IsolationForest(
        n_estimators=200, contamination=CONTAMINATION, random_state=42, n_jobs=-1
    )
    detector.fit(train[FEATURES])

    train_scores = -detector.score_samples(train[FEATURES])
    print("Trained on 2018-2019. At the time, this looked like a good model:")
    print(f"   flag rate on training data : {(detector.predict(train[FEATURES]) == -1).mean():.1%}")
    print(f"   mean anomaly score         : {train_scores.mean():.4f}\n")

    # ---- Register it as a historical version --------------------------------
    resp = client.post("/api/v1/models", json={
        "name": MODEL_NAME,
        "version": VERSION,
        "model_type": "traditional_ml",
        "use_case": (
            "Daily FX exposure anomaly detection — original version, trained on "
            "2018-2019 data and retired after the March 2020 market dislocation"
        ),
        "owner": "treasury-risk-team",
        "risk_tier": "medium",
        "extra_metadata": {
            "framework": "sklearn.IsolationForest",
            "training_window": f"{TRAIN_START} to {TRAIN_END}",
            "data_source": "ECB reference rates (real, historical)",
            "retired_because": "March 2020 pandemic market dislocation",
        },
    })
    if resp.status_code == 409:
        print(f"ℹ️  {VERSION} already registered — reusing it.")
        existing = client.get("/api/v1/models").json()
        model = next(
            m for m in existing
            if m["name"] == MODEL_NAME and m["version"] == VERSION
        )
    elif resp.status_code != 201:
        raise RuntimeError(f"Registration failed: HTTP {resp.status_code} {resp.text}")
    else:
        model = resp.json()

    model_id = model["id"]
    print(f"✅ Registered {MODEL_NAME} {VERSION} (id={model_id})")

    _reset_scenario(model_id)

    client.post(f"/api/v1/models/{model_id}/lineage", json={
        "source_table": "ecb_reference_rates_2018_2019",
        "features_used": list(FEATURES),
        "notes": (
            "REAL historical ECB reference rates. Trained on 2018-2019 and "
            "evaluated month by month across 2020-2021 on data it never saw. "
            "The degradation recorded against this version is genuine market "
            "history, not injected drift."
        ),
    })

    # The scores it was signed off on. Respectable for a medium-tier model,
    # and entirely accurate for the world as it stood in January 2020 — which
    # is the uncomfortable part. Nothing here was negligent.
    scores_resp = client.patch(f"/api/v1/models/{model_id}/scores", json={
        "efficiency_score": 8.0,
        "adoption_score": 7.5,
        "input_quality_score": 8.5,
        "cost_reduction_score": 6.5,
        "revenue_impact_score": 7.0,
    })
    if scores_resp.status_code != 200:
        raise RuntimeError(
            f"Failed to set scores: HTTP {scores_resp.status_code} {scores_resp.text}"
        )
    print("✅ Governance scorecard set to 7.5/10 — it genuinely passed review.")

    # ---- Walk forward through 2020-2021 ------------------------------------
    print("\nWalking forward, one month at a time, on data the model never saw:\n")
    print(f"   {'month':<10} {'days':>5} {'flagged':>9} {'drift':>7}   verdict")
    print("   " + "-" * 58)

    broke_on: pd.Timestamp | None = None
    worst_rate = 0.0

    for month_end in _month_ends(TEST_START, TEST_END):
        month_start = month_end.replace(day=1)
        window = features[
            (features["observed_on"] >= month_start)
            & (features["observed_on"] <= month_end)
        ]
        if len(window) < 5:
            continue

        flagged = detector.predict(window[FEATURES]) == -1
        scores = -detector.score_samples(window[FEATURES])
        rate = float(flagged.mean())
        drift_share, drifted_count = _measure_drift(train, window)

        stamp = month_end.to_pydatetime()
        _log(model_id, "anomaly_rate", rate, stamp)
        _log(model_id, "mean_anomaly_score", float(scores.mean()), stamp)
        _log(model_id, "drift_share", drift_share, stamp)
        _log(model_id, "days_observed", float(len(window)), stamp)

        if rate > worst_rate:
            worst_rate = rate
        if broke_on is None and rate >= BROKEN_ANOMALY_RATE:
            broke_on = month_end

        verdict = (
            "⚠️  BREAKING DOWN" if rate >= BROKEN_ANOMALY_RATE
            else "elevated" if rate > CONTAMINATION * 3
            else "normal"
        )
        print(f"   {month_end:%Y-%m}    {len(window):>5} {rate:>8.1%} {drift_share:>7.0%}   {verdict}")

    # ---- Write the lifecycle it actually had --------------------------------
    print()
    if broke_on is None:
        print("No month crossed the breakdown threshold — unexpected for this window.")
        return

    _record_history(model_id, _lifecycle(broke_on, worst_rate))

    print(f"🚨 The model stopped working in {broke_on:%B %Y}: "
          f"{worst_rate:.0%} of trading days flagged as anomalous.")
    print()
    print("   For context, it was configured to expect 2%. A detector firing on")
    print("   a third of all days isn't detecting anything — it's telling you")
    print("   its idea of 'normal' no longer exists.")
    print()
    print(f"✅ Lifecycle written. Open {MODEL_NAME} {VERSION} in the dashboard:")
    print("   the chart shows a flat line through January and February and then")
    print("   a cliff, and the audit trail shows it being pulled on the date it")
    print("   happened — from real rates, with nothing injected.")


def _lifecycle(broke_on: pd.Timestamp, worst_rate: float) -> list[dict]:
    """The stages this version actually went through, on the dates it went
    through them."""
    from app.models.registry import ModelStage

    return [
        {
            "from": None, "to": ModelStage.PILOT, "by": "treasury-risk-team",
            "at": datetime(2019, 9, 2),
            "comment": "Registered for pilot. Trained on 2018-2019 FX reference rates.",
        },
        {
            "from": ModelStage.PILOT, "to": ModelStage.REVIEW, "by": "s.rao",
            "at": datetime(2019, 11, 4),
            "comment": "Two months of stable pilot metrics. Submitting for independent review.",
        },
        {
            "from": ModelStage.REVIEW, "to": ModelStage.PRODUCTION, "by": "risk-committee",
            "at": datetime(2020, 1, 6),
            "comment": (
                "Approved for production. Governance score 7.5/10, clearing the 7.0 "
                "bar for a medium-tier model. Flag rate stable at ~2% across the "
                "validation window."
            ),
        },
        {
            "from": ModelStage.PRODUCTION, "to": ModelStage.REVIEW,
            "by": "drift-monitor-service",
            "at": broke_on.to_pydatetime(),
            "comment": (
                f"Auto-demoted from production. Anomaly rate reached {worst_rate:.0%} "
                f"of trading days against a configured expectation of 2%, with input "
                f"feature distributions diverging sharply from the 2018-2019 training "
                f"baseline. The model's definition of a normal trading day no longer "
                f"corresponds to the market. Not a data quality fault — a regime change."
            ),
        },
        {
            "from": ModelStage.REVIEW, "to": ModelStage.DEPRECATED, "by": "risk-committee",
            "at": datetime(2020, 6, 15),
            "comment": (
                "Retired. Retraining on pre-2020 data cannot recover this version; "
                "the volatility regime it encodes no longer exists. Superseded by a "
                "successor trained on a window that includes the dislocation."
            ),
        },
    ]


if __name__ == "__main__":
    run()
