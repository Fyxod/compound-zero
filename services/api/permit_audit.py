"""Deterministic permit/evidence checks with bounded compliance language."""

from __future__ import annotations

import hashlib
import json

from .brief_schemas import (
    AuditFinding,
    AuditReference,
    PermitAuditRequest,
    PermitAuditResponse,
)

OISD_105 = AuditReference(
    source_id="OISD-STD-105-METADATA",
    title="OISD-STD-105 - Work Permit System (catalogue metadata only)",
    url="https://www.oisd.gov.in/en-in/oisd-standards-list",
    locator="OISD-STD-105; Aug 2023 edition listed",
    access_scope="PUBLIC_METADATA_ONLY",
)
FACTORIES_S36 = AuditReference(
    source_id="FACTORIES-ACT-1948-S36",
    title="The Factories Act, 1948 - Section 36",
    url="https://www.indiacode.nic.in/show-data?actid=AC_CEN_6_6_000010_194863_1517807319577&orderno=38",
    locator="Precautions against dangerous fumes, gases, etc.",
    access_scope="PUBLIC_LEGISLATION",
)
FACTORIES_S37 = AuditReference(
    source_id="FACTORIES-ACT-1948-S37",
    title="The Factories Act, 1948 - Section 37",
    url="https://www.indiacode.nic.in/handle/123456789/13657",
    locator="Explosive or inflammable dust, gas, etc.",
    access_scope="PUBLIC_LEGISLATION",
)
FACTORIES_S38 = AuditReference(
    source_id="FACTORIES-ACT-1948-S38",
    title="The Factories Act, 1948 - Section 38",
    url="https://www.indiacode.nic.in/handle/123456789/13657",
    locator="Precautions in case of fire",
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
    severity: str,
    title: str,
    evidence_refs: list[str],
    rationale: str,
    recommended_action: str,
    references: list[AuditReference],
) -> AuditFinding:
    return AuditFinding(
        finding_id=finding_id,
        severity=severity,  # type: ignore[arg-type]
        title=title,
        evidence_refs=sorted(set(evidence_refs)),
        rationale=rationale,
        recommended_action=recommended_action,
        references=references,
    )


def audit_permit(request: PermitAuditRequest) -> PermitAuditResponse:
    permit = request.permit
    context = request.context
    evidence_ids = {item.evidence_id for item in request.evidence}
    evidence_types = {item.evidence_type for item in request.evidence}
    base_refs = [item.evidence_id for item in request.evidence]
    findings: list[AuditFinding] = []

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

    if permit.status == "ACTIVE" and permit.area_authority_approval_ref is None:
        findings.append(
            _finding(
                "area-approval-evidence-missing",
                "HIGH",
                "Area-authority approval evidence is missing",
                base_refs,
                "The active permit payload contains no area-authority approval reference.",
                "Obtain and verify approval evidence using the authorised site workflow.",
                [OISD_105],
            )
        )

    atmosphere_work = permit.work_type in {"hot_work", "confined_space"}
    gas_evidence_present = (
        permit.gas_test_evidence_ref is not None
        and permit.gas_test_evidence_ref in evidence_ids
        and "gas_test" in evidence_types
    )
    if permit.status == "ACTIVE" and atmosphere_work and not gas_evidence_present:
        findings.append(
            _finding(
                "gas-test-evidence-missing",
                "HIGH",
                "Gas-test evidence cannot be resolved",
                base_refs,
                "The permit requires atmosphere context in this prototype, but its gas-test reference is absent from the submitted evidence manifest.",
                "Require competent human verification against the site-approved test procedure before proceeding.",
                [OISD_105, FACTORIES_S36 if permit.work_type == "confined_space" else FACTORIES_S37],
            )
        )
    elif atmosphere_work and permit.gas_test_age_minutes is not None and permit.gas_test_age_minutes > 30:
        findings.append(
            _finding(
                "gas-test-review-window-exceeded",
                "REVIEW",
                "Gas-test evidence exceeds the prototype review window",
                [permit.gas_test_evidence_ref] if permit.gas_test_evidence_ref else [],
                "The supplied gas test is older than the demo's configurable 30-minute review heuristic; this is not asserted as a statutory limit.",
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
                "The supplied conditions combine an ignition-source permit, barrier impairment, and a LEL ratio at or above the prototype's 0.35 review trigger. The trigger is analytic, not a legal exposure limit.",
                "Propose permit pause, worker withdrawal, and ventilation verification through human approval gates.",
                [OISD_105, FACTORIES_S37],
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
                "The supplied metadata reports occupancy and an oxygen-deficit ratio at or above the prototype's 0.15 review trigger. It does not establish a safe or unsafe statutory concentration.",
                "Escalate immediately to the competent person and area authority for manual site-procedure decisions.",
                [OISD_105, FACTORIES_S36],
            )
        )

    if permit.status == "ACTIVE" and permit.work_type == "confined_space" and not permit.attendant_evidence_ref:
        findings.append(
            _finding(
                "confined-space-attendant-evidence-missing",
                "HIGH",
                "Confined-space attendant evidence is missing",
                base_refs,
                "No attendant evidence reference was supplied for the active confined-space permit.",
                "Verify personnel and rescue arrangements against the approved site procedure.",
                [OISD_105, FACTORIES_S36],
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
                "A privacy-preserving observation reports an obstruction; a human must verify the physical condition.",
                "Dispatch an authorised verifier and use the approved emergency plan for any operational response.",
                [FACTORIES_S38],
            )
        )

    required_types = {"permit"}
    if permit.status == "ACTIVE" and atmosphere_work:
        required_types.add("gas_test")
    if permit.status == "ACTIVE":
        required_types.add("approval")
    evidence_complete = required_types.issubset(evidence_types)

    severities = {finding.severity for finding in findings}
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
        result=result,  # type: ignore[arg-type]
        evaluated_at=context.evaluated_at,
        permit_id=permit.permit_id,
        evidence_manifest_sha256=evidence_manifest_sha256,
        evidence_complete=evidence_complete,
        findings=findings,
        proposed_response_actions=proposed_actions,
        compliance_boundary=(
            "Prototype evidence-completeness and conflict checks only. This response is not a legal determination, "
            "OISD/Factories Act certification, safe-work authorisation, or substitute for licensed standards and site procedures."
        ),
        llm_used=False,
    )
