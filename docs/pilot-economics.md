# Pilot economics evidence slice

> **ILLUSTRATIVE / SIMULATED — NOT A FACTUAL ROI CLAIM, FIELD RESULT, QUOTE, OR BUDGET.**

This sensitivity model answers a narrow question: if Compound Zero changes a defined set of safety-administration workflows by assumed amounts, what capacity and nuisance-downtime exposure could those changes represent? Every input is authored, visible, and editable. None is presented as observed customer performance.

## Decision view

All currency values are INR. The benefit-cost ratio is a simple, undiscounted three-year ratio. “Payback” means one-time implementation cost divided by annual quantified benefit after annual operating cost.

| Authored scenario | Annual quantified benefit | Annual net after operating cost | 3-year benefit / cost | Simple payback |
|---|---:|---:|---:|---:|
| Low / conservative | 38,008 | -261,992 | 0.07 | Not reached |
| Base / illustrative | 973,875 | 523,875 | 1.19 | 25.2 months |
| High / sensitivity bound | 3,975,157 | 3,275,157 | 3.06 | 6.6 months |

The low case is intentionally retained even though it is unattractive. The result shows that a small pilot with limited adoption does **not** support payback under these inputs. The base and high rows are sensitivity cases, not forecasts.

## Ethical and claim boundary

- The model assigns **no monetary value to a prevented death, injury, near miss, regulatory consequence, environmental event, property loss, or catastrophic shutdown**.
- It does not estimate incident frequency or claim that Compound Zero prevents any incident.
- “Downtime exposure” covers only authored administrative or nuisance holds. It is not avoided-incident value and is not guaranteed cash savings.
- Released staff time is a capacity equivalent. It becomes cash savings only if the operator can actually redeploy or avoid that cost.
- The calculations do not use the prototype’s simulated risk-model performance as a field benefit assumption.
- Tax, inflation, financing, depreciation, residual value, discounting, and risk adjustment are excluded.

## Editable inputs

The complete machine-readable inputs live under `inputs` in `artifacts/pilot_economics.json`. The three sets below vary site scale, workflow delta, adoption, and cost together to expose sensitivity.

| Input | Low | Base | High |
|---|---:|---:|---:|
| Operating days / year | 250 | 300 | 330 |
| Shifts / day | 2 | 3 | 3 |
| Safety alerts / shift | 2 | 4 | 6 |
| Active permits reconciled / shift | 3 | 6 | 10 |
| False-alarm deep reviews / shift | 0.8 | 2 | 3 |
| Closed investigations / year | 6 | 12 | 18 |
| Investigation team size | 2 | 3 | 4 |
| Alert triage, before → after (minutes) | 12 → 10 | 16 → 9 | 18 → 8 |
| Permit reconciliation, before → after (minutes) | 12 → 10 | 16 → 9 | 18 → 8 |
| Investigation cycle, before → after (hours) | 10 → 9 | 13 → 8 | 16 → 8 |
| False-alarm deep-review time (minutes) | 12 | 15 | 18 |
| False-alarm deep-review reduction | 15% | 40% | 55% |
| Nuisance holds avoided / year | 1 | 4 | 8 |
| Hours / nuisance hold | 0.25 | 0.50 | 0.75 |
| Nuisance-downtime exposure / hour | 25,000 | 50,000 | 100,000 |
| Loaded labor cost / person-hour | 650 | 850 | 1,100 |
| Workflow adoption | 50% | 75% | 85% |
| One-time implementation cost | 800,000 | 1,100,000 | 1,800,000 |
| Annual operating cost | 300,000 | 450,000 | 700,000 |

The evaluation horizon is three years in all three cases. The model currently reports INR only so mixed currencies cannot silently enter one result.

## Transparent arithmetic

For each scenario:

1. `annual shifts = operating days × shifts per day`
2. `annual workflow volume = annual shifts × workflow events per shift`
3. `triage hours released = annual alerts × (minutes before − minutes after) ÷ 60`
4. `permit hours released = annual permits × (minutes before − minutes after) ÷ 60`
5. `investigation person-hours released = investigations × (cycle hours before − cycle hours after) × team size`
6. `false-alarm review hours released = annual deep reviews × reduction fraction × review minutes ÷ 60`
7. `labor capacity value = released person-hours × loaded labor cost`
8. `nuisance-downtime exposure = holds avoided × hours per hold × exposure per hour`
9. `annual quantified benefit = (labor capacity + nuisance-downtime exposure) × workflow adoption`
10. `annual net = annual quantified benefit − annual operating cost`
11. `three-year benefit-cost ratio = (annual quantified benefit × 3) ÷ (one-time cost + annual operating cost × 3)`
12. `simple payback months = one-time cost ÷ positive annual net × 12`; otherwise payback is not reached.

Initial alert triage and false-alarm deep review are intentionally separate: triage is the first decision on every alert, while deep review is subsequent analysis on the subset considered false. Permit reconciliation and closed-investigation work are also separate workflows. A real pilot must verify that local process definitions do not overlap before combining benefits.

## Base-case audit trail

The base assumptions yield 900 shifts, 3,600 alert triages, 5,400 permit reconciliations, 1,800 false-alarm deep reviews, and 12 investigations per year. The raw workflow deltas are:

| Workflow | Annual delta | Realized value after 75% adoption |
|---|---:|---:|
| Initial alert triage | 420 person-hours | 267,750 INR |
| Permit reconciliation | 630 person-hours | 401,625 INR |
| Closed investigations | 60 calendar hours / 180 person-hours | 114,750 INR |
| False-alarm deep review | 720 reviews / 180 person-hours | 114,750 INR |
| Administrative nuisance holds | 2 hours | 75,000 INR |
| **Total** | **1,410 person-hours plus 2 hold-hours** | **973,875 INR** |

After 450,000 INR annual operating cost, the authored base case leaves 523,875 INR per year against 1,100,000 INR one-time implementation cost. That arithmetic produces 25.2 months simple payback and a 1.19 undiscounted three-year benefit-cost ratio. These are scenario outputs only.

## How a real pilot replaces assumptions

Before any procurement or ROI decision, define a baseline window and a shadow-mode pilot window of comparable duration, then replace each input with customer-approved evidence:

| Input family | Pilot evidence needed |
|---|---|
| Alert triage | Time-stamped alert queue, analyst start/close time, alert disposition, and blinded before/after sampling |
| Permit reconciliation | Permit and SIMOPS logs with reviewer time; exclude work already counted in alert triage |
| Investigation cycle | Case-open/case-close timestamps, actual participants, and person-hours—not just elapsed calendar time |
| False-alarm burden | Agreed false-alarm definition, adjudicated sample, review duration, and confidence interval |
| Nuisance holds | Approved hold taxonomy, start/end timestamps, and site finance’s marginal exposure—not headline revenue |
| Adoption | Eligible workflows versus workflows actually using the system, with exceptions recorded |
| Costs | Vendor quote, integration labor, infrastructure, training, change management, support, and recurring operations |

Safety performance must remain a separate pilot gate. A favorable workflow result cannot substitute for hazard review, calibration, human-factors assessment, cybersecurity testing, or field validation.

## Reproduce or edit

Generate the checked-in defaults:

```powershell
python -m ml.pilot_economics --output artifacts/pilot_economics.json
python -m pytest tests/backend/test_pilot_economics.py -q
```

To run a custom case, copy the generated artifact, edit any field under `inputs`, and regenerate. Existing `results` are ignored when the file is loaded:

```powershell
Copy-Item artifacts/pilot_economics.json tmp/pilot-economics-input.json
# Edit tmp/pilot-economics-input.json -> inputs
python -m ml.pilot_economics `
  --input-json tmp/pilot-economics-input.json `
  --output tmp/pilot-economics-custom.json
```

The generator validates non-negative finite values, fraction bounds, before/after ordering, currency, horizon, and scenario order. The artifact records a SHA-256 hash of the canonical editable inputs so a displayed result can be tied back to its exact assumption set.
