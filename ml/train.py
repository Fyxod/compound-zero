"""CLI for reproducibly generating ScenarioBench and training Compound Zero."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib

from .modeling import train_and_evaluate
from .scenario_bench import ScenarioBenchConfig, dataset_metadata, write_benchmark


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def train(
    *,
    data_dir: Path,
    artifact_dir: Path,
    config: ScenarioBenchConfig,
    random_state: int = 20260722,
) -> tuple[Path, Path, dict[str, object]]:
    frame, csv_path = write_benchmark(data_dir, config)
    metadata = dataset_metadata(frame, config)
    dataset_hash = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    metadata["sha256"] = dataset_hash
    metadata_path = data_dir / "metadata.json"
    _write_json(metadata_path, metadata)

    bundle, metrics = train_and_evaluate(frame, random_state=random_state)
    bundle["dataset_sha256"] = dataset_hash
    metrics["dataset"] = metadata
    artifact_dir.mkdir(parents=True, exist_ok=True)
    model_path = artifact_dir / "compound_zero_model.joblib"
    metrics_path = artifact_dir / "metrics.json"
    model_card_path = artifact_dir / "model_card.json"
    joblib.dump(bundle, model_path, compress=3)
    model_artifact_sha256 = _sha256_file(model_path)
    _write_json(metrics_path, metrics)
    _write_json(
        model_card_path,
        {
            "model_version": bundle["model_version"],
            "intended_use": "Prototype early-warning evaluation and deterministic demo replay.",
            "prohibited_claims": [
                "Field-validated safety performance",
                "Autonomous shutdown authorization",
                "Regulatory certification or compliance completeness",
            ],
            "data_classification": "SIMULATED",
            "decision_engine": bundle["decision_engine"],
            "dataset_sha256": dataset_hash,
            "model_artifact_filename": model_path.name,
            "model_artifact_sha256": model_artifact_sha256,
            "model_artifact_bytes": model_path.stat().st_size,
            "features": bundle["full_features"],
            "decision_threshold": round(float(bundle["full_threshold"]), 6),
            "limitations": metrics["limitations"],
        },
    )
    return model_path, metrics_path, metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/scenario_bench"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--first-seed", type=int, default=1000)
    parser.add_argument("--seed-count", type=int, default=64)
    parser.add_argument("--duration-minutes", type=int, default=48)
    parser.add_argument("--forecast-horizon-minutes", type=int, default=12)
    parser.add_argument("--random-state", type=int, default=20260722)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = ScenarioBenchConfig(
        first_seed=args.first_seed,
        seed_count=args.seed_count,
        duration_minutes=args.duration_minutes,
        forecast_horizon_minutes=args.forecast_horizon_minutes,
    )
    model_path, metrics_path, metrics = train(
        data_dir=args.data_dir,
        artifact_dir=args.artifact_dir,
        config=config,
        random_state=args.random_state,
    )
    summary = {
        "model": str(model_path),
        "metrics": str(metrics_path),
        "data_classification": metrics["data_classification"],
        "split_overlap_count": metrics["split"]["overlap_count"],
        "single_sensor": metrics["methods"]["single_sensor"],
        "process_only": metrics["methods"]["process_only"],
        "full_fusion": metrics["methods"]["full_fusion"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
