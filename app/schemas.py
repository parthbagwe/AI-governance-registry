"""
Pydantic schemas — these are the request/response contracts for the API.
Kept separate from the SQLAlchemy models (app/models/registry.py) on purpose:
DB models describe storage, these describe the wire format.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

from app.models.registry import ModelType, ModelStage


class ModelCreate(BaseModel):
    name: str
    version: str
    model_type: ModelType
    use_case: str
    owner: str
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
    approved_by: str
    comment: Optional[str] = None


class MetricCreate(BaseModel):
    metric_name: str
    metric_value: float


class ModelResponse(BaseModel):
    id: str
    name: str
    version: str
    model_type: ModelType
    use_case: str
    owner: str
    stage: ModelStage
    efficiency_score: Optional[float]
    adoption_score: Optional[float]
    input_quality_score: Optional[float]
    cost_reduction_score: Optional[float]
    revenue_impact_score: Optional[float]
    governance_score: Optional[float]
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


class ApprovalEventResponse(BaseModel):
    from_stage: Optional[ModelStage]
    to_stage: ModelStage
    approved_by: str
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class LineageResponse(BaseModel):
    source_table: str
    features_used: List[str]
    notes: Optional[str]

    class Config:
        from_attributes = True