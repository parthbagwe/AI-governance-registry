"""
Dataset samples.

A registry that records *which* data fed a model but gives you no way to look
at any of it leaves an obvious gap: a reviewer reading "trained on
gst_returns" has to take that entirely on trust. So each model can expose a
capped sample of the data behind it.

Two constraints shape this, and both are deliberate:

**Not every model gets to.** Exposure is opt-in per model, declared below.
A real bank's credit model trains on live customer records, and an API that
would hand those out because a governance tool found it convenient is a
breach waiting to be written up. Every dataset offered here is either
synthetic or already public — that's the entire test for inclusion, and a
model whose data doesn't meet it returns 403 with the reason.

**Samples, never the full file.** Capped at 1000 rows. A lineage register
exists to describe data, not to become a second copy of it — the moment it
serves complete datasets it is itself a system that needs governing.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from fastapi import HTTPException
from fastapi.responses import Response

MAX_SAMPLE_ROWS = 1000

# Project root — this file is app/api/datasets.py, so up three levels.
ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class DatasetSpec:
    filename: str
    label: str
    provenance: str
    description: str


# Keyed by model name. Absence from this map means "not exposed", which is the
# safe default: adding a dataset is a deliberate act, forgetting to add one
# doesn't leak anything.
DATASETS: dict[str, DatasetSpec] = {
    "sme-credit-scorer": DatasetSpec(
        filename="data_train.csv",
        label="SME credit training set",
        provenance="synthetic",
        description=(
            "Synthetic SME lending data with deliberately engineered "
            "correlations between GST filing behaviour, transaction patterns "
            "and default. Real GST filing records are not public anywhere, so "
            "simulation is the only responsible option here — not a shortcut."
        ),
    ),
    "personal-loan-credit-scorer": DatasetSpec(
        filename="personal_data_train.csv",
        label="Consumer credit training set",
        provenance="real_public",
        description=(
            "Real anonymised borrower records from the 2011 Kaggle 'Give Me "
            "Some Credit' competition — roughly 150,000 rows with genuine "
            "default outcomes. Already public, which is why it can be shown."
        ),
    ),
    "fx-exposure-monitor": DatasetSpec(
        filename="live_baseline.csv",
        label="Daily FX baseline",
        provenance="real_public",
        description=(
            "Engineered daily features from real ECB reference rates — one "
            "row per business day describing how the whole INR exposure "
            "basket behaved. Published by the ECB every business day."
        ),
    ),
    "fx-intraday-monitor": DatasetSpec(
        filename="intraday_baseline.csv",
        label="Intraday FX baseline",
        provenance="real_public",
        description=(
            "Engineered features from real 1-minute USD/INR bars. Market "
            "data, licensed for use but not for redistribution in bulk — "
            "another reason the sample is capped rather than complete."
        ),
    ),
}

PROVENANCE_LABEL = {
    "synthetic": "Synthetic",
    "real_public": "Real, public",
}


def _spec_or_403(model_name: str) -> DatasetSpec:
    spec = DATASETS.get(model_name)
    if spec is None:
        raise HTTPException(
            status_code=403,
            detail=(
                f"No dataset is exposed for '{model_name}'. Datasets are "
                f"opt-in per model, and only synthetic or already-public data "
                f"qualifies. A model trained on customer records would never "
                f"be readable through this API."
            ),
        )
    return spec


def _load_or_404(spec: DatasetSpec) -> pd.DataFrame:
    path = ROOT / spec.filename
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"'{spec.filename}' isn't present on this instance. Datasets "
                f"are generated locally and not committed, so a deployed "
                f"instance won't have them unless they were shipped with it. "
                f"Locally, re-run the pipeline scripts to produce it."
            ),
        )
    try:
        return pd.read_csv(path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not read '{spec.filename}': {e}")


def dataset_info(model_name: str) -> dict:
    """Metadata only — enough for the UI to describe what's available without
    downloading anything."""
    spec = DATASETS.get(model_name)
    if spec is None:
        return {"available": False, "reason": "not_exposed"}

    path = ROOT / spec.filename
    if not path.exists():
        return {"available": False, "reason": "file_missing", "filename": spec.filename}

    df = pd.read_csv(path)
    return {
        "available": True,
        "filename": spec.filename,
        "label": spec.label,
        "provenance": spec.provenance,
        "provenance_label": PROVENANCE_LABEL.get(spec.provenance, spec.provenance),
        "description": spec.description,
        "total_rows": int(len(df)),
        "columns": list(df.columns),
        "sample_rows": min(len(df), MAX_SAMPLE_ROWS),
        "capped": len(df) > MAX_SAMPLE_ROWS,
        "preview": df.head(8).round(4).to_dict(orient="records"),
    }


def dataset_csv(model_name: str, limit: int | None = None) -> Response:
    """A capped sample as CSV. Opens directly in Excel."""
    spec = _spec_or_403(model_name)
    df = _load_or_404(spec)

    rows = min(limit or MAX_SAMPLE_ROWS, MAX_SAMPLE_ROWS, len(df))

    # head(), not sample(). A random draw would be more statistically
    # representative and far less useful: these are time series, and someone
    # opening the file wants consecutive rows they can actually read down.
    body = df.head(rows).to_csv(index=False)

    stem = spec.filename.rsplit(".", 1)[0]
    return Response(
        # BOM, or Excel on Windows mangles anything non-ASCII in the headers.
        content="﻿" + body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{stem}-sample-{rows}rows.csv"',
            "X-Total-Rows": str(len(df)),
            "X-Sample-Rows": str(rows),
        },
    )
