"""
Registers fx-intraday-monitor in the governance registry.

Note the risk tier: HIGH, where the daily fx-exposure-monitor is MEDIUM —
despite both watching the same currency pair, built by the same team, on the
same kind of model.

The difference isn't technical. The daily model's output lands on an analyst's
desk the next morning; a person decides what to do about it. A 1-minute model
is fast enough to feed automated hedging, which means its output can move money
with nobody in the loop. Removing the human is what raises the tier.

This matters for a demo: it's a case where the *same signal* needs different
governance depending on how it's consumed. Under the tiering rules, this model
now needs 8.5 to reach production where its daily sibling needs 7.0 — so the
faster model is held to the stricter bar, which is the right way round.

Run AFTER:
    python -m app.ml.intraday_feed
    python -m app.ml.train_intraday_model
"""

from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.registry import DataLineage
from app.ml.intraday_feed import API_URL, FEATURES, INTERVAL, SYMBOL
from app.ml.train_intraday_model import train

client = TestClient(app)

MODEL_NAME = "fx-intraday-monitor"


def register_and_log():
    resp = client.post("/api/v1/models", json={
        "name": MODEL_NAME,
        "version": "v1.0.0",
        "model_type": "traditional_ml",
        "use_case": (
            f"Intraday {SYMBOL} anomaly detection on {INTERVAL} bars — "
            f"feeds automated hedging with no human in the loop"
        ),
        "owner": "treasury-risk-team",
        # High tier — see the module docstring. Speed without a human reviewer
        # is the risk, not the model.
        "risk_tier": "high",
        "extra_metadata": {
            "framework": "sklearn.IsolationForest",
            "supervision": "unsupervised",
            "data_source": "live_market_api",
            "provider": "Twelve Data",
            "symbol": SYMBOL,
            "interval": INTERVAL,
            "human_in_the_loop": False,
        },
    })

    if resp.status_code != 201:
        print(f"⚠️  Already registered? HTTP {resp.status_code}")
        models = client.get("/api/v1/models").json()
        model = next((m for m in models if m["name"] == MODEL_NAME), None)
        if not model:
            raise RuntimeError(f"Could not register or find {MODEL_NAME}.")
    else:
        model = resp.json()

    model_id = model["id"]
    print(f"✅ Registered {MODEL_NAME} (id={model_id})")

    db = SessionLocal()
    if not db.query(DataLineage).filter(DataLineage.model_id == model_id).first():
        db.add(DataLineage(
            model_id=model_id,
            source_table=f"live: {API_URL} ({SYMBOL} @ {INTERVAL})",
            features_used=list(FEATURES),
            notes=(
                f"LIVE market data — {INTERVAL} {SYMBOL} bars fetched at monitoring "
                "time, so every run sees minutes that did not exist on the previous "
                "run. Same market as fx-exposure-monitor, but tiered HIGH rather "
                "than MEDIUM because this model is fast enough to drive automated "
                "hedging without a human reviewer between its output and the "
                "action. Features are expressed in basis points rather than price "
                "so the model does not silently break if the pair re-rates."
            ),
        ))
        db.commit()
        print("✅ Lineage recorded (flagged as a live source).")
    db.close()

    _, metrics = train()
    for name, value in metrics.items():
        client.post(
            f"/api/v1/models/{model_id}/metrics",
            json={"metric_name": name, "metric_value": value},
        )
        print(f"  logged {name} = {value:.4f}")

    print(f"\n✅ {MODEL_NAME} registered.")
    print("   It's HIGH risk, so it needs a governance score of 8.5 to go live —")
    print("   a stricter bar than the daily model watching the same market.")
    print("   That's the tiering doing its job, not a misconfiguration.")
    print("\n   Next: python -m app.ml.intraday_monitor")


if __name__ == "__main__":
    register_and_log()
