"""
Unit tests for the governance rules themselves.

These call app/workflow.py directly, with no database and no HTTP. That
separation is the point: the rules are the product, and they should be
provable in isolation from whatever happens to be calling them. An auditor
asking "prove a model can't skip review" should get an answer that doesn't
depend on the web layer being correct.
"""

import pytest

from app.models.registry import ModelStage, RiskTier
from app.workflow import (
    ALLOWED_TRANSITIONS,
    GovernanceGateError,
    InvalidTransitionError,
    MIN_SCORE_BY_TIER,
    kill_switch,
    validate_transition,
)


class TestStateMachine:
    def test_pilot_can_reach_review(self):
        validate_transition(ModelStage.PILOT, ModelStage.REVIEW, None, RiskTier.LOW)

    def test_pilot_cannot_skip_straight_to_production(self):
        """The gap this closes is the obvious one: a model that never had a
        reviewer look at it going live because someone posted the right JSON."""
        with pytest.raises(InvalidTransitionError):
            validate_transition(
                ModelStage.PILOT, ModelStage.PRODUCTION, 10.0, RiskTier.LOW
            )

    def test_deprecated_is_terminal(self):
        for target in ModelStage:
            if target is ModelStage.DEPRECATED:
                continue
            with pytest.raises(InvalidTransitionError):
                validate_transition(
                    ModelStage.DEPRECATED, target, 10.0, RiskTier.LOW
                )

    def test_production_can_be_demoted_to_review(self):
        """
        Regression test.

        The state machine originally allowed only production -> deprecated.
        Wiring up the drift monitor exposed the gap: a model whose data has
        shifted needs pulling back for re-review, not killing outright. Without
        this, an automated monitor's only available action against a degrading
        production model would have been to retire it permanently.
        """
        validate_transition(
            ModelStage.PRODUCTION, ModelStage.REVIEW, None, RiskTier.HIGH
        )

    def test_every_stage_has_an_entry(self):
        """A stage missing from the map would silently deny every transition
        out of it — a model could enter it and never leave."""
        for stage in ModelStage:
            assert stage in ALLOWED_TRANSITIONS

    def test_no_stage_can_transition_to_itself(self):
        for stage, targets in ALLOWED_TRANSITIONS.items():
            assert stage not in targets, f"{stage} can transition to itself"


class TestGovernanceGate:
    @pytest.mark.parametrize(
        "tier,threshold",
        [(RiskTier.LOW, 5.0), (RiskTier.MEDIUM, 7.0), (RiskTier.HIGH, 8.5)],
    )
    def test_threshold_scales_with_risk(self, tier, threshold):
        assert MIN_SCORE_BY_TIER[tier] == threshold

        # Just under the bar fails.
        with pytest.raises(GovernanceGateError):
            validate_transition(
                ModelStage.REVIEW, ModelStage.PRODUCTION, threshold - 0.01, tier
            )

        # Exactly on it passes — the threshold is inclusive, and a model
        # scoring precisely 7.00 shouldn't be refused on a rounding artefact.
        validate_transition(
            ModelStage.REVIEW, ModelStage.PRODUCTION, threshold, tier
        )

    def test_unscored_model_cannot_reach_production(self):
        """None is not zero and must not be treated as merely low — an unscored
        model hasn't failed assessment, it hasn't been assessed."""
        with pytest.raises(GovernanceGateError):
            validate_transition(
                ModelStage.REVIEW, ModelStage.PRODUCTION, None, RiskTier.LOW
            )

    def test_a_score_good_enough_for_medium_is_not_enough_for_high(self):
        """The tiering exists to make exactly this distinction. 8.0 clears a
        medium-tier model and fails a high-tier one."""
        validate_transition(
            ModelStage.REVIEW, ModelStage.PRODUCTION, 8.0, RiskTier.MEDIUM
        )
        with pytest.raises(GovernanceGateError):
            validate_transition(
                ModelStage.REVIEW, ModelStage.PRODUCTION, 8.0, RiskTier.HIGH
            )

    def test_gate_only_applies_to_production(self):
        """A low score should not prevent a model being retired. Making it
        harder to switch something off than to switch it on is backwards."""
        validate_transition(
            ModelStage.REVIEW, ModelStage.DEPRECATED, 0.1, RiskTier.HIGH
        )


class TestKillSwitch:
    def test_requires_a_documented_reason(self):
        for empty in ("", "   ", "\n"):
            with pytest.raises(ValueError):
                kill_switch(empty)

    def test_lands_in_deprecated(self):
        assert kill_switch("Producing invalid scores") is ModelStage.DEPRECATED
