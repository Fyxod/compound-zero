from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ml.features import SENSOR_LEVEL_FEATURES, SENSOR_TREND_FEATURES
from ml.robustness_bench import (
    apply_missing_stream,
    apply_sensor_noise,
    bootstrap_event_intervals,
    event_outcomes,
    expected_calibration_error,
    run_loso_evaluation,
    summarize_event_outcomes,
    write_metrics,
)
from ml.scenario_bench import ScenarioBenchConfig, generate_benchmark


def _event_fixture() -> tuple[pd.DataFrame, np.ndarray]:
    records: list[dict[str, object]] = []
    predictions: list[bool] = []
    cases = (
        ("event-device-later", 3, 0, 2),
        ("event-device-never", 3, 1, None),
        ("event-model-miss", 3, None, 1),
        ("non-event", -1, 1, None),
    )
    for scenario_id, event_minute, model_minute, device_minute in cases:
        for minute in range(4):
            records.append(
                {
                    "scenario_id": scenario_id,
                    "scenario_type": "fixture",
                    "minute": minute,
                    "event_minute": event_minute,
                    "risk_within_horizon": int(event_minute >= 0 and minute <= event_minute),
                    "single_sensor_alarm": int(device_minute == minute),
                }
            )
            predictions.append(model_minute == minute)
    return pd.DataFrame.from_records(records), np.asarray(predictions, dtype=bool)


def test_event_metrics_keep_eventual_device_and_never_device_strata_disjoint() -> None:
    frame, prediction = _event_fixture()
    metrics = summarize_event_outcomes(frame, prediction)
    strata = metrics["device_strata"]

    assert metrics["event_groups"] == 3
    assert metrics["detected_event_groups"] == 2
    assert metrics["event_recall"] == 0.666667
    assert metrics["event_false_negative_rate"] == 0.333333
    assert strata["device_eventually_alarm_groups"] == 2
    assert strata["device_never_alarm_groups"] == 1
    assert strata["model_detected_before_eventual_device_alarm_groups"] == 1
    assert strata["model_detected_before_eventual_device_alarm_rate"] == 0.5
    assert strata["model_detected_when_device_never_alarms_groups"] == 1
    assert strata["model_detected_when_device_never_alarms_rate"] == 1.0


def test_ece_and_group_bootstrap_are_deterministic() -> None:
    ece = expected_calibration_error([0, 0, 1, 1], [0.1, 0.3, 0.7, 0.9], bins=5)
    assert ece["value"] == 0.2

    frame, prediction = _event_fixture()
    outcomes = event_outcomes(frame, prediction)
    first = bootstrap_event_intervals(outcomes, iterations=200, random_state=42)
    second = bootstrap_event_intervals(outcomes, iterations=200, random_state=42)
    assert first == second
    assert first["event_recall"]["estimate"] == 0.667
    assert first["event_false_negative_rate"]["estimate"] == 0.333


def test_stress_transforms_are_repeatable_and_rebuild_derived_features() -> None:
    frame = generate_benchmark(ScenarioBenchConfig(seed_count=5))
    medians = {
        feature: float(frame[feature].median())
        for feature in SENSOR_LEVEL_FEATURES + SENSOR_TREND_FEATURES
    }
    first_noise = apply_sensor_noise(frame, sigma=0.02, random_state=91)
    second_noise = apply_sensor_noise(frame, sigma=0.02, random_state=91)
    pd.testing.assert_frame_equal(first_noise, second_noise)
    assert not first_noise[SENSOR_LEVEL_FEATURES].equals(frame[SENSOR_LEVEL_FEATURES])
    assert not first_noise["gas_burden"].equals(frame["gas_burden"])

    first_dropout = apply_missing_stream(
        frame,
        stream="process_sensor_packet_dropout_20pct",
        training_medians=medians,
        random_state=91,
    )
    second_dropout = apply_missing_stream(
        frame,
        stream="process_sensor_packet_dropout_20pct",
        training_medians=medians,
        random_state=91,
    )
    pd.testing.assert_frame_equal(first_dropout, second_dropout)
    assert 0 < int((first_dropout["stream_quality"] == 0).sum()) < len(first_dropout)


def test_loso_fold_never_fits_or_calibrates_on_held_out_scenario_type() -> None:
    frame = generate_benchmark(ScenarioBenchConfig(seed_count=10))
    result = run_loso_evaluation(
        frame,
        held_out_types=("compound_hot_work",),
        random_state=113,
    )
    fold = result["folds"]["compound_hot_work"]
    assert result["fold_count"] == 1
    assert fold["held_out_absent_from_training"] is True
    assert "compound_hot_work" not in fold["training_scenario_types"]
    assert fold["evaluation"]["scenario_groups"] == 10
    assert fold["evaluation"]["event"]["event_groups"] == 10


def test_checked_in_artifact_has_matching_inputs_and_stable_json(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    artifact = root / "artifacts" / "robustness_metrics.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    dataset = root / "data" / "scenario_bench" / "scenario_bench.csv"
    model = root / "artifacts" / "compound_zero_model.joblib"

    assert payload["data_classification"] == "SIMULATED"
    assert payload["inputs"]["dataset_sha256"] == hashlib.sha256(dataset.read_bytes()).hexdigest()
    assert payload["inputs"]["model_artifact_sha256"] == hashlib.sha256(model.read_bytes()).hexdigest()
    assert payload["leave_one_scenario_type_out"]["fold_count"] == 9
    assert all(
        fold["held_out_absent_from_training"]
        for fold in payload["leave_one_scenario_type_out"]["folds"].values()
    )
    assert "not field validation" in payload["claim_boundary"]

    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    write_metrics(first, payload)
    write_metrics(second, payload)
    assert first.read_bytes() == second.read_bytes() == artifact.read_bytes()
