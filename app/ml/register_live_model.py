"""
Registers fx-exposure-monitor in the governance registry.

This is the only model in the portfolio whose data source is *live* rather
than a stored file. Its lineage records the actual endpoint, so anyone
auditing the registry can go and pull the same numbers themselves — which is
the entire point of recording lineage rather than describing it in a wiki.

Run this AFTER:
    python -m app.ml.live_feed        (builds live_baseline.csv)
    python -m app.ml.train_live_model (trains fx_anomaly_model.pkl)
"""

from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.registry import DataLineage
from app.ml.live_feed import API_ROOT, BASE, BASKET, FEATURES
from app.ml.train_live_model import train

client = TestClient(app)

MODEL_NAME = "fx-exposure-monitor"


def register_and_log():
    resp = client.post("/api/v1/models", json={
        "name": MODEL_NAME,
        "version": "v1.0.0",
        "model_type": "traditional_ml",
        "use_case": (
            "Daily FX exposure anomaly detection across the bank's currency "
            "basket — flags abnormal trading days for treasury review"
        ),
        "owner": "treasury-risk-team",
        # Medium tier: this moves the bank's own book and desk attention, not
        # a customer's access to their money. Tiering it 'high' alongside the
        # credit models would be inflating it, and the whole point of tiering
        # is that it means something.
        "risk_tier": "medium",
        "extra_metadata": {
            "framework": "sklearn.IsolationForest",
            "supervision": "unsupervised",
            "data_source": "live_public_api",
            "provider": "ECB reference rates via frankfurter.dev",
            "base_currency": BASE,
            "basket": BASKET,
        },
    })

    if resp.status_code == 409:
        # Expected on a re-run: this version already exists. Reuse it rather
        # than creating a duplicate — the registry treats (name, version) as
        # an identity, so a second row would be a second model.
        print("ℹ️  Already registered — reusing the existing entry.")
        models = client.get("/api/v1/models").json()
        model = next((m for m in models if m["name"] == MODEL_NAME), None)
        if not model:
            raise RuntimeError(f"Registry says {MODEL_NAME} exists, but it isn't listed.")
    elif resp.status_code != 201:
        raise RuntimeError(f"Registration failed: HTTP {resp.status_code} {resp.text}")
    else:
        model = resp.json()

    model_id = model["id"]
    print(f"✅ Registered {MODEL_NAME} (id={model_id})")

    # Lineage goes in through the DB session directly — there is no create
    # endpoint for it, deliberately. Lineage is set once at registration and
    # shouldn't be casually editable through the API afterwards.
    db = SessionLocal()
    if not db.query(DataLineage).filter(DataLineage.model_id == model_id).first():
        db.add(DataLineage(
            model_id=model_id,
            source_table=f"live: {API_ROOT} (ECB reference rates)",
            features_used=list(FEATURES),
            notes=(
                "LIVE public API — rates are fetched at monitoring time, not read "
                "from a stored file, so each run sees business days that did not "
                "exist on the previous run. Unlike the credit models in this "
                f"portfolio, no simulation is involved: these are the same {BASE}-based "
                "ECB reference rates a treasury desk works from. Basket: "
                + ", ".join(BASKET) + "."
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

    print(f"\n✅ {MODEL_NAME} registered with its real-market baseline.")
    print("   It starts in PILOT with no governance scores — so it cannot reach")
    print("   production until someone actually evaluates it. That's the gate")
    print("   working, not an oversight.")
    print("\n   Next: python -m app.ml.live_monitor")


if __name__ == "__main__":
    register_and_log()
