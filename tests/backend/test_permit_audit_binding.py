from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from services.api.brief_schemas import PermitAuditRequest
from services.api.permit_audit import audit_permit


def _valid_payload() -> dict[str, object]:
    return {
        "data_classification": "SIMULATED",
        "permit": {
            "permit_id": "PTW-CS-100",
            "work_type": "confined_space",
            "zone_id": "ZONE-T1",
            "status": "ACTIVE",
            "valid_from": "2026-07-22T09:00:00Z",
            "valid_until": "2026-07-22T13:00:00Z",
            "isolation_confirmed": True,
            "gas_test_evidence_ref": "ev-gas-100",
            "attendant_evidence_ref": "ev-attendant-100",
            "area_authority_approval_ref": "ev-approval-100",
        },
        "context": {
            "evaluated_at": "2026-07-22T10:00:00Z",
            "workers_in_zone": 0,
        },
        "evidence": [
            {
                "evidence_id": "ev-permit-100",
                "evidence_type": "permit",
                "permit_id": "PTW-CS-100",
                "zone_id": "ZONE-T1",
                "source_system": "SIMULATED PTW",
                "observed_at": "2026-07-22T09:00:00Z",
            },
            {
                "evidence_id": "ev-gas-100",
                "evidence_type": "gas_test",
                "permit_id": "PTW-CS-100",
                "zone_id": "ZONE-T1",
                "role": "COMPETENT_PERSON",
                "source_system": "SIMULATED GAS TEST",
                "observed_at": "2026-07-22T09:40:00Z",
            },
            {
                "evidence_id": "ev-approval-100",
                "evidence_type": "approval",
                "permit_id": "PTW-CS-100",
                "zone_id": "ZONE-T1",
                "role": "AREA_AUTHORITY",
                "source_system": "SIMULATED PTW",
                "observed_at": "2026-07-22T09:10:00Z",
            },
            {
                "evidence_id": "ev-attendant-100",
                "evidence_type": "attendant",
                "permit_id": "PTW-CS-100",
                "zone_id": "ZONE-T1",
                "role": "CONFINED_SPACE_ATTENDANT",
                "source_system": "SIMULATED PERSONNEL ROSTER",
                "observed_at": "2026-07-22T09:15:00Z",
            },
        ],
    }


def _finding_ids(payload: dict[str, object]) -> tuple[set[str], object]:
    response = audit_permit(PermitAuditRequest.model_validate(payload))
    return {finding.finding_id for finding in response.findings}, response


def test_valid_references_bind_and_gas_age_is_derived_from_timestamps() -> None:
    finding_ids, response = _finding_ids(_valid_payload())

    assert finding_ids == set()
    assert response.result == "NO_FINDINGS"
    assert response.evidence_complete is True
    assert response.derived_gas_test_age_minutes == 20.0
    assert response.resolved_evidence_refs == {
        "permit": "ev-permit-100",
        "gas_test": "ev-gas-100",
        "area_authority_approval": "ev-approval-100",
        "confined_space_attendant": "ev-attendant-100",
    }


def test_confined_space_atmosphere_finding_has_scoped_final_rules_reference() -> None:
    payload = _valid_payload()
    payload["context"]["workers_in_zone"] = 1  # type: ignore[index]
    payload["context"]["oxygen_deficit_ratio"] = 0.2  # type: ignore[index]

    finding_ids, response = _finding_ids(payload)

    assert "confined-space-occupancy-atmosphere" in finding_ids
    finding = next(
        item
        for item in response.findings
        if item.finding_id == "confined-space-occupancy-atmosphere"
    )
    reference = next(
        item
        for item in finding.references
        if item.source_id == "OSHWC-CENTRAL-RULES-2026-R23-R24-III"
    )
    assert "Rules 23(ii) and 24(iii)" in reference.locator
    assert "Scoped risk mapping only" in reference.locator


def test_unrelated_evidence_never_substitutes_for_bad_references() -> None:
    payload = _valid_payload()
    payload["evidence"] = [
        payload["evidence"][0],  # type: ignore[index]
        {
            "evidence_id": "ev-gas-100",
            "evidence_type": "sensor",
            "permit_id": "PTW-CS-100",
            "zone_id": "ZONE-T1",
            "source_system": "SIMULATED SENSOR",
            "observed_at": "2026-07-22T09:40:00Z",
        },
        {
            "evidence_id": "ev-approval-100",
            "evidence_type": "approval",
            "permit_id": "PTW-CS-100",
            "zone_id": "ZONE-OTHER",
            "role": "AREA_AUTHORITY",
            "source_system": "SIMULATED PTW",
            "observed_at": "2026-07-22T09:10:00Z",
        },
        {
            "evidence_id": "ev-attendant-100",
            "evidence_type": "attendant",
            "permit_id": "PTW-CS-100",
            "zone_id": "ZONE-T1",
            "role": "SAFETY_OFFICER",
            "source_system": "SIMULATED PERSONNEL ROSTER",
            "observed_at": "2026-07-22T09:15:00Z",
        },
        # Correct evidence exists, but the permit does not reference these IDs.
        {
            "evidence_id": "ev-gas-unrelated",
            "evidence_type": "gas_test",
            "permit_id": "PTW-CS-100",
            "zone_id": "ZONE-T1",
            "source_system": "SIMULATED GAS TEST",
            "observed_at": "2026-07-22T09:45:00Z",
        },
        {
            "evidence_id": "ev-approval-unrelated",
            "evidence_type": "approval",
            "permit_id": "PTW-CS-100",
            "zone_id": "ZONE-T1",
            "role": "AREA_AUTHORITY",
            "source_system": "SIMULATED PTW",
            "observed_at": "2026-07-22T09:10:00Z",
        },
        {
            "evidence_id": "ev-attendant-unrelated",
            "evidence_type": "attendant",
            "permit_id": "PTW-CS-100",
            "zone_id": "ZONE-T1",
            "role": "CONFINED_SPACE_ATTENDANT",
            "source_system": "SIMULATED PERSONNEL ROSTER",
            "observed_at": "2026-07-22T09:15:00Z",
        },
    ]

    finding_ids, response = _finding_ids(payload)

    assert {
        "gas-test-evidence-invalid-binding",
        "area-approval-evidence-invalid-binding",
        "confined-space-attendant-evidence-invalid-binding",
    }.issubset(finding_ids)
    assert response.evidence_complete is False
    assert response.derived_gas_test_age_minutes is None
    assert response.resolved_evidence_refs == {
        "permit": "ev-permit-100",
        "gas_test": None,
        "area_authority_approval": None,
        "confined_space_attendant": None,
    }


def test_stale_gas_test_uses_evidence_timestamp_not_caller_claim() -> None:
    payload = _valid_payload()
    payload["evidence"][1]["observed_at"] = "2026-07-22T09:14:30Z"  # type: ignore[index]

    finding_ids, response = _finding_ids(payload)

    assert response.derived_gas_test_age_minutes == 45.5
    assert "gas-test-review-window-exceeded" in finding_ids


def test_future_dated_evidence_is_not_bound() -> None:
    payload = _valid_payload()
    payload["evidence"][1]["observed_at"] = "2026-07-22T10:00:01Z"  # type: ignore[index]

    finding_ids, response = _finding_ids(payload)

    assert "gas-test-evidence-invalid-binding" in finding_ids
    assert response.derived_gas_test_age_minutes is None
    assert response.resolved_evidence_refs["gas_test"] is None


def test_caller_supplied_gas_age_and_duplicate_evidence_ids_are_rejected() -> None:
    payload = _valid_payload()
    payload["permit"]["gas_test_age_minutes"] = 1  # type: ignore[index]
    with pytest.raises(ValidationError, match="gas_test_age_minutes"):
        PermitAuditRequest.model_validate(payload)

    duplicate_payload = deepcopy(_valid_payload())
    duplicate_payload["evidence"].append(deepcopy(duplicate_payload["evidence"][0]))  # type: ignore[union-attr,index]
    with pytest.raises(ValidationError, match="evidence_id values must be unique"):
        PermitAuditRequest.model_validate(duplicate_payload)
