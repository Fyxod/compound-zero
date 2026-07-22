"""Deterministic, assumption-led pilot economics for Compound Zero.

The calculations in this module are an editable planning aid for a simulated
pilot.  They are not measured field results, an ROI forecast, or a claim that
Compound Zero prevents a particular incident.  Human injury and loss of life
are deliberately excluded from monetary valuation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


DATA_CLASSIFICATION = "ILLUSTRATIVE_SIMULATED"
METHOD_VERSION = "1.0.0"
SCENARIO_ORDER = ("low", "base", "high")


@dataclass(frozen=True, slots=True)
class ScenarioInputs:
    """One completely editable set of pilot planning assumptions."""

    key: str
    description: str
    annual_operating_days: int
    shifts_per_day: int
    safety_alerts_per_shift: float
    active_permits_reconciled_per_shift: float
    false_alarm_deep_reviews_per_shift: float
    investigations_per_year: float
    investigation_team_size: float
    alert_triage_minutes_before: float
    alert_triage_minutes_after: float
    permit_reconciliation_minutes_before: float
    permit_reconciliation_minutes_after: float
    investigation_cycle_hours_before: float
    investigation_cycle_hours_after: float
    false_alarm_deep_review_minutes: float
    false_alarm_deep_review_reduction_fraction: float
    nuisance_holds_avoided_per_year: float
    nuisance_hold_hours_each: float
    nuisance_downtime_exposure_inr_per_hour: float
    loaded_labor_cost_inr_per_person_hour: float
    workflow_adoption_fraction: float
    one_time_implementation_cost_inr: float
    annual_operating_cost_inr: float

    def validate(self) -> None:
        if self.key not in SCENARIO_ORDER:
            raise ValueError(f"scenario key must be one of {SCENARIO_ORDER}")
        if not self.description.strip():
            raise ValueError("scenario description cannot be empty")

        numeric_fields = {
            name: value
            for name, value in asdict(self).items()
            if name not in {"key", "description"}
        }
        for name, value in numeric_fields.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be numeric")
            if not math.isfinite(float(value)) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")

        for name, value in (
            ("annual_operating_days", self.annual_operating_days),
            ("shifts_per_day", self.shifts_per_day),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
        if self.annual_operating_days < 1 or self.shifts_per_day < 1:
            raise ValueError("annual operating days and shifts per day must be positive")
        for name, fraction in (
            (
                "false_alarm_deep_review_reduction_fraction",
                self.false_alarm_deep_review_reduction_fraction,
            ),
            ("workflow_adoption_fraction", self.workflow_adoption_fraction),
        ):
            if fraction > 1:
                raise ValueError(f"{name} must be between 0 and 1")

        before_after_pairs = (
            (
                "alert triage",
                self.alert_triage_minutes_before,
                self.alert_triage_minutes_after,
            ),
            (
                "permit reconciliation",
                self.permit_reconciliation_minutes_before,
                self.permit_reconciliation_minutes_after,
            ),
            (
                "investigation cycle",
                self.investigation_cycle_hours_before,
                self.investigation_cycle_hours_after,
            ),
        )
        for label, before, after in before_after_pairs:
            if after > before:
                raise ValueError(f"{label} after-time cannot exceed before-time")


@dataclass(frozen=True, slots=True)
class PilotEconomicsInputs:
    """Shared settings and the ordered low/base/high assumption sets."""

    currency: str
    horizon_years: int
    scenarios: tuple[ScenarioInputs, ...]

    def validate(self) -> None:
        if self.currency != "INR":
            raise ValueError("this evidence slice currently reports INR only")
        if isinstance(self.horizon_years, bool) or not isinstance(
            self.horizon_years, int
        ):
            raise TypeError("horizon_years must be an integer")
        if self.horizon_years < 1:
            raise ValueError("horizon_years must be a positive integer")
        if tuple(scenario.key for scenario in self.scenarios) != SCENARIO_ORDER:
            raise ValueError(f"scenarios must be ordered exactly as {SCENARIO_ORDER}")
        for scenario in self.scenarios:
            scenario.validate()


DEFAULT_INPUTS = PilotEconomicsInputs(
    currency="INR",
    horizon_years=3,
    scenarios=(
        ScenarioInputs(
            key="low",
            description="Conservative small-site pilot with limited adoption and modest workflow deltas.",
            annual_operating_days=250,
            shifts_per_day=2,
            safety_alerts_per_shift=2.0,
            active_permits_reconciled_per_shift=3.0,
            false_alarm_deep_reviews_per_shift=0.8,
            investigations_per_year=6.0,
            investigation_team_size=2.0,
            alert_triage_minutes_before=12.0,
            alert_triage_minutes_after=10.0,
            permit_reconciliation_minutes_before=12.0,
            permit_reconciliation_minutes_after=10.0,
            investigation_cycle_hours_before=10.0,
            investigation_cycle_hours_after=9.0,
            false_alarm_deep_review_minutes=12.0,
            false_alarm_deep_review_reduction_fraction=0.15,
            nuisance_holds_avoided_per_year=1.0,
            nuisance_hold_hours_each=0.25,
            nuisance_downtime_exposure_inr_per_hour=25_000.0,
            loaded_labor_cost_inr_per_person_hour=650.0,
            workflow_adoption_fraction=0.50,
            one_time_implementation_cost_inr=800_000.0,
            annual_operating_cost_inr=300_000.0,
        ),
        ScenarioInputs(
            key="base",
            description="Illustrative three-shift site with partial workflow adoption and moderate deltas.",
            annual_operating_days=300,
            shifts_per_day=3,
            safety_alerts_per_shift=4.0,
            active_permits_reconciled_per_shift=6.0,
            false_alarm_deep_reviews_per_shift=2.0,
            investigations_per_year=12.0,
            investigation_team_size=3.0,
            alert_triage_minutes_before=16.0,
            alert_triage_minutes_after=9.0,
            permit_reconciliation_minutes_before=16.0,
            permit_reconciliation_minutes_after=9.0,
            investigation_cycle_hours_before=13.0,
            investigation_cycle_hours_after=8.0,
            false_alarm_deep_review_minutes=15.0,
            false_alarm_deep_review_reduction_fraction=0.40,
            nuisance_holds_avoided_per_year=4.0,
            nuisance_hold_hours_each=0.50,
            nuisance_downtime_exposure_inr_per_hour=50_000.0,
            loaded_labor_cost_inr_per_person_hour=850.0,
            workflow_adoption_fraction=0.75,
            one_time_implementation_cost_inr=1_100_000.0,
            annual_operating_cost_inr=450_000.0,
        ),
        ScenarioInputs(
            key="high",
            description="Upside large-site case with broad adoption; it is a sensitivity bound, not a forecast.",
            annual_operating_days=330,
            shifts_per_day=3,
            safety_alerts_per_shift=6.0,
            active_permits_reconciled_per_shift=10.0,
            false_alarm_deep_reviews_per_shift=3.0,
            investigations_per_year=18.0,
            investigation_team_size=4.0,
            alert_triage_minutes_before=18.0,
            alert_triage_minutes_after=8.0,
            permit_reconciliation_minutes_before=18.0,
            permit_reconciliation_minutes_after=8.0,
            investigation_cycle_hours_before=16.0,
            investigation_cycle_hours_after=8.0,
            false_alarm_deep_review_minutes=18.0,
            false_alarm_deep_review_reduction_fraction=0.55,
            nuisance_holds_avoided_per_year=8.0,
            nuisance_hold_hours_each=0.75,
            nuisance_downtime_exposure_inr_per_hour=100_000.0,
            loaded_labor_cost_inr_per_person_hour=1_100.0,
            workflow_adoption_fraction=0.85,
            one_time_implementation_cost_inr=1_800_000.0,
            annual_operating_cost_inr=700_000.0,
        ),
    ),
)


def _rounded(value: float) -> float:
    return round(float(value) + 0.0, 2)


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def inputs_to_mapping(inputs: PilotEconomicsInputs) -> dict[str, Any]:
    """Return the editable inputs in a stable JSON-friendly shape."""

    inputs.validate()
    return {
        "currency": inputs.currency,
        "horizon_years": inputs.horizon_years,
        "scenarios": [asdict(scenario) for scenario in inputs.scenarios],
    }


def inputs_from_mapping(payload: Mapping[str, Any]) -> PilotEconomicsInputs:
    """Parse either a raw input mapping or this module's generated artifact."""

    raw: Any = payload.get("inputs", payload)
    if not isinstance(raw, Mapping):
        raise TypeError("inputs must be a JSON object")
    scenarios = raw.get("scenarios")
    if not isinstance(scenarios, list):
        raise TypeError("inputs.scenarios must be a JSON array")
    try:
        parsed = PilotEconomicsInputs(
            currency=raw["currency"],
            horizon_years=raw["horizon_years"],
            scenarios=tuple(ScenarioInputs(**item) for item in scenarios),
        )
    except KeyError as exc:
        raise ValueError(f"missing required input: {exc.args[0]}") from exc
    parsed.validate()
    return parsed


def evaluate_scenario(
    scenario: ScenarioInputs,
    *,
    horizon_years: int,
    currency: str = "INR",
) -> dict[str, Any]:
    """Apply transparent arithmetic to one illustrative assumption set."""

    scenario.validate()
    if horizon_years < 1:
        raise ValueError("horizon_years must be positive")

    annual_shifts = scenario.annual_operating_days * scenario.shifts_per_day
    annual_alerts = annual_shifts * scenario.safety_alerts_per_shift
    annual_permits = annual_shifts * scenario.active_permits_reconciled_per_shift
    annual_deep_reviews = annual_shifts * scenario.false_alarm_deep_reviews_per_shift

    triage_hours = annual_alerts * (
        scenario.alert_triage_minutes_before - scenario.alert_triage_minutes_after
    ) / 60
    permit_hours = annual_permits * (
        scenario.permit_reconciliation_minutes_before
        - scenario.permit_reconciliation_minutes_after
    ) / 60
    investigation_calendar_hours = scenario.investigations_per_year * (
        scenario.investigation_cycle_hours_before
        - scenario.investigation_cycle_hours_after
    )
    investigation_person_hours = (
        investigation_calendar_hours * scenario.investigation_team_size
    )
    avoided_deep_reviews = (
        annual_deep_reviews * scenario.false_alarm_deep_review_reduction_fraction
    )
    false_alarm_review_hours = (
        avoided_deep_reviews * scenario.false_alarm_deep_review_minutes / 60
    )

    labor_rate = scenario.loaded_labor_cost_inr_per_person_hour
    unadjusted_benefits = {
        "alert_triage_capacity_inr": triage_hours * labor_rate,
        "permit_reconciliation_capacity_inr": permit_hours * labor_rate,
        "investigation_capacity_inr": investigation_person_hours * labor_rate,
        "false_alarm_deep_review_capacity_inr": false_alarm_review_hours * labor_rate,
        "nuisance_downtime_exposure_inr": (
            scenario.nuisance_holds_avoided_per_year
            * scenario.nuisance_hold_hours_each
            * scenario.nuisance_downtime_exposure_inr_per_hour
        ),
    }
    unadjusted_total = sum(unadjusted_benefits.values())
    realized_benefits = {
        key: value * scenario.workflow_adoption_fraction
        for key, value in unadjusted_benefits.items()
    }
    annual_quantified_benefit = sum(realized_benefits.values())
    annual_net_after_operating_cost = (
        annual_quantified_benefit - scenario.annual_operating_cost_inr
    )
    horizon_benefit = annual_quantified_benefit * horizon_years
    horizon_cost = (
        scenario.one_time_implementation_cost_inr
        + scenario.annual_operating_cost_inr * horizon_years
    )
    horizon_net = horizon_benefit - horizon_cost
    benefit_cost_ratio = horizon_benefit / horizon_cost if horizon_cost else None
    simple_payback_months = (
        scenario.one_time_implementation_cost_inr
        / annual_net_after_operating_cost
        * 12
        if annual_net_after_operating_cost > 0
        else None
    )

    return {
        "scenario": scenario.key,
        "description": scenario.description,
        "data_classification": DATA_CLASSIFICATION,
        "annual_site_scale": {
            "operating_days": scenario.annual_operating_days,
            "shifts": annual_shifts,
            "safety_alerts_reviewed": _rounded(annual_alerts),
            "active_permits_reconciled": _rounded(annual_permits),
            "false_alarm_deep_reviews": _rounded(annual_deep_reviews),
            "investigations": _rounded(scenario.investigations_per_year),
        },
        "annual_workflow_deltas": {
            "alert_triage_person_hours_released": _rounded(triage_hours),
            "permit_reconciliation_person_hours_released": _rounded(permit_hours),
            "investigation_calendar_hours_reduced": _rounded(
                investigation_calendar_hours
            ),
            "investigation_person_hours_released": _rounded(
                investigation_person_hours
            ),
            "false_alarm_deep_reviews_avoided": _rounded(avoided_deep_reviews),
            "false_alarm_review_person_hours_released": _rounded(
                false_alarm_review_hours
            ),
            "nuisance_hold_hours_avoided": _rounded(
                scenario.nuisance_holds_avoided_per_year
                * scenario.nuisance_hold_hours_each
            ),
        },
        "annualized_quantified_benefit": {
            "currency": currency,
            "workflow_adoption_fraction": scenario.workflow_adoption_fraction,
            "unadjusted_total_inr": _rounded(unadjusted_total),
            "realized_components_inr": {
                key: _rounded(value) for key, value in realized_benefits.items()
            },
            "realized_total_inr": _rounded(annual_quantified_benefit),
            "interpretation": (
                "Illustrative capacity and nuisance-downtime exposure; not guaranteed cash savings."
            ),
        },
        "costs_and_indicators": {
            "currency": currency,
            "one_time_implementation_cost_inr": _rounded(
                scenario.one_time_implementation_cost_inr
            ),
            "annual_operating_cost_inr": _rounded(
                scenario.annual_operating_cost_inr
            ),
            "annual_net_after_operating_cost_inr": _rounded(
                annual_net_after_operating_cost
            ),
            "evaluation_horizon_years": horizon_years,
            "horizon_quantified_benefit_inr": _rounded(horizon_benefit),
            "horizon_total_cost_inr": _rounded(horizon_cost),
            "horizon_net_inr": _rounded(horizon_net),
            "undiscounted_benefit_cost_ratio": (
                _rounded(benefit_cost_ratio) if benefit_cost_ratio is not None else None
            ),
            "simple_payback_months": (
                _rounded(simple_payback_months)
                if simple_payback_months is not None
                else None
            ),
            "payback_interpretation": (
                "Not reached because annual quantified benefit does not exceed annual operating cost."
                if simple_payback_months is None
                else "Simple, undiscounted payback on one-time cost after annual operating cost."
            ),
        },
    }


def build_pilot_economics(
    inputs: PilotEconomicsInputs = DEFAULT_INPUTS,
) -> dict[str, Any]:
    """Build the deterministic low/base/high evidence artifact."""

    inputs.validate()
    editable_inputs = inputs_to_mapping(inputs)
    return {
        "artifact": "compound_zero_pilot_economics",
        "artifact_version": METHOD_VERSION,
        "data_classification": DATA_CLASSIFICATION,
        "purpose": (
            "Editable sensitivity analysis for pilot planning; not a factual ROI claim or field result."
        ),
        "boundaries": {
            "human_harm_valuation_included": False,
            "prevented_incidents_claimed": False,
            "field_performance_claimed": False,
            "cash_savings_guaranteed": False,
            "downtime_scope": (
                "Administrative or nuisance holds only; excludes injury, fatality, property, "
                "environmental, regulatory, and catastrophic-loss valuation."
            ),
            "double_counting_control": (
                "Initial alert triage, subsequent false-alarm deep review, permit administration, "
                "and closed-investigation work are modelled as distinct workflows."
            ),
            "finance_scope": (
                "Simple undiscounted arithmetic; excludes tax, inflation, financing, depreciation, "
                "residual value, and risk adjustment."
            ),
        },
        "inputs": editable_inputs,
        "input_manifest_sha256": hashlib.sha256(
            _canonical_json_bytes(editable_inputs)
        ).hexdigest(),
        "results": [
            evaluate_scenario(
                scenario,
                horizon_years=inputs.horizon_years,
                currency=inputs.currency,
            )
            for scenario in inputs.scenarios
        ],
    }


def write_pilot_economics(
    path: Path,
    inputs: PilotEconomicsInputs = DEFAULT_INPUTS,
) -> Path:
    """Write a stable, human-readable JSON artifact."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_pilot_economics(inputs)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _load_inputs(path: Path) -> PilotEconomicsInputs:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise TypeError("input JSON must contain an object")
    return inputs_from_mapping(payload)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Generate the illustrative Compound Zero pilot economics artifact."
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        help=(
            "Optional editable input JSON. A generated artifact is accepted directly because "
            "its 'inputs' object is self-contained."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "artifacts" / "pilot_economics.json",
    )
    parser.add_argument("--print", action="store_true", dest="print_payload")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    inputs = _load_inputs(args.input_json) if args.input_json else DEFAULT_INPUTS
    output = write_pilot_economics(args.output, inputs)
    if args.print_payload:
        print(output.read_text(encoding="utf-8"), end="")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
