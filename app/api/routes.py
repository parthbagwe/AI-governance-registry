from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.registry import MLModel, ModelMetric, ApprovalEvent, DataLineage
from app.schemas import (
    ModelCreate, ModelResponse, ScoreUpdate, ApprovalRequest,
    MetricCreate, MetricResponse, ApprovalEventResponse,
    LineageCreate, LineageResponse, LineageExportRow,
)
from app.workflow import validate_transition, InvalidTransitionError, GovernanceGateError, kill_switch

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


@router.get("/lineage", response_model=List[LineageExportRow])
def export_lineage(db: Session = Depends(get_db)):
    """
    Every data source, across every model version, in one call.

    This is the query a data steward actually needs and which a per-model
    endpoint can't answer: *if this table changed, which models are affected?*
    Asking that ten times, once per model, and joining the answers by hand is
    exactly the manual process a lineage register exists to remove.

    Declared before /models/{model_id} would matter if the paths collided —
    they don't here, but the ordering is kept deliberate so a future
    /lineage/{something} doesn't get swallowed by a wildcard route.
    """
    rows = (
        db.query(DataLineage, MLModel)
        .join(MLModel, DataLineage.model_id == MLModel.id)
        .order_by(MLModel.name.asc(), MLModel.version.asc(), DataLineage.source_table.asc())
        .all()
    )

    return [
        LineageExportRow(
            model_id=model.id,
            model_name=model.name,
            model_version=model.version,
            stage=model.stage,
            risk_tier=model.risk_tier,
            owner=model.owner,
            source_table=lineage.source_table,
            features_used=lineage.features_used,
            notes=lineage.notes,
        )
        for lineage, model in rows
    ]


@router.get("/models", response_model=List[ModelResponse])
def list_models(db: Session = Depends(get_db)):
    """List every registered model version."""
    models = db.query(MLModel).order_by(MLModel.created_at.desc()).all()
    return [_to_response(m) for m in models]


@router.post("/models", response_model=ModelResponse, status_code=201)
def register_model(payload: ModelCreate, db: Session = Depends(get_db)):
    """
    Register a new model version. Always starts life in PILOT stage.

    (name, version) must be unique. Re-registering an existing version is
    rejected with 409 rather than quietly creating a second row: a registry
    holding two copies of "v1.0.0" can't say which one is live, and each copy
    would accumulate its own separate approval history. If a model genuinely
    changed, it needs a new version number — that's what version numbers are.
    """
    existing = (
        db.query(MLModel)
        .filter(MLModel.name == payload.name, MLModel.version == payload.version)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                f"'{payload.name}' version '{payload.version}' is already "
                f"registered (id={existing.id}, currently '{existing.stage.value}'). "
                f"Bump the version to register a change, or update the existing "
                f"entry instead."
            ),
        )

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
        validate_transition(model.stage, payload.to_stage, model.governance_score, model.risk_tier)
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


@router.post("/models/{model_id}/kill-switch", response_model=ModelResponse)
def emergency_kill_switch(model_id: str, reason: str, triggered_by: str, db: Session = Depends(get_db)):
    """
    Emergency override: immediately deactivates a model regardless of its
    current stage, with NO governance-score check and NO respect for the
    normal ALLOWED_TRANSITIONS map. This exists specifically because RBI's
    draft Model Risk Management guidance mandates an override/suspension/
    kill-switch mechanism independent of routine approval workflow.

    Deliberately a separate endpoint from /approve, not a parameter on it —
    an emergency stop should never be reachable by the same form a routine
    reviewer fills in; it needs its own explicit, harder-to-hit-by-accident door.
    """
    model = _get_model_or_404(db, model_id)

    try:
        new_stage = kill_switch(reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db.add(ApprovalEvent(
        model_id=model.id, from_stage=model.stage, to_stage=new_stage,
        approved_by=triggered_by, comment=f"[EMERGENCY KILL-SWITCH] {reason}",
        is_emergency=True,
    ))
    model.stage = new_stage
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
    """
    Log a single performance metric snapshot for a model.

    `recorded_at` may be supplied to backfill historical monitoring data.
    That's deliberate and limited: a measurement legitimately belongs to the
    date it describes. Approvals have no such field — see MetricCreate.
    """
    _get_model_or_404(db, model_id)

    fields = payload.model_dump(exclude_none=True)
    metric = ModelMetric(model_id=model_id, **fields)
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


@router.post("/models/{model_id}/lineage", response_model=LineageResponse, status_code=201)
def add_lineage(model_id: str, payload: LineageCreate, db: Session = Depends(get_db)):
    """
    Record a data source for this model version.

    Create-only by design: there is no PUT or DELETE for lineage. What data a
    model version was built on is a historical fact — if it changed, what you
    have is a different model version, and the registry should say so. Being
    able to quietly rewrite a model's stated inputs would undermine the reason
    for recording them.

    Re-posting the same source_table is treated as idempotent rather than an
    error, so registration scripts can safely be re-run.
    """
    _get_model_or_404(db, model_id)

    existing = (
        db.query(DataLineage)
        .filter(
            DataLineage.model_id == model_id,
            DataLineage.source_table == payload.source_table,
        )
        .first()
    )
    if existing:
        return existing

    lineage = DataLineage(model_id=model_id, **payload.model_dump())
    db.add(lineage)
    db.commit()
    db.refresh(lineage)
    return lineage


@router.post("/models/{model_id}/explain")
def explain_prediction(model_id: str, applicant: dict, db: Session = Depends(get_db)):
    """
    Only meaningful for sme-credit-scorer today, but deliberately placed on
    the generic model route (not a standalone script) since RBI's draft
    guidance treats explainability as a first-class requirement of the
    model itself, not an optional side tool a data scientist runs manually.
    """
    model = _get_model_or_404(db, model_id)
    if model.name != "sme-credit-scorer":
        raise HTTPException(status_code=400, detail="Explainability is only wired up for sme-credit-scorer in this prototype.")

    from app.ml.explain import explain_applicant

    try:
        prob, contributions = explain_applicant(applicant)
    except FileNotFoundError as e:
        # 503 rather than 500: the service is fine, the model artifact isn't
        # available. That's a deployment state, not a bug, and the caller
        # should be told which.
        raise HTTPException(status_code=503, detail=str(e))
    except KeyError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required applicant field: {e}",
        )

    return {
        "predicted_default_probability": round(float(prob), 4),
        "decision": "FLAGGED AS HIGHER RISK" if prob > 0.5 else "LOOKS OKAY",
        "top_factors": [
            {"feature": f, "value": float(v), "impact": float(c), "direction": "increased_risk" if c > 0 else "decreased_risk"}
            for f, v, c in contributions
        ],
    }