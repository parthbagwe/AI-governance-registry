"""
Replaces the synthetic SME data with the real, public "Give Me Some Credit"
Kaggle dataset (2011 competition). This is real, legally usable credit data
(anonymized at source by Kaggle/the original data provider) — unlike GST
filing records, which are never public and must stay synthetic.

cs-training.csv has labels (SeriousDlqin2yrs) -> used to TRAIN the model.
cs-test.csv has NO labels (Kaggle withholds them for the competition)
  -> we use it purely as "current production data" for DRIFT detection,
     since Evidently only compares feature distributions, never needs labels.

Run this once, with cs-training.csv and cs-test.csv sitting in the project
root (same folder as this script), before running train_model.py.
"""

import pandas as pd

RENAME_MAP = {
    "RevolvingUtilizationOfUnsecuredLines": "revolving_utilization",
    "age": "age",
    "NumberOfTime30-59DaysPastDueNotWorse": "late_30_59_days",
    "DebtRatio": "debt_ratio",
    "MonthlyIncome": "monthly_income",
    "NumberOfOpenCreditLinesAndLoans": "open_credit_lines",
    "NumberOfTimes90DaysLate": "late_90_days",
    "NumberRealEstateLoansOrLines": "real_estate_loans",
    "NumberOfTime60-89DaysPastDueNotWorse": "late_60_89_days",
    "NumberOfDependents": "dependents",
    "SeriousDlqin2yrs": "defaulted",
}

FEATURES = [
    "revolving_utilization", "age", "late_30_59_days", "debt_ratio",
    "monthly_income", "open_credit_lines", "late_90_days",
    "real_estate_loans", "late_60_89_days", "dependents",
]


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=RENAME_MAP)
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")], errors="ignore")

    # MonthlyIncome and NumberOfDependents both have real missing values in
    # this dataset — impute with median rather than dropping rows, since
    # dropping would bias the sample toward people who fully filled the form.
    df["monthly_income"] = df["monthly_income"].fillna(df["monthly_income"].median())
    df["dependents"] = df["dependents"].fillna(df["dependents"].median())

    # A small number of rows have implausible values (e.g. age=0, or
    # utilization/debt ratios in the thousands due to data entry errors in
    # the original dataset) — this is a well-known quirk of this specific
    # Kaggle dataset, not something we introduced. Clip rather than drop, to
    # keep the sample size intact while preventing these outliers from
    # dominating training.
    df["age"] = df["age"].clip(lower=18, upper=100)
    df["debt_ratio"] = df["debt_ratio"].clip(upper=df["debt_ratio"].quantile(0.99))
    df["revolving_utilization"] = df["revolving_utilization"].clip(upper=df["revolving_utilization"].quantile(0.99))

    return df


def prepare():
    train_raw = pd.read_csv("cs-training.csv")
    test_raw = pd.read_csv("cs-test.csv")

    train_clean = _clean(train_raw)
    test_clean = _clean(test_raw)

    train_clean.to_csv("personal_data_train.csv", index=False)
    # cs-test.csv has no "defaulted" column (Kaggle withholds it) -- that's
    # fine, it's only ever used for drift's feature-distribution comparison.
    test_clean.to_csv("personal_data_current.csv", index=False)

    print(f"✅ Real training data prepared: {len(train_clean)} rows")
    print(f"   Default rate: {train_clean['defaulted'].mean():.2%}")
    print(f"✅ Real 'current' data prepared (for drift checks): {len(test_clean)} rows")
    print(f"   Columns: {FEATURES}")


if __name__ == "__main__":
    prepare()