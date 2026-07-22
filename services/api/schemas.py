"""Typed API contracts for Compound Zero."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RiskScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_classification: Literal["SIMULATED"] = "SIMULATED"
    scenario_id: str | None = Field(default=None, max_length=120)
    lel_ratio: float = Field(ge=0.0, le=3.0)
    h2s_ratio: float = Field(ge=0.0, le=3.0)
    co_ratio: float = Field(ge=0.0, le=3.0)
    oxygen_deficit_ratio: float = Field(ge=0.0, le=3.0)
    pressure_ratio: float = Field(ge=0.0, le=3.0)
    lel_slope: float = Field(default=0.0, ge=-1.0, le=1.0)
    h2s_slope: float = Field(default=0.0, ge=-1.0, le=1.0)
    co_slope: float = Field(default=0.0, ge=-1.0, le=1.0)
    oxygen_slope: float = Field(default=0.0, ge=-1.0, le=1.0)
    pressure_slope: float = Field(default=0.0, ge=-1.0, le=1.0)
    ventilation_impaired: bool = False
    hot_work_active: bool = False
    confined_space_active: bool = False
    workers_in_zone: int = Field(default=0, ge=0, le=100)
    min_worker_distance_m: float = Field(default=120.0, ge=0.0, le=5_000.0)
    shift_handover: bool = False
    permit_overlap_count: int = Field(default=0, ge=0, le=50)
    isolation_active: bool = False
    stream_quality: float = Field(default=1.0, ge=0.0, le=1.0)


class RiskFactorResponse(BaseModel):
    id: str
    label: str
    detail: str
    value: float
    evidence_type: Literal["sensor", "permit", "asset", "people", "operations"]


class RiskScoreResponse(BaseModel):
    data_classification: Literal["SIMULATED"]
    model_version: str
    decision_engine: str
    risk_probability: float
    risk_score: int
    decision_threshold: float
    severity: Literal["nominal", "watch", "elevated", "critical"]
    prediction_active: bool
    single_sensor_alarm: bool
    abstained: bool
    abstention_reason: str | None
    factors: list[RiskFactorResponse]
    limitations: list[str]

