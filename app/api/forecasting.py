"""Transparent metric projections and a curated regulatory watchlist.

The forecast deliberately uses an inspectable weighted linear trend instead
of a black-box model. A governance dashboard must show uncertainty and method,
especially when the history is synthetic demo data or contains a regime
change. Regulatory entries are source-linked scenarios, not predictions of
what a regulator will enact.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
import math

import numpy as np

from app.models.registry import MLModel, ModelMetric, RiskTier
from app.schemas import (
    ForecastPoint,
    MetricForecastResponse,
    ModelForecastResponse,
    RegulatorySignal,
)

REGULATORY_AS_OF = "2026-08-15"

LOWER_IS_BETTER = (
    "latency", "error", "loss", "drift", "anomaly", "complaint",
    "hallucination", "false_positive", "default_rate", "bias_gap",
)


def _bounded_metric(name: str, values: list[float]) -> bool:
    """Only clamp measures that look like ratios; never clamp money/latency."""
    if any(token in name.lower() for token in ("latency", "price", "bps", "count", "days", "bars", "size")):
        return False
    return min(values) >= 0 and max(values) <= 1.05


def _health_trajectory(name: str, delta: float, stable_band: float) -> str:
    if abs(delta) <= stable_band:
        return "stable"
    lower_is_better = any(token in name.lower() for token in LOWER_IS_BETTER)
    improving = delta < 0 if lower_is_better else delta > 0
    return "improving" if improving else "worsening"


def build_metric_forecasts(
    metrics: list[ModelMetric], horizon_days: int
) -> list[MetricForecastResponse]:
    grouped: dict[str, list[ModelMetric]] = defaultdict(list)
    for metric in metrics:
        grouped[metric.metric_name].append(metric)

    output: list[MetricForecastResponse] = []
    for name, rows in sorted(grouped.items()):
        rows.sort(key=lambda row: row.recorded_at)
        if len(rows) < 3:
            continue

        # Repeated measurements at the same timestamp cannot establish a time
        # trend, so use at most one (the latest row) for each instant.
        unique = {row.recorded_at: row for row in rows}
        rows = sorted(unique.values(), key=lambda row: row.recorded_at)
        if len(rows) < 3:
            continue

        start = rows[0].recorded_at
        x = np.array([(row.recorded_at - start).total_seconds() / 86400 for row in rows], dtype=float)
        y = np.array([row.metric_value for row in rows], dtype=float)
        if float(np.ptp(x)) == 0:
            continue

        # Recent observations receive more weight while older evidence still
        # contributes. This reacts to drift without pretending the last point
        # is the whole story.
        weights = np.linspace(0.55, 1.0, len(rows))
        slope, intercept = np.polyfit(x, y, 1, w=weights)
        fitted = intercept + slope * x
        residual_std = float(np.sqrt(np.average((y - fitted) ** 2, weights=weights)))

        last_at = rows[-1].recorded_at
        last_x = x[-1]
        steps = min(10, max(4, math.ceil(horizon_days / 7)))
        bounded = _bounded_metric(name, y.tolist())
        points: list[ForecastPoint] = []
        for step in range(1, steps + 1):
            days_ahead = horizon_days * step / steps
            predicted = float(intercept + slope * (last_x + days_ahead))
            uncertainty = 1.96 * residual_std * math.sqrt(1 + step / len(rows))
            lower = predicted - uncertainty
            upper = predicted + uncertainty
            if bounded:
                predicted = min(1.0, max(0.0, predicted))
                lower = min(1.0, max(0.0, lower))
                upper = min(1.0, max(0.0, upper))
            points.append(ForecastPoint(
                recorded_at=last_at + timedelta(days=days_ahead),
                predicted_value=round(predicted, 6),
                lower_bound=round(lower, 6),
                upper_bound=round(upper, 6),
            ))

        projected_delta = points[-1].predicted_value - float(y[-1])
        stable_band = max(abs(float(y[-1])) * 0.02, residual_std * 0.35, 0.001)
        noise_ratio = residual_std / max(float(np.ptp(y)), abs(float(np.mean(y))) * 0.05, 1e-9)
        if len(rows) >= 20 and noise_ratio < 0.18:
            confidence = "high"
        elif len(rows) >= 8 and noise_ratio < 0.45:
            confidence = "medium"
        else:
            confidence = "low"

        output.append(MetricForecastResponse(
            metric_name=name,
            historical_points=len(rows),
            last_observed_at=last_at,
            last_observed_value=round(float(y[-1]), 6),
            slope_per_day=round(float(slope), 8),
            trajectory=_health_trajectory(name, projected_delta, stable_band),
            confidence=confidence,
            forecast_points=points,
        ))

    return output


def _regulatory_signals(model: MLModel) -> list[RegulatorySignal]:
    text = f"{model.name} {model.use_case} {model.owner}".lower()
    personal_data = any(term in text for term in (
        "customer", "client", "credit", "loan", "transaction", "fraud",
        "kyc", "offer", "relationship", "complaint", "collection", "account",
    ))
    securities = any(term in text for term in (
        "trading", "investment", "securities", "market", "surveillance", "fx",
    ))
    regions = model.extra_metadata.get("deployment_regions", []) if model.extra_metadata else []
    eu_deployed = isinstance(regions, list) and "EU" in regions

    signals = [
        RegulatorySignal(
            authority="Reserve Bank of India",
            title="Draft Guidance on Regulatory Principles for Model Risk Management, 2026",
            status="Draft; consultation closed 24 July 2026",
            applicability="direct",
            likely_control_scope=[
                "risk-tiered inventory", "independent validation", "ongoing monitoring",
                "explainability and overrides", "board and senior-management accountability",
            ],
            model_impact=(
                "Prepare evidence for broader model-risk coverage and stronger lifecycle controls; "
                "do not wait for the text to become final before closing material gaps."
            ),
            source_url="https://rbidocs.rbi.org.in/rdocs/Content/PDFs/DRAFTGUIDANCE24062026FF12A4FF7BC84E8887009D5C5365F8BF.PDF",
        ),
        RegulatorySignal(
            authority="Reserve Bank of India",
            title="FREE-AI Committee Report",
            status="RBI committee report, August 2025; directional framework",
            applicability="direct",
            likely_control_scope=[
                "trustworthy AI", "fairness", "accountability", "transparency",
                "privacy", "operational resilience and human oversight",
            ],
            model_impact="Use the principles as a design baseline and retain evidence of human oversight and outcome testing.",
            source_url="https://www.rbi.org.in/Scripts/BS_ViewPublicationReport.aspx",
        ),
    ]

    if personal_data:
        signals.append(RegulatorySignal(
            authority="MeitY / Government of India",
            title="Digital Personal Data Protection Rules, 2025",
            status="Final rules with phased commencement",
            applicability="direct",
            likely_control_scope=[
                "clear notices and lawful purpose", "data minimisation and retention",
                "security safeguards", "breach response", "data-principal rights",
            ],
            model_impact="Map every personal-data feature to purpose, notice, retention, access control, and deletion evidence.",
            source_url="https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa",
        ))

    signals.append(RegulatorySignal(
        authority="Securities and Exchange Board of India",
        title="Responsibility for the use of artificial intelligence",
        status="Binding amendments effective 10 February 2025",
        applicability="direct" if securities else "conditional",
        likely_control_scope=[
            "privacy, security and integrity of investor data",
            "accountability for AI outputs", "compliance with applicable law",
        ],
        model_impact=(
            "A SEBI-regulated operator remains responsible even when the AI is supplied by a third party."
            if not securities else
            "Treat output validation, data integrity, and vendor controls as direct accountable obligations."
        ),
        source_url="https://www.sebi.gov.in/sebi_data/attachdocs/feb-2025/1739276753544.pdf",
    ))

    signals.append(RegulatorySignal(
        authority="European Union",
        title="Regulation (EU) 2024/1689 — Artificial Intelligence Act",
        status="Phased obligations; general application from 2 August 2026",
        applicability="direct" if eu_deployed else "conditional",
        likely_control_scope=[
            "risk classification", "data and technical documentation", "human oversight",
            "accuracy, robustness and cybersecurity", "post-market monitoring",
        ],
        model_impact=(
            "EU deployment is recorded, so complete an AI Act role and risk classification now."
            if eu_deployed else
            "Apply if the system, provider, deployer, or affected output falls within EU territorial scope."
        ),
        source_url="https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng",
    ))
    return signals


def build_model_forecast(
    model: MLModel, metrics: list[ModelMetric], horizon_days: int
) -> ModelForecastResponse:
    forecasts = build_metric_forecasts(metrics, horizon_days)
    worsening = any(item.trajectory == "worsening" for item in forecasts)
    if model.risk_tier == RiskTier.HIGH and worsening:
        priority = "urgent"
    elif model.risk_tier == RiskTier.HIGH or worsening:
        priority = "elevated"
    else:
        priority = "standard"

    return ModelForecastResponse(
        generated_at=datetime.utcnow(),
        horizon_days=horizon_days,
        method="Recency-weighted linear trend with a 95% residual uncertainty band",
        disclaimer=(
            "Scenario projection, not a promise or legal opinion. It extrapolates recorded history, "
            "does not know future incidents or regulatory decisions, and must be reviewed by a human."
        ),
        forecasts=forecasts,
        regulatory_as_of=REGULATORY_AS_OF,
        readiness_priority=priority,
        regulatory_signals=_regulatory_signals(model),
    )
