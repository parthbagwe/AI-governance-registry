"""
Pydantic schemas — these are the request/response contracts for the API.
Kept separate from the SQLAlchemy models (app/models/registry.py) on purpose:
DB models describe storage, these describe the wire format. Mixing them
gets messy fast once you add computed fields or hide internal columns.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal

from pydantic import BaseModel, Field

from app.models.registry import ModelType, ModelStage, RiskTier


class ModelCreate(BaseModel):
    name: str
    version: str
    model_type: ModelType
    use_case: str
    owner: str
    risk_tier: RiskTier = RiskTier.MEDIUM
    extra_metadata: Optional[Dict[str, Any]] = None


class ScoreUpdate(BaseModel):
    """Partial update — any subset of the five governance scores."""
    efficiency_score: Optional[float] = Field(None, ge=0, le=10)
    adoption_score: Optional[float] = Field(None, ge=0, le=10)
    input_quality_score: Optional[float] = Field(None, ge=0, le=10)
    cost_reduction_score: Optional[float] = Field(None, ge=0, le=10)
    revenue_impact_score: Optional[float] = Field(None, ge=0, le=10)


class ApprovalRequest(BaseModel):
    to_stage: ModelStage
    # Retained only for backwards-compatible tests and local scripts when
    # AUTH_DISABLED=true. Authenticated deployments ignore caller-supplied text.
    approved_by: Optional[str] = None
    comment: Optional[str] = None


class MetricCreate(BaseModel):
    metric_name: str
    metric_value: float

    # Optional, for backfilling historical monitoring data — e.g. replaying a
    # model's performance across a past period. Defaults to now.
    #
    # Note there is deliberately no equivalent on ApprovalRequest. Backfilling
    # a *measurement* is honest bookkeeping: the number genuinely describes
    # that date. Backdating an *approval* would mean the audit trail could be
    # made to say a decision was taken earlier than it was, which is the one
    # thing an audit trail exists to prevent.
    recorded_at: Optional[datetime] = None


class ModelResponse(BaseModel):
    id: str
    name: str
    version: str
    model_type: ModelType
    use_case: str
    owner: str
    stage: ModelStage
    risk_tier: RiskTier
    efficiency_score: Optional[float]
    adoption_score: Optional[float]
    input_quality_score: Optional[float]
    cost_reduction_score: Optional[float]
    revenue_impact_score: Optional[float]
    governance_score: Optional[float]

    # Returned on the list endpoint so the UI can distinguish a model fed by a
    # live feed from one trained on a static file, without an N+1 query into
    # the lineage table for every row.
    extra_metadata: Optional[Dict[str, Any]] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # lets us build this straight from an ORM object


class MetricResponse(BaseModel):
    metric_name: str
    metric_value: float
    recorded_at: datetime

    class Config:
        from_attributes = True


class ForecastPoint(BaseModel):
    recorded_at: datetime
    predicted_value: float
    lower_bound: float
    upper_bound: float


class MetricForecastResponse(BaseModel):
    metric_name: str
    historical_points: int
    last_observed_at: datetime
    last_observed_value: float
    slope_per_day: float
    trajectory: Literal["improving", "stable", "worsening"]
    confidence: Literal["low", "medium", "high"]
    forecast_points: List[ForecastPoint]


class RegulatorySignal(BaseModel):
    authority: str
    title: str
    status: str
    applicability: Literal["direct", "conditional", "watch"]
    likely_control_scope: List[str]
    model_impact: str
    source_url: str


class ModelForecastResponse(BaseModel):
    generated_at: datetime
    horizon_days: int
    method: str
    disclaimer: str
    forecasts: List[MetricForecastResponse]
    regulatory_as_of: str
    readiness_priority: Literal["standard", "elevated", "urgent"]
    regulatory_signals: List[RegulatorySignal]


class ApprovalEventResponse(BaseModel):
    from_stage: Optional[ModelStage]
    to_stage: ModelStage
    approved_by: str
    comment: Optional[str]
    is_emergency: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class LineageCreate(BaseModel):
    source_table: str
    features_used: List[str]
    notes: Optional[str] = None


class LineageResponse(BaseModel):
    source_table: str
    features_used: List[str]
    notes: Optional[str]

    class Config:
        from_attributes = True


class LineageExportRow(BaseModel):
    """
    One row per (model version, data source), flattened for export.

    Denormalised on purpose. The consumer is a person opening a spreadsheet or
    an auditor asking "which models touch this table?", and neither wants to
    join two files to find out. Model identity is repeated on every row so each
    line stands on its own.
    """
    model_id: str
    model_name: str
    model_version: str
    stage: ModelStage
    risk_tier: RiskTier
    owner: str
    source_table: str
    features_used: List[str]
    notes: Optional[str]
