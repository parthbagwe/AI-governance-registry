"""
Creates all tables and seeds the registry with 3 realistic model entries:

1. sme-credit-scorer   (traditional_ml) -> already in production
2. fraud-flagger       (traditional_ml) -> in review, borderline governance score
3. rm-copilot-intents  (slm)            -> pilot, just registered

Run with: python seed.py
"""

from datetime import datetime, timedelta
import random

from app.database import Base, engine, SessionLocal
from app.models.registry import (
    MLModel, ModelMetric, ApprovalEvent, DataLineage, ModelType, ModelStage, RiskTier
)

# Fresh start every time we seed, so this script is idempotent for demos
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# ---------------------------------------------------------------
# Model 1: SME Credit Scorer -> already promoted to production
# ---------------------------------------------------------------
sme_model = MLModel(
    name="sme-credit-scorer",
    version="v1.0.0",
    model_type=ModelType.TRADITIONAL_ML,
    use_case="SME dynamic credit line scoring using GST + transaction data",
    owner="risk-analytics-team",
    stage=ModelStage.PRODUCTION,
    risk_tier=RiskTier.HIGH,  # directly decides customers' credit access -> highest RBI scrutiny
    efficiency_score=8.5,
    adoption_score=9.0,
    input_quality_score=8.0,
    cost_reduction_score=7.5,
    revenue_impact_score=8.8,
    extra_metadata={"framework": "xgboost", "n_features": 14, "training_rows": 50000},
)
db.add(sme_model)
db.flush()  # so sme_model.id is populated before we reference it

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

# ---------------------------------------------------------------
# Model 2: Fraud Flagger -> in review, mediocre governance score
# ---------------------------------------------------------------
fraud_model = MLModel(
    name="fraud-flagger",
    version="v2.1.0",
    model_type=ModelType.TRADITIONAL_ML,
    use_case="Cross-border transaction fraud detection",
    owner="fraud-ops-team",
    stage=ModelStage.REVIEW,
    risk_tier=RiskTier.HIGH,  # blocks/allows real money movement -> highest RBI scrutiny
    efficiency_score=7.0,
    adoption_score=5.5,   # low adoption -> not yet trusted by ops team
    input_quality_score=6.5,
    cost_reduction_score=6.0,
    revenue_impact_score=None,  # not yet measured
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

# ---------------------------------------------------------------
# Model 3: RM Copilot Intent Classifier -> fresh pilot (SLM)
# ---------------------------------------------------------------
rm_model = MLModel(
    name="rm-copilot-intents",
    version="v0.1.0",
    model_type=ModelType.SLM,
    use_case="Relationship manager copilot: classify client query intent",
    owner="cx-ai-team",
    stage=ModelStage.PILOT,
    risk_tier=RiskTier.LOW,  # internal advisory tool for staff, doesn't directly decide customer outcomes
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

# ---------------------------------------------------------------
# Model 4: Internal Knowledge Bot (LLM, low risk) -> already in production
# ---------------------------------------------------------------
knowledge_bot = MLModel(
    name="enterprise-knowledge-bot",
    version="v1.3.0",
    model_type=ModelType.LLM,
    use_case="RAG chatbot answering staff questions about internal policy documents",
    owner="cx-ai-team",
    stage=ModelStage.PRODUCTION,
    risk_tier=RiskTier.LOW,   # internal staff tool, wrong answer -> re-ask, not a customer harm event
    efficiency_score=8.0,
    adoption_score=8.5,
    input_quality_score=7.0,
    cost_reduction_score=6.5,
    revenue_impact_score=5.0,
)
db.add(knowledge_bot)
db.flush()
db.add(DataLineage(
    model_id=knowledge_bot.id, source_table="internal_policy_docs",
    features_used=["document_text", "document_version", "last_updated"],
))
db.add(ApprovalEvent(
    model_id=knowledge_bot.id, from_stage=None, to_stage=ModelStage.PRODUCTION,
    approved_by="risk-committee", comment="Low risk tier, fast-tracked to production",
    created_at=datetime.utcnow() - timedelta(days=40),
))

# ---------------------------------------------------------------
# Model 5: Next Best Offer Recommender (medium risk) -> in review
# ---------------------------------------------------------------
nbo_model = MLModel(
    name="next-best-offer-recommender",
    version="v0.9.0",
    model_type=ModelType.TRADITIONAL_ML,
    use_case="Recommends personalized banking products (cards, FDs, loans) at login",
    owner="marketing-analytics-team",
    stage=ModelStage.REVIEW,
    risk_tier=RiskTier.MEDIUM,  # influences offers shown, not a direct credit/fraud decision
    efficiency_score=7.5,
    adoption_score=6.0,
    input_quality_score=7.0,
    cost_reduction_score=5.5,
    revenue_impact_score=8.0,
)
db.add(nbo_model)
db.flush()
db.add(DataLineage(
    model_id=nbo_model.id, source_table="customer_product_holdings",
    features_used=["existing_products", "recent_logins", "life_stage_segment"],
))
db.add(ApprovalEvent(
    model_id=nbo_model.id, from_stage=None, to_stage=ModelStage.PILOT,
    approved_by="m.desai", comment="Initial pilot for cross-sell recommendations",
    created_at=datetime.utcnow() - timedelta(days=25),
))
db.add(ApprovalEvent(
    model_id=nbo_model.id, from_stage=ModelStage.PILOT, to_stage=ModelStage.REVIEW,
    approved_by="m.desai", comment="Moved to review after pilot",
    created_at=datetime.utcnow() - timedelta(days=8),
))

# ---------------------------------------------------------------
# Model 6: AML Transaction Monitor (highest risk) -> pilot, early stage
# ---------------------------------------------------------------
aml_model = MLModel(
    name="aml-transaction-monitor",
    version="v0.2.0",
    model_type=ModelType.TRADITIONAL_ML,
    use_case="Flags potential money-laundering patterns in transaction networks",
    owner="compliance-ai-team",
    stage=ModelStage.PILOT,
    risk_tier=RiskTier.HIGH,   # false negatives here have direct regulatory/compliance consequences
    efficiency_score=6.5,
    adoption_score=None,
    input_quality_score=6.0,
    cost_reduction_score=None,
    revenue_impact_score=None,
)
db.add(aml_model)
db.flush()
db.add(DataLineage(
    model_id=aml_model.id, source_table="transaction_network_graph",
    features_used=["txn_graph_centrality", "shell_company_flag", "rapid_movement_score"],
    notes="Early pilot — feature set still being validated by compliance team",
))
db.add(ApprovalEvent(
    model_id=aml_model.id, from_stage=None, to_stage=ModelStage.PILOT,
    approved_by="compliance-ai-team", comment="Initial registration, high-risk tier per AML use case",
    created_at=datetime.utcnow() - timedelta(days=3),
))

db.commit()
db.close()

print("✅ Database seeded: governance.db")
print("   - sme-credit-scorer         (production, HIGH risk, drift injected)")
print("   - fraud-flagger             (review, HIGH risk, low adoption score)")
print("   - rm-copilot-intents        (pilot, LOW risk, just registered)")
print("   - enterprise-knowledge-bot  (production, LOW risk)")
print("   - next-best-offer-recommender (review, MEDIUM risk)")
print("   - aml-transaction-monitor   (pilot, HIGH risk, early stage)")