"""
Explains individual sme-credit-scorer predictions using SHAP.

RBI's June 2026 draft guidance explicitly rules out "black-box AI" for
decisions that affect customers — if a model rejects someone's loan, the
bank has to be able to say *why*, in terms a non-technical reviewer (or
eventually the customer) can understand. This script produces exactly
that explanation for a single applicant.
"""

import pickle

import pandas as pd
import shap

from app.ml.train_model import FEATURES

FEATURE_LABELS = {
    "avg_monthly_turnover": "Average monthly business turnover",
    "filing_delay_days": "GST filing delay (days)",
    "itc_claim_ratio": "Input tax credit claim ratio",
    "avg_balance": "Average bank balance",
    "inflow_volatility": "Inflow volatility (income stability)",
    "bounce_count_90d": "Bounced payments in last 90 days",
}


def explain_applicant(applicant_row: dict):
    with open("sme_credit_model.pkl", "rb") as f:
        model = pickle.load(f)

    X = pd.DataFrame([applicant_row])[FEATURES]

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    # shap_values[0] = per-feature contribution to THIS applicant's risk score.
    # Positive = pushed risk UP (worse for the applicant), negative = pushed risk DOWN.
    contributions = list(zip(FEATURES, X.iloc[0].values, shap_values[0]))
    contributions.sort(key=lambda x: abs(x[2]), reverse=True)

    predicted_prob = model.predict_proba(X)[0][1]

    print(f"Predicted default probability: {predicted_prob:.1%}")
    print(f"Decision: {'FLAGGED AS HIGHER RISK' if predicted_prob > 0.5 else 'LOOKS OKAY'}")
    print()
    print("Why the model reached this conclusion (top factors):")
    for feature, value, contribution in contributions:
        direction = "⬆ increased risk" if contribution > 0 else "⬇ decreased risk"
        print(f"  {FEATURE_LABELS[feature]:45s} = {value:>10.2f}   {direction} ({contribution:+.3f})")

    return predicted_prob, contributions


if __name__ == "__main__":
    # A believable "borderline" SME applicant: decent turnover, but a slow
    # GST filer with a couple of bounced payments recently.
    example_applicant = {
        "avg_monthly_turnover": 850000,
        "filing_delay_days": 12,
        "itc_claim_ratio": 0.55,
        "avg_balance": 95000,
        "inflow_volatility": 0.6,
        "bounce_count_90d": 2,
    }
    explain_applicant(example_applicant)