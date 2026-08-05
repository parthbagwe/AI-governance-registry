"""
Trains the intraday FX monitor on ~1000 minutes of real 1-minute bars.

Unsupervised, for the same reason as every other monitor here: nobody labels
"minutes a desk should have reacted to" in advance. The label only exists once
the move has already happened.

Contamination is set *lower* than the daily model's — 1% instead of 2% — and
that asymmetry is deliberate. At daily cadence, 2% is about five alerts a year.
At 1-minute cadence, 2% would be roughly fourteen alerts an hour. Nobody reads
fourteen alerts an hour; they mute the channel, and then the one that mattered
goes unseen. Alert volume is the constraint that governs this number, not
model fit.
"""

import pickle

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.ml.intraday_feed import BASELINE_PATH, FEATURES

MODEL_PATH = "fx_intraday_model.pkl"

# ~6 flagged minutes per 1000 — roughly one per two hours of trading.
CONTAMINATION = 0.01


def train():
    df = pd.read_csv(BASELINE_PATH)
    if len(df) < 200:
        raise RuntimeError(
            f"Only {len(df)} bars in {BASELINE_PATH} — too few to characterise "
            f"normal intraday behaviour. Re-run: python -m app.ml.intraday_feed"
        )

    X = df[FEATURES]

    model = IsolationForest(
        n_estimators=200,
        contamination=CONTAMINATION,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X)

    # Negated so a higher logged number means "more unusual", consistent with
    # every other metric in this registry.
    scores = -model.score_samples(X)
    flags = model.predict(X) == -1

    metrics = {
        "anomaly_rate": float(flags.mean()),
        "mean_anomaly_score": float(np.mean(scores)),
        "p99_anomaly_score": float(np.percentile(scores, 99)),
        "baseline_sample_size": float(len(df)),
        "baseline_mean_range_bps": float(df["range_bps"].mean()),
    }

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    print(f"✅ Trained on {len(df)} real 1-minute bars -> {MODEL_PATH}")
    for k, v in metrics.items():
        print(f"   {k}: {v:.4f}")

    flagged = df.loc[flags].copy()
    if not flagged.empty:
        flagged["anomaly_score"] = scores[flags]
        print("\n🚩 Most unusual minutes in the baseline window:")
        for _, row in flagged.nlargest(min(6, len(flagged)), "anomaly_score").iterrows():
            print(
                f"   {row['observed_at']} UTC  "
                f"px={row['close']:.5f}  "
                f"move {row['return_bps']:>+7.2f}bps  "
                f"range {row['range_bps']:>6.2f}bps  "
                f"({row['range_vs_recent']:>5.1f}× recent)  "
                f"body {row['body_ratio']:.2f}"
            )
        print("\n   A high range with a low body ratio is a wick — the market")
        print("   gapped and recovered within the minute. That's a liquidity")
        print("   event, not a trend, and worth flagging differently.")

    return model, metrics


if __name__ == "__main__":
    train()
