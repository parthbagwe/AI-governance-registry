"""
Trains a SECOND, separate model — personal-loan-credit-scorer — on real
data from the 2011 Kaggle "Give Me Some Credit" competition.

Kept entirely separate from sme-credit-scorer (which stays on realistic
synthetic data, since real GST filing records are never public) so the
two models don't collide, and so the portfolio honestly shows both a
real-data model and a synthetic-data model side by side.
"""

import pickle

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, precision_score, recall_score
import xgboost as xgb

FEATURES = [
    "revolving_utilization", "age", "late_30_59_days", "debt_ratio",
    "monthly_income", "open_credit_lines", "late_90_days",
    "real_estate_loans", "late_60_89_days", "dependents",
]
TARGET = "defaulted"


def train():
    df = pd.read_csv("personal_data_train.csv")
    X_train, X_test, y_train, y_test = train_test_split(
        df[FEATURES], df[TARGET], test_size=0.2, random_state=42, stratify=df[TARGET]
    )

    n_pos = y_train.sum()
    n_neg = len(y_train) - n_pos
    scale_pos_weight = n_neg / n_pos

    model = xgb.XGBClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.05,
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

    with open("personal_credit_model.pkl", "wb") as f:
        pickle.dump(model, f)

    print("✅ Real-data model trained and saved to personal_credit_model.pkl")
    for k, v in metrics.items():
        print(f"   {k}: {v:.4f}")

    return model, metrics


if __name__ == "__main__":
    train()