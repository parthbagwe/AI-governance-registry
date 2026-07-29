"""
The workflow state machine: defines which stage transitions are legal.

Deliberately its own module (not buried in the API route) so it can be
unit-tested independently and so the *rules* of governance are visible
in one place — exactly what an auditor would want to check in isolation.
"""

from app.models.registry import ModelStage

# Allowed transitions: current_stage -> set of stages it can legally move to
ALLOWED_TRANSITIONS = {
    ModelStage.PILOT: {ModelStage.REVIEW, ModelStage.DEPRECATED},
    ModelStage.REVIEW: {ModelStage.PRODUCTION, ModelStage.PILOT, ModelStage.DEPRECATED},
    ModelStage.PRODUCTION: {ModelStage.DEPRECATED},
    ModelStage.DEPRECATED: set(),  # terminal state, no way out
}

# Minimum governance score required to move INTO production.
# This is the "gate" — mirrors a real risk-committee sign-off threshold.
MIN_SCORE_FOR_PRODUCTION = 7.0


class InvalidTransitionError(Exception):
    pass


class GovernanceGateError(Exception):
    """Raised when a model's governance_score is too low to promote."""
    pass


def validate_transition(current_stage: ModelStage, target_stage: ModelStage, governance_score):
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
        if governance_score is None or governance_score < MIN_SCORE_FOR_PRODUCTION:
            raise GovernanceGateError(
                f"Governance score {governance_score} is below the required "
                f"{MIN_SCORE_FOR_PRODUCTION} threshold for production promotion. "
                f"Score all five dimensions (efficiency, adoption, input quality, "
                f"cost reduction, revenue impact) before requesting promotion."
            )