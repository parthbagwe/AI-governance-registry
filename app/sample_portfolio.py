"""Non-destructive sample portfolio expansion used by local demos and seeding."""

from __future__ import annotations

from datetime import datetime, timedelta
import random

from sqlalchemy.orm import Session

from app.models.registry import (
    ApprovalEvent,
    DataLineage,
    MLModel,
    ModelMetric,
    ModelStage,
    ModelType,
    RiskTier,
)


def _history(
    db: Session,
    model: MLModel,
    metric_name: str,
    base: float,
    daily_slope: float,
    volatility: float,
    days: int = 35,
) -> None:
    exists = (
        db.query(ModelMetric)
        .filter(ModelMetric.model_id == model.id, ModelMetric.metric_name == metric_name)
        .first()
    )
    if exists:
        return

    rng = random.Random(sum(ord(char) for char in f"{model.name}:{metric_name}"))
    now = datetime.utcnow()
    for index in range(days):
        age = days - index
        value = base + daily_slope * index + rng.uniform(-volatility, volatility)
        if 0 <= base <= 1:
            value = min(1.0, max(0.0, value))
        db.add(ModelMetric(
            model_id=model.id,
            metric_name=metric_name,
            metric_value=round(value, 6),
            recorded_at=now - timedelta(days=age),
        ))


def _add_model(db: Session, spec: dict) -> MLModel:
    existing = (
        db.query(MLModel)
        .filter(MLModel.name == spec["name"], MLModel.version == spec["version"])
        .first()
    )
    if existing:
        return existing

    lineage = spec.pop("lineage")
    metrics = spec.pop("metrics")
    model = MLModel(**spec)
    db.add(model)
    db.flush()
    db.add(ApprovalEvent(
        model_id=model.id,
        from_stage=None,
        to_stage=model.stage,
        approved_by="sample-portfolio-bootstrap",
        comment="Sample model added for governance scenario testing",
        created_at=datetime.utcnow() - timedelta(days=42),
    ))
    for source_table, features, notes in lineage:
        db.add(DataLineage(
            model_id=model.id,
            source_table=source_table,
            features_used=features,
            notes=notes,
        ))
    for metric in metrics:
        _history(db, model, *metric)
    return model


def expand_sample_portfolio(db: Session) -> int:
    """Add missing sample models and forecastable demo history; never delete."""
    specs = [
        dict(
            name="mule-account-network-detector", version="v0.8.0",
            model_type=ModelType.TRADITIONAL_ML,
            use_case="Detects mule-account networks using payment graph behaviour",
            owner="financial-crime-analytics", stage=ModelStage.REVIEW, risk_tier=RiskTier.HIGH,
            efficiency_score=8.2, adoption_score=7.4, input_quality_score=7.8,
            cost_reduction_score=7.1, revenue_impact_score=8.0,
            extra_metadata={"framework": "graph-neural-network", "regulatory_domains": ["RBI", "DPDP"], "demo_data": True},
            lineage=[("payment_network_edges", ["shared_device_count", "rapid_fund_hops", "beneficiary_overlap"], "Synthetic demo lineage; replace with approved production sources")],
            metrics=[("recall", 0.75, 0.0015, 0.009), ("false_positive_rate", 0.16, -0.0012, 0.006)],
        ),
        dict(
            name="kyc-document-verifier", version="v1.4.0",
            model_type=ModelType.TRADITIONAL_ML,
            use_case="Verifies KYC identity documents and flags suspected tampering",
            owner="onboarding-risk-team", stage=ModelStage.PRODUCTION, risk_tier=RiskTier.HIGH,
            efficiency_score=9.0, adoption_score=8.8, input_quality_score=8.6,
            cost_reduction_score=8.5, revenue_impact_score=7.9,
            extra_metadata={"framework": "vision-transformer", "regulatory_domains": ["RBI", "DPDP"], "demo_data": True},
            lineage=[("kyc_document_images", ["document_image", "ocr_text", "tamper_features"], "Biometric and identity data require strict access and retention controls")],
            metrics=[("accuracy", 0.955, 0.00015, 0.003), ("false_reject_rate", 0.052, -0.00035, 0.003)],
        ),
        dict(
            name="collections-priority-engine", version="v0.5.0",
            model_type=ModelType.TRADITIONAL_ML,
            use_case="Prioritises delinquent-loan outreach while preserving human review",
            owner="retail-collections-analytics", stage=ModelStage.PILOT, risk_tier=RiskTier.HIGH,
            efficiency_score=7.3, adoption_score=6.1, input_quality_score=7.2,
            cost_reduction_score=6.8, revenue_impact_score=7.5,
            extra_metadata={"framework": "lightgbm", "regulatory_domains": ["RBI", "DPDP"], "demo_data": True},
            lineage=[("collections_case_history", ["days_past_due", "contact_outcome", "repayment_pattern"], "Protected attributes excluded from treatment recommendations")],
            metrics=[("repayment_precision", 0.64, 0.0017, 0.012), ("fairness_ratio", 0.88, 0.0006, 0.008)],
        ),
        dict(
            name="customer-service-genai", version="v0.7.0",
            model_type=ModelType.LLM,
            use_case="Customer-facing generative assistant for banking service queries",
            owner="digital-service-ai", stage=ModelStage.REVIEW, risk_tier=RiskTier.MEDIUM,
            efficiency_score=8.0, adoption_score=7.2, input_quality_score=7.0,
            cost_reduction_score=7.6, revenue_impact_score=6.4,
            extra_metadata={"framework": "rag-llm", "deployment_regions": ["IN", "EU"], "regulatory_domains": ["RBI", "DPDP", "EU_AI_ACT"], "demo_data": True},
            lineage=[("approved_customer_help_content", ["article_text", "effective_date", "product_scope"], "Only approved content is eligible for retrieval")],
            metrics=[("groundedness", 0.90, -0.0009, 0.008), ("hallucination_rate", 0.035, 0.0007, 0.003)],
        ),
        dict(
            name="market-abuse-surveillance", version="v1.1.0",
            model_type=ModelType.TRADITIONAL_ML,
            use_case="Detects suspicious trading patterns for market-abuse investigation",
            owner="market-surveillance-team", stage=ModelStage.REVIEW, risk_tier=RiskTier.HIGH,
            efficiency_score=8.1, adoption_score=7.0, input_quality_score=8.2,
            cost_reduction_score=7.4, revenue_impact_score=7.0,
            extra_metadata={"framework": "temporal-graph-model", "regulatory_domains": ["SEBI"], "demo_data": True},
            lineage=[("orders_and_trades", ["order_cancel_ratio", "price_impact", "linked_account_graph"], "Alerts require analyst investigation before escalation")],
            metrics=[("alert_precision", 0.70, 0.0013, 0.01), ("recall", 0.78, 0.0007, 0.009)],
        ),
        dict(
            name="payment-routing-optimizer", version="v2.0.0",
            model_type=ModelType.TRADITIONAL_ML,
            use_case="Selects resilient payment routes using live success and latency signals",
            owner="payments-platform-ai", stage=ModelStage.PRODUCTION, risk_tier=RiskTier.MEDIUM,
            efficiency_score=9.1, adoption_score=9.0, input_quality_score=8.5,
            cost_reduction_score=8.2, revenue_impact_score=8.7,
            extra_metadata={"framework": "contextual-bandit", "data_source": "live_payment_telemetry", "regulatory_domains": ["RBI"], "demo_data": True},
            lineage=[("payment_route_telemetry", ["success_rate", "p95_latency_ms", "processor_availability"], "Decision falls back to deterministic routing on monitor failure")],
            metrics=[("success_rate", 0.965, 0.00025, 0.002), ("latency_ms", 92.0, -0.65, 2.5)],
        ),
        dict(
            name="biometric-liveness-detector", version="v1.2.0",
            model_type=ModelType.TRADITIONAL_ML,
            use_case="Detects presentation attacks during remote customer onboarding",
            owner="digital-identity-risk", stage=ModelStage.PRODUCTION, risk_tier=RiskTier.HIGH,
            efficiency_score=8.8, adoption_score=8.6, input_quality_score=8.3,
            cost_reduction_score=8.0, revenue_impact_score=7.8,
            extra_metadata={"framework": "vision-transformer", "regulatory_domains": ["RBI", "DPDP"], "demo_data": True},
            lineage=[("onboarding_liveness_frames", ["face_motion", "depth_consistency", "replay_artifacts"], "Biometric frames are synthetic in this demo and require tightly bounded retention in production")],
            metrics=[("spoof_detection_recall", 0.93, 0.0004, 0.004), ("false_reject_rate", 0.045, -0.0003, 0.0025)],
        ),
        dict(
            name="cashflow-early-warning-system", version="v0.9.0",
            model_type=ModelType.TRADITIONAL_ML,
            use_case="Identifies early cash-flow stress in commercial-banking borrowers",
            owner="wholesale-credit-risk", stage=ModelStage.REVIEW, risk_tier=RiskTier.HIGH,
            efficiency_score=7.9, adoption_score=7.1, input_quality_score=7.7,
            cost_reduction_score=7.2, revenue_impact_score=8.1,
            extra_metadata={"framework": "gradient-boosting", "regulatory_domains": ["RBI", "DPDP"], "demo_data": True},
            lineage=[("commercial_cashflows", ["inflow_trend", "payment_delays", "working_capital_utilisation"], "Human credit review remains mandatory")],
            metrics=[("recall", 0.74, 0.0012, 0.009), ("false_positive_rate", 0.19, -0.0010, 0.007)],
        ),
        dict(
            name="cheque-fraud-vision", version="v2.3.0",
            model_type=ModelType.TRADITIONAL_ML,
            use_case="Flags altered cheques and signature anomalies before clearing",
            owner="payments-fraud-ai", stage=ModelStage.PRODUCTION, risk_tier=RiskTier.HIGH,
            efficiency_score=9.0, adoption_score=8.7, input_quality_score=8.5,
            cost_reduction_score=8.4, revenue_impact_score=8.2,
            extra_metadata={"framework": "multimodal-vision", "regulatory_domains": ["RBI", "DPDP"], "demo_data": True},
            lineage=[("cheque_scan_archive", ["signature_embedding", "amount_text_match", "image_tamper_score"], "Sample images only; no customer documents ship with the repository")],
            metrics=[("precision", 0.91, 0.00035, 0.004), ("latency_ms", 145.0, -0.8, 3.0)],
        ),
        dict(
            name="voice-banking-intent-risk", version="v0.4.0",
            model_type=ModelType.SLM,
            use_case="Classifies voice-banking requests and routes high-risk intents to staff",
            owner="contact-centre-ai", stage=ModelStage.PILOT, risk_tier=RiskTier.MEDIUM,
            efficiency_score=7.0, adoption_score=5.8, input_quality_score=6.9,
            cost_reduction_score=6.5, revenue_impact_score=5.8,
            extra_metadata={"framework": "speech-small-language-model", "regulatory_domains": ["RBI", "DPDP"], "demo_data": True},
            lineage=[("consented_call_transcripts", ["transcript_text", "intent_label", "risk_phrase_flags"], "Requires consent, redaction, retention limits, and human escalation")],
            metrics=[("intent_accuracy", 0.82, 0.0008, 0.007), ("escalation_recall", 0.88, 0.00025, 0.006)],
        ),
        dict(
            name="sanctions-name-screening", version="v1.6.0",
            model_type=ModelType.TRADITIONAL_ML,
            use_case="Ranks sanctions and adverse-name matches for compliance investigation",
            owner="financial-sanctions-team", stage=ModelStage.REVIEW, risk_tier=RiskTier.HIGH,
            efficiency_score=8.4, adoption_score=7.9, input_quality_score=8.0,
            cost_reduction_score=7.8, revenue_impact_score=7.2,
            extra_metadata={"framework": "entity-resolution", "regulatory_domains": ["RBI", "DPDP"], "demo_data": True},
            lineage=[("sanctions_and_customer_names", ["name_tokens", "date_of_birth", "country_codes"], "Analysts decide all true matches; the model only ranks candidates")],
            metrics=[("recall", 0.965, 0.0001, 0.002), ("false_positive_rate", 0.22, -0.0014, 0.006)],
        ),
        dict(
            name="cyber-incident-anomaly-detector", version="v3.0.0",
            model_type=ModelType.TRADITIONAL_ML,
            use_case="Detects anomalous authentication and network events across bank systems",
            owner="security-operations-analytics", stage=ModelStage.PRODUCTION, risk_tier=RiskTier.HIGH,
            efficiency_score=8.9, adoption_score=9.1, input_quality_score=8.7,
            cost_reduction_score=8.6, revenue_impact_score=8.3,
            extra_metadata={"framework": "isolation-forest-ensemble", "data_source": "live_security_telemetry", "regulatory_domains": ["RBI"], "demo_data": True},
            lineage=[("security_event_stream", ["failed_login_velocity", "device_novelty", "network_path_anomaly"], "Security telemetry is access-controlled and pseudonymised")],
            metrics=[("precision", 0.86, 0.0007, 0.006), ("detection_latency_minutes", 18.0, -0.12, 0.6)],
        ),
        dict(
            name="regulatory-reporting-copilot", version="v0.3.0",
            model_type=ModelType.LLM,
            use_case="Drafts regulatory reporting narratives from approved evidence packs",
            owner="regulatory-reporting-office", stage=ModelStage.PILOT, risk_tier=RiskTier.MEDIUM,
            efficiency_score=7.4, adoption_score=5.5, input_quality_score=7.6,
            cost_reduction_score=6.9, revenue_impact_score=5.5,
            extra_metadata={"framework": "rag-llm", "regulatory_domains": ["RBI", "SEBI"], "demo_data": True},
            lineage=[("approved_regulatory_evidence", ["control_results", "policy_citations", "reporting_period"], "Every draft requires accountable human sign-off")],
            metrics=[("groundedness", 0.89, 0.00015, 0.006), ("hallucination_rate", 0.025, -0.00015, 0.002)],
        ),
        dict(
            name="treasury-liquidity-forecaster", version="v1.0.0",
            model_type=ModelType.TRADITIONAL_ML,
            use_case="Forecasts intraday liquidity requirements for treasury operations",
            owner="treasury-risk-analytics", stage=ModelStage.REVIEW, risk_tier=RiskTier.HIGH,
            efficiency_score=8.2, adoption_score=7.3, input_quality_score=8.4,
            cost_reduction_score=7.6, revenue_impact_score=8.5,
            extra_metadata={"framework": "temporal-fusion-transformer", "regulatory_domains": ["RBI"], "demo_data": True},
            lineage=[("liquidity_and_payment_flows", ["opening_balance", "scheduled_payments", "market_settlements"], "Scenario overlays remain owned by treasury risk")],
            metrics=[("forecast_accuracy", 0.84, 0.0009, 0.007), ("error_rate", 0.16, -0.0008, 0.006)],
        ),
        dict(
            name="insurance-claims-fraud-triage", version="v0.8.0",
            model_type=ModelType.TRADITIONAL_ML,
            use_case="Prioritises suspicious insurance claims for investigator review",
            owner="insurance-fraud-analytics", stage=ModelStage.REVIEW, risk_tier=RiskTier.HIGH,
            efficiency_score=7.8, adoption_score=6.9, input_quality_score=7.5,
            cost_reduction_score=7.3, revenue_impact_score=7.7,
            extra_metadata={"framework": "xgboost", "regulatory_domains": ["IRDAI", "DPDP"], "demo_data": True},
            lineage=[("claims_and_provider_history", ["claim_pattern", "provider_network", "document_consistency"], "No claim is denied solely from model output")],
            metrics=[("precision", 0.73, 0.0011, 0.009), ("recall", 0.81, 0.0006, 0.008)],
        ),
        dict(
            name="merchant-risk-rating", version="v0.6.0",
            model_type=ModelType.TRADITIONAL_ML,
            use_case="Rates acquiring merchants for fraud, dispute, and operational risk",
            owner="merchant-acquiring-risk", stage=ModelStage.PILOT, risk_tier=RiskTier.HIGH,
            efficiency_score=7.5, adoption_score=6.0, input_quality_score=7.3,
            cost_reduction_score=6.8, revenue_impact_score=7.9,
            extra_metadata={"framework": "gradient-boosting", "regulatory_domains": ["RBI", "DPDP"], "demo_data": True},
            lineage=[("merchant_activity_profile", ["chargeback_rate", "volume_spike", "category_risk"], "Enhanced due diligence remains a human-controlled process")],
            metrics=[("auc", 0.79, 0.0010, 0.008), ("fairness_ratio", 0.91, 0.0003, 0.005)],
        ),
    ]

    before = db.query(MLModel).count()
    for raw_spec in specs:
        # _add_model removes helper-only fields; give it a fresh shallow copy so
        # this function remains safe if called twice in one process.
        spec = dict(raw_spec)
        spec["lineage"] = list(raw_spec["lineage"])
        spec["metrics"] = list(raw_spec["metrics"])
        _add_model(db, spec)

    db.flush()
    # Every model gets a clearly named synthetic governance-health history so
    # every detail page can demonstrate forecasting, even if its real monitor
    # has not yet logged three comparable observations.
    for model in db.query(MLModel).all():
        base = (model.governance_score / 10) if model.governance_score is not None else 0.68
        slope = -0.001 if model.stage == ModelStage.DEPRECATED else 0.0004
        _history(db, model, "demo_governance_health", base, slope, 0.008, days=35)
        metadata = dict(model.extra_metadata or {})
        metadata.setdefault("demo_forecast_metric", "demo_governance_health")
        model.extra_metadata = metadata

    db.commit()
    return db.query(MLModel).count() - before
