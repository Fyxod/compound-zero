from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

import services.api.main as api_main
from services.api.model_store import ModelStore


def _client(trained_case: dict[str, Any]) -> TestClient:
    api_main.store = ModelStore(trained_case["artifact_dir"])
    return TestClient(api_main.app)


def test_health_and_model_metadata(trained_case: dict[str, Any]) -> None:
    client = _client(trained_case)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["ready"] is True
    assert health.json()["llm_in_risk_path"] is False

    model = client.get("/v1/model")
    assert model.status_code == 200
    assert model.json()["data_classification"] == "SIMULATED"
    assert model.json()["llm_in_risk_path"] is False


def test_score_abstains_on_bad_stream_quality(trained_case: dict[str, Any]) -> None:
    client = _client(trained_case)
    response = client.post(
        "/v1/risk/score",
        json={
            "lel_ratio": 0.62,
            "h2s_ratio": 0.48,
            "co_ratio": 0.51,
            "oxygen_deficit_ratio": 0.32,
            "pressure_ratio": 0.71,
            "ventilation_impaired": True,
            "hot_work_active": True,
            "workers_in_zone": 4,
            "min_worker_distance_m": 14,
            "permit_overlap_count": 2,
            "stream_quality": 0.5,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["abstained"] is True
    assert body["prediction_active"] is False
    assert body["single_sensor_alarm"] is False


def test_replay_is_deterministic_and_detects_prethreshold_risk(trained_case: dict[str, Any]) -> None:
    client = _client(trained_case)
    url = "/v1/scenarios/compound_hot_work/replay?seed=24001"
    first = client.get(url)
    second = client.get(url)
    assert first.status_code == 200
    assert first.json() == second.json()

    body = first.json()
    assert body["data_classification"] == "SIMULATED"
    assert body["seed"] == 24001
    first_snapshot = body["snapshots"][0]
    assert set(first_snapshot["slopes"]) == {
        "lel_slope",
        "h2s_slope",
        "co_slope",
        "oxygen_slope",
        "pressure_slope",
    }
    assert 0.0 <= first_snapshot["stream_quality"] <= 1.0
    prethreshold_alerts = [
        snapshot
        for snapshot in body["snapshots"]
        if snapshot["prediction_active"] and not snapshot["single_sensor_alarm"]
    ]
    assert prethreshold_alerts


def test_preview_origin_is_allowed_by_cors(trained_case: dict[str, Any]) -> None:
    client = _client(trained_case)
    response = client.options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:4173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:4173"
