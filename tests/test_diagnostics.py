"""
Tests for the dataset diagnostics.

Statistical code is the easiest place to be confidently wrong, because a
plausible-looking number never announces itself as incorrect. So the PSI
implementation is tested against cases where the right answer is known in
advance: identical distributions must score ~0, and a deliberately shifted one
must clear the significance threshold.
"""

import numpy as np
import pandas as pd

from app.api.diagnostics import PSI_SIGNIFICANT, _psi, diagnose


class TestPSI:
    def test_identical_distributions_score_near_zero(self):
        rng = np.random.default_rng(0)
        sample = pd.Series(rng.normal(100, 10, 2000))
        assert _psi(sample, sample) < 0.01

    def test_a_shifted_distribution_is_flagged(self):
        rng = np.random.default_rng(1)
        reference = pd.Series(rng.normal(100, 10, 2000))
        shifted = pd.Series(rng.normal(140, 10, 2000))
        assert _psi(reference, shifted) > PSI_SIGNIFICANT

    def test_a_wider_distribution_is_flagged_even_at_the_same_mean(self):
        """Volatility changing while the average holds is exactly what happened
        to FX in March 2020 — a check that only watched the mean would have
        missed it entirely."""
        rng = np.random.default_rng(2)
        calm = pd.Series(rng.normal(100, 5, 3000))
        turbulent = pd.Series(rng.normal(100, 30, 3000))
        assert _psi(calm, turbulent) > PSI_SIGNIFICANT

    def test_too_few_rows_returns_nan_rather_than_a_number(self):
        """Refusing to answer beats answering badly. A PSI computed from twelve
        points would be noise wearing a decimal point."""
        small = pd.Series([1, 2, 3])
        assert np.isnan(_psi(small, small))

    def test_a_constant_feature_returns_nan(self):
        flat = pd.Series([5.0] * 500)
        assert np.isnan(_psi(flat, flat))


class TestDiagnose:
    def test_detects_severe_class_imbalance(self):
        df = pd.DataFrame(
            {
                "feature_a": np.random.default_rng(3).normal(0, 1, 1000),
                "default": [1] * 20 + [0] * 980,
            }
        )
        result = diagnose(df)
        assert result["stats"]["detected_target"] == "default"
        assert any("imbalance" in f["title"].lower() for f in result["findings"])

    def test_flags_too_few_rows_for_the_feature_count(self):
        rng = np.random.default_rng(4)
        df = pd.DataFrame({f"f{i}": rng.normal(0, 1, 40) for i in range(20)})
        result = diagnose(df)
        assert result["stats"]["rows_per_feature"] < 10
        assert any("too few rows" in f["title"].lower() for f in result["findings"])

    def test_flags_protected_attribute_candidates(self):
        df = pd.DataFrame(
            {
                "age": [30, 40, 50] * 40,
                "gender": [0, 1, 0] * 40,
                "pincode": [400001, 110001, 560001] * 40,
                "income": [50000, 60000, 70000] * 40,
            }
        )
        result = diagnose(df)
        flagged = result["stats"]["protected_candidates"]
        assert {"age", "gender", "pincode"}.issubset(set(flagged))
        assert "income" not in flagged

    def test_flags_constant_columns(self):
        df = pd.DataFrame(
            {
                "varies": np.random.default_rng(5).normal(0, 1, 200),
                "never_changes": [7.0] * 200,
            }
        )
        result = diagnose(df)
        assert any("constant" in f["title"].lower() for f in result["findings"])

    def test_measures_drift_when_a_date_column_exists(self):
        """The empirical check. The second half of this frame is deliberately
        shifted, so the diagnostics must notice without being told."""
        rng = np.random.default_rng(6)
        dates = pd.date_range("2024-01-01", periods=600, freq="D")
        values = np.concatenate(
            [rng.normal(100, 5, 300), rng.normal(160, 5, 300)]
        )
        df = pd.DataFrame({"observed_on": dates, "price": values})

        result = diagnose(df)
        assert result["drift"] is not None
        assert result["drift"]["date_column"] == "observed_on"
        assert "price" in result["drift"]["significant"]
        assert any("drifts" in f["title"].lower() for f in result["findings"])

    def test_reports_stability_when_nothing_moves(self):
        rng = np.random.default_rng(7)
        df = pd.DataFrame(
            {
                "observed_on": pd.date_range("2024-01-01", periods=600, freq="D"),
                "price": rng.normal(100, 5, 600),
            }
        )
        result = diagnose(df)
        assert result["drift"]["significant"] == []
        assert any("stable" in f["title"].lower() for f in result["findings"])

    def test_says_so_when_drift_cannot_be_measured(self):
        """Silence would imply "no drift found". The absence of a date column
        means the question wasn't asked, and the report has to distinguish
        those two things."""
        df = pd.DataFrame({"a": [1.0] * 200, "b": np.arange(200.0)})
        result = diagnose(df)
        assert result["drift"] is None
        assert any("no date column" in f["title"].lower() for f in result["findings"])


class TestDatasetEndpoint:
    def test_accepts_a_csv_and_returns_findings(self, client):
        csv = "observed_on,price\n" + "\n".join(
            f"2024-01-{(i % 28) + 1:02d},{100 + i * 0.4}" for i in range(300)
        )
        resp = client.post(
            "/api/v1/assessment/dataset",
            files={"file": ("sample.csv", csv, "text/csv")},
        )
        assert resp.status_code == 200
        assert resp.json()["stats"]["rows"] == 300

    def test_rejects_a_non_csv(self, client):
        resp = client.post(
            "/api/v1/assessment/dataset",
            files={"file": ("model.xlsx", b"not really a spreadsheet", "application/vnd.ms-excel")},
        )
        assert resp.status_code == 422

    def test_rejects_an_empty_file(self, client):
        resp = client.post(
            "/api/v1/assessment/dataset",
            files={"file": ("empty.csv", "a,b\n", "text/csv")},
        )
        assert resp.status_code == 422
