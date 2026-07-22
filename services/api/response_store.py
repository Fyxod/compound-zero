"""Bounded in-memory demo response plans with immutable human approval gates."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
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
DEFAULT_TTL_SECONDS = 15 * 60.0
DEFAULT_MAX_ENTRIES = 1_000


class IdempotencyConflictError(ValueError):
    """The same idempotency key was reused for a different request."""


class ResponsePlanCapacityError(RuntimeError):
    """Active plan retention is full; active safety records are not evicted."""


@dataclass
class _StoredPlan:
    plan: ResponsePlan
    fingerprint: str
    expires_at: float
    idempotency_key: str | None


def _required_roles(actions: list[str]) -> list[str]:
    roles = {"SAFETY_OFFICER"}
    if set(actions) & AREA_CONTROL_ACTIONS:
        roles.add("AREA_AUTHORITY")
    if set(actions) & HIGH_CONSEQUENCE_ACTIONS:
        roles.update({"AREA_AUTHORITY", "INCIDENT_COMMANDER"})
    return [role for role in ROLE_ORDER if role in roles]


def _request_fingerprint(request: ResponsePlanRequest) -> str:
    canonical = request.model_dump(mode="json", exclude={"idempotency_key"})
    canonical["actions"] = sorted(canonical["actions"])
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _plan_id(request: ResponsePlanRequest, fingerprint: str) -> str:
    identity = (
        f"key:{request.idempotency_key}:{fingerprint}"
        if request.idempotency_key
        else f"payload:{fingerprint}"
    )
    return f"rsp-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]}"


class ResponsePlanStore:
    """Thread-safe, TTL-bounded prototype store with no actuator client.

    TTL is measured with an injected monotonic clock rather than the caller's
    SIMULATED requested_at timestamp. Idempotent replays do not extend TTL, so
    repeated requests cannot retain ephemeral records forever.
    """

    def __init__(
        self,
        *,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not 1.0 <= ttl_seconds <= 86_400.0:
            raise ValueError("ttl_seconds must be between 1 second and 24 hours")
        if not 1 <= max_entries <= 100_000:
            raise ValueError("max_entries must be between 1 and 100000")
        self.ttl_seconds = float(ttl_seconds)
        self.max_entries = max_entries
        self._clock = clock
        self._plans: dict[str, _StoredPlan] = {}
        self._idempotency_keys: dict[str, str] = {}
        self._lock = RLock()

    @property
    def entry_count(self) -> int:
        with self._lock:
            self._purge_expired(self._clock())
            return len(self._plans)

    def _purge_expired(self, now: float) -> None:
        expired_ids = [
            plan_id
            for plan_id, entry in self._plans.items()
            if entry.expires_at <= now
        ]
        for plan_id in expired_ids:
            entry = self._plans.pop(plan_id)
            if (
                entry.idempotency_key is not None
                and self._idempotency_keys.get(entry.idempotency_key) == plan_id
            ):
                del self._idempotency_keys[entry.idempotency_key]

    def create(self, request: ResponsePlanRequest) -> ResponsePlan:
        fingerprint = _request_fingerprint(request)
        plan_id = _plan_id(request, fingerprint)
        with self._lock:
            now = self._clock()
            self._purge_expired(now)

            if request.idempotency_key is not None:
                existing_id = self._idempotency_keys.get(request.idempotency_key)
                if existing_id is not None:
                    existing = self._plans[existing_id]
                    if existing.fingerprint != fingerprint:
                        raise IdempotencyConflictError(
                            "idempotency_key is already bound to a different response-plan request"
                        )
                    return existing.plan.model_copy(deep=True)
            elif plan_id in self._plans:
                # Requests without an explicit key remain content-idempotent.
                return self._plans[plan_id].plan.model_copy(deep=True)

            if len(self._plans) >= self.max_entries:
                raise ResponsePlanCapacityError(
                    "response-plan store is at active-record capacity; retry after TTL expiry"
                )

            plan = ResponsePlan(
                data_classification="SIMULATED",
                plan_id=plan_id,
                idempotency_key=request.idempotency_key,
                retention_ttl_seconds=self.ttl_seconds,
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
                    "Approver roles are supplied SIMULATED claims, not authenticated identities; production use requires plant IAM. "
                    "The in-memory record expires after a bounded TTL and is not a durable audit log."
                ),
            )
            self._plans[plan_id] = _StoredPlan(
                plan=plan,
                fingerprint=fingerprint,
                expires_at=now + self.ttl_seconds,
                idempotency_key=request.idempotency_key,
            )
            if request.idempotency_key is not None:
                self._idempotency_keys[request.idempotency_key] = plan_id
            return plan.model_copy(deep=True)

    def get(self, plan_id: str) -> ResponsePlan | None:
        with self._lock:
            self._purge_expired(self._clock())
            entry = self._plans.get(plan_id)
            return None if entry is None else entry.plan.model_copy(deep=True)

    def approve(self, plan_id: str, request: ResponseApprovalRequest) -> ResponsePlan:
        with self._lock:
            self._purge_expired(self._clock())
            entry = self._plans.get(plan_id)
            if entry is None:
                raise KeyError(plan_id)
            plan = entry.plan
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
            self._idempotency_keys.clear()
