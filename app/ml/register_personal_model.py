"""
Registers personal-loan-credit-scorer as a new model in the governance
registry, logs its real training metrics, and records its data lineage —
explicitly noting it's trained on REAL Kaggle data, unlike sme-credit-scorer
which stays synthetic (since real GST data isn't public).

Run this AFTER prepare_real_data.py and train_personal_model.py.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.registry import DataLineage
from app.ml.train_personal_model import train

client = TestClient(app)


def register_and_log():
    # 1. Register the model (starts in PILOT by default)
    resp = client.post("/api/v1/models", json={
        "name": "personal-loan-credit-scorer",
        "version": "v1.0.0",
        "model_type": "traditional_ml",
        "use_case": "Personal loan default risk scoring, trained on real historical credit data",
        "owner": "risk-analytics-team",
        "risk_tier": "high",  # directly decides individual customers' credit access
    })
    if resp.status_code == 409:
        # Expected on a re-run: this version already exists. Reuse it rather
        # than creating a duplicate — the registry treats (name, version) as
        # an identity, so a second row would be a second model.
        print("ℹ️  Already registered — reusing the existing entry.")
        models = client.get("/api/v1/models").json()
        model = next((m for m in models if m["name"] == "personal-loan-credit-scorer"), None)
        if not model:
            raise RuntimeError("Registry says the model exists, but it isn't listed.")
    elif resp.status_code != 201:
        raise RuntimeError(f"Registration failed: HTTP {resp.status_code} {resp.text}")
    else:
        model = resp.json()

    model_id = model["id"]
    print(f"✅ Registered personal-loan-credit-scorer (id={model_id})")

    # 2. Record data lineage directly via DB session (no API endpoint exists
    # for creating lineage — only for reading it, since lineage is meant to
    # be set once at registration time, not edited casually through the API)
    db = SessionLocal()
    existing = db.query(DataLineage).filter(DataLineage.model_id == model_id).first()
    if not existing:
        db.add(DataLineage(
            model_id=model_id,
            source_table="kaggle_give_me_some_credit_2011",
            features_used=[
                "revolving_utilization", "age", "late_30_59_days", "debt_ratio",
                "monthly_income", "open_credit_lines", "late_90_days",
                "real_estate_loans", "late_60_89_days", "dependents",
            ],
            notes=(
                "REAL public dataset (Kaggle 'Give Me Some Credit', 2011 competition), "
                "unlike sme-credit-scorer which uses synthetic data since real GST "
                "filing records are not publicly available."
            ),
        ))
        db.commit()
        print("✅ Data lineage recorded (flagged as real public data).")
    db.close()

    # 3. Train and log real metrics
    _, metrics = train()
    for metric_name, value in metrics.items():
        client.post(
            f"/api/v1/models/{model_id}/metrics",
            json={"metric_name": f"real_{metric_name}", "metric_value": value},
        )
        print(f"  logged real_{metric_name} = {value:.4f}")

    print(f"\n✅ personal-loan-credit-scorer fully registered with real training metrics.")
    print(f"   View it in the dashboard alongside your other 8 models.")


if __name__ == "__main__":
    register_and_log()