from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import services.api.model_store as model_store_module
from services.api.model_store import DEFAULT_ARTIFACT_DIR, ModelStore


def _artifact_copy(trained_case: dict[str, Any], destination: Path) -> Path:
    return Path(shutil.copytree(Path(trained_case["artifact_dir"]), destination))


def test_checked_in_artifact_matches_checked_in_manifest() -> None:
    store = ModelStore(DEFAULT_ARTIFACT_DIR)

    assert store.ready is True, store.load_error
    assert store.model_artifact_sha256 is not None
    assert len(store.model_artifact_sha256) == 64


def test_checked_in_metrics_support_published_device_alarm_partition() -> None:
    metrics = json.loads(
        (DEFAULT_ARTIFACT_DIR / "metrics.json").read_text(encoding="utf-8")
    )
    full_event = metrics["methods"]["full_fusion"]["event"]

    assert full_event["event_groups"] == 65
    assert full_event["device_alarm_by_event_groups"] == 13
    assert full_event["no_device_alarm_by_event_groups"] == 52
    assert full_event["detected_before_device_alarm_groups"] == 13
    assert full_event["detected_without_device_alarm_by_event_groups"] == 52
    assert full_event["detected_before_device_alarm_rate_given_device_alarm"] == 1.0
    assert full_event["detected_without_device_alarm_by_event_rate"] == 1.0


def test_valid_artifact_digest_is_exposed(trained_case: dict[str, Any]) -> None:
    store = ModelStore(Path(trained_case["artifact_dir"]))
    card = json.loads(
        (Path(trained_case["artifact_dir"]) / "model_card.json").read_text(encoding="utf-8")
    )

    assert store.ready is True
    assert store.load_error is None
    assert store.model_artifact_sha256 == card["model_artifact_sha256"]
    assert card["model_artifact_bytes"] == Path(trained_case["model_path"]).stat().st_size


def test_tampered_model_is_rejected_before_joblib_deserialization(
    trained_case: dict[str, Any],
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    artifact_dir = _artifact_copy(trained_case, tmp_path / "tampered-artifacts")
    model_path = artifact_dir / "compound_zero_model.joblib"
    model_bytes = bytearray(model_path.read_bytes())
    model_bytes[len(model_bytes) // 2] ^= 0x01
    model_path.write_bytes(model_bytes)
    deserialization_attempted = False

    def fail_if_called(_: object) -> object:
        nonlocal deserialization_attempted
        deserialization_attempted = True
        raise AssertionError("joblib.load must not receive unverified model bytes")

    monkeypatch.setattr(model_store_module.joblib, "load", fail_if_called)
    store = ModelStore(artifact_dir)

    assert store.ready is False
    assert deserialization_attempted is False
    assert store.model_artifact_sha256 is None
    assert store.load_error is not None
    assert "ModelArtifactIntegrityError" in store.load_error
    assert "SHA-256 mismatch" in store.load_error


def test_missing_manifest_digest_is_rejected_before_deserialization(
    trained_case: dict[str, Any],
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    artifact_dir = _artifact_copy(trained_case, tmp_path / "missing-digest-artifacts")
    card_path = artifact_dir / "model_card.json"
    card = json.loads(card_path.read_text(encoding="utf-8"))
    del card["model_artifact_sha256"]
    card_path.write_text(json.dumps(card), encoding="utf-8")
    deserialization_attempted = False

    def fail_if_called(_: object) -> object:
        nonlocal deserialization_attempted
        deserialization_attempted = True
        raise AssertionError("joblib.load must not run without a trusted digest")

    monkeypatch.setattr(model_store_module.joblib, "load", fail_if_called)
    store = ModelStore(artifact_dir)

    assert store.ready is False
    assert deserialization_attempted is False
    assert store.load_error is not None
    assert "valid lowercase SHA-256 digest" in store.load_error
