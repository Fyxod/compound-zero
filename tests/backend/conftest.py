from __future__ import annotations

from pathlib import Path

import pytest

from ml.scenario_bench import ScenarioBenchConfig
from ml.train import train


@pytest.fixture(scope="session")
def trained_case(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    root: Path = tmp_path_factory.mktemp("compound-zero-test")
    artifact_dir = root / "artifacts"
    data_dir = root / "data"
    model_path, metrics_path, metrics = train(
        data_dir=data_dir,
        artifact_dir=artifact_dir,
        config=ScenarioBenchConfig(seed_count=20),
    )
    return {
        "root": root,
        "artifact_dir": artifact_dir,
        "data_dir": data_dir,
        "model_path": model_path,
        "metrics_path": metrics_path,
        "metrics": metrics,
    }

