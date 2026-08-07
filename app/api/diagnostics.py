"""
Dataset diagnostics.

Everything here is a measured statistic, not a judgement. Each check maps to
one of the seven AI risk dimensions the RBI draft names in Chapter V-B.1, and
each finding carries the number it was derived from — so a reviewer can
disagree with the threshold without having to take the conclusion on trust.

The most useful check by far is the temporal one. If the file has a date
column, the early and late portions are compared feature by feature, which
gives a genuinely evidence-based answer to "is this the kind of data that
drifts?" Everything else is structural; that one is empirical.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.api.assessment import Finding

# Rows per feature below which overfitting becomes a live concern. Not a law of
# nature — a widely used rule of thumb, stated openly so it can be argued with.
MIN_ROWS_PER_FEATURE = 10

# Population Stability Index, the standard credit-risk convention:
#   < 0.10  stable
#   0.10-0.25  moderate shift, worth watching
#   > 0.25  significant shift
PSI_MODERATE = 0.10
PSI_SIGNIFICANT = 0.25

# Column names that commonly encode, or proxy for, protected characteristics.
PROTECTED_HINTS = [
    "gender", "sex", "age", "dob", "birth", "marital", "religion", "caste",
    "race", "ethnic", "nationality", "disability", "pregnan", "pincode",
    "pin_code", "zip", "postcode", "district", "region", "language",
]

DATE_HINTS = ["date", "time", "timestamp", "observed", "recorded", "period", "month", "day"]


def _psi(reference: pd.Series, current: pd.Series, bins: int = 10) -> float:
    """
    Population Stability Index between two samples of one feature.

    Bin edges come from the reference distribution only — using the combined
    range would let the current period redefine what "normal" looks like, which
    is precisely the shift being measured. Both sides are floored at a small
    epsilon so an empty bucket produces a large finite number rather than
    infinity.
    """
    ref = pd.to_numeric(reference, errors="coerce").dropna()
    cur = pd.to_numeric(current, errors="coerce").dropna()
    if len(ref) < 20 or len(cur) < 20:
        return float("nan")

    quantiles = np.linspace(0, 1, bins + 1)
    edges = np.unique(np.quantile(ref, quantiles))
    if len(edges) < 3:
        return float("nan")  # near-constant feature; PSI is meaningless

    edges[0], edges[-1] = -np.inf, np.inf
    ref_pct = np.histogram(ref, bins=edges)[0] / len(ref)
    cur_pct = np.histogram(cur, bins=edges)[0] / len(cur)

    eps = 1e-6
    ref_pct = np.clip(ref_pct, eps, None)
    cur_pct = np.clip(cur_pct, eps, None)

    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def _find_date_column(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        if any(h in col.lower() for h in DATE_HINTS):
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().mean() > 0.8:
                return col
    return None


def _find_binary_target(df: pd.DataFrame) -> str | None:
    """Last-resort heuristic: a 0/1 column, preferring conventional names."""
    candidates = []
    for col in df.columns:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(s) == 0:
            continue
        uniques = set(s.unique().tolist())
        if uniques <= {0, 1} and len(uniques) == 2:
            candidates.append(col)
    if not candidates:
        return None
    for name in ("target", "label", "default", "y", "flag", "churn", "fraud"):
        for c in candidates:
            if name in c.lower():
                return c
    return candidates[-1]


def diagnose(df: pd.DataFrame) -> dict:
    findings: list[Finding] = []
    stats: dict = {}

    rows, cols = df.shape
    stats["rows"] = int(rows)
    stats["columns"] = int(cols)

    numeric = df.select_dtypes(include=[np.number])
    feature_count = max(len(numeric.columns), 1)
    rows_per_feature = rows / feature_count
    stats["rows_per_feature"] = round(rows_per_feature, 1)

    # --- Overfitting / generalisation -------------------------------------
    if rows_per_feature < MIN_ROWS_PER_FEATURE:
        findings.append(Finding(
            "high",
            "Too few rows for the number of features",
            f"{rows:,} rows across {feature_count} numeric features — about "
            f"{rows_per_feature:.1f} rows per feature. Below roughly "
            f"{MIN_ROWS_PER_FEATURE}, a model can fit the sample closely and "
            f"generalise poorly, which looks like excellent training performance "
            f"right up until deployment.",
            "Gather more rows, cut features, or regularise hard — and judge the "
            "model only on out-of-sample performance.",
            "Overfitting and generalisation",
            "Chapter V-B.1, risk dimension 4",
            evidence=f"{rows_per_feature:.1f} rows per feature",
        ))

    # --- Data quality ------------------------------------------------------
    missing = df.isna().mean().sort_values(ascending=False)
    worst_missing = missing[missing > 0.05]
    stats["columns_with_missing"] = int((missing > 0).sum())
    stats["worst_missing"] = (
        {"column": str(missing.index[0]), "share": round(float(missing.iloc[0]), 4)}
        if len(missing) and missing.iloc[0] > 0
        else None
    )

    if len(worst_missing):
        top = ", ".join(f"{c} ({v:.0%})" for c, v in worst_missing.head(4).items())
        findings.append(Finding(
            "high" if worst_missing.iloc[0] > 0.3 else "medium",
            "Material missing data",
            f"{len(worst_missing)} column(s) are more than 5% empty: {top}. How "
            f"missing values are filled quietly becomes part of the model's "
            f"behaviour, and imputation choices are rarely revisited once made.",
            "Document the imputation strategy and test whether the model's outputs "
            "are sensitive to it.",
            "Data risks — quality, completeness",
            "Chapter V-B.1, risk dimension 7",
            evidence=f"worst column {worst_missing.iloc[0]:.1%} missing",
        ))

    # --- Spurious correlation / dead features ------------------------------
    near_constant = []
    for col in numeric.columns:
        s = numeric[col].dropna()
        if len(s) and s.nunique() <= 1:
            near_constant.append(col)
        elif len(s) and s.std(ddof=0) == 0:
            near_constant.append(col)
    if near_constant:
        findings.append(Finding(
            "medium",
            "Constant features present",
            f"{len(near_constant)} feature(s) never vary: "
            f"{', '.join(map(str, near_constant[:5]))}. They contribute nothing but "
            f"add surface area — and a feature that is constant in training but not "
            f"in production is a live failure mode.",
            "Drop them, and check why they're constant here but presumably not in "
            "the real population.",
            "Spurious correlations",
            "Chapter V-B.1, risk dimension 5",
            evidence=f"{len(near_constant)} constant column(s)",
        ))

    # --- Bias / protected attributes ---------------------------------------
    flagged = [c for c in df.columns if any(h in str(c).lower() for h in PROTECTED_HINTS)]
    stats["protected_candidates"] = flagged
    if flagged:
        findings.append(Finding(
            "high",
            "Possible protected or proxy attributes",
            f"Column names suggest protected characteristics or close proxies: "
            f"{', '.join(map(str, flagged[:6]))}. Geography and age in particular "
            f"often stand in for characteristics that cannot lawfully be used "
            f"directly — removing the obvious column doesn't remove the effect.",
            "Run a disparate-impact test across the affected segments. Justify each "
            "attribute individually, and test for proxies among what's left.",
            "Bias and discriminatory outputs",
            "Chapter V-B.1, risk dimension 3",
            evidence=f"{len(flagged)} candidate column(s)",
        ))

    # --- Class imbalance ---------------------------------------------------
    target = _find_binary_target(df)
    stats["detected_target"] = target
    if target:
        rate = float(pd.to_numeric(df[target], errors="coerce").dropna().mean())
        stats["positive_rate"] = round(rate, 4)
        minority = min(rate, 1 - rate)
        if minority < 0.05:
            findings.append(Finding(
                "high",
                "Severe class imbalance",
                f"'{target}' has a positive rate of {rate:.1%}. A classifier can "
                f"reach {max(rate, 1 - rate):.1%} accuracy by always predicting the "
                f"majority class and learning nothing — which is why accuracy is the "
                f"wrong headline metric here.",
                "Weight the minority class or resample, and report AUC, precision and "
                "recall rather than accuracy.",
                "Overfitting and generalisation",
                "Chapter V-B.1, risk dimension 4",
                evidence=f"{minority:.1%} minority class",
            ))
        elif minority < 0.15:
            findings.append(Finding(
                "medium",
                "Class imbalance",
                f"'{target}' has a positive rate of {rate:.1%}. Manageable, but "
                f"accuracy will flatter the model.",
                "Use class weighting and report AUC alongside precision and recall.",
                "Overfitting and generalisation",
                "Chapter V-B.1, risk dimension 4",
                evidence=f"{minority:.1%} minority class",
            ))

    # --- Temporal drift — the empirical one --------------------------------
    date_col = _find_date_column(df)
    stats["date_column"] = date_col
    drift_detail: dict | None = None

    if date_col and rows >= 100:
        ordered = df.copy()
        ordered["_ts"] = pd.to_datetime(ordered[date_col], errors="coerce")
        ordered = ordered.dropna(subset=["_ts"]).sort_values("_ts")

        split = len(ordered) // 2
        early, late = ordered.iloc[:split], ordered.iloc[split:]

        psis: dict[str, float] = {}
        for col in numeric.columns:
            if col == target:
                continue
            value = _psi(early[col], late[col])
            if not np.isnan(value):
                psis[str(col)] = round(value, 4)

        if psis:
            shifted = {k: v for k, v in psis.items() if v >= PSI_MODERATE}
            significant = {k: v for k, v in psis.items() if v >= PSI_SIGNIFICANT}
            share = len(shifted) / len(psis)

            drift_detail = {
                "date_column": date_col,
                "early_period": str(early["_ts"].min().date()),
                "split_at": str(late["_ts"].min().date()),
                "late_period": str(late["_ts"].max().date()),
                "per_feature_psi": dict(sorted(psis.items(), key=lambda kv: -kv[1])),
                "shifted_share": round(share, 3),
                "significant": list(significant.keys()),
            }

            if significant:
                worst = max(significant.items(), key=lambda kv: kv[1])
                findings.append(Finding(
                    "high",
                    "This data already drifts within itself",
                    f"Comparing the first half of the file against the second, "
                    f"{len(significant)} of {len(psis)} features show a significant "
                    f"distribution shift (PSI above {PSI_SIGNIFICANT}). The worst is "
                    f"'{worst[0]}' at {worst[1]:.2f}. That shift happened inside your "
                    f"own training window — production will not be kinder.",
                    "Assume this model degrades. Set drift thresholds and a retraining "
                    "trigger before deployment rather than after the first incident.",
                    "Data risks — data drift and concept drift",
                    "Chapter V-B.1, risk dimension 7",
                    evidence=f"{len(significant)}/{len(psis)} features PSI > {PSI_SIGNIFICANT}",
                ))
            elif shifted:
                findings.append(Finding(
                    "medium",
                    "Moderate movement within the training window",
                    f"{len(shifted)} of {len(psis)} features shift moderately "
                    f"(PSI {PSI_MODERATE}–{PSI_SIGNIFICANT}) between the first and "
                    f"second half of the file. Not alarming, but not static either.",
                    "Monitor these features specifically once deployed.",
                    "Data risks — data drift and concept drift",
                    "Chapter V-B.1, risk dimension 7",
                    evidence=f"{len(shifted)}/{len(psis)} features PSI > {PSI_MODERATE}",
                ))
            else:
                findings.append(Finding(
                    "info",
                    "Stable across the training window",
                    f"No feature shifts materially between the first and second half "
                    f"of the file (all PSI below {PSI_MODERATE}). Encouraging — though "
                    f"a stable past is weak evidence about a turbulent future, as any "
                    f"model trained on 2019 data discovered in March 2020.",
                    "Still set drift thresholds. Stability is a measurement, not a "
                    "guarantee.",
                    "Data risks — data drift and concept drift",
                    "Chapter V-B.1, risk dimension 7",
                    evidence=f"max PSI {max(psis.values()):.3f}",
                ))
    elif not date_col:
        findings.append(Finding(
            "info",
            "No date column — drift can't be measured here",
            "Nothing in this file identifies when each row was observed, so there's "
            "no way to test whether the data moves over time. That's the single most "
            "informative check available and it isn't possible on this input.",
            "Include a timestamp column if one exists. Without it, drift monitoring "
            "has to start from scratch after deployment.",
            "Data risks — data drift and concept drift",
            "Chapter V-B.1, risk dimension 7",
        ))

    return {
        "stats": stats,
        "drift": drift_detail,
        "findings": [f.as_dict() for f in findings],
    }
