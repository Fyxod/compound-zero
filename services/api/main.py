"""Compound Zero API.

Run with: uvicorn services.api.main:app --reload
"""

from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from threadpoolctl import threadpool_limits

from ml.features import FULL_FEATURES
from ml.scenario_bench import (
    DATA_CLASSIFICATION,
    SCENARIO_DESCRIPTIONS,
    SCENARIO_TYPES,
    generate_scenario,
)
from .brief_schemas import (
    ContextualRiskScoreRequest,
    ContextualRiskScoreResponse,
    PatternSearchRequest,
    PatternSearchResponse,
    PermitAuditRequest,
    PermitAuditResponse,
    ResponseApprovalRequest,
    ResponsePlan,
    ResponsePlanRequest,
)
from .knowledge import IncidentPatternIndex
from .model_store import ModelStore, severity_for, structured_factors
from .permit_audit import audit_permit
from .response_store import (
    IdempotencyConflictError,
    ResponsePlanCapacityError,
    ResponsePlanStore,
)
from .schemas import RiskScoreRequest, RiskScoreResponse
from .vision_context import derive_vision_context

app = FastAPI(
    title="Compound Zero API",
    version="0.2.0",
    description=(
        "Deterministic simulated replay and calibrated compound-risk inference. "
        "No LLM participates in safety decisions."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

store = ModelStore()
pattern_index = IncidentPatternIndex()
response_plans = ResponsePlanStore()


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "Compound Zero",
        "status": "ready" if store.ready else "model-unavailable",
        "data_classification": DATA_CLASSIFICATION,
    }


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok" if store.ready else "degraded",
        "ready": store.ready,
        "model_version": None if not store.bundle else store.bundle["model_version"],
        "model_artifact_sha256": store.model_artifact_sha256,
        "data_classification": DATA_CLASSIFICATION,
        "decision_engine": "deterministic feature pipeline plus calibrated scikit-learn model",
        "llm_in_risk_path": False,
        "capabilities": [
            "compound-risk-scoring",
            "privacy-preserving-cctv-context",
            "local-bm25-incident-pattern-retrieval",
            "permit-evidence-audit",
            "human-gated-response-plans",
        ],
        "actuator_connected": False,
        "load_error": store.load_error,
    }


@app.get("/v1/model")
def model_metadata() -> dict[str, object]:
    if not store.ready or store.bundle is None:
        raise HTTPException(status_code=503, detail=store.load_error or "Model unavailable")
    return {
        "model_version": store.bundle["model_version"],
        "data_classification": store.bundle["data_classification"],
        "decision_engine": store.bundle["decision_engine"],
        "features": store.bundle["full_features"],
        "decision_threshold": round(float(store.bundle["full_threshold"]), 6),
        "dataset_sha256": store.bundle.get("dataset_sha256"),
        "model_artifact_sha256": store.model_artifact_sha256,
        "llm_in_risk_path": False,
    }


@app.get("/v1/benchmark")
def benchmark_metrics() -> dict[str, object]:
    if not store.ready or store.metrics is None:
        raise HTTPException(status_code=503, detail=store.load_error or "Metrics unavailable")
    return store.metrics


@app.post("/v1/risk/score", response_model=RiskScoreResponse)
def score_risk(request: RiskScoreRequest) -> RiskScoreResponse:
    try:
        return store.score(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/v1/risk/score-with-cctv", response_model=ContextualRiskScoreResponse)
def score_risk_with_cctv(
    request: ContextualRiskScoreRequest,
) -> ContextualRiskScoreResponse:
    """Fuse anonymous CCTV event metadata into existing numeric model inputs."""

    try:
        raw, vision_context = derive_vision_context(request)
        score = store.score_features(raw)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ContextualRiskScoreResponse(
        data_classification="SIMULATED",
        score=score,
        vision_context=vision_context,
        integration_method=(
            "Anonymous in-zone counts, nearest hazard distance, and observation confidence are deterministically "
            "mapped to workers_in_zone, min_worker_distance_m, and stream_quality before the same calibrated model runs."
        ),
        llm_in_risk_path=False,
    )


@app.get("/v1/intelligence/corpus")
def pattern_corpus_metadata() -> dict[str, object]:
    return pattern_index.metadata()


@app.post("/v1/intelligence/patterns", response_model=PatternSearchResponse)
def search_incident_patterns(request: PatternSearchRequest) -> PatternSearchResponse:
    return pattern_index.search(request)


@app.post("/v1/audit/permits", response_model=PermitAuditResponse)
def audit_permit_evidence(request: PermitAuditRequest) -> PermitAuditResponse:
    return audit_permit(request)


@app.post("/v1/response/plans", response_model=ResponsePlan, status_code=201)
def create_response_plan(request: ResponsePlanRequest) -> ResponsePlan:
    try:
        return response_plans.create(request)
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ResponsePlanCapacityError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/v1/response/plans/{plan_id}", response_model=ResponsePlan)
def get_response_plan(
    plan_id: Annotated[str, Path(pattern=r"^rsp-[a-f0-9]{16}$")],
) -> ResponsePlan:
    plan = response_plans.get(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Response plan not found")
    return plan


@app.post("/v1/response/plans/{plan_id}/approvals", response_model=ResponsePlan)
def decide_response_plan(
    plan_id: Annotated[str, Path(pattern=r"^rsp-[a-f0-9]{16}$")],
    request: ResponseApprovalRequest,
) -> ResponsePlan:
    try:
        return response_plans.approve(plan_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Response plan not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/v1/scenarios")
def list_scenarios() -> dict[str, object]:
    return {
        "data_classification": DATA_CLASSIFICATION,
        "deterministic": True,
        "scenarios": [
            {"id": scenario, "description": SCENARIO_DESCRIPTIONS[scenario]}
            for scenario in SCENARIO_TYPES
        ],
    }


@app.get("/v1/scenarios/{scenario_type}/replay")
def replay_scenario(
    scenario_type: Annotated[str, Path(description="ScenarioBench template identifier")],
    seed: Annotated[int, Query(ge=0, le=2_147_483_647)] = 24001,
) -> dict[str, object]:
    if scenario_type not in SCENARIO_TYPES:
        raise HTTPException(
            status_code=404,
            detail={"message": "Unknown scenario", "available": list(SCENARIO_TYPES)},
        )
    if not store.ready or store.bundle is None:
        raise HTTPException(status_code=503, detail=store.load_error or "Model unavailable")

    frame = generate_scenario(seed, scenario_type)
    feature_names = store.bundle["full_features"]
    with threadpool_limits(limits=1):
        probabilities = store.bundle["full_model"].predict_proba(frame[feature_names])[:, 1]
    threshold = float(store.bundle["full_threshold"])
    snapshots: list[dict[str, object]] = []
    for (_, row), probability in zip(frame.iterrows(), probabilities, strict=True):
        raw = {name: float(row[name]) for name in FULL_FEATURES}
        risk_score = int(round(float(probability) * 100))
        abstained = raw["stream_quality"] < 0.80
        snapshots.append(
            {
                "minute": int(row["minute"]),
                "risk_probability": round(float(probability), 6),
                "risk_score": risk_score,
                "severity": severity_for(risk_score),
                "prediction_active": bool(probability >= threshold and not abstained),
                "single_sensor_alarm": bool(row["single_sensor_alarm"]),
                "harmful_state": bool(row["harmful_state"]),
                "risk_within_horizon": bool(row["risk_within_horizon"]),
                "event_minute": int(row["event_minute"]),
                "sensors": {
                    "lel_ratio": round(float(row["lel_ratio"]), 5),
                    "h2s_ratio": round(float(row["h2s_ratio"]), 5),
                    "co_ratio": round(float(row["co_ratio"]), 5),
                    "oxygen_deficit_ratio": round(float(row["oxygen_deficit_ratio"]), 5),
                    "pressure_ratio": round(float(row["pressure_ratio"]), 5),
                },
                "slopes": {
                    "lel_slope": round(float(row["lel_slope"]), 6),
                    "h2s_slope": round(float(row["h2s_slope"]), 6),
                    "co_slope": round(float(row["co_slope"]), 6),
                    "oxygen_slope": round(float(row["oxygen_slope"]), 6),
                    "pressure_slope": round(float(row["pressure_slope"]), 6),
                },
                "stream_quality": round(float(row["stream_quality"]), 6),
                "context": {
                    "ventilation_impaired": bool(row["ventilation_impaired"]),
                    "hot_work_active": bool(row["hot_work_active"]),
                    "confined_space_active": bool(row["confined_space_active"]),
                    "workers_in_zone": int(row["workers_in_zone"]),
                    "min_worker_distance_m": round(float(row["min_worker_distance_m"]), 2),
                    "shift_handover": bool(row["shift_handover"]),
                    "permit_overlap_count": int(row["permit_overlap_count"]),
                },
                "factors": [factor.model_dump() for factor in structured_factors(raw)],
            }
        )
    return {
        "scenario_id": f"{scenario_type}-{seed}",
        "scenario_type": scenario_type,
        "seed": seed,
        "data_classification": DATA_CLASSIFICATION,
        "disclaimer": "Deterministic simulated replay; not field safety validation.",
        "model_version": store.bundle["model_version"],
        "decision_threshold": round(threshold, 6),
        "snapshots": snapshots,
    }
