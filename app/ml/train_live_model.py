"""
Trains the payment-anomaly monitor on a live baseline snapshot.

Unsupervised on purpose. Nobody hands you labelled fraud in a live payment
stream — by the time a transaction is confirmed fraudulent, it's weeks old and
the pattern has moved on. So this is an Isolation Forest: it learns the shape
of ordinary traffic and flags what doesn't fit, which is how the unsupervised
half of a real bank's fraud stack works alongside its supervised models.

The contamination rate is the one honest judgement call here: it's the share
of traffic we assume is anomalous, and it directly sets how many alerts an
operations team gets handed each day. Setting it too high is not a modelling
error, it's an operational one — analysts drown, and real alerts get lost in
the noise. 2% is deliberately conservative.
"""

import pickle

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.ml.live_feed import FEATURES

BASELINE_PATH = "live_baseline.csv"
MODEL_PATH = "payment_anomaly_model.pkl"

# Share of live traffic assumed anomalous. This is an alert-volume decision
# dressed up as a hyperparameter — see the module docstring.
CONTAMINATION = 0.02


def train():
    df = pd.read_csv(BASELINE_PATH)
    X = df[FEATURES]

    model = IsolationForest(
        n_estimators=200,
        contamination=CONTAMINATION,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X)

    # score_samples: lower = more anomalous. Negated so that in the registry
    # a *higher* logged number consistently means *more* unusual, matching
    # how every other metric in this project reads.
    scores = -model.score_samples(X)
    flags = model.predict(X) == -1

    metrics = {
        "anomaly_rate": float(flags.mean()),
        "mean_anomaly_score": float(np.mean(scores)),
        "p99_anomaly_score": float(np.percentile(scores, 99)),
        "baseline_sample_size": float(len(df)),
    }

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    print(f"✅ Trained on {len(df)} live transactions -> {MODEL_PATH}")
    for k, v in metrics.items():
        print(f"   {k}: {v:.4f}")

    flagged = df.loc[flags].copy()
    if not flagged.empty:
        flagged["anomaly_score"] = scores[flags]
        top = flagged.nlargest(min(5, len(flagged)), "anomaly_score")
        print("\n🚩 Most unusual transactions in this baseline:")
        for _, row in top.iterrows():
            print(
                f"   {row['txid'][:16]}…  "
                f"value={row['value']:>14,.0f}  "
                f"fee={row['fee']:>9,.0f}  "
                f"fee/value={row['fee_ratio_bps']:>9,.0f}bps  "
                f"score={row['anomaly_score']:.3f}"
            )

    return model, metrics


if __name__ == "__main__":
    train()
