"""
The workflow state machine: defines which stage transitions are legal.

This is deliberately its own module (not buried in the API route) so it can
be unit-tested independently and so the *rules* of governance are visible
in one place — exactly the kind of thing an auditor or reviewer would want
to check in isolation.
"""

from app.models.registry import ModelStage, RiskTier

# Allowed transitions: current_stage -> set of stages it can legally move to
ALLOWED_TRANSITIONS = {
    ModelStage.PILOT: {ModelStage.REVIEW, ModelStage.DEPRECATED},
    ModelStage.REVIEW: {ModelStage.PRODUCTION, ModelStage.PILOT, ModelStage.DEPRECATED},
    ModelStage.PRODUCTION: {ModelStage.DEPRECATED, ModelStage.REVIEW},
    ModelStage.DEPRECATED: set(),  # terminal state, no way out
}

# Minimum governance score required to move INTO production, scaled by how
# much the model's output can affect a customer's money or the bank's
# compliance position. This mirrors RBI's June 2026 draft Guidance on
# Regulatory Principles for Model Risk Management, which requires
# risk-based model tiering rather than a single flat bar for every model.
MIN_SCORE_BY_TIER = {
    RiskTier.LOW: 5.0,      # e.g. an internal FAQ bot — low blast radius if imperfect
    RiskTier.MEDIUM: 7.0,   # e.g. a marketing lead-scoring model
    RiskTier.HIGH: 8.5,     # e.g. credit decisions, fraud blocking — directly moves customers' money
}


class InvalidTransitionError(Exception):
    pass


class GovernanceGateError(Exception):
    """Raised when a model's governance_score is too low to promote."""
    pass


def validate_transition(current_stage: ModelStage, target_stage: ModelStage, governance_score, risk_tier: RiskTier = RiskTier.MEDIUM):
    """
    Raises InvalidTransitionError or GovernanceGateError if the transition
    isn't allowed. Returns silently if it's fine.
    """
    allowed = ALLOWED_TRANSITIONS.get(current_stage, set())
    if target_stage not in allowed:
        raise InvalidTransitionError(
            f"Cannot move model from '{current_stage.value}' to '{target_stage.value}'. "
            f"Allowed next stages: {[s.value for s in allowed] or 'none (terminal state)'}"
        )

    if target_stage == ModelStage.PRODUCTION:
        required = MIN_SCORE_BY_TIER[risk_tier]
        if governance_score is None or governance_score < required:
            raise GovernanceGateError(
                f"Governance score {governance_score} is below the required "
                f"{required} threshold for a '{risk_tier.value}' risk-tier model. "
                f"Higher-risk models (like credit or fraud decisions) face a stricter bar "
                f"than lower-risk ones (like an internal chatbot). "
                f"Score all five dimensions (efficiency, adoption, input quality, "
                f"cost reduction, revenue impact) before requesting promotion."
            )


def kill_switch(reason: str):
    """
    RBI's draft guidance explicitly mandates an override/suspension/
    deactivation mechanism — a 'kill switch' — so a model can be halted
    immediately regardless of its current stage, bypassing the normal
    step-by-step workflow. This is intentionally NOT subject to
    ALLOWED_TRANSITIONS: an emergency stop must work from ANY state,
    including straight out of PRODUCTION, with no governance-score check.
    It always lands the model in DEPRECATED and is logged as an emergency
    event, never disguised as a routine approval.
    """
    if not reason or not reason.strip():
        raise ValueError("A kill-switch action requires a documented reason — this cannot be silent.")
    return ModelStage.DEPRECATED