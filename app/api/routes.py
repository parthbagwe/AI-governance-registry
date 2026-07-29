from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.registry import MLModel, ModelMetric, ApprovalEvent, DataLineage
from app.schemas import (
    ModelCreate, ModelResponse, ScoreUpdate, ApprovalRequest,
    MetricCreate, MetricResponse, ApprovalEventResponse, LineageResponse,
)
from app.workflow import validate_transition, InvalidTransitionError, GovernanceGateError

router = APIRouter()


def _get_model_or_404(db: Session, model_id: str) -> MLModel:
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return model


def _to_response(model: MLModel) -> ModelResponse:
    """
    Builds a ModelResponse from an ORM object via from_attributes, then
    manually attaches governance_score since it's a Python @property on the
    ORM class, not a mapped column, so it needs an explicit getattr pull.
    """
    resp = ModelResponse.model_validate(model)
    resp.governance_score = model.governance_score
    return resp


@router.get("/models", response_model=List[ModelResponse])
def list_models(db: Session = Depends(get_db)):
    """List every registered model version."""
    models = db.query(MLModel).order_by(MLModel.created_at.desc()).all()
    return [_to_response(m) for m in models]


@router.post("/models", response_model=ModelResponse, status_code=201)
def register_model(payload: ModelCreate, db: Session = Depends(get_db)):
    """Register a new model version. Always starts life in PILOT stage."""
    model = MLModel(**payload.model_dump())
    db.add(model)
    db.commit()
    db.refresh(model)

    # Log the registration itself as the first approval event, for a
    # complete audit trail from birth to (eventually) deprecation.
    db.add(ApprovalEvent(
        model_id=model.id, from_stage=None, to_stage=model.stage,
        approved_by=model.owner, comment="Initial registration",
    ))
    db.commit()

    return _to_response(model)


@router.get("/models/{model_id}", response_model=ModelResponse)
def get_model(model_id: str, db: Session = Depends(get_db)):
    model = _get_model_or_404(db, model_id)
    return _to_response(model)


@router.patch("/models/{model_id}/scores", response_model=ModelResponse)
def update_scores(model_id: str, payload: ScoreUpdate, db: Session = Depends(get_db)):
    """Update any subset of the five governance-scorecard dimensions."""
    model = _get_model_or_404(db, model_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(model, field, value)
    db.commit()
    db.refresh(model)
    return _to_response(model)


@router.post("/models/{model_id}/approve", response_model=ModelResponse)
def approve_transition(model_id: str, payload: ApprovalRequest, db: Session = Depends(get_db)):
    """
    Move a model to a new lifecycle stage. Enforces the state machine
    (app/workflow.py) — including the governance-score gate for production.
    """
    model = _get_model_or_404(db, model_id)

    try:
        validate_transition(model.stage, payload.to_stage, model.governance_score)
    except InvalidTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GovernanceGateError as e:
        raise HTTPException(status_code=403, detail=str(e))

    db.add(ApprovalEvent(
        model_id=model.id, from_stage=model.stage, to_stage=payload.to_stage,
        approved_by=payload.approved_by, comment=payload.comment,
    ))
    model.stage = payload.to_stage
    db.commit()
    db.refresh(model)
    return _to_response(model)


@router.get("/models/{model_id}/history", response_model=List[ApprovalEventResponse])
def get_history(model_id: str, db: Session = Depends(get_db)):
    """Full audit trail of stage transitions for a model."""
    _get_model_or_404(db, model_id)
    events = (
        db.query(ApprovalEvent)
        .filter(ApprovalEvent.model_id == model_id)
        .order_by(ApprovalEvent.created_at.asc())
        .all()
    )
    return events


@router.post("/models/{model_id}/metrics", response_model=MetricResponse, status_code=201)
def log_metric(model_id: str, payload: MetricCreate, db: Session = Depends(get_db)):
    """Log a single performance metric snapshot for a model."""
    _get_model_or_404(db, model_id)
    metric = ModelMetric(model_id=model_id, **payload.model_dump())
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric


@router.get("/models/{model_id}/metrics", response_model=List[MetricResponse])
def get_metrics(model_id: str, metric_name: str = None, db: Session = Depends(get_db)):
    """Get time-series metrics for a model, optionally filtered by metric name."""
    _get_model_or_404(db, model_id)
    query = db.query(ModelMetric).filter(ModelMetric.model_id == model_id)
    if metric_name:
        query = query.filter(ModelMetric.metric_name == metric_name)
    return query.order_by(ModelMetric.recorded_at.asc()).all()


@router.get("/models/{model_id}/lineage", response_model=List[LineageResponse])
def get_lineage(model_id: str, db: Session = Depends(get_db)):
    """Which source tables/features fed this model version."""
    _get_model_or_404(db, model_id)
    return db.query(DataLineage).filter(DataLineage.model_id == model_id).all()