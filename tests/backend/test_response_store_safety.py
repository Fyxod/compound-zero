from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

import services.api.main as api_main
from services.api.brief_schemas import ResponseApprovalRequest, ResponsePlanRequest
from services.api.response_store import (
    IdempotencyConflictError,
    ResponsePlanCapacityError,
    ResponsePlanStore,
)


@dataclass
class FakeClock:
    now: float = 1_000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _request(
    *,
    risk_case_id: str = "risk-case-100",
    idempotency_key: str | None = None,
    rationale: str = "Notify the safety team for manual verification.",
) -> ResponsePlanRequest:
    return ResponsePlanRequest.model_validate(
        {
            "data_classification": "SIMULATED",
            "idempotency_key": idempotency_key,
            "risk_case_id": risk_case_id,
            "requested_at": "2026-07-22T10:00:00Z",
            "severity": "elevated",
            "actions": ["NOTIFY_SAFETY_TEAM"],
            "rationale": rationale,
        }
    )


def _approval() -> ResponseApprovalRequest:
    return ResponseApprovalRequest.model_validate(
        {
            "data_classification": "SIMULATED",
            "approver_ref": "safety-officer-1",
            "approver_role": "SAFETY_OFFICER",
            "decision": "APPROVE",
            "decided_at": "2026-07-22T10:01:00Z",
            "reason": "Verified for manual execution.",
        }
    )


def test_idempotent_replay_returns_same_plan_without_extending_ttl() -> None:
    clock = FakeClock()
    store = ResponsePlanStore(ttl_seconds=10, clock=clock)
    request = _request(idempotency_key="demo-key-100")

    first = store.create(request)
    clock.advance(9)
    replay = store.create(request)
    clock.advance(1)

    assert replay == first
    assert replay.retention_ttl_seconds == 10.0
    assert store.get(first.plan_id) is None
    assert store.entry_count == 0


def test_idempotency_key_cannot_be_reused_for_different_payload() -> None:
    store = ResponsePlanStore()
    store.create(_request(idempotency_key="demo-key-100"))

    with pytest.raises(IdempotencyConflictError, match="different response-plan request"):
        store.create(
            _request(
                idempotency_key="demo-key-100",
                rationale="A materially different manual response rationale.",
            )
        )

    assert store.entry_count == 1


def test_expired_plan_cannot_be_read_or_approved() -> None:
    clock = FakeClock()
    store = ResponsePlanStore(ttl_seconds=5, clock=clock)
    plan = store.create(_request())
    clock.advance(5)

    assert store.get(plan.plan_id) is None
    with pytest.raises(KeyError):
        store.approve(plan.plan_id, _approval())


def test_capacity_never_evicts_active_safety_record_and_recovers_after_expiry() -> None:
    clock = FakeClock()
    store = ResponsePlanStore(ttl_seconds=5, max_entries=1, clock=clock)
    retained = store.create(_request(risk_case_id="risk-case-retained"))

    with pytest.raises(ResponsePlanCapacityError, match="active-record capacity"):
        store.create(_request(risk_case_id="risk-case-blocked"))

    assert store.get(retained.plan_id) == retained
    clock.advance(5)
    replacement = store.create(_request(risk_case_id="risk-case-replacement"))
    assert replacement.risk_case_id == "risk-case-replacement"
    assert store.entry_count == 1


def test_approval_is_retained_only_until_original_expiry() -> None:
    clock = FakeClock()
    store = ResponsePlanStore(ttl_seconds=10, clock=clock)
    plan = store.create(_request())
    clock.advance(9)
    approved = store.approve(plan.plan_id, _approval())

    assert approved.status == "AUTHORIZED_FOR_MANUAL_EXECUTION"
    clock.advance(1)
    assert store.get(plan.plan_id) is None


def test_api_maps_idempotency_conflict_and_capacity_to_safe_status_codes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ResponsePlanStore(max_entries=1)
    monkeypatch.setattr(api_main, "response_plans", store)
    client = TestClient(api_main.app)
    first_payload = _request(idempotency_key="demo-key-100").model_dump(mode="json")

    assert client.post("/v1/response/plans", json=first_payload).status_code == 201

    conflicting_payload = dict(first_payload)
    conflicting_payload["rationale"] = "A materially different manual response rationale."
    conflict = client.post("/v1/response/plans", json=conflicting_payload)
    assert conflict.status_code == 409
    assert "already bound" in conflict.json()["detail"]

    capacity_payload = _request(
        risk_case_id="risk-case-capacity",
        idempotency_key="demo-key-200",
    ).model_dump(mode="json")
    capacity = client.post("/v1/response/plans", json=capacity_payload)
    assert capacity.status_code == 503
    assert "active-record capacity" in capacity.json()["detail"]
