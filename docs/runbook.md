# Compound Zero Runbook

This runbook covers the local **SIMULATED** prototype. It does not authorize connection to a plant, safety system or real worker data.

## 1. Prerequisites

- Windows PowerShell.
- Python 3.11 or newer.
- Node.js compatible with Vite 8.
- pnpm 11.x (`package.json` declares `pnpm@11.9.0`).

Confirm the tools:

```powershell
python --version
node --version
pnpm --version
```

## 2. First-time setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
pnpm install
```

Using the virtual-environment interpreter directly avoids PowerShell activation-policy issues.

## 3. Verify checked-in artifacts

The service expects these files:

```text
artifacts/compound_zero_model.joblib
artifacts/metrics.json
artifacts/model_card.json
artifacts/robustness_metrics.json
artifacts/geospatial_metrics.json
data/scenario_bench/scenario_bench.csv
data/scenario_bench/metadata.json
```

Inspect the dataset receipt:

```powershell
Get-Content -Raw data\scenario_bench\metadata.json
Get-Content -Raw artifacts\model_card.json
```

Expected key values:

- Classification: `SIMULATED`.
- Dataset rows: `27648`.
- Seeds: `64`.
- Forecast horizon: `12` minutes.
- Model: `compound-zero-scenariobench-v1`.
- Dataset SHA-256: `96166a2762577a2fa8440e2a6f0f819c342aef9e9cf790e3ed2bef3eb6f4e314`.

The robustness artifact must also remain classified `SIMULATED`. Its expected headline values are base whole-seed event recall `1.0` (65/65), pooled scenario-type LOSO recall `0.8` (256/320), and held-out `process_drift` recall `0.0` (0/64). The latter is an explicit field-entry blocker, not a passing result.

## 4. Regenerate data, model and metrics

Run only when you intend to replace the checked-in generated artifacts:

```powershell
.\.venv\Scripts\python.exe -m ml.train
```

The run should regenerate the CSV/metadata, train and calibrate the process-only and full-fusion models, evaluate all three methods, and write the joblib/metrics/model-card artifacts.

After regeneration, run all tests and inspect the artifact diff. A change in dataset SHA, split, threshold or metric must be explained in the submission materials before it is accepted.

Regenerate the deterministic **SIMULATED** robustness artifact after the model and base metrics are frozen:

```powershell
.\.venv\Scripts\python.exe -m ml.robustness_bench --output artifacts\robustness_metrics.json
```

This runs nine scenario-type holdouts plus frozen-model missing-stream, packet-dropout and sensor-noise stresses. Expected diagnostics include pooled LOSO recall `0.8`, `process_drift` recall `0.0`, missing process/barrier-plus-shift recall `0.8`, and a false-alarm increase to `47.884615` episodes per simulated 24 hours under authored Gaussian `σ=0.05` noise. These values diagnose the current model; they are not field transfer, a production imputation policy or a safety guarantee.

Regenerate the independent **SIMULATED** geometry-conformance artifact without retraining the risk model:

```powershell
.\.venv\Scripts\python.exe -m ml.geospatial_bench --output artifacts\geospatial_metrics.json
```

The expected default artifact contains 337 boundary-heavy fictional cases, point-only versus uncertainty-aware exposure review metrics, and deterministic case/layout SHA-256 receipts. It is not surveyed-plant validation or a plume-physics result.

## 5. Start the backend

```powershell
.\.venv\Scripts\python.exe -m services.api.run
```

Expected listener: `http://127.0.0.1:8000`.

In a second PowerShell terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health | ConvertTo-Json -Depth 5
```

Healthy output has:

- `status: "ok"`
- `ready: true`
- `data_classification: "SIMULATED"`
- `llm_in_risk_path: false`
- a non-null model version

If `ready` is false, inspect `load_error` and confirm the artifact paths. To use a different artifact directory for a process:

```powershell
$env:COMPOUND_ZERO_ARTIFACT_DIR = "C:\absolute\path\to\artifacts"
.\.venv\Scripts\python.exe -m services.api.run
```

Do not point this variable at untrusted joblib files.

## 6. Exercise the API

### Model receipt

```powershell
Invoke-RestMethod http://127.0.0.1:8000/v1/model | ConvertTo-Json -Depth 8
```

### Benchmark metrics

```powershell
Invoke-RestMethod http://127.0.0.1:8000/v1/benchmark | ConvertTo-Json -Depth 12
```

### Scenario catalogue

```powershell
Invoke-RestMethod http://127.0.0.1:8000/v1/scenarios | ConvertTo-Json -Depth 8
```

### Deterministic compound-hot-work replay

```powershell
$replay = Invoke-RestMethod "http://127.0.0.1:8000/v1/scenarios/compound_hot_work/replay?seed=24001"
$replay.snapshots |
  Where-Object { $_.prediction_active -and -not $_.single_sensor_alarm } |
  Select-Object -First 5 minute, risk_score, severity, prediction_active, single_sensor_alarm
```

Calling the same URL with the same seed should return byte-equivalent logical content.

### Direct risk score

```powershell
$body = @{
  data_classification = "SIMULATED"
  scenario_id = "manual-smoke-001"
  lel_ratio = 0.62
  h2s_ratio = 0.48
  co_ratio = 0.51
  oxygen_deficit_ratio = 0.32
  pressure_ratio = 0.71
  lel_slope = 0.03
  h2s_slope = 0.02
  co_slope = 0.02
  oxygen_slope = 0.01
  pressure_slope = 0.02
  ventilation_impaired = $true
  hot_work_active = $true
  confined_space_active = $false
  workers_in_zone = 4
  min_worker_distance_m = 14
  shift_handover = $false
  permit_overlap_count = 2
  isolation_active = $false
  stream_quality = 1.0
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/v1/risk/score `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json -Depth 8
```

Repeat with `stream_quality = 0.5`; the response should set `abstained` to true and `prediction_active` to false.

### Metadata-only CCTV fusion

The endpoint accepts simulated analytics metadata, not frames or identities:

```powershell
$cctvBody = @{
  evaluation_time = "2026-07-22T10:01:00Z"
  target_zone_id = "ZONE-C7"
  process = ($body | ConvertFrom-Json)
  observations = @(
    @{
      observation_id = "obs-c7-001"
      observed_at = "2026-07-22T10:00:40Z"
      camera_ref = "CAM-C7"
      zone_id = "ZONE-C7"
      event_type = "unsafe_proximity"
      entity_count = 4
      min_hazard_distance_m = 6.5
      confidence = 0.94
    }
  )
} | ConvertTo-Json -Depth 8

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/v1/risk/score-with-cctv `
  -ContentType "application/json" `
  -Body $cctvBody | ConvertTo-Json -Depth 10
```

Adding `raw_media_included = $true`, `biometric_processing = $true` or `identity_tracking = $true` must produce HTTP 422.

### Cited incident-pattern retrieval

```powershell
Invoke-RestMethod http://127.0.0.1:8000/v1/intelligence/corpus | ConvertTo-Json -Depth 8

$patternBody = @{
  query = "hot work while extraction ventilation is impaired"
  context_signals = @("flammable gas trend", "workers in zone")
  top_k = 3
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/v1/intelligence/patterns `
  -ContentType "application/json" `
  -Body $patternBody | ConvertTo-Json -Depth 12
```

Verify `retrieval_method` is `LOCAL_BM25`, `generative_model_used` is false, and every returned pattern includes source metadata. A nonsense query can legitimately return an empty result.

### Permit/evidence audit

```powershell
$auditBody = @{
  permit = @{
    permit_id = "PTW-HOT-2041"
    work_type = "hot_work"
    zone_id = "ZONE-C7"
    status = "ACTIVE"
    valid_from = "2026-07-22T09:00:00Z"
    valid_until = "2026-07-22T12:00:00Z"
    overlapping_permit_ids = @("PTW-MECH-991")
  }
  context = @{
    evaluated_at = "2026-07-22T10:01:00Z"
    ventilation_impaired = $true
    lel_ratio = 0.62
    workers_in_zone = 4
    shift_handover = $true
  }
  evidence = @(
    @{
      evidence_id = "ev-permit-2041"
      evidence_type = "permit"
      permit_id = "PTW-HOT-2041"
      zone_id = "ZONE-C7"
      source_system = "SIMULATED PTW"
      observed_at = "2026-07-22T10:00:00Z"
    }
  )
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/v1/audit/permits `
  -ContentType "application/json" `
  -Body $auditBody | ConvertTo-Json -Depth 12
```

The output is a deterministic review, not a compliance or safe-work authorization. Check the evidence-manifest SHA-256, finding evidence references, public-source metadata and `compliance_boundary`.

### Human-gated response record

```powershell
$requestedAt = (Get-Date).ToUniversalTime()
$planBody = @{
  risk_case_id = "CASE-DEMO-$($requestedAt.Ticks)"
  requested_at = $requestedAt.ToString("o")
  severity = "elevated"
  actions = @("NOTIFY_SAFETY_TEAM")
  rationale = "Present the simulated risk case to the safety team for manual review."
} | ConvertTo-Json

$plan = Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/v1/response/plans `
  -ContentType "application/json" `
  -Body $planBody

$approvalBody = @{
  approver_ref = "simulated-safety-officer"
  approver_role = "SAFETY_OFFICER"
  decision = "APPROVE"
  decided_at = $requestedAt.AddSeconds(1).ToString("o")
  reason = "Reviewed the simulated evidence; manual execution only."
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/v1/response/plans/$($plan.plan_id)/approvals" `
  -ContentType "application/json" `
  -Body $approvalBody | ConvertTo-Json -Depth 8
```

The terminal status authorizes **manual execution only**. `actuation_performed` and `autonomous_shutdown_or_evacuation` must remain false. Records disappear when the API process restarts and approver references are not authenticated in this prototype.

Interactive OpenAPI documentation is available at <http://127.0.0.1:8000/docs>.

## 7. Start the web application

In a separate terminal:

```powershell
pnpm dev
```

Open <http://127.0.0.1:4173>.

The browser requests the deterministic model replay from `http://127.0.0.1:8000/v1/scenarios/compound_hot_work/replay?seed=24001`. Start the API first to run in **CALIBRATED MODEL API** mode. If the request fails, the application remains usable but visibly switches to **UX FALLBACK**. The UI does not currently post live ticks to `/v1/risk/score`; worker/permit animation and control projections remain client-side simulation.

Controls:

- `Space`: play or pause.
- `1`: Replay twin.
- `2`: Why now?.
- `3`: Intelligence.
- `4`: Model evidence.
- `5`: Safety case.
- Replay bar: scrub to a specific minute.
- Speed buttons: 1×, 2× or 4×.
- Reset: return to the initial replay state and clear completed dry-run controls.

## 8. Demo choreography

Use this sequence for a live review or recording. Keep the **SIMULATED** labels visible.

1. Open Command and state the thesis: independent alarms miss combinations; Compound Zero correlates process, permit, maintenance and exposure context.
2. Reset, play at 4×, and show extraction impairment, correlated gas movement, permit activation and worker movement on the map.
3. Pause when the priority banner appears. Point out that the configured device baseline remains clear and state the displayed lead—do not narrate a hard-coded number if the current screen differs.
4. Open **Explain this alert**. Walk left-to-right through signal/context → compound risk → controls, then show raw traces and the simulation disclosure.
5. Open **Model Evidence**. Compare the single-sensor, process-only and full-fusion rows, then show the robustness strip. Explicitly separate the 65/65 base whole-seed result from 256/320 pooled scenario-type LOSO recall, point out the 0/64 held-out `process_drift` failure, and call every result **simulated**.
6. Return to Command, open Response Studio, choose **Hold hot-work permit**, and compare current versus projected risk.
7. Approve the dry-run control. Explain that no real actuator exists and that process isolation would require two-person authorization through the existing plant workflow.
8. Open Safety Case and export the JSON pack. Say that the export is currently unsigned and the audit chain is production intent, not implemented tamper resistance.

Recommended phrasing:

> “This prototype proves the software and evaluation path on transparent simulation. The next evidence gate is a read-only, shadow-mode pilot with site calibration and safety review.”

Avoid:

- “Prevents 80% of accidents.”
- “OISD compliant” or “ISO certified.”
- “Real-time SCADA/CCTV integration” in the current build.
- “Autonomous evacuation/shutdown.”
- Treating a UI confidence label as field-calibrated probability.

## 9. Verification gates

### Backend

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The suite covers deterministic generation, compound events before device alarms, isolated device spikes, seed disjointness, model/baseline comparisons, deterministic scenario-type holdouts and stress artifacts, artifact creation, health/model metadata, poor-quality abstention, deterministic API replay, CCTV privacy/fusion, cited BM25 retrieval, bounded permit audits and locked multi-role response plans.

### Frontend

```powershell
pnpm test
pnpm typecheck
pnpm build
```

Do not describe the interface as browser-validated until the built application has also been exercised in a real browser at the target viewport. Static HTTP status and compilation are not interaction tests.

### Suggested manual browser checklist

- All five navigation items open without console errors.
- Play/pause, scrub, speed and reset behave correctly.
- The fused-risk state appears before the device baseline in the intended replay.
- Evidence factors and charts update with the selected tick.
- Each response option shows a projected score; an approved dry-run changes the replay state.
- Evidence export downloads valid JSON with a simulation disclosure.
- Layout remains usable at 1440×900 and a laptop-size viewport.
- Keyboard focus is visible and interactive elements have accessible names.
- No screen suggests live data, certification or autonomous plant control.

## 10. Troubleshooting

### API reports `model-unavailable` or `degraded`

- Confirm `artifacts/compound_zero_model.joblib` and `artifacts/metrics.json` exist.
- Run `python -m ml.train` with the same interpreter used to start the API.
- Inspect `/health` → `load_error`.
- Remove any incorrect `COMPOUND_ZERO_ARTIFACT_DIR` value from the current shell:

```powershell
Remove-Item Env:COMPOUND_ZERO_ARTIFACT_DIR -ErrorAction SilentlyContinue
```

### Port already in use

Identify the owner before stopping anything:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object LocalAddress, LocalPort, OwningProcess
Get-NetTCPConnection -LocalPort 4173 -State Listen | Select-Object LocalAddress, LocalPort, OwningProcess
```

Do not terminate a process unless you have confirmed it belongs to this workspace and is safe to stop.

### pnpm cannot write `.vite-temp` or TypeScript build-info files

- Stop duplicate Vite/Vitest/TypeScript processes for this repository after confirming ownership.
- Check whether antivirus, indexing or another shared process is holding `apps/web/node_modules` or `tsconfig.*.tsbuildinfo`.
- Re-run one frontend command at a time.
- Do not delete a broad workspace or shared package store as a first response.

### PowerShell will not activate `.venv`

Use the interpreter directly, as every command in this runbook does. Activation is optional.

## 11. Shutdown

Use `Ctrl+C` in each terminal running the local API or Vite development server. No persistent service or external resource is created by the documented commands.

## 12. Operational boundary

This runbook stops at a local, simulated prototype. A plant pilot requires the security and functional-safety gate in [security-safety.md](security-safety.md), the target deployment in [architecture.md](architecture.md), and site-owned operating procedures.
