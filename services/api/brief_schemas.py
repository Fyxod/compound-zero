"""Contracts for the PS1 brief-completeness prototype endpoints.

The safety-critical boundaries are expressed in the types themselves: CCTV
inputs contain metadata only, retrieval is source-attributed, and response
plans never represent physical actuation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .schemas import RiskScoreRequest, RiskScoreResponse


Classification = Literal["SIMULATED"]
ReferenceClassification = Literal["REFERENCE"]


def _require_timezone(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include an explicit UTC offset")
    return value


class CCTVObservation(BaseModel):
    """Privacy-preserving analytics output; never a frame or person identity."""

    model_config = ConfigDict(extra="forbid")

    data_classification: Classification = "SIMULATED"
    observation_id: str = Field(min_length=3, max_length=96, pattern=r"^[A-Za-z0-9._:-]+$")
    observed_at: datetime
    camera_ref: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$")
    zone_id: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$")
    event_type: Literal[
        "occupancy",
        "restricted_zone_entry",
        "unsafe_proximity",
        "ppe_nonconformance",
        "worker_down",
        "blocked_egress",
    ]
    entity_count: int = Field(default=1, ge=1, le=250)
    min_hazard_distance_m: float | None = Field(default=None, ge=0.0, le=5_000.0)
    confidence: float = Field(ge=0.0, le=1.0)
    raw_media_included: Literal[False] = False
    biometric_processing: Literal[False] = False
    identity_tracking: Literal[False] = False
    retention_mode: Literal["METADATA_ONLY"] = "METADATA_ONLY"

    _timezone = field_validator("observed_at")(_require_timezone)

    @model_validator(mode="after")
    def require_distance_for_proximity(self) -> "CCTVObservation":
        if self.event_type == "unsafe_proximity" and self.min_hazard_distance_m is None:
            raise ValueError("unsafe_proximity observations require min_hazard_distance_m")
        return self


class ContextualRiskScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_classification: Classification = "SIMULATED"
    evaluation_time: datetime
    target_zone_id: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$")
    process: RiskScoreRequest
    observations: Annotated[list[CCTVObservation], Field(min_length=1, max_length=100)]
    max_observation_age_seconds: int = Field(default=120, ge=1, le=900)

    _timezone = field_validator("evaluation_time")(_require_timezone)


class VisionContextSummary(BaseModel):
    data_classification: Classification
    target_zone_id: str
    observations_received: int
    observations_used: int
    observations_discarded: int
    max_observed_people: int
    min_observed_hazard_distance_m: float | None
    mean_confidence: float | None
    event_counts: dict[str, int]
    derived_model_inputs: dict[str, float]
    privacy_contract: dict[str, object]
    caveats: list[str]


class ContextualRiskScoreResponse(BaseModel):
    data_classification: Classification
    score: RiskScoreResponse
    vision_context: VisionContextSummary
    integration_method: str
    llm_in_risk_path: Literal[False] = False


class PatternSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_classification: Classification = "SIMULATED"
    query: str = Field(min_length=3, max_length=500)
    context_signals: list[str] = Field(default_factory=list, max_length=20)
    top_k: int = Field(default=3, ge=1, le=5)


class PatternSource(BaseModel):
    source_id: str
    publisher: str
    title: str
    url: str
    locator: str
    access_scope: str
    note: str


class PatternMatch(BaseModel):
    pattern_id: str
    title: str
    classification: ReferenceClassification
    score: float
    matched_terms: list[str]
    pattern_summary: str
    signals: list[str]
    review_prompts: list[str]
    sources: list[PatternSource]


class PatternSearchResponse(BaseModel):
    data_classification: ReferenceClassification
    corpus_name: str
    corpus_version: str
    corpus_sha256: str
    retrieval_method: Literal["LOCAL_BM25"]
    generative_model_used: Literal[False] = False
    query: str
    results: list[PatternMatch]
    corpus_scope_note: str
    licensing_note: str


class PermitRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permit_id: str = Field(min_length=3, max_length=96, pattern=r"^[A-Za-z0-9._:-]+$")
    work_type: Literal["hot_work", "confined_space", "electrical", "line_break", "general"]
    zone_id: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$")
    status: Literal["DRAFT", "ACTIVE", "SUSPENDED", "CLOSED", "EXPIRED"]
    valid_from: datetime
    valid_until: datetime
    overlapping_permit_ids: list[str] = Field(default_factory=list, max_length=30)
    isolation_confirmed: bool = False
    gas_test_evidence_ref: str | None = Field(default=None, max_length=128)
    gas_test_age_minutes: int | None = Field(default=None, ge=0, le=100_000)
    attendant_evidence_ref: str | None = Field(default=None, max_length=128)
    area_authority_approval_ref: str | None = Field(default=None, max_length=128)

    _valid_from_timezone = field_validator("valid_from")(_require_timezone)
    _valid_until_timezone = field_validator("valid_until")(_require_timezone)

    @model_validator(mode="after")
    def validate_window(self) -> "PermitRecord":
        if self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be later than valid_from")
        return self


class AuditEvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=3, max_length=96, pattern=r"^[A-Za-z0-9._:-]+$")
    evidence_type: Literal["permit", "gas_test", "asset_state", "sensor", "vision_metadata", "approval"]
    source_system: str = Field(min_length=2, max_length=80)
    observed_at: datetime
    sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    classification: Classification = "SIMULATED"

    _timezone = field_validator("observed_at")(_require_timezone)


class PermitAuditContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluated_at: datetime
    ventilation_impaired: bool = False
    lel_ratio: float = Field(default=0.0, ge=0.0, le=3.0)
    oxygen_deficit_ratio: float = Field(default=0.0, ge=0.0, le=3.0)
    workers_in_zone: int = Field(default=0, ge=0, le=250)
    shift_handover: bool = False
    blocked_egress_observed: bool = False

    _timezone = field_validator("evaluated_at")(_require_timezone)


class PermitAuditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_classification: Classification = "SIMULATED"
    permit: PermitRecord
    context: PermitAuditContext
    evidence: Annotated[list[AuditEvidenceItem], Field(max_length=100)] = Field(default_factory=list)


class AuditReference(BaseModel):
    source_id: str
    title: str
    url: str
    locator: str
    access_scope: str


class AuditFinding(BaseModel):
    finding_id: str
    severity: Literal["INFO", "REVIEW", "HIGH", "CRITICAL"]
    title: str
    evidence_refs: list[str]
    rationale: str
    recommended_action: str
    references: list[AuditReference]


class PermitAuditResponse(BaseModel):
    data_classification: Classification
    audit_id: str
    result: Literal["NO_FINDINGS", "HUMAN_REVIEW_REQUIRED", "CRITICAL_HUMAN_REVIEW"]
    evaluated_at: datetime
    permit_id: str
    evidence_manifest_sha256: str
    evidence_complete: bool
    findings: list[AuditFinding]
    proposed_response_actions: list[str]
    compliance_boundary: str
    llm_used: Literal[False] = False


ResponseAction = Literal[
    "NOTIFY_SAFETY_TEAM",
    "DISPATCH_SAFETY_OFFICER",
    "PAUSE_PERMIT",
    "RESTRICT_ZONE_ACCESS",
    "RESTORE_VENTILATION",
    "CONTROLLED_EVACUATION",
    "PROCESS_SHUTDOWN",
]


class ResponsePlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_classification: Classification = "SIMULATED"
    risk_case_id: str = Field(min_length=3, max_length=96, pattern=r"^[A-Za-z0-9._:-]+$")
    requested_at: datetime
    severity: Literal["watch", "elevated", "critical"]
    actions: Annotated[list[ResponseAction], Field(min_length=1, max_length=7)]
    rationale: str = Field(min_length=10, max_length=1_000)

    _timezone = field_validator("requested_at")(_require_timezone)

    @field_validator("actions")
    @classmethod
    def unique_actions(cls, value: list[ResponseAction]) -> list[ResponseAction]:
        if len(value) != len(set(value)):
            raise ValueError("actions must be unique")
        return value


class ResponseApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_classification: Classification = "SIMULATED"
    approver_ref: str = Field(min_length=3, max_length=96, pattern=r"^[A-Za-z0-9._:-]+$")
    approver_role: Literal["SHIFT_IN_CHARGE", "AREA_AUTHORITY", "SAFETY_OFFICER", "INCIDENT_COMMANDER"]
    decision: Literal["APPROVE", "REJECT"]
    decided_at: datetime
    reason: str = Field(min_length=3, max_length=500)

    _timezone = field_validator("decided_at")(_require_timezone)


class ApprovalRecord(BaseModel):
    approver_ref: str
    approver_role: str
    decision: str
    decided_at: datetime
    reason: str


class ResponsePlan(BaseModel):
    data_classification: Classification
    plan_id: str
    risk_case_id: str
    requested_at: datetime
    severity: str
    actions: list[ResponseAction]
    rationale: str
    required_approval_roles: list[str]
    approvals: list[ApprovalRecord]
    status: Literal["AWAITING_HUMAN_APPROVAL", "REJECTED", "AUTHORIZED_FOR_MANUAL_EXECUTION"]
    execution_mode: Literal["MANUAL_ONLY"] = "MANUAL_ONLY"
    actuation_performed: Literal[False] = False
    autonomous_shutdown_or_evacuation: Literal[False] = False
    boundary: str
