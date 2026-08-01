"""
Generates synthetic SME credit data that mimics ICICI's real approach:
fusing GST filing behavior with bank transaction behavior to predict
whether an SME will default on a credit line.

The correlations are deliberately built in (not pure random noise) so the
model has real signal to learn, and so a "drift" later means something
meaningful (a genuine shift in the underlying relationship, not just luck).
"""

import numpy as np
import pandas as pd

np.random.seed(42)


def generate_sme_data(n_rows: int, drift: bool = False) -> pd.DataFrame:
    """
    drift=False -> "healthy" data distribution (what the model was trained on)
    drift=True  -> shifted distribution (simulates a post-training market shift,
                   e.g. a slowdown that changes SME repayment behavior)
    """
    # --- GST features ---
    avg_monthly_turnover = np.random.lognormal(mean=13.0, sigma=0.6, size=n_rows)  # in INR
    filing_delay_days = np.random.exponential(scale=3 if not drift else 9, size=n_rows)
    itc_claim_ratio = np.clip(np.random.normal(0.75, 0.15, n_rows), 0, 1)

    # --- Transaction features ---
    avg_balance = avg_monthly_turnover * np.random.uniform(0.05, 0.25, n_rows)
    inflow_volatility = np.random.gamma(shape=2, scale=0.15 if not drift else 0.35, size=n_rows)
    bounce_count_90d = np.random.poisson(lam=0.5 if not drift else 2.2, size=n_rows)

    # --- Target: default probability driven by a realistic combination ---
    risk_score = (
        0.35 * (filing_delay_days / 15)
        + 0.25 * (1 - itc_claim_ratio)
        + 0.20 * (inflow_volatility / 1.0)
        + 0.20 * (bounce_count_90d / 5)
    )
    default_prob = 1 / (1 + np.exp(-10 * (risk_score - 0.5)))  # steeper logistic -> stronger signal
    defaulted = np.random.binomial(1, default_prob)

    return pd.DataFrame({
        "avg_monthly_turnover": avg_monthly_turnover,
        "filing_delay_days": filing_delay_days,
        "itc_claim_ratio": itc_claim_ratio,
        "avg_balance": avg_balance,
        "inflow_volatility": inflow_volatility,
        "bounce_count_90d": bounce_count_90d,
        "defaulted": defaulted,
    })


if __name__ == "__main__":
    df_train = generate_sme_data(5000, drift=False)
    df_train.to_csv("data_train.csv", index=False)
    print(f"✅ Training data: {len(df_train)} rows, default rate = {df_train['defaulted'].mean():.2%}")
    df_current = generate_sme_data(1000, drift=True)
    df_current.to_csv("data_current.csv", index=False)
    print(f"✅ Current (drifted) data: {len(df_current)} rows, default rate = {df_current['defaulted'].mean():.2%}")