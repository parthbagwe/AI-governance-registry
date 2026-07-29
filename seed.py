"""
Creates all tables and seeds the registry with 3 realistic model entries:

1. sme-credit-scorer   (traditional_ml) -> already in production
2. fraud-flagger       (traditional_ml) -> in review, borderline governance score
3. rm-copilot-intents  (slm)            -> pilot, just registered
"""

from datetime import datetime, timedelta
import random

from app.database import Base, engine, SessionLocal
from app.models.registry import (
    MLModel, ModelMetric, ApprovalEvent, DataLineage, ModelType, ModelStage
)

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Model 1: SME Credit Scorer -> already promoted to production
sme_model = MLModel(
    name="sme-credit-scorer",
    version="v1.0.0",
    model_type=ModelType.TRADITIONAL_ML,
    use_case="SME dynamic credit line scoring using GST + transaction data",
    owner="risk-analytics-team",
    stage=ModelStage.PRODUCTION,
    efficiency_score=8.5,
    adoption_score=9.0,
    input_quality_score=8.0,
    cost_reduction_score=7.5,
    revenue_impact_score=8.8,
    extra_metadata={"framework": "xgboost", "n_features": 14, "training_rows": 50000},
)
db.add(sme_model)
db.flush()

db.add(DataLineage(
    model_id=sme_model.id,
    source_table="gst_returns",
    features_used=["avg_monthly_turnover", "filing_delay_days", "itc_claim_ratio"],
    notes="Monthly GST filing data, 24-month lookback window",
))
db.add(DataLineage(
    model_id=sme_model.id,
    source_table="bank_transactions",
    features_used=["avg_balance", "inflow_volatility", "bounce_count_90d"],
))

db.add(ApprovalEvent(
    model_id=sme_model.id, from_stage=None, to_stage=ModelStage.PILOT,
    approved_by="a.sharma", comment="Initial registration for pilot testing",
    created_at=datetime.utcnow() - timedelta(days=60),
))
db.add(ApprovalEvent(
    model_id=sme_model.id, from_stage=ModelStage.PILOT, to_stage=ModelStage.REVIEW,
    approved_by="a.sharma", comment="Pilot metrics stable over 30 days, moving to review",
    created_at=datetime.utcnow() - timedelta(days=30),
))
db.add(ApprovalEvent(
    model_id=sme_model.id, from_stage=ModelStage.REVIEW, to_stage=ModelStage.PRODUCTION,
    approved_by="risk-committee", comment="Governance score 8.36/10, approved for production",
    created_at=datetime.utcnow() - timedelta(days=10),
))

# 45 days of healthy accuracy metrics, then a *drift* in the last 10 days
for day in range(45, 0, -1):
    ts = datetime.utcnow() - timedelta(days=day)
    if day > 10:
        acc = random.uniform(0.90, 0.93)   # healthy
    else:
        acc = random.uniform(0.78, 0.84)   # degraded -> should trigger drift alert
    db.add(ModelMetric(model_id=sme_model.id, metric_name="accuracy", metric_value=acc, recorded_at=ts))
    db.add(ModelMetric(model_id=sme_model.id, metric_name="latency_ms", metric_value=random.uniform(40, 60), recorded_at=ts))

# Model 2: Fraud Flagger -> in review, mediocre governance score
fraud_model = MLModel(
    name="fraud-flagger",
    version="v2.1.0",
    model_type=ModelType.TRADITIONAL_ML,
    use_case="Cross-border transaction fraud detection",
    owner="fraud-ops-team",
    stage=ModelStage.REVIEW,
    efficiency_score=7.0,
    adoption_score=5.5,
    input_quality_score=6.5,
    cost_reduction_score=6.0,
    revenue_impact_score=None,
)
db.add(fraud_model)
db.flush()

db.add(DataLineage(
    model_id=fraud_model.id,
    source_table="cross_border_transactions",
    features_used=["txn_velocity_1h", "new_beneficiary_flag", "country_risk_score"],
))
db.add(ApprovalEvent(
    model_id=fraud_model.id, from_stage=None, to_stage=ModelStage.PILOT,
    approved_by="s.rao", comment="Initial pilot, SWIFT-style cross-border fraud pattern",
    created_at=datetime.utcnow() - timedelta(days=20),
))
db.add(ApprovalEvent(
    model_id=fraud_model.id, from_stage=ModelStage.PILOT, to_stage=ModelStage.REVIEW,
    approved_by="s.rao", comment="Moved to review, adoption still low pending ops training",
    created_at=datetime.utcnow() - timedelta(days=5),
))
for day in range(20, 0, -1):
    ts = datetime.utcnow() - timedelta(days=day)
    db.add(ModelMetric(model_id=fraud_model.id, metric_name="precision", metric_value=random.uniform(0.70, 0.78), recorded_at=ts))

# Model 3: RM Copilot Intent Classifier -> fresh pilot (SLM)
rm_model = MLModel(
    name="rm-copilot-intents",
    version="v0.1.0",
    model_type=ModelType.SLM,
    use_case="Relationship manager copilot: classify client query intent",
    owner="cx-ai-team",
    stage=ModelStage.PILOT,
    efficiency_score=6.0,
    adoption_score=None,
    input_quality_score=7.0,
    cost_reduction_score=None,
    revenue_impact_score=None,
)
db.add(rm_model)
db.flush()

db.add(DataLineage(
    model_id=rm_model.id,
    source_table="rm_client_interaction_logs",
    features_used=["query_text", "client_segment", "past_product_holdings"],
))
db.add(ApprovalEvent(
    model_id=rm_model.id, from_stage=None, to_stage=ModelStage.PILOT,
    approved_by="n.iyer", comment="Just registered, baseline metrics pending",
    created_at=datetime.utcnow() - timedelta(days=2),
))

db.commit()
db.close()

print("✅ Database seeded: governance.db")