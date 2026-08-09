"""
Tests for the pre-registration assessment.

The rule worth protecting most carefully is the anti-dilution one. It's the
paragraph people misread — averaging materiality and complexity feels natural
and is exactly what the guidance rules out, because it lets a simple model
with enormous consequences be scored down to medium on the strength of being
simple.
"""

from app.api.assessment import ModelProposal, assess_governance, assess_tier, summarise

from tests.conftest import API


def proposal(**overrides) -> ModelProposal:
    base = {"name": "test", "use_case": "testing"}
    base.update(overrides)
    return ModelProposal(**base)


def titles(findings) -> list[str]:
    return [f.title for f in findings]


class TestTiering:
    def test_simple_but_consequential_model_stays_high(self):
        """
        The anti-dilution rule, Para 20.

        A spreadsheet that sets lending rates: trivially simple, entirely
        explainable, and it decides what customers pay. Averaging materiality
        against complexity would land this at medium. It must not.
        """
        result = assess_tier(
            proposal(
                model_type="traditional_ml",
                explainable=True,
                affects_customer_money=True,
                autonomy="fully_automated",
            )
        )
        assert result["materiality"]["band"] == "high"
        assert result["complexity"]["band"] == "low"
        assert result["tier"] == "high"
        assert result["anti_dilution_applied"] is True

    def test_complex_but_inconsequential_model_is_still_high(self):
        """Symmetry check: the rule takes the higher of the two in both
        directions, not just the one that's convenient."""
        result = assess_tier(
            proposal(model_type="llm", is_generative=True, explainable=False)
        )
        assert result["complexity"]["band"] == "high"
        assert result["tier"] == "high"

    def test_an_internal_tool_lands_low(self):
        result = assess_tier(proposal())
        assert result["tier"] == "low"
        assert result["anti_dilution_applied"] is False

    def test_removing_the_human_raises_materiality(self):
        """Para 52: for AI, the extent of reliance and level of autonomy are
        tiering inputs in their own right. Same model, no human, higher tier."""
        supervised = assess_tier(proposal(autonomy="human_in_the_loop"))
        autonomous = assess_tier(proposal(autonomy="fully_automated"))
        assert autonomous["materiality"]["score"] > supervised["materiality"]["score"]

    def test_every_tier_decision_is_explained(self):
        result = assess_tier(proposal(affects_customer_money=True, model_type="llm"))
        assert result["materiality"]["reasons"]
        assert result["complexity"]["reasons"]
        assert "anti-dilution" in result["rationale"].lower()


class TestGovernanceFindings:
    def test_missing_validation_is_a_blocker(self):
        findings = assess_governance(proposal(independently_validated=False), "low")
        blockers = [f for f in findings if f.severity == "blocker"]
        assert any("independent validation" in f.title.lower() for f in blockers)

    def test_autonomous_without_a_kill_switch_is_a_blocker(self):
        findings = assess_governance(
            proposal(autonomy="fully_automated", has_kill_switch=False), "high"
        )
        assert any(
            f.severity == "blocker" and "kill switch" in f.title.lower()
            for f in findings
        )

    def test_unmonitored_is_a_blocker(self):
        findings = assess_governance(proposal(monitoring="none"), "low")
        assert any(
            f.severity == "blocker" and "monitoring" in f.title.lower()
            for f in findings
        )

    def test_customer_facing_ai_requires_disclosure_and_a_human_route(self):
        findings = assess_governance(
            proposal(customer_facing=True, model_type="llm"), "high"
        )
        assert any("disclosure" in t.lower() for t in titles(findings))

    def test_generative_models_raise_hallucination_risk(self):
        findings = assess_governance(proposal(is_generative=True), "medium")
        assert any("hallucination" in t.lower() for t in titles(findings))

    def test_third_party_accountability_does_not_transfer(self):
        findings = assess_governance(proposal(third_party=True), "medium")
        assert any("third-party" in t.lower() for t in titles(findings))

    def test_every_finding_cites_a_principle(self):
        """The whole argument for this being a rules engine rather than a score
        is that each output is traceable. An uncited finding is just an
        opinion with a colour attached."""
        findings = assess_governance(
            proposal(
                model_type="llm",
                is_generative=True,
                third_party=True,
                customer_facing=True,
                autonomy="fully_automated",
                auto_updates=True,
                uses_protected_attributes=True,
            ),
            "high",
        )
        assert findings
        for f in findings:
            assert f.principle.strip()
            assert f.reference.strip()
            assert f.action.strip()

    def test_a_well_governed_model_produces_no_blockers(self):
        findings = assess_governance(
            proposal(
                independently_validated=True,
                has_kill_switch=True,
                monitoring="continuous",
                documented_fallback=True,
                retrain_frequency="quarterly",
                explainable=True,
            ),
            "low",
        )
        assert not [f for f in findings if f.severity == "blocker"]


class TestSummary:
    def test_any_blocker_means_not_ready(self):
        findings = assess_governance(proposal(monitoring="none"), "low")
        assert summarise(findings, "low")["verdict"] == "not_ready"

    def test_a_clean_model_is_sound(self):
        findings = assess_governance(
            proposal(
                independently_validated=True,
                has_kill_switch=True,
                monitoring="continuous",
                documented_fallback=True,
                retrain_frequency="quarterly",
            ),
            "low",
        )
        assert summarise(findings, "low")["verdict"] == "sound"


class TestAssessmentEndpoint:
    def test_returns_tiering_findings_and_a_citation(self, client):
        resp = client.post(
            f"{API}/assessment",
            json={
                "name": "collections-agent",
                "use_case": "Sends repayment reminders and offers settlements",
                "model_type": "llm",
                "is_generative": True,
                "affects_customer_money": True,
                "customer_facing": True,
                "autonomy": "fully_automated",
                "monitoring": "none",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["tiering"]["tier"] == "high"
        assert body["summary"]["verdict"] == "not_ready"
        assert body["source"]["reference"].startswith("Press Release")

    def test_name_and_use_case_are_required(self, client):
        assert client.post(f"{API}/assessment", json={"name": "x"}).status_code == 422

    def test_assessing_does_not_register_anything(self, client):
        """Exploring a hypothetical must not leave a trail of half-formed
        proposals in the inventory."""
        client.post(
            f"{API}/assessment",
            json={"name": "hypothetical", "use_case": "just thinking about it"},
        )
        assert client.get(f"{API}/models").json() == []

    def test_unknown_fields_are_ignored_rather_than_erroring(self, client):
        """A caller sending an extra key shouldn't get a 422 — the assessment
        is a convenience, not a strict contract."""
        resp = client.post(
            f"{API}/assessment",
            json={"name": "x", "use_case": "y", "nonsense_field": True},
        )
        assert resp.status_code == 200
