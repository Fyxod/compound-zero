from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from ml.pilot_economics import (
    DATA_CLASSIFICATION,
    DEFAULT_INPUTS,
    PilotEconomicsInputs,
    build_pilot_economics,
    inputs_from_mapping,
    inputs_to_mapping,
    write_pilot_economics,
)


def _result(payload: dict[str, object], key: str) -> dict[str, object]:
    results = payload["results"]
    assert isinstance(results, list)
    return next(result for result in results if result["scenario"] == key)


def test_artifact_is_explicitly_illustrative_and_excludes_human_harm_valuation() -> None:
    payload = build_pilot_economics()

    assert payload["data_classification"] == DATA_CLASSIFICATION
    assert "not a factual ROI claim" in payload["purpose"]
    assert payload["boundaries"]["human_harm_valuation_included"] is False
    assert payload["boundaries"]["prevented_incidents_claimed"] is False
    assert payload["boundaries"]["field_performance_claimed"] is False
    assert "Administrative or nuisance holds only" in payload["boundaries"]["downtime_scope"]
    assert [result["scenario"] for result in payload["results"]] == [
        "low",
        "base",
        "high",
    ]


def test_base_case_arithmetic_is_transparent_and_reproducible() -> None:
    base = _result(build_pilot_economics(), "base")

    assert base["annual_site_scale"] == {
        "operating_days": 300,
        "shifts": 900,
        "safety_alerts_reviewed": 3_600.0,
        "active_permits_reconciled": 5_400.0,
        "false_alarm_deep_reviews": 1_800.0,
        "investigations": 12.0,
    }
    assert base["annual_workflow_deltas"] == {
        "alert_triage_person_hours_released": 420.0,
        "permit_reconciliation_person_hours_released": 630.0,
        "investigation_calendar_hours_reduced": 60.0,
        "investigation_person_hours_released": 180.0,
        "false_alarm_deep_reviews_avoided": 720.0,
        "false_alarm_review_person_hours_released": 180.0,
        "nuisance_hold_hours_avoided": 2.0,
    }
    benefit = base["annualized_quantified_benefit"]
    assert benefit["unadjusted_total_inr"] == 1_298_500.0
    assert benefit["realized_total_inr"] == 973_875.0
    assert benefit["workflow_adoption_fraction"] == 0.75

    indicators = base["costs_and_indicators"]
    assert indicators["annual_net_after_operating_cost_inr"] == 523_875.0
    assert indicators["horizon_quantified_benefit_inr"] == 2_921_625.0
    assert indicators["horizon_total_cost_inr"] == 2_450_000.0
    assert indicators["horizon_net_inr"] == 471_625.0
    assert indicators["undiscounted_benefit_cost_ratio"] == 1.19
    assert indicators["simple_payback_months"] == 25.2


def test_range_preserves_downside_instead_of_forcing_positive_payback() -> None:
    payload = build_pilot_economics()
    low = _result(payload, "low")["costs_and_indicators"]
    base = _result(payload, "base")["costs_and_indicators"]
    high = _result(payload, "high")["costs_and_indicators"]

    assert low["annual_net_after_operating_cost_inr"] < 0
    assert low["simple_payback_months"] is None
    assert base["undiscounted_benefit_cost_ratio"] == 1.19
    assert high["undiscounted_benefit_cost_ratio"] == 3.06
    assert high["simple_payback_months"] == 6.6


def test_every_input_round_trips_and_callers_can_replace_assumptions() -> None:
    editable = inputs_to_mapping(DEFAULT_INPUTS)
    assert inputs_from_mapping(editable) == DEFAULT_INPUTS

    base = DEFAULT_INPUTS.scenarios[1]
    custom_base = replace(
        base,
        workflow_adoption_fraction=0.50,
        loaded_labor_cost_inr_per_person_hour=1_000.0,
        one_time_implementation_cost_inr=1_250_000.0,
    )
    custom_inputs = replace(
        DEFAULT_INPUTS,
        scenarios=(DEFAULT_INPUTS.scenarios[0], custom_base, DEFAULT_INPUTS.scenarios[2]),
    )
    custom_payload = build_pilot_economics(custom_inputs)

    assert custom_payload["inputs"]["scenarios"][1]["workflow_adoption_fraction"] == 0.50
    assert _result(custom_payload, "base")["annualized_quantified_benefit"][
        "realized_total_inr"
    ] != _result(build_pilot_economics(), "base")["annualized_quantified_benefit"][
        "realized_total_inr"
    ]


def test_invalid_assumptions_fail_closed() -> None:
    base = DEFAULT_INPUTS.scenarios[1]
    with pytest.raises(ValueError, match="between 0 and 1"):
        replace(base, workflow_adoption_fraction=1.01).validate()
    with pytest.raises(ValueError, match="after-time cannot exceed"):
        replace(
            base,
            alert_triage_minutes_before=5.0,
            alert_triage_minutes_after=6.0,
        ).validate()
    with pytest.raises(ValueError, match="ordered exactly"):
        PilotEconomicsInputs(
            currency="INR",
            horizon_years=3,
            scenarios=tuple(reversed(DEFAULT_INPUTS.scenarios)),
        ).validate()
    with pytest.raises(TypeError, match="horizon_years must be an integer"):
        replace(DEFAULT_INPUTS, horizon_years=3.5).validate()
    with pytest.raises(TypeError, match="annual_operating_days must be an integer"):
        replace(base, annual_operating_days=300.5).validate()


def test_checked_in_artifact_matches_generator_byte_for_byte(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    write_pilot_economics(first)
    write_pilot_economics(second)
    assert first.read_bytes() == second.read_bytes()

    checked_in = Path(__file__).resolve().parents[2] / "artifacts" / "pilot_economics.json"
    assert checked_in.read_bytes() == first.read_bytes()
    parsed = json.loads(checked_in.read_text(encoding="utf-8"))
    assert len(parsed["input_manifest_sha256"]) == 64
    assert inputs_from_mapping(parsed) == DEFAULT_INPUTS
