"""
Pre-registration risk assessment.

What this is NOT: a predictor of whether a model will fail. There is no
training set of "models that later broke", and a confident-sounding
probability derived from one wouldn't survive contact with a validator. A
black-box failure score inside a governance tool built to argue against
black boxes would be self-refuting.

What it is: a **rules engine**. Every finding names the RBI principle it comes
from, with the paragraph reference, so a reviewer can go and read the source
and disagree with the reasoning. Nothing here is learned, inferred, or
weighted by anything other than the rules written below in plain sight.

Source: Reserve Bank of India, draft 'Guidance on Regulatory Principles for
Model Risk Management, 2026', Press Release 2026-2027/528, 24 June 2026.
Public comments closed 24 July 2026. This is a draft, not final regulation,
and the assessment says so on every report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

RBI_SOURCE = {
    "title": "Guidance on Regulatory Principles for Model Risk Management, 2026",
    "issuer": "Reserve Bank of India, Department of Regulation",
    "reference": "Press Release 2026-2027/528",
    "dated": "24 June 2026",
    "status": "Draft for public consultation — not final regulation",
    "url": "https://rbidocs.rbi.org.in/rdocs/Content/PDFs/DRAFTGUIDANCE24062026FF12A4FF7BC84E8887009D5C5365F8BF.PDF",
}

Severity = Literal["blocker", "high", "medium", "info"]


@dataclass
class Finding:
    severity: Severity
    title: str
    detail: str
    action: str
    principle: str
    reference: str
    evidence: str | None = None  # a measured number, where one exists

    def as_dict(self) -> dict:
        return {
            "severity": self.severity,
            "title": self.title,
            "detail": self.detail,
            "action": self.action,
            "principle": self.principle,
            "reference": self.reference,
            "evidence": self.evidence,
        }


@dataclass
class ModelProposal:
    """What the person describing the model tells us."""
    name: str
    use_case: str
    model_type: str = "traditional_ml"      # traditional_ml | slm | llm
    is_generative: bool = False
    third_party: bool = False
    customer_facing: bool = False
    affects_customer_money: bool = False    # credit, pricing, payments, claims
    autonomy: str = "human_in_the_loop"     # human_in_the_loop | human_on_the_loop | fully_automated
    explainable: bool = True
    auto_updates: bool = False
    has_kill_switch: bool = False
    independently_validated: bool = False
    monitoring: str = "none"                # none | periodic | continuous
    retrain_frequency: str = "never"        # never | annually | quarterly | monthly | continuous
    uses_protected_attributes: bool = False
    documented_fallback: bool = False


# ---------------------------------------------------------------------------
# Risk tiering
# ---------------------------------------------------------------------------

def assess_tier(p: ModelProposal) -> dict:
    """
    Materiality and complexity scored separately, then combined under the
    anti-dilution rule.

    Para 19 sets the criteria — materiality, complexity, and other regulatory
    factors. Para 20 is the one people get wrong: a low complexity score must
    not drag down the tier of a highly material model. So this deliberately
    does *not* average the two. A simple spreadsheet that sets lending rates is
    high-materiality and therefore high-risk, however trivial its internals.

    Para 52 adds a third axis for AI specifically: the extent of reliance and
    level of autonomy placed on the model's output.
    """
    materiality = 0
    reasons_m: list[str] = []

    if p.affects_customer_money:
        materiality += 3
        reasons_m.append("directly affects customers' money or credit access")
    if p.customer_facing:
        materiality += 2
        reasons_m.append("interacts with customers directly")
    if p.autonomy == "fully_automated":
        materiality += 3
        reasons_m.append("acts without a human in the decision path")
    elif p.autonomy == "human_on_the_loop":
        materiality += 1
        reasons_m.append("humans supervise rather than approve each decision")

    complexity = 0
    reasons_c: list[str] = []

    if p.model_type == "llm":
        complexity += 3
        reasons_c.append("large language model — limited interpretability")
    elif p.model_type == "slm":
        complexity += 2
        reasons_c.append("language model — interpretability constraints")
    if p.is_generative:
        complexity += 2
        reasons_c.append("generative output, so behaviour is open-ended")
    if not p.explainable:
        complexity += 3
        reasons_c.append("outputs cannot be fully explained")
    if p.auto_updates:
        complexity += 2
        reasons_c.append("updates itself automatically, so behaviour shifts without review")
    if p.third_party:
        complexity += 1
        reasons_c.append("third-party model — internals not fully visible")

    def band(score: int, high: int, med: int) -> str:
        return "high" if score >= high else "medium" if score >= med else "low"

    m_band = band(materiality, 3, 2)
    c_band = band(complexity, 4, 2)

    # Anti-dilution (Para 20): the composite is the *higher* of the two, never
    # a blend. Averaging is exactly the failure mode the paragraph names.
    order = {"low": 0, "medium": 1, "high": 2}
    tier = m_band if order[m_band] >= order[c_band] else c_band

    return {
        "tier": tier,
        "materiality": {"band": m_band, "score": materiality, "reasons": reasons_m},
        "complexity": {"band": c_band, "score": complexity, "reasons": reasons_c},
        "anti_dilution_applied": order[m_band] > order[c_band],
        "rationale": (
            f"Materiality assessed {m_band}, complexity {c_band}. Under the "
            f"anti-dilution rule (Para 20) the composite tier is the higher of "
            f"the two, not an average — a low complexity score must not reduce "
            f"the tier of a highly material model."
        ),
    }


# ---------------------------------------------------------------------------
# Governance findings
# ---------------------------------------------------------------------------

def assess_governance(p: ModelProposal, tier: str) -> list[Finding]:
    f: list[Finding] = []
    is_ai = p.model_type in ("llm", "slm") or p.is_generative

    if tier == "high":
        f.append(Finding(
            "high",
            "Requires Risk Management Committee of the Board approval",
            "High-tier models cannot be signed off by a delegated authority. The "
            "RMCB must review the validation report and approve deployment.",
            "Route the validation report to the RMCB and record its approval before go-live.",
            "Risk tier drives approval structure",
            "Chapter III-A",
        ))

    if not p.independently_validated:
        f.append(Finding(
            "blocker",
            "No independent validation",
            "Validation must be carried out by a function independent of model "
            "development, ownership and use — before deployment, after deployment, "
            "after any modification, and periodically thereafter.",
            "Appoint a validator outside the development team. The person who built "
            "it cannot be the person who signs it off.",
            "Independent validation of all models",
            "Chapter IV-B, Para 15 (three lines of defence)",
        ))

    if p.third_party:
        f.append(Finding(
            "high",
            "Third-party model — accountability does not transfer",
            "A vendor's certificate is not validation. The regulated entity remains "
            "fully accountable for the outcomes of a third-party model, and must "
            "validate it independently regardless of any assurance the provider gives. "
            "Third-party models also attract RMCB oversight irrespective of tier.",
            "Secure contractual audit rights, minimum technical documentation, and "
            "exit arrangements. Budget for your own validation.",
            "Third-party accountability",
            "Chapter V-A, Para 45 and Para 47",
        ))
        f.append(Finding(
            "medium",
            "Supply-chain and provider-update risk",
            "Where a material AI model comes from a small number of providers, "
            "provider-driven updates can change behaviour without your control, and "
            "independent validation may be constrained.",
            "Contract for change notification. Re-validate after provider updates.",
            "Supply chain risk for third-party AI",
            "Chapter V-B.1, Para 53",
        ))

    if p.autonomy == "fully_automated" and not p.has_kill_switch:
        f.append(Finding(
            "blocker",
            "Autonomous, with no kill switch",
            "Human oversight arrangements must include override, suspension and "
            "deactivation mechanisms — kill-switch arrangements — for AI models. A "
            "model acting without a human in the path and without a stop control has "
            "no containment if it misbehaves.",
            "Implement a deactivation path that works from any state, requires a "
            "documented reason, and is logged separately from routine approvals.",
            "Human oversight — override, suspension, deactivation",
            "Chapter V-B.3",
        ))
    elif not p.has_kill_switch and is_ai:
        f.append(Finding(
            "high",
            "No kill switch",
            "Kill-switch arrangements are mandated for AI models regardless of how "
            "much human supervision sits around them.",
            "Add a deactivation control independent of the normal approval workflow.",
            "Human oversight — override, suspension, deactivation",
            "Chapter V-B.3",
        ))

    if not p.explainable:
        f.append(Finding(
            "high" if p.affects_customer_money else "medium",
            "Explainability below threshold",
            "Explainability thresholds must be defined for all AI models, with higher "
            "thresholds where the model drives material decisions or has significant "
            "customer impact. Where full explainability isn't achievable, compensating "
            "controls are required — not an exemption.",
            "Either add attribution (SHAP or equivalent), or document compensating "
            "controls: enhanced validation, output verification, more frequent "
            "revalidation, continuous monitoring, and usage restrictions.",
            "Explainability and transparency",
            "Chapter V-B.1, risk dimension 1",
        ))

    if p.monitoring == "none":
        f.append(Finding(
            "blocker",
            "No ongoing monitoring",
            "All deployed models must be subject to ongoing monitoring for continued "
            "alignment with intended outcomes, including detection of data drift and "
            "concept drift. Approval is a statement about conditions at a point in "
            "time; without monitoring nothing tells you when those conditions end.",
            "Define monitoring metrics and cadence before deployment, with thresholds "
            "that trigger revalidation.",
            "Ongoing monitoring; data and concept drift",
            "Chapter IV-D; Chapter V-B.1, risk dimension 7",
        ))
    elif p.monitoring == "periodic" and tier == "high":
        f.append(Finding(
            "medium",
            "Periodic monitoring may be too thin for a high-tier model",
            "Risk tier determines the scope, frequency and detail of monitoring. A "
            "high-tier model on a periodic cycle can run degraded for the length of "
            "that cycle before anyone notices.",
            "Move to continuous monitoring, or shorten the cycle and justify it.",
            "Risk tier drives monitoring scope",
            "Chapter III-A",
        ))

    if p.customer_facing and is_ai:
        f.append(Finding(
            "high",
            "Customer-facing AI — disclosure and human handoff required",
            "Users must be told they are interacting with an AI system and told its "
            "limitations. They must also be able to switch to human assistance on "
            "request: an AI interface cannot be a dead end.",
            "Add an AI disclosure notice and a visible route to a human.",
            "Disclosure to users; human assistance option",
            "Chapter V-B.2 (ii) and (iii)",
        ))
        f.append(Finding(
            "medium",
            "Adversarial input exposure",
            "Customer-facing models need controls against prompt injection and "
            "adversarial inputs, limits on session and context persistence, and "
            "detection of anomalous usage.",
            "Add input sanitisation, session limits, and anomaly detection on usage "
            "patterns. Run structured red-teaming before launch.",
            "Cyber security controls; red-teaming",
            "Chapter V-B.2 (i); Para 55",
        ))

    if p.is_generative:
        f.append(Finding(
            "high",
            "Hallucination risk",
            "Generative models require control boundaries — through system-level "
            "controls or model design — particularly where outputs drive customer "
            "interaction or decision-making.",
            "Constrain outputs to retrieved or verified sources, and add a "
            "verification step before anything reaches a customer.",
            "Hallucinations",
            "Chapter V-B.1, risk dimension 2",
        ))
        f.append(Finding(
            "medium",
            "Output variability",
            "Outputs under similar inputs must not vary excessively or inexplicably. "
            "Stochastic behaviour has to be managed, not accepted.",
            "Pin sampling parameters, measure variance across repeated identical "
            "inputs, and surface confidence scores.",
            "Output variability and uncertainty",
            "Chapter V-B.1, risk dimension 6",
        ))

    if p.auto_updates:
        f.append(Finding(
            "high",
            "Automatic updates without a change gate",
            "Models that update dynamically need enhanced controls: a defined scope "
            "of what may change automatically, strict justification for enabling it, "
            "enhanced data quality checks, and more frequent monitoring. Separately, "
            "change management requires a documented impact assessment and a defined "
            "threshold for what counts as a material change.",
            "Define what may auto-update and what must not. Set a material-change "
            "threshold that re-triggers full validation and approval.",
            "Dynamic and automatic updates; change management",
            "Chapter V-B.1, Para 56; Chapter IV-E",
        ))

    if p.uses_protected_attributes:
        f.append(Finding(
            "high",
            "Protected or proxy attributes in the feature set",
            "Bias and discriminatory-output risk must be identified wherever customer "
            "groups could be treated unfairly, with fairness assessments and mitigants "
            "including recalibration or redesign. Constraining complexity and limiting "
            "feature selection are named mitigations.",
            "Run a disparate-impact test across affected segments. Remove or justify "
            "each attribute individually — and check for proxies, which is where this "
            "usually goes wrong.",
            "Bias and discriminatory outputs",
            "Chapter V-B.1, risk dimension 3",
        ))

    if not p.documented_fallback:
        f.append(Finding(
            "medium",
            "No documented fallback",
            "Model continuity planning must form part of the entity's Business "
            "Continuity Planning, covering unavailability, performance degradation and "
            "outright failure, with fallback mechanisms — manual intervention, "
            "substitution, or backup arrangements.",
            "Write down what happens when this model is unavailable or wrong, and who "
            "does it.",
            "Business continuity management",
            "Chapter IV-F",
        ))

    if p.retrain_frequency == "never":
        f.append(Finding(
            "medium",
            "No retraining cadence",
            "Model risk explicitly includes time-suitability — models becoming less "
            "fit or unsuitable over time. A model with no retraining plan has no "
            "answer to that beyond hoping the world holds still.",
            "Set a review and retraining cadence proportionate to how fast the "
            "underlying behaviour moves.",
            "Model risk — time-suitability",
            "Chapter I-C (definition of Model Risk)",
        ))

    f.append(Finding(
        "info",
        "Inventory and retention",
        "No model may be used or deployed unless it is in the inventory. Once "
        "decommissioned it must be retained there for at least ten years from "
        "decommissioning or from when it ceases to serve as a backup or benchmark, "
        "whichever is later.",
        "Register it before deployment, and don't delete the record afterwards.",
        "Model inventory and documentation",
        "Chapter III-B",
    ))

    return f


def summarise(findings: list[Finding], tier: str) -> dict:
    counts = {s: 0 for s in ("blocker", "high", "medium", "info")}
    for x in findings:
        counts[x.severity] += 1

    if counts["blocker"]:
        verdict = "not_ready"
        headline = "Not ready for registration"
        detail = (
            f"{counts['blocker']} requirement"
            f"{'s' if counts['blocker'] != 1 else ''} would block this model from "
            f"deployment under the draft Guidance. These aren't recommendations."
        )
    elif counts["high"] >= 3:
        verdict = "significant_gaps"
        headline = "Significant gaps to close first"
        detail = (
            f"{counts['high']} high-severity findings. None is individually "
            f"disqualifying, but together they describe a model that would struggle "
            f"through independent validation."
        )
    elif counts["high"]:
        verdict = "conditional"
        headline = "Registrable with conditions"
        detail = (
            f"{counts['high']} high-severity finding"
            f"{'s' if counts['high'] != 1 else ''} to address, alongside "
            f"{counts['medium']} of medium severity."
        )
    else:
        verdict = "sound"
        headline = "No structural blockers found"
        detail = (
            "Nothing here would stop registration. That is not the same as the model "
            "being good — this assessment reads your description, not your model."
        )

    return {
        "verdict": verdict,
        "headline": headline,
        "detail": detail,
        "counts": counts,
        "tier": tier,
    }
