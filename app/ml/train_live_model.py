"""
Trains the FX exposure monitor on three years of real ECB market data.

Unsupervised on purpose. There is no labelled dataset of "days a treasury desk
should have escalated" — the label only exists in hindsight, often months
later, and by then the regime has moved. So this is an Isolation Forest: it
learns the shape of an ordinary trading day and flags the ones that don't fit.
That's how the unsupervised half of a real market-risk stack works, sitting
alongside the supervised and rules-based pieces rather than replacing them.

The contamination rate is the one honest judgement call here. It is not a
tuning knob — it directly sets how many days a year get escalated to a human.
Set it at 5% and you hand a desk an alert every three weeks that mostly says
nothing; the real alerts then get ignored. 2% is deliberately conservative:
roughly five flagged days a year.
"""

import pickle

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.ml.live_feed import FEATURES

BASELINE_PATH = "live_baseline.csv"
MODEL_PATH = "fx_anomaly_model.pkl"

# Share of trading days assumed anomalous — an alert-volume decision dressed
# up as a hyperparameter. See the module docstring.
CONTAMINATION = 0.02


def train():
    df = pd.read_csv(BASELINE_PATH)
    if len(df) < 100:
        raise RuntimeError(
            f"Only {len(df)} days in {BASELINE_PATH} — too few to characterise "
            f"normal market behaviour. Re-run: python -m app.ml.live_feed"
        )

    X = df[FEATURES]

    model = IsolationForest(
        n_estimators=200,
        contamination=CONTAMINATION,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X)

    # score_samples: lower = more anomalous. Negated so a higher logged number
    # consistently means "more unusual", matching how every other metric in
    # this registry reads.
    scores = -model.score_samples(X)
    flags = model.predict(X) == -1

    metrics = {
        # Named "baseline_flag_rate", not "anomaly_rate", because on the
        # training set this number is *defined* by CONTAMINATION — it can only
        # ever hand back the hyperparameter it was given. It's recorded for
        # completeness, not as a finding.
        #
        # The measurement that means something is the anomaly rate the monitor
        # observes on data the model has never seen. Keeping the two names
        # distinct also stops them being plotted as one series in the
        # dashboard, which would mix a setting with a result.
        "baseline_flag_rate": float(flags.mean()),
        "mean_anomaly_score": float(np.mean(scores)),
        "p99_anomaly_score": float(np.percentile(scores, 99)),
        "baseline_sample_size": float(len(df)),
    }

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    print(f"✅ Trained on {len(df)} real trading days -> {MODEL_PATH}")
    for k, v in metrics.items():
        print(f"   {k}: {v:.4f}")

    flagged = df.loc[flags].copy()
    if not flagged.empty:
        flagged["anomaly_score"] = scores[flags]
        print("\n🚩 Most unusual trading days in the baseline period:")
        for _, row in flagged.nlargest(min(6, len(flagged)), "anomaly_score").iterrows():
            print(
                f"   {row['observed_on']}  "
                f"worst mover {row['max_abs_move']:>6.2f}%  "
                f"USD/INR {row['usd_move']:>+6.2f}%  "
                f"{int(row['n_material_moves'])} material moves  "
                f"score={row['anomaly_score']:.3f}"
            )
        print("\n   Worth sanity-checking a couple of these against the news for")
        print("   those dates — if the model is working, they should line up with")
        print("   something that actually happened.")

    return model, metrics


if __name__ == "__main__":
    train()
