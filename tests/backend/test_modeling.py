from __future__ import annotations

from typing import Any


def test_seed_holdout_has_no_overlap(trained_case: dict[str, Any]) -> None:
    metrics = trained_case["metrics"]
    split = metrics["split"]
    assert split["overlap_count"] == 0
    train = set(split["train_seeds"])
    calibration = set(split["calibration_seeds"])
    test = set(split["test_seeds"])
    assert train.isdisjoint(calibration)
    assert train.isdisjoint(test)
    assert calibration.isdisjoint(test)


def test_full_fusion_outperforms_fixed_device_baseline(trained_case: dict[str, Any]) -> None:
    metrics = trained_case["metrics"]
    methods = metrics["methods"]
    assert methods["full_fusion"]["event"]["event_recall"] > methods["single_sensor"]["event"]["event_recall"]
    assert methods["full_fusion"]["row"]["average_precision"] > methods["process_only"]["row"]["average_precision"]
    assert methods["full_fusion"]["event"]["detected_before_device_alarm_rate"] > 0
    assert metrics["data_classification"] == "SIMULATED"


def test_artifacts_are_written(trained_case: dict[str, Any]) -> None:
    assert trained_case["model_path"].is_file()
    assert trained_case["metrics_path"].is_file()
    assert (trained_case["artifact_dir"] / "model_card.json").is_file()
    assert (trained_case["data_dir"] / "scenario_bench.csv").is_file()
    assert (trained_case["data_dir"] / "metadata.json").is_file()

