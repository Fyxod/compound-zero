"""Deterministic permit/evidence checks with bounded compliance language."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal

from .brief_schemas import (
    AuditEvidenceItem,
    AuditFinding,
    AuditReference,
    PermitAuditRequest,
    PermitAuditResponse,
)

GAS_TEST_REVIEW_WINDOW_MINUTES = 30.0

OISD_105 = AuditReference(
    source_id="OISD-STD-105-METADATA",
    title="OISD-STD-105 - Work Permit System (catalogue metadata only)",
    url="https://www.oisd.gov.in/en-in/oisd-standards-list",
    locator="OISD-STD-105; Aug 2023 edition listed",
    access_scope="PUBLIC_METADATA_ONLY",
)
OSHWC_SAFETY_MATTERS = AuditReference(
    source_id="OSHWC-CODE-2020-SCHEDULE-II",
    title="Occupational Safety, Health and Working Conditions Code, 2020 - Second Schedule",
    url="https://labour.gov.in/sites/default/files/osh_gazette.pdf",
    locator="Section 18(2)(f), Second Schedule items 16, 18 and 23: dangerous fumes/gases, explosive or inflammable atmospheres, and prohibition in danger",
    access_scope="PUBLIC_LEGISLATION",
)
OSHWC_HAZARDOUS_PROCESS = AuditReference(
    source_id="OSHWC-CODE-2020-S84",
    title="Occupational Safety, Health and Working Conditions Code, 2020 - Section 84",
    url="https://labour.gov.in/sites/default/files/osh_gazette.pdf",
    locator="Hazard disclosure, hazardous-substance measures and on-site emergency planning",
    access_scope="PUBLIC_LEGISLATION",
)
OSHWC_IMMINENT_DANGER = AuditReference(
    source_id="OSHWC-CODE-2020-S89",
    title="Occupational Safety, Health and Working Conditions Code, 2020 - Section 89",
    url="https://labour.gov.in/sites/default/files/osh_gazette.pdf",
    locator="Imminent-danger notice, immediate remedial action and escalation",
    access_scope="PUBLIC_LEGISLATION",
)
OSHWC_RULES_FACTORY_ATMOSPHERE = AuditReference(
    source_id="OSHWC-CENTRAL-RULES-2026-R23-R24-I-II",
    title="OSH&WC (Central) Rules, 2026 - factory ventilation and exhaust context",
    url="https://www.labour.gov.in/static/uploads/2026/05/ee246f790cad0b8e99c3828f34fa09a6.pdf",
    locator=(
        "Rules 23(ii) and 24(i)-(ii): ventilation to clear fumes/dilute inflammable or noxious gases, "
        "and separation/treatment of relevant exhaust streams. Risk mapping only; not a specific statutory PTW or hot-work rule"
    ),
    access_scope="PUBLIC_LEGISLATION",
)
OSHWC_RULES_CONFINED_SPACE = AuditReference(
    source_id="OSHWC-CENTRAL-RULES-2026-R23-R24-III",
    title="OSH&WC (Central) Rules, 2026 - factory atmosphere and confined-space context",
    url="https://www.labour.gov.in/static/uploads/2026/05/ee246f790cad0b8e99c3828f34fa09a6.pdf",
    locator=(
        "Rules 23(ii) and 24(iii): ventilation to clear fumes/dilute gases and practicable measures before entry "
        "where noxious gas, fume, vapour or dust may be present. Scoped risk mapping only"
    ),
    access_scope="PUBLIC_LEGISLATION",
)
OSHWC_RULES_EMERGENCY_LIGHTING = AuditReference(
    source_id="OSHWC-CENTRAL-RULES-2026-R46",
    title="OSH&WC (Central) Rules, 2026 - ordinary and emergency illumination",
    url="https://www.labour.gov.in/static/uploads/2026/05/ee246f790cad0b8e99c3828f34fa09a6.pdf",
    locator=(
        "Rule 46(i)-(iii): illumination where employees work or pass, including emergencies, and independent emergency lighting. "
        "Visibility risk mapping only; not an egress-obstruction rule"
    ),
    access_scope="PUBLIC_LEGISLATION",
)


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _finding(
    finding_id: str,
    severity: Literal["INFO", "REVIEW", "HIGH", "CRITICAL"],
    title: str,
    evidence_refs: list[str],
    rationale: str,
    recommended_action: str,
    references: list[AuditReference],
) -> AuditFinding:
    return AuditFinding(
        finding_id=finding_id,
        severity=severity,
        title=title,
        evidence_refs=sorted(set(evidence_refs)),
        rationale=rationale,
        recommended_action=recommended_action,
        references=references,
    )


def _bound_evidence(
    evidence_by_id: dict[str, AuditEvidenceItem],
    evidence_ref: str | None,
    *,
    expected_type: str,
    permit_id: str,
    zone_id: str,
    evaluated_at: datetime,
    expected_role: str | None = None,
) -> AuditEvidenceItem | None:
    """Resolve one reference only when its type, subject and time all bind.

    A different evidence record of the expected type is never substituted for
    a bad reference. This prevents an unrelated gas test or approval elsewhere
    in the manifest from satisfying the permit under review.
    """

    if evidence_ref is None:
        return None
    item = evidence_by_id.get(evidence_ref)
    if item is None:
        return None
    if item.evidence_type != expected_type:
        return None
    if item.permit_id != permit_id or item.zone_id != zone_id:
        return None
    if expected_role is not None and item.role != expected_role:
        return None
    if item.observed_at > evaluated_at:
        return None
    return item


def audit_permit(request: PermitAuditRequest) -> PermitAuditResponse:
    permit = request.permit
    context = request.context
    evidence_by_id = {item.evidence_id: item for item in request.evidence}
    base_refs = [item.evidence_id for item in request.evidence]
    findings: list[AuditFinding] = []

    permit_evidence = next(
        (
            item
            for item in request.evidence
            if item.evidence_type == "permit"
            and item.permit_id == permit.permit_id
            and item.zone_id == permit.zone_id
            and item.observed_at <= context.evaluated_at
        ),
        None,
    )
    gas_evidence = _bound_evidence(
        evidence_by_id,
        permit.gas_test_evidence_ref,
        expected_type="gas_test",
        permit_id=permit.permit_id,
        zone_id=permit.zone_id,
        evaluated_at=context.evaluated_at,
    )
    approval_evidence = _bound_evidence(
        evidence_by_id,
        permit.area_authority_approval_ref,
        expected_type="approval",
        permit_id=permit.permit_id,
        zone_id=permit.zone_id,
        evaluated_at=context.evaluated_at,
        expected_role="AREA_AUTHORITY",
    )
    attendant_evidence = _bound_evidence(
        evidence_by_id,
        permit.attendant_evidence_ref,
        expected_type="attendant",
        permit_id=permit.permit_id,
        zone_id=permit.zone_id,
        evaluated_at=context.evaluated_at,
        expected_role="CONFINED_SPACE_ATTENDANT",
    )
    derived_gas_test_age_minutes = (
        round((context.evaluated_at - gas_evidence.observed_at).total_seconds() / 60.0, 3)
        if gas_evidence is not None
        else None
    )

    if permit_evidence is None:
        findings.append(
            _finding(
                "permit-record-evidence-missing",
                "HIGH",
                "Permit record evidence cannot be resolved to this permit and zone",
                [],
                "The evidence manifest has no non-future permit item bound to the permit and zone under review.",
                "Supply the authoritative permit record through the approved site workflow.",
                [OISD_105],
            )
        )

    if permit.status == "ACTIVE" and not (permit.valid_from <= context.evaluated_at <= permit.valid_until):
        findings.append(
            _finding(
                "permit-outside-validity-window",
                "CRITICAL",
                "Active permit is outside its recorded validity window",
                base_refs,
                "The evaluated timestamp is not inside the permit's supplied validity interval.",
                "Pause work and route the record to the area authority; the API performs no plant actuation.",
                [OISD_105],
            )
        )

    if permit.status == "ACTIVE" and approval_evidence is None:
        approval_ref = permit.area_authority_approval_ref
        findings.append(
            _finding(
                (
                    "area-approval-evidence-missing"
                    if approval_ref is None
                    else "area-approval-evidence-invalid-binding"
                ),
                "HIGH",
                "Area-authority approval evidence cannot be resolved to this permit and zone",
                [approval_ref] if approval_ref else [],
                (
                    "The active permit has no area-authority approval reference."
                    if approval_ref is None
                    else "The referenced item is absent, future-dated, has the wrong type or role, or is bound to a different permit/zone."
                ),
                "Obtain and verify approval evidence using the authorised site workflow.",
                [OISD_105],
            )
        )

    atmosphere_work = permit.work_type in {"hot_work", "confined_space"}
    if permit.status == "ACTIVE" and atmosphere_work and gas_evidence is None:
        gas_ref = permit.gas_test_evidence_ref
        findings.append(
            _finding(
                (
                    "gas-test-evidence-missing"
                    if gas_ref is None
                    else "gas-test-evidence-invalid-binding"
                ),
                "HIGH",
                "Gas-test evidence cannot be resolved to this permit and zone",
                [gas_ref] if gas_ref else [],
                (
                    "The permit has no gas-test evidence reference."
                    if gas_ref is None
                    else "The referenced item is absent, future-dated, has the wrong type, or is bound to a different permit/zone. An unrelated gas-test item is not substituted."
                ),
                "Require competent human verification against the site-approved test procedure before proceeding.",
                [
                    OISD_105,
                    OSHWC_SAFETY_MATTERS,
                    (
                        OSHWC_RULES_FACTORY_ATMOSPHERE
                        if permit.work_type == "hot_work"
                        else OSHWC_RULES_CONFINED_SPACE
                    ),
                ],
            )
        )
    elif (
        permit.status == "ACTIVE"
        and atmosphere_work
        and derived_gas_test_age_minutes is not None
        and derived_gas_test_age_minutes > GAS_TEST_REVIEW_WINDOW_MINUTES
    ):
        findings.append(
            _finding(
                "gas-test-review-window-exceeded",
                "REVIEW",
                "Gas-test evidence exceeds the prototype review window",
                [permit.gas_test_evidence_ref] if permit.gas_test_evidence_ref else [],
                f"The referenced gas test is {derived_gas_test_age_minutes:.3f} minutes old, derived from evidence and evaluation timestamps. It exceeds the demo's configurable 30-minute review heuristic, which is not asserted as a statutory limit.",
                "Have an authorised person apply the site's actual re-test interval.",
                [OISD_105],
            )
        )

    if (
        permit.status == "ACTIVE"
        and permit.work_type == "hot_work"
        and context.ventilation_impaired
        and context.lel_ratio >= 0.35
    ):
        findings.append(
            _finding(
                "hot-work-barrier-gas-overlap",
                "CRITICAL",
                "Hot work overlaps impaired ventilation and a rising flammable-gas context",
                base_refs,
                "The supplied conditions combine an ignition-source permit, barrier impairment, and a LEL ratio at or above the prototype's 0.35 review trigger. The trigger is analytic, not a legal exposure limit; rules 23(ii) and 24(i)-(ii) are cited only as ventilation/exhaust risk context, not as a specific statutory PTW or hot-work rule.",
                "Propose permit pause, worker withdrawal, and ventilation verification through human approval gates.",
                [
                    OISD_105,
                    OSHWC_SAFETY_MATTERS,
                    OSHWC_IMMINENT_DANGER,
                    OSHWC_RULES_FACTORY_ATMOSPHERE,
                ],
            )
        )

    if (
        permit.status == "ACTIVE"
        and permit.work_type == "confined_space"
        and context.workers_in_zone > 0
        and context.oxygen_deficit_ratio >= 0.15
    ):
        findings.append(
            _finding(
                "confined-space-occupancy-atmosphere",
                "CRITICAL",
                "Occupied confined-space work overlaps a deteriorating atmosphere signal",
                base_refs,
                "The supplied metadata reports occupancy and an oxygen-deficit ratio at or above the prototype's 0.15 review trigger. It does not establish a safe or unsafe statutory concentration; rules 23(ii) and 24(iii) are scoped atmosphere/entry context only.",
                "Escalate immediately to the competent person and area authority for manual site-procedure decisions.",
                [
                    OISD_105,
                    OSHWC_SAFETY_MATTERS,
                    OSHWC_IMMINENT_DANGER,
                    OSHWC_RULES_CONFINED_SPACE,
                ],
            )
        )

    if (
        permit.status == "ACTIVE"
        and permit.work_type == "confined_space"
        and attendant_evidence is None
    ):
        attendant_ref = permit.attendant_evidence_ref
        findings.append(
            _finding(
                (
                    "confined-space-attendant-evidence-missing"
                    if attendant_ref is None
                    else "confined-space-attendant-evidence-invalid-binding"
                ),
                "HIGH",
                "Confined-space attendant evidence cannot be resolved to this permit and zone",
                [attendant_ref] if attendant_ref else [],
                (
                    "No attendant evidence reference was supplied for the active confined-space permit."
                    if attendant_ref is None
                    else "The referenced item is absent, future-dated, has the wrong type or role, or is bound to a different permit/zone."
                ),
                "Verify personnel and rescue arrangements against the approved site procedure.",
                [OISD_105, OSHWC_SAFETY_MATTERS],
            )
        )

    if permit.status == "ACTIVE" and permit.overlapping_permit_ids and context.shift_handover:
        findings.append(
            _finding(
                "overlap-during-handover",
                "HIGH",
                "Permit overlap crosses a shift handover",
                [*base_refs, *permit.overlapping_permit_ids],
                "The record contains simultaneous permit identifiers in the same review context during handover.",
                "Require incoming and outgoing authorised roles to reconcile permits, work state, and isolations.",
                [OISD_105],
            )
        )

    if permit.status == "ACTIVE" and permit.work_type in {"electrical", "line_break"} and not permit.isolation_confirmed:
        findings.append(
            _finding(
                "isolation-evidence-unconfirmed",
                "HIGH",
                "Isolation is not confirmed in the supplied permit record",
                base_refs,
                "The active energy-intervention permit has isolation_confirmed=false.",
                "Route the isolation state to an authorised site role for physical verification.",
                [OISD_105],
            )
        )

    if permit.status == "ACTIVE" and context.blocked_egress_observed:
        findings.append(
            _finding(
                "blocked-egress-observation",
                "CRITICAL",
                "Metadata reports blocked egress during active work",
                [
                    item.evidence_id
                    for item in request.evidence
                    if item.evidence_type == "vision_metadata"
                ],
                "A privacy-preserving observation reports an obstruction; a human must verify the physical condition. Rule 46 is cited only as emergency-route illumination context, not as an egress-obstruction rule.",
                "Dispatch an authorised verifier and use the approved emergency plan for any operational response.",
                [
                    OSHWC_HAZARDOUS_PROCESS,
                    OSHWC_IMMINENT_DANGER,
                    OSHWC_RULES_EMERGENCY_LIGHTING,
                ],
            )
        )

    evidence_complete = permit_evidence is not None
    if permit.status == "ACTIVE":
        evidence_complete = evidence_complete and approval_evidence is not None
    if permit.status == "ACTIVE" and atmosphere_work:
        evidence_complete = evidence_complete and gas_evidence is not None
    if permit.status == "ACTIVE" and permit.work_type == "confined_space":
        evidence_complete = evidence_complete and attendant_evidence is not None

    severities = {finding.severity for finding in findings}
    result: Literal["NO_FINDINGS", "HUMAN_REVIEW_REQUIRED", "CRITICAL_HUMAN_REVIEW"]
    if "CRITICAL" in severities:
        result = "CRITICAL_HUMAN_REVIEW"
    elif findings:
        result = "HUMAN_REVIEW_REQUIRED"
    else:
        result = "NO_FINDINGS"

    proposed_actions: list[str] = []
    if findings:
        proposed_actions.extend(["PAUSE_PERMIT_FOR_AUTHORISED_REVIEW", "DISPATCH_SAFETY_OFFICER"])
    if any(finding.finding_id == "hot-work-barrier-gas-overlap" for finding in findings):
        proposed_actions.append("VERIFY_AND_RESTORE_VENTILATION")
    if context.workers_in_zone > 0 and "CRITICAL" in severities:
        proposed_actions.append("PROPOSE_WORKER_WITHDRAWAL_TO_INCIDENT_COMMANDER")
    if context.blocked_egress_observed:
        proposed_actions.append("VERIFY_AND_CLEAR_EGRESS")

    canonical_request = request.model_dump(mode="json")
    audit_hash = _canonical_sha256(canonical_request)
    evidence_manifest_sha256 = _canonical_sha256(
        {
            "permit_id": permit.permit_id,
            "evidence": sorted(
                (item.model_dump(mode="json") for item in request.evidence),
                key=lambda item: item["evidence_id"],
            ),
        }
    )
    return PermitAuditResponse(
        data_classification="SIMULATED",
        audit_id=f"audit-{audit_hash[:16]}",
        result=result,
        evaluated_at=context.evaluated_at,
        permit_id=permit.permit_id,
        evidence_manifest_sha256=evidence_manifest_sha256,
        evidence_complete=evidence_complete,
        resolved_evidence_refs={
            "permit": permit_evidence.evidence_id if permit_evidence else None,
            "gas_test": gas_evidence.evidence_id if gas_evidence else None,
            "area_authority_approval": (
                approval_evidence.evidence_id if approval_evidence else None
            ),
            "confined_space_attendant": (
                attendant_evidence.evidence_id if attendant_evidence else None
            ),
        },
        derived_gas_test_age_minutes=derived_gas_test_age_minutes,
        findings=findings,
        proposed_response_actions=proposed_actions,
        compliance_boundary=(
            "Prototype evidence-completeness and conflict checks only. This response is not a legal determination, "
            "OISD/OSH&WC certification, safe-work authorisation, or substitute for current law, licensed standards and site procedures. "
            "The OSH&WC Code commenced on 21 November 2025 and section 143 repeals the Factories Act, 1948 subject to savings; "
            "applicability of saved instruments requires qualified review. The final Central Rules took effect on 8 May 2026, and "
            "the rules 23, 24 and 46 pointers here are scoped risk mappings, not a claim of a specific statutory PTW or hot-work rule."
        ),
        llm_used=False,
    )
