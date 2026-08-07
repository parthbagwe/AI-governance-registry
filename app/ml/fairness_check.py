"""
Checks sme-credit-scorer for fairness across business-size segments.

RBI's draft guidance requires AI systems to be "fair" as well as safe and
explainable — this script operationalizes that into an actual test rather
than a claim. We use the "disparate impact ratio" (also called the 80%
rule), a standard fairness metric: if one group is approved at less than
80% the rate of the group with the highest approval rate, that's flagged
as a potential fairness concern worth human review.

This does NOT prove the model is unbiased — it's a first-pass screening
test, the same way a real model risk team would run one check among many.
"""

import pickle

import pandas as pd

from app.ml.train_model import FEATURES

DISPARATE_IMPACT_THRESHOLD = 0.80  # standard "80% rule" from US fair-lending practice


def segment_by_turnover(df: pd.DataFrame) -> pd.Series:
    """
    Splits SMEs into size segments by monthly turnover. This is a proxy
    grouping (small businesses vs larger ones) — real fairness testing
    would use protected characteristics, but turnover-based segmentation
    is a legitimate, commonly used lens for SME lending fairness reviews
    since very small businesses are often a policy-sensitive group.
    """
    return pd.cut(
        df["avg_monthly_turnover"],
        bins=[0, 300_000, 1_000_000, float("inf")],
        labels=["small_business", "mid_business", "large_business"],
    )


def run_fairness_check():
    with open("sme_credit_model.pkl", "rb") as f:
        model = pickle.load(f)

    df = pd.read_csv("data_train.csv")
    df["segment"] = segment_by_turnover(df)
    df["predicted_default_prob"] = model.predict_proba(df[FEATURES])[:, 1]
    df["approved"] = df["predicted_default_prob"] < 0.5  # simple approve/reject cutoff

    approval_rates = df.groupby("segment", observed=True)["approved"].mean()

    print("Approval rate by business size segment:")
    for segment, rate in approval_rates.items():
        print(f"  {segment:20s}: {rate:.1%}  (n={int((df['segment'] == segment).sum())})")

    highest_rate = approval_rates.max()
    print(f"\nHighest approval rate: {highest_rate:.1%} ({approval_rates.idxmax()})")
    print(f"Disparate impact threshold (80% rule): flagging any segment below {highest_rate * DISPARATE_IMPACT_THRESHOLD:.1%}\n")

    flagged_segments = []
    for segment, rate in approval_rates.items():
        ratio = rate / highest_rate
        status = "🔴 FLAGGED" if ratio < DISPARATE_IMPACT_THRESHOLD else "🟢 OK"
        print(f"  {segment:20s}: disparate impact ratio = {ratio:.2f}  {status}")
        if ratio < DISPARATE_IMPACT_THRESHOLD:
            flagged_segments.append(segment)

    if flagged_segments:
        print(f"\n⚠️  Fairness concern: {flagged_segments} approved at less than "
              f"{DISPARATE_IMPACT_THRESHOLD:.0%} the rate of the best-performing segment. "
              f"This model should not be auto-approved for production without human review "
              f"of this finding.")
    else:
        print("\n✅ No disparate impact flagged across business-size segments.")

    _log_to_registry(approval_rates, flagged_segments)
    return approval_rates, flagged_segments


def _log_to_registry(approval_rates, flagged_segments):
    """
    Logs the worst-case disparate impact ratio as a registry metric, the
    same way drift_check.py logs drift_share — so fairness becomes part of
    the model's tracked history, not a one-off script output nobody sees again.
    """
    from app.ml.registry_client import describe_target, fetch_model, get_client

    client = get_client()
    print(f"\n📕 Registry: {describe_target()}")

    sme = fetch_model(client, "sme-credit-scorer")
    if not sme:
        print("   sme-credit-scorer isn't registered — nothing to log against.")
        return
    model_id = sme["id"]

    worst_ratio = (approval_rates / approval_rates.max()).min()
    client.post(
        f"/api/v1/models/{model_id}/metrics",
        json={"metric_name": "fairness_min_disparate_impact_ratio", "metric_value": float(worst_ratio)},
    )
    print(f"\n📝 Logged fairness_min_disparate_impact_ratio = {worst_ratio:.3f} to the registry.")


if __name__ == "__main__":
    run_fairness_check()