"""In-memory demo response plans with immutable human approval gates."""

from __future__ import annotations

import hashlib
import json
from threading import RLock

from .brief_schemas import (
    ApprovalRecord,
    ResponseApprovalRequest,
    ResponsePlan,
    ResponsePlanRequest,
)

ROLE_ORDER = ["SHIFT_IN_CHARGE", "AREA_AUTHORITY", "SAFETY_OFFICER", "INCIDENT_COMMANDER"]
HIGH_CONSEQUENCE_ACTIONS = {"CONTROLLED_EVACUATION", "PROCESS_SHUTDOWN"}
AREA_CONTROL_ACTIONS = {
    "PAUSE_PERMIT",
    "RESTRICT_ZONE_ACCESS",
    "RESTORE_VENTILATION",
}


def _required_roles(actions: list[str]) -> list[str]:
    roles = {"SAFETY_OFFICER"}
    if set(actions) & AREA_CONTROL_ACTIONS:
        roles.add("AREA_AUTHORITY")
    if set(actions) & HIGH_CONSEQUENCE_ACTIONS:
        roles.update({"AREA_AUTHORITY", "INCIDENT_COMMANDER"})
    return [role for role in ROLE_ORDER if role in roles]


def _plan_id(request: ResponsePlanRequest) -> str:
    canonical = request.model_dump(mode="json")
    canonical["actions"] = sorted(canonical["actions"])
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"rsp-{hashlib.sha256(raw).hexdigest()[:16]}"


class ResponsePlanStore:
    """Thread-safe prototype store; deliberately contains no actuator client."""

    def __init__(self) -> None:
        self._plans: dict[str, ResponsePlan] = {}
        self._lock = RLock()

    def create(self, request: ResponsePlanRequest) -> ResponsePlan:
        plan_id = _plan_id(request)
        with self._lock:
            if plan_id not in self._plans:
                self._plans[plan_id] = ResponsePlan(
                    data_classification="SIMULATED",
                    plan_id=plan_id,
                    risk_case_id=request.risk_case_id,
                    requested_at=request.requested_at,
                    severity=request.severity,
                    actions=request.actions,
                    rationale=request.rationale,
                    required_approval_roles=_required_roles(request.actions),
                    approvals=[],
                    status="AWAITING_HUMAN_APPROVAL",
                    execution_mode="MANUAL_ONLY",
                    actuation_performed=False,
                    autonomous_shutdown_or_evacuation=False,
                    boundary=(
                        "Approval changes this record only to AUTHORIZED_FOR_MANUAL_EXECUTION. "
                        "Compound Zero has no API path to actuate shutdown, evacuation, isolation, access control, or equipment. "
                        "Approver roles are supplied SIMULATED claims, not authenticated identities; production use requires plant IAM."
                    ),
                )
            return self._plans[plan_id].model_copy(deep=True)

    def get(self, plan_id: str) -> ResponsePlan | None:
        with self._lock:
            plan = self._plans.get(plan_id)
            return None if plan is None else plan.model_copy(deep=True)

    def approve(self, plan_id: str, request: ResponseApprovalRequest) -> ResponsePlan:
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                raise KeyError(plan_id)
            if plan.status != "AWAITING_HUMAN_APPROVAL":
                raise ValueError(f"plan is locked in status {plan.status}")
            if request.approver_role not in plan.required_approval_roles:
                raise ValueError(
                    f"role {request.approver_role} is not a required approver for this plan"
                )
            if request.decided_at < plan.requested_at:
                raise ValueError("approval timestamp cannot precede plan request time")
            if any(
                approval.approver_role == request.approver_role
                for approval in plan.approvals
            ):
                raise ValueError(f"role {request.approver_role} has already decided")

            plan.approvals.append(
                ApprovalRecord(
                    approver_ref=request.approver_ref,
                    approver_role=request.approver_role,
                    decision=request.decision,
                    decided_at=request.decided_at,
                    reason=request.reason,
                )
            )
            if request.decision == "REJECT":
                plan.status = "REJECTED"
            else:
                approved_roles = {
                    approval.approver_role
                    for approval in plan.approvals
                    if approval.decision == "APPROVE"
                }
                if set(plan.required_approval_roles).issubset(approved_roles):
                    plan.status = "AUTHORIZED_FOR_MANUAL_EXECUTION"
            return plan.model_copy(deep=True)

    def clear(self) -> None:
        """Reset ephemeral prototype state (primarily useful for tests)."""

        with self._lock:
            self._plans.clear()
