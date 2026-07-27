"""
Core schema for the AI Model Governance Registry.

Four tables, each mapping to a real governance need:

1. MLModel            -> "what models exist, and what stage are they at"
2. ModelMetric        -> "how is each model performing over time" (feeds drift detection)
3. ApprovalEvent      -> "who moved a model between stages, and when" (audit trail)
4. DataLineage        -> "what data fed this model version" (traceability / compliance)
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, DateTime, ForeignKey, Enum, Text, JSON, Integer
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class ModelType(str, enum.Enum):
    TRADITIONAL_ML = "traditional_ml"   # e.g. XGBoost credit scorer
    SLM = "slm"                         # small language model, e.g. intent classifier
    LLM = "llm"                         # large language model, e.g. RM copilot / knowledge bot


class ModelStage(str, enum.Enum):
    PILOT = "pilot"
    REVIEW = "review"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"


class MLModel(Base):
    """
    One row per *model version*. A model "name" can have many versions
    (v1, v2, ...) each with its own lifecycle stage.
    """
    __tablename__ = "ml_models"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False, index=True)          # e.g. "sme-credit-scorer"
    version = Column(String, nullable=False)                    # e.g. "v1.2.0"
    model_type = Column(Enum(ModelType), nullable=False)
    use_case = Column(String, nullable=False)                   # e.g. "SME loan pre-approval"
    owner = Column(String, nullable=False)                      # team/person responsible
    stage = Column(Enum(ModelStage), nullable=False, default=ModelStage.PILOT)

    # Governance scorecard fields (mirrors a "pilot -> production" evaluation framework:
    # efficiency, adoption, input data quality, cost reduction, revenue impact)
    efficiency_score = Column(Float, nullable=True)
    adoption_score = Column(Float, nullable=True)
    input_quality_score = Column(Float, nullable=True)
    cost_reduction_score = Column(Float, nullable=True)
    revenue_impact_score = Column(Float, nullable=True)

    extra_metadata = Column(JSON, nullable=True)  # flexible config: hyperparams, framework, etc.

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    metrics = relationship("ModelMetric", back_populates="model", cascade="all, delete-orphan")
    approval_events = relationship("ApprovalEvent", back_populates="model", cascade="all, delete-orphan")
    lineage = relationship("DataLineage", back_populates="model", cascade="all, delete-orphan")

    @property
    def governance_score(self):
        """Simple composite score used to gate pilot -> production promotion."""
        scores = [
            self.efficiency_score, self.adoption_score, self.input_quality_score,
            self.cost_reduction_score, self.revenue_impact_score
        ]
        valid = [s for s in scores if s is not None]
        return round(sum(valid) / len(valid), 2) if valid else None


class ModelMetric(Base):
    """
    Time-series performance snapshots for a model. This is what our
    drift-detection job will read to decide "has this model degraded?"
    """
    __tablename__ = "model_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String, ForeignKey("ml_models.id"), nullable=False)

    metric_name = Column(String, nullable=False)   # e.g. "accuracy", "auc", "latency_ms", "drift_score"
    metric_value = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    model = relationship("MLModel", back_populates="metrics")


class ApprovalEvent(Base):
    """
    Audit trail: every stage transition a model goes through, who approved it,
    and why. This is the table that makes the difference between a 'toy
    project' and something that reads as regulator-ready.
    """
    __tablename__ = "approval_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String, ForeignKey("ml_models.id"), nullable=False)

    from_stage = Column(Enum(ModelStage), nullable=True)
    to_stage = Column(Enum(ModelStage), nullable=False)
    approved_by = Column(String, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    model = relationship("MLModel", back_populates="approval_events")


class DataLineage(Base):
    """
    Which source tables/features fed a given model version.
    Useful for "if this data changes, which models need re-review".
    """
    __tablename__ = "data_lineage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String, ForeignKey("ml_models.id"), nullable=False)

    source_table = Column(String, nullable=False)     # e.g. "gst_returns"
    features_used = Column(JSON, nullable=False)       # e.g. ["avg_monthly_turnover", "filing_delay_days"]
    notes = Column(Text, nullable=True)

    model = relationship("MLModel", back_populates="lineage")