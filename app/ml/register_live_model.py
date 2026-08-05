"""
Registers payment-anomaly-monitor in the governance registry.

This is the only model in the portfolio whose data source is *live* rather
than a file. Its lineage says so explicitly, with the actual endpoint recorded
— so anyone auditing the registry can go and look at the same feed themselves,
which is the entire point of recording lineage in the first place.

Run this AFTER:
    python -m app.ml.live_feed        (builds live_baseline.csv)
    python -m app.ml.train_live_model (trains payment_anomaly_model.pkl)
"""

from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.registry import DataLineage
from app.ml.live_feed import FEATURES, RECENT_URL
from app.ml.train_live_model import train

client = TestClient(app)

MODEL_NAME = "payment-anomaly-monitor"


def register_and_log():
    resp = client.post("/api/v1/models", json={
        "name": MODEL_NAME,
        "version": "v1.0.0",
        "model_type": "traditional_ml",
        "use_case": (
            "Real-time payment anomaly detection on a live settlement feed — "
            "stand-in for cross-border payment fraud monitoring"
        ),
        "owner": "fraud-ops-team",
        # High tier: a flag here holds someone's payment. Getting it wrong in
        # either direction is expensive — a missed alert costs money, a false
        # one blocks a legitimate customer mid-transaction.
        "risk_tier": "high",
        "extra_metadata": {
            "framework": "sklearn.IsolationForest",
            "supervision": "unsupervised",
            "data_source": "live_public_api",
            "endpoint": RECENT_URL,
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

    # Lineage goes in via the DB session directly — there's no create endpoint
    # for it, deliberately: lineage is set once at registration and shouldn't
    # be casually editable through the API afterwards.
    db = SessionLocal()
    if not db.query(DataLineage).filter(DataLineage.model_id == model_id).first():
        db.add(DataLineage(
            model_id=model_id,
            source_table=f"live: {RECENT_URL}",
            features_used=list(FEATURES),
            notes=(
                "LIVE public API — data is fetched at monitoring time, not read "
                "from a stored file, so every run sees traffic that did not exist "
                "on the previous run. Real cross-border payment traffic (SWIFT, "
                "RTGS) is private and has no public feed; a public settlement "
                "ledger is used as an observable stand-in so the monitoring loop "
                "runs against genuinely arriving data rather than a replayed CSV."
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

    print(f"\n✅ {MODEL_NAME} registered with its live baseline.")
    print("   It starts in PILOT with no governance scores — so it cannot")
    print("   reach production until someone actually evaluates it. That's")
    print("   the gate working, not an oversight.")
    print("\n   Next: python -m app.ml.live_monitor")


if __name__ == "__main__":
    register_and_log()
