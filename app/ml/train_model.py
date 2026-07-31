"""
Trains the sme-credit-scorer XGBoost model on the "healthy" training data,
evaluates it, and saves it to disk. This is the model whose real-world
performance we'll later measure against the drifted "current" data.
"""

import pickle

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, precision_score, recall_score
import xgboost as xgb

FEATURES = [
    "avg_monthly_turnover", "filing_delay_days", "itc_claim_ratio",
    "avg_balance", "inflow_volatility", "bounce_count_90d",
]
TARGET = "defaulted"


def train():
    df = pd.read_csv("data_train.csv")
    X_train, X_test, y_train, y_test = train_test_split(
        df[FEATURES], df[TARGET], test_size=0.2, random_state=42, stratify=df[TARGET]
    )

    # Defaults are rare (~16%), so a plain classifier will just learn to
    # predict "no default" most of the time and still look "accurate."
    # scale_pos_weight corrects for this by up-weighting the minority class
    # during training — standard practice for credit/fraud data, and worth
    # mentioning explicitly in an interview since it shows you understand
    # why raw accuracy is a misleading metric here.
    n_pos = y_train.sum()
    n_neg = len(y_train) - n_pos
    scale_pos_weight = n_neg / n_pos

    model = xgb.XGBClassifier(
        n_estimators=150, max_depth=4, learning_rate=0.08,
        eval_metric="logloss", random_state=42,
        scale_pos_weight=scale_pos_weight,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": accuracy_score(y_test, preds),
        "auc": roc_auc_score(y_test, proba),
        "precision": precision_score(y_test, preds),
        "recall": recall_score(y_test, preds),
    }

    with open("sme_credit_model.pkl", "wb") as f:
        pickle.dump(model, f)

    print("✅ Model trained and saved to sme_credit_model.pkl")
    for k, v in metrics.items():
        print(f"   {k}: {v:.4f}")

    return model, metrics


if __name__ == "__main__":
    train()