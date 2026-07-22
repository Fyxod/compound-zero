from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

import services.api.main as api_main
from services.api.model_store import ModelStore


def _client(trained_case: dict[str, Any]) -> TestClient:
    api_main.store = ModelStore(trained_case["artifact_dir"])
    api_main.response_plans.clear()
    return TestClient(api_main.app)


def _process_payload() -> dict[str, object]:
    return {
        "data_classification": "SIMULATED",
        "scenario_id": "demo-cctv-001",
        "lel_ratio": 0.62,
        "h2s_ratio": 0.42,
        "co_ratio": 0.35,
        "oxygen_deficit_ratio": 0.21,
        "pressure_ratio": 0.56,
        "lel_slope": 0.03,
        "h2s_slope": 0.02,
        "co_slope": 0.015,
        "oxygen_slope": 0.01,
        "pressure_slope": 0.02,
        "ventilation_impaired": True,
        "hot_work_active": True,
        "workers_in_zone": 0,
        "min_worker_distance_m": 120,
        "permit_overlap_count": 1,
        "stream_quality": 1.0,
    }


def test_cctv_metadata_is_fused_without_identity_or_raw_media(
    trained_case: dict[str, Any],
) -> None:
    client = _client(trained_case)
    payload = {
        "data_classification": "SIMULATED",
        "evaluation_time": "2026-07-22T10:01:00Z",
        "target_zone_id": "ZONE-C7",
        "process": _process_payload(),
        "observations": [
            {
                "observation_id": "obs-occupancy-1",
                "observed_at": "2026-07-22T10:00:40Z",
                "camera_ref": "CAM-C7-WEST",
                "zone_id": "ZONE-C7",
                "event_type": "occupancy",
                "entity_count": 4,
                "confidence": 0.96,
            },
            {
                "observation_id": "obs-distance-1",
                "observed_at": "2026-07-22T10:00:45Z",
                "camera_ref": "CAM-C7-EAST",
                "zone_id": "ZONE-C7",
                "event_type": "unsafe_proximity",
                "entity_count": 2,
                "min_hazard_distance_m": 6.5,
                "confidence": 0.94,
            },
            {
                "observation_id": "obs-off-zone",
                "observed_at": "2026-07-22T10:00:50Z",
                "camera_ref": "CAM-A1",
                "zone_id": "ZONE-A1",
                "event_type": "occupancy",
                "entity_count": 20,
                "confidence": 0.99,
            },
        ],
    }
    response = client.post("/v1/risk/score-with-cctv", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data_classification"] == "SIMULATED"
    assert body["llm_in_risk_path"] is False
    assert body["score"]["decision_engine"]
    context = body["vision_context"]
    assert context["observations_received"] == 3
    assert context["observations_used"] == 2
    assert context["observations_discarded"] == 1
    assert context["max_observed_people"] == 4
    assert context["min_observed_hazard_distance_m"] == 6.5
    assert context["derived_model_inputs"]["workers_in_zone"] == 4.0
    assert context["derived_model_inputs"]["min_worker_distance_m"] == 6.5
    assert context["privacy_contract"]["raw_frames_accepted"] is False
    assert context["privacy_contract"]["identity_tracking_accepted"] is False


def test_cctv_contract_rejects_raw_media_and_biometrics(
    trained_case: dict[str, Any],
) -> None:
    client = _client(trained_case)
    payload = {
        "evaluation_time": "2026-07-22T10:01:00Z",
        "target_zone_id": "ZONE-C7",
        "process": _process_payload(),
        "observations": [
            {
                "observation_id": "obs-illegal-payload",
                "observed_at": "2026-07-22T10:00:40Z",
                "camera_ref": "CAM-C7",
                "zone_id": "ZONE-C7",
                "event_type": "occupancy",
                "entity_count": 1,
                "confidence": 0.99,
                "raw_media_included": True,
                "biometric_processing": True,
            }
        ],
    }
    response = client.post("/v1/risk/score-with-cctv", json=payload)
    assert response.status_code == 422


def test_local_pattern_retrieval_is_ranked_cited_and_non_generative(
    trained_case: dict[str, Any],
) -> None:
    client = _client(trained_case)
    response = client.post(
        "/v1/intelligence/patterns",
        json={
            "query": "hot work ignition while ventilation extraction is impaired",
            "context_signals": ["flammable gas trend", "workers in zone"],
            "top_k": 3,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["retrieval_method"] == "LOCAL_BM25"
    assert body["generative_model_used"] is False
    assert len(body["corpus_sha256"]) == 64
    assert body["results"][0]["pattern_id"] == "compound-hot-work-barrier-loss"
    assert body["results"][0]["matched_terms"]
    sources = body["results"][0]["sources"]
    assert any(source["source_id"] == "OISD-STD-105-METADATA" for source in sources)
    assert any(source["source_id"] == "OSHWC-CODE-2020-SCHEDULE-II" for source in sources)
    rules_source = next(
        source
        for source in sources
        if source["source_id"] == "OSHWC-CENTRAL-RULES-2026-R23-R24-I-II"
    )
    assert "Rules 23(ii) and 24(i)-(ii)" in rules_source["locator"]
    assert "not a claim" in rules_source["note"]
    assert any(source["access_scope"] == "PUBLIC_METADATA_ONLY" for source in sources)
    assert "not bundled" in body["licensing_note"].lower()

    metadata = client.get("/v1/intelligence/corpus")
    assert metadata.status_code == 200
    assert metadata.json()["pattern_count"] == 5
    assert metadata.json()["generative_model_used"] is False


def test_pattern_retrieval_does_not_hallucinate_a_match(
    trained_case: dict[str, Any],
) -> None:
    client = _client(trained_case)
    response = client.post(
        "/v1/intelligence/patterns",
        json={"query": "quasar zeppelin xylophone", "top_k": 5},
    )
    assert response.status_code == 200
    assert response.json()["results"] == []


def _critical_hot_work_audit_payload() -> dict[str, object]:
    return {
        "data_classification": "SIMULATED",
        "permit": {
            "permit_id": "PTW-HOT-2041",
            "work_type": "hot_work",
            "zone_id": "ZONE-C7",
            "status": "ACTIVE",
            "valid_from": "2026-07-22T09:00:00Z",
            "valid_until": "2026-07-22T12:00:00Z",
            "overlapping_permit_ids": ["PTW-MECH-991"],
            "isolation_confirmed": False,
        },
        "context": {
            "evaluated_at": "2026-07-22T10:01:00Z",
            "ventilation_impaired": True,
            "lel_ratio": 0.62,
            "workers_in_zone": 4,
            "shift_handover": True,
            "blocked_egress_observed": True,
        },
        "evidence": [
            {
                "evidence_id": "ev-permit-2041",
                "evidence_type": "permit",
                "permit_id": "PTW-HOT-2041",
                "zone_id": "ZONE-C7",
                "source_system": "SIMULATED PTW",
                "observed_at": "2026-07-22T10:00:00Z",
            },
            {
                "evidence_id": "ev-vision-egress",
                "evidence_type": "vision_metadata",
                "permit_id": "PTW-HOT-2041",
                "zone_id": "ZONE-C7",
                "source_system": "SIMULATED CCTV METADATA",
                "observed_at": "2026-07-22T10:00:40Z",
            },
        ],
    }


def test_permit_audit_is_deterministic_evidence_linked_and_bounded(
    trained_case: dict[str, Any],
) -> None:
    client = _client(trained_case)
    payload = _critical_hot_work_audit_payload()
    first = client.post("/v1/audit/permits", json=payload)
    second = client.post("/v1/audit/permits", json=payload)
    assert first.status_code == 200, first.text
    assert first.json() == second.json()
    body = first.json()
    assert body["result"] == "CRITICAL_HUMAN_REVIEW"
    assert body["evidence_complete"] is False
    assert body["llm_used"] is False
    finding_ids = {finding["finding_id"] for finding in body["findings"]}
    assert "hot-work-barrier-gas-overlap" in finding_ids
    assert "gas-test-evidence-missing" in finding_ids
    assert "blocked-egress-observation" in finding_ids
    findings_by_id = {finding["finding_id"]: finding for finding in body["findings"]}
    hot_work_reference_ids = {
        reference["source_id"]
        for reference in findings_by_id["hot-work-barrier-gas-overlap"]["references"]
    }
    assert "OSHWC-CENTRAL-RULES-2026-R23-R24-I-II" in hot_work_reference_ids
    blocked_egress_reference_ids = {
        reference["source_id"]
        for reference in findings_by_id["blocked-egress-observation"]["references"]
    }
    assert "OSHWC-CENTRAL-RULES-2026-R46" in blocked_egress_reference_ids
    assert "not a legal determination" in body["compliance_boundary"]
    assert "subject to savings" in body["compliance_boundary"]
    assert "not a claim of a specific statutory PTW or hot-work rule" in body["compliance_boundary"]
    assert "PROPOSE_WORKER_WITHDRAWAL_TO_INCIDENT_COMMANDER" in body["proposed_response_actions"]
    assert all(finding["references"] for finding in body["findings"])


def test_complete_general_permit_has_no_findings(trained_case: dict[str, Any]) -> None:
    client = _client(trained_case)
    response = client.post(
        "/v1/audit/permits",
        json={
            "permit": {
                "permit_id": "PTW-GEN-1",
                "work_type": "general",
                "zone_id": "ZONE-A1",
                "status": "ACTIVE",
                "valid_from": "2026-07-22T09:00:00Z",
                "valid_until": "2026-07-22T12:00:00Z",
                "area_authority_approval_ref": "ev-approval-1",
            },
            "context": {"evaluated_at": "2026-07-22T10:00:00Z"},
            "evidence": [
                {
                    "evidence_id": "ev-permit-1",
                    "evidence_type": "permit",
                    "permit_id": "PTW-GEN-1",
                    "zone_id": "ZONE-A1",
                    "source_system": "SIMULATED PTW",
                    "observed_at": "2026-07-22T09:00:00Z",
                },
                {
                    "evidence_id": "ev-approval-1",
                    "evidence_type": "approval",
                    "permit_id": "PTW-GEN-1",
                    "zone_id": "ZONE-A1",
                    "role": "AREA_AUTHORITY",
                    "source_system": "SIMULATED PTW",
                    "observed_at": "2026-07-22T09:00:00Z",
                },
            ],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["result"] == "NO_FINDINGS"
    assert body["evidence_complete"] is True
    assert body["findings"] == []


def test_high_consequence_response_requires_three_humans_and_never_actuates(
    trained_case: dict[str, Any],
) -> None:
    client = _client(trained_case)
    create = client.post(
        "/v1/response/plans",
        json={
            "risk_case_id": "CASE-C7-2041",
            "requested_at": "2026-07-22T10:02:00Z",
            "severity": "critical",
            "actions": ["NOTIFY_SAFETY_TEAM", "CONTROLLED_EVACUATION", "PROCESS_SHUTDOWN"],
            "rationale": "Compound risk is critical; present a bounded plan to authorised site roles.",
        },
    )
    assert create.status_code == 201, create.text
    plan = create.json()
    plan_id = plan["plan_id"]
    assert plan["status"] == "AWAITING_HUMAN_APPROVAL"
    assert plan["required_approval_roles"] == [
        "AREA_AUTHORITY",
        "SAFETY_OFFICER",
        "INCIDENT_COMMANDER",
    ]
    assert plan["execution_mode"] == "MANUAL_ONLY"
    assert plan["actuation_performed"] is False
    assert plan["autonomous_shutdown_or_evacuation"] is False
    assert "no API path to actuate" in plan["boundary"]

    for index, role in enumerate(plan["required_approval_roles"]):
        decision = client.post(
            f"/v1/response/plans/{plan_id}/approvals",
            json={
                "approver_ref": f"simulated-{role.lower()}",
                "approver_role": role,
                "decision": "APPROVE",
                "decided_at": f"2026-07-22T10:0{3 + index}:00Z",
                "reason": "Reviewed the simulated evidence and authorise manual execution only.",
            },
        )
        assert decision.status_code == 200, decision.text
        plan = decision.json()
        if index < 2:
            assert plan["status"] == "AWAITING_HUMAN_APPROVAL"

    assert plan["status"] == "AUTHORIZED_FOR_MANUAL_EXECUTION"
    assert plan["actuation_performed"] is False
    assert plan["autonomous_shutdown_or_evacuation"] is False

    locked = client.post(
        f"/v1/response/plans/{plan_id}/approvals",
        json={
            "approver_ref": "simulated-safety-officer-2",
            "approver_role": "SAFETY_OFFICER",
            "decision": "APPROVE",
            "decided_at": "2026-07-22T10:10:00Z",
            "reason": "Attempt to alter a locked plan.",
        },
    )
    assert locked.status_code == 409

    fetched = client.get(f"/v1/response/plans/{plan_id}")
    assert fetched.status_code == 200
    assert fetched.json() == plan
