from datetime import datetime, timedelta

from tests.conftest import API


def _log_series(client, model_id: str, name: str, values: list[float]):
    start = datetime(2026, 1, 1)
    for index, value in enumerate(values):
        response = client.post(
            f"{API}/models/{model_id}/metrics",
            json={
                "metric_name": name,
                "metric_value": value,
                "recorded_at": (start + timedelta(days=index)).isoformat(),
            },
        )
        assert response.status_code == 201, response.text


def test_forecast_projects_history_with_uncertainty(client, register):
    model = register(use_case="Credit decision model", risk_tier="high")
    _log_series(client, model["id"], "accuracy", [0.94, 0.93, 0.92, 0.90, 0.89, 0.87, 0.86, 0.84])

    response = client.get(f"{API}/models/{model['id']}/forecast", params={"horizon_days": 30})
    assert response.status_code == 200
    body = response.json()
    assert body["horizon_days"] == 30
    assert body["readiness_priority"] == "urgent"
    assert len(body["forecasts"]) == 1
    forecast = body["forecasts"][0]
    assert forecast["metric_name"] == "accuracy"
    assert forecast["trajectory"] == "worsening"
    assert len(forecast["forecast_points"]) >= 4
    assert all(point["lower_bound"] <= point["predicted_value"] <= point["upper_bound"] for point in forecast["forecast_points"])
    assert any(signal["authority"] == "Reserve Bank of India" for signal in body["regulatory_signals"])


def test_lower_latency_is_classified_as_improving(client, register):
    model = register()
    _log_series(client, model["id"], "latency_ms", [120, 115, 109, 104, 98, 92])

    forecast = client.get(f"{API}/models/{model['id']}/forecast").json()["forecasts"][0]
    assert forecast["trajectory"] == "improving"


def test_forecast_keeps_regulatory_outlook_when_history_is_short(client, register):
    model = register(use_case="Internal FAQ")
    _log_series(client, model["id"], "accuracy", [0.8, 0.81])

    body = client.get(f"{API}/models/{model['id']}/forecast").json()
    assert body["forecasts"] == []
    assert len(body["regulatory_signals"]) >= 3
    assert "not a promise" in body["disclaimer"]


def test_securities_use_case_gets_direct_sebi_scope(client, register):
    model = register(use_case="Trading market surveillance")
    body = client.get(f"{API}/models/{model['id']}/forecast").json()
    sebi = next(signal for signal in body["regulatory_signals"] if "Securities" in signal["authority"])
    assert sebi["applicability"] == "direct"


def test_forecast_rejects_unreasonable_horizon(client, register):
    model = register()
    assert client.get(f"{API}/models/{model['id']}/forecast?horizon_days=2").status_code == 422
    assert client.get(f"{API}/models/{model['id']}/forecast?horizon_days=365").status_code == 422
