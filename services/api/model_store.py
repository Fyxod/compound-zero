"""Persisted model loading and non-LLM risk inference."""

from __future__ import annotations

import hashlib
import hmac
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


class ModelArtifactIntegrityError(ValueError):
    """Raised before deserialization when checked-in model bytes are untrusted."""


def _sha256_stream(handle: Any) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


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
        self.model_card: dict[str, Any] | None = None
        self.model_artifact_sha256: str | None = None
        self.load_error: str | None = None
        self.reload()

    @property
    def ready(self) -> bool:
        return self.bundle is not None and self.metrics is not None

    def reload(self) -> None:
        model_path = self.artifact_dir / "compound_zero_model.joblib"
        metrics_path = self.artifact_dir / "metrics.json"
        model_card_path = self.artifact_dir / "model_card.json"
        try:
            model_card = json.loads(model_card_path.read_text(encoding="utf-8"))
            if not isinstance(model_card, dict):
                raise ModelArtifactIntegrityError("Model card must be a JSON object")
            expected_filename = model_card.get("model_artifact_filename")
            expected_sha256 = model_card.get("model_artifact_sha256")
            expected_bytes = model_card.get("model_artifact_bytes")
            if expected_filename != model_path.name:
                raise ModelArtifactIntegrityError(
                    "Model card filename does not match the configured artifact"
                )
            if (
                not isinstance(expected_sha256, str)
                or len(expected_sha256) != 64
                or any(character not in "0123456789abcdef" for character in expected_sha256)
            ):
                raise ModelArtifactIntegrityError(
                    "Model card is missing a valid lowercase SHA-256 digest"
                )
            if (
                isinstance(expected_bytes, bool)
                or not isinstance(expected_bytes, int)
                or expected_bytes <= 0
            ):
                raise ModelArtifactIntegrityError(
                    "Model card is missing a valid artifact byte count"
                )
            # Keep one file handle open from validation through deserialization
            # so the bytes cannot change between the digest check and load.
            with model_path.open("rb") as model_handle:
                actual_bytes = os.fstat(model_handle.fileno()).st_size
                if actual_bytes != expected_bytes:
                    raise ModelArtifactIntegrityError(
                        f"Model artifact size mismatch: expected {expected_bytes}, got {actual_bytes}"
                    )
                actual_sha256 = _sha256_stream(model_handle)
                if not hmac.compare_digest(actual_sha256, expected_sha256):
                    raise ModelArtifactIntegrityError(
                        "Model artifact SHA-256 mismatch; refusing deserialization"
                    )

                # joblib/pickle deserialization happens only after both cheap
                # size and cryptographic digest verification succeed, using
                # the exact file handle that was verified above.
                model_handle.seek(0)
                bundle = joblib.load(model_handle)
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            if not isinstance(bundle, dict):
                raise ModelArtifactIntegrityError("Loaded model bundle must be a mapping")
            if not isinstance(metrics, dict):
                raise ModelArtifactIntegrityError("Metrics artifact must be a JSON object")
            dataset_sha256 = model_card.get("dataset_sha256")
            if bundle.get("model_version") != model_card.get("model_version"):
                raise ModelArtifactIntegrityError(
                    "Loaded model version does not match the verified model card"
                )
            if bundle.get("dataset_sha256") != dataset_sha256:
                raise ModelArtifactIntegrityError(
                    "Loaded model dataset fingerprint does not match the verified model card"
                )
            metrics_dataset = metrics.get("dataset")
            if (
                not isinstance(metrics_dataset, dict)
                or metrics_dataset.get("sha256") != dataset_sha256
            ):
                raise ModelArtifactIntegrityError(
                    "Metrics dataset fingerprint does not match the verified model card"
                )

            self.bundle = bundle
            self.metrics = metrics
            self.model_card = model_card
            self.model_artifact_sha256 = actual_sha256
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
            self.model_card = None
            self.model_artifact_sha256 = None
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
