"""Persisted model loading and non-LLM risk inference."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from threadpoolctl import threadpool_limits

from ml.features import enrich_feature_row, single_sensor_alarm
from .schemas import RiskFactorResponse, RiskScoreRequest, RiskScoreResponse

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT_DIR = ROOT / "artifacts"


def severity_for(score: int) -> str:
    if score >= 76:
        return "critical"
    if score >= 52:
        return "elevated"
    if score >= 28:
        return "watch"
    return "nominal"


def structured_factors(features: dict[str, float]) -> list[RiskFactorResponse]:
    candidates = [
        RiskFactorResponse(
            id="correlated-process-rise",
            label="Correlated process trend",
            detail="Multiple normalized process channels are rising together.",
            value=features["gas_burden"] + 4.0 * features["mean_positive_slope"],
            evidence_type="sensor",
        ),
        RiskFactorResponse(
            id="hot-work-overlap",
            label="Hot-work overlap",
            detail="An active ignition-source permit overlaps the evolving process condition.",
            value=features["hotwork_gas_interaction"],
            evidence_type="permit",
        ),
        RiskFactorResponse(
            id="barrier-loss",
            label="Extraction barrier impaired",
            detail="Ventilation or extraction is unavailable while gas burden is increasing.",
            value=features["barrier_gas_interaction"],
            evidence_type="asset",
        ),
        RiskFactorResponse(
            id="worker-exposure",
            label="Personnel exposure",
            detail="Workers are close to the affected zone during the correlated trend.",
            value=features["worker_gas_interaction"],
            evidence_type="people",
        ),
        RiskFactorResponse(
            id="confined-space",
            label="Confined-space oxygen risk",
            detail="Occupied confined-space work overlaps deteriorating oxygen conditions.",
            value=features["confined_oxygen_interaction"],
            evidence_type="permit",
        ),
        RiskFactorResponse(
            id="handover-overlap",
            label="Shift handover overlap",
            detail="Permit overlap coincides with an operational handover window.",
            value=features["handover_permit_interaction"],
            evidence_type="operations",
        ),
    ]
    active = [factor for factor in candidates if factor.value > 0.015]
    return sorted(active, key=lambda factor: factor.value, reverse=True)[:5]


class ModelStore:
    def __init__(self, artifact_dir: Path | None = None) -> None:
        configured = os.environ.get("COMPOUND_ZERO_ARTIFACT_DIR")
        self.artifact_dir = Path(configured) if configured else artifact_dir or DEFAULT_ARTIFACT_DIR
        self.bundle: dict[str, Any] | None = None
        self.metrics: dict[str, Any] | None = None
        self.load_error: str | None = None
        self.reload()

    @property
    def ready(self) -> bool:
        return self.bundle is not None and self.metrics is not None

    def reload(self) -> None:
        model_path = self.artifact_dir / "compound_zero_model.joblib"
        metrics_path = self.artifact_dir / "metrics.json"
        try:
            self.bundle = joblib.load(model_path)
            self.metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            # Small edge-inference batches become slower when OpenMP fans out
            # across every host core. Warm the native pool once and keep each
            # prediction bounded to a single worker for stable UI latency.
            warm_frame = pd.DataFrame(
                [{name: 0.0 for name in self.bundle["full_features"]}]
            )
            with threadpool_limits(limits=1):
                self.bundle["full_model"].predict_proba(warm_frame)
            self.load_error = None
        except (FileNotFoundError, OSError, ValueError, KeyError) as exc:
            self.bundle = None
            self.metrics = None
            self.load_error = f"{type(exc).__name__}: {exc}"

    def score_features(self, raw: dict[str, Any]) -> RiskScoreResponse:
        if not self.ready or self.bundle is None:
            raise RuntimeError(self.load_error or "Model artifacts are unavailable")
        features = enrich_feature_row(raw)
        feature_names = self.bundle["full_features"]
        feature_frame = pd.DataFrame([{name: features[name] for name in feature_names}])
        with threadpool_limits(limits=1):
            probability = float(self.bundle["full_model"].predict_proba(feature_frame)[0, 1])
        threshold = float(self.bundle["full_threshold"])
        score = int(round(probability * 100))
        stream_quality = features["stream_quality"]
        abstained = stream_quality < 0.80
        prediction_active = bool(probability >= threshold and not abstained)
        return RiskScoreResponse(
            data_classification="SIMULATED",
            model_version=str(self.bundle["model_version"]),
            decision_engine=str(self.bundle["decision_engine"]),
            risk_probability=round(probability, 6),
            risk_score=score,
            decision_threshold=round(threshold, 6),
            severity=severity_for(score),
            prediction_active=prediction_active,
            single_sensor_alarm=single_sensor_alarm(features),
            abstained=abstained,
            abstention_reason=(
                "Stream quality is below the prototype inference floor; escalate for manual review."
                if abstained
                else None
            ),
            factors=structured_factors(features),
            limitations=[
                "This score is produced from a model trained only on simulated ScenarioBench data.",
                "It is decision support, not authorization for autonomous plant control.",
            ],
        )

    def score(self, request: RiskScoreRequest) -> RiskScoreResponse:
        return self.score_features(request.model_dump(exclude={"scenario_id", "data_classification"}))
