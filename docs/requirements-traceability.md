# PS1 Requirements Traceability

This matrix maps the complete **AI-Powered Industrial Safety Intelligence for Zero-Harm Operations** brief to repository evidence. It distinguishes working code from visual simulation and planned work.

## Status legend

| Status | Meaning |
|---|---|
| **Implemented** | Working code or generated artifact exists and is directly inspectable. |
| **Simulated** | Working behavior exists, but its inputs/outcomes are authored demo data rather than live plant integration. |
| **Partial** | A bounded subset exists; the missing part is stated. |
| **Not implemented** | No working implementation is present. It is not claimed in the pitch. |

## Challenge-statement inputs

| Brief requirement | Status | Repository evidence | Exact boundary / next gate |
|---|---|---|---|
| Bring IoT sensor data into one layer | **Partial / simulated** | Five normalized level channels and slopes in `ml/features.py`; typed scoring contract in `services/api/schemas.py`; animated sensor panel in `apps/web` | No MQTT, OPC UA, historian or device connector; no live ingestion or event-time alignment |
| Bring SCADA data into one layer | **Partial / simulated** | Process-level and trend features; UI identifies simulated SCADA provenance | No SCADA adapter or authorized historian data; provenance rows are demo fixtures |
| Bring permit-to-work logs into one layer | **Partial / simulated** | Hot-work, confined-space and permit-overlap features; `PTW-2841`/`PTW-2837` replay; response-studio permit hold | No PTW-system connector, document parser, signature verification or issuer workflow |
| Bring CCTV feeds into one layer | **Partial / simulated** | `/v1/risk/score-with-cctv` validates recent same-zone anonymous event metadata and maps counts, distance and confidence into the same numeric model. Raw media, biometrics and identity tracking are rejected | No feed connector, decoder or CV model; requires authorized video, camera governance and measured CV/privacy evaluation |
| Bring shift records into one layer | **Partial / simulated** | `shift_handover` and `handover_permit_interaction` features; compound handover scenario | No roster/shift-system adapter or identity policy |
| Bring maintenance records into one layer | **Partial / simulated** | `ventilation_impaired`, `isolation_active`, barrier interaction, EF-04 maintenance replay | No CMMS adapter, work-order validation or asset master-data reconciliation |
| Detect compound risks no single sensor flags | **Implemented on simulated data** | Full-fusion calibrated model; engineered interaction features; deterministic compound scenarios; API factors; browser evidence graph | Must be recalibrated and shadow-validated on authorized site data |
| Trigger pre-emptive interventions | **Partial / simulated** | Response Studio proposes permit hold, extraction restoration, evacuation and isolation; projected scores; operator dry-run action | No notification gateway, emergency channel, access control or plant actuation. Consequential actions must remain human-gated |

## Suggested build areas

| Suggested area | Status | What exists | What does not exist |
|---|---|---|---|
| Compound Risk Detection Engine | **Implemented on simulated data** | Calibrated histogram gradient boosting, process/work-context interactions, single-device and process-only baselines, event/row evaluation, nine-fold scenario-type LOSO and frozen-model stress suite | LOSO exposes a `process_drift` transfer failure (0/64 detected); multi-site validation, online windows, drift monitoring and production MLOps remain absent |
| Geospatial Safety Heatmap | **Implemented on simulated geometry** | Plant-layout SVG plus `ml/geospatial_bench.py`: four fictional site-local polygons, point-in-polygon, nearest authored hazard distance, bounded localization uncertainty and conservative exposure classification; exact artifact in `artifacts/geospatial_metrics.json` | Benchmark is boundary-heavy authored software-conformance data. No GIS connector, surveyed coordinates, plume physics, localization hardware or field geospatial accuracy claim |
| Incident Pattern Intelligence / RAG | **Partial / implemented retrieval** | Deterministic local BM25 over five project-authored, source-attributed patterns; corpus/version/SHA endpoint; cited results; no-match behavior; no generator | Not generative/vector RAG; small reference corpus, no site incident archive, embeddings or retrieval-quality benchmark |
| Digital Permit Intelligence Agent | **Partial / simulated** | Structured permit/context correlation; deterministic evidence-completeness and conflict audit with cited findings; operator-approved dry-run hold | No PTW connector/NLP, agent, procedure reasoning, verified identity or approval-system writeback |
| Emergency Response Orchestrator | **Partial / simulated** | UI response studio plus API response plans with action-dependent role gates, one-decision-per-role locking and manual-only authorization | In-memory/unauthenticated only; no notification, responder dispatch, procedure engine, durable workflow, report generator or actuation |
| Quality & Compliance Audit Agent | **Partial / deterministic checklist** | Permit/evidence checks, canonical SHA-256 manifest receipt, public reference metadata, JSON evidence-pack demo | No continuous connector, licensed normative corpus, control-coverage measure, legal determination, corrective-action lifecycle or certification |

The examples in the brief are illustrative, not a requirement to implement every agent. Compound Zero prioritizes the stated evaluation focus: a defensible compound-risk engine, lead-time proof, false-negative comparison, geospatial demonstration and safe response workflow.

## Suggested technologies

| Suggested technology | Status | Evidence / rationale |
|---|---|---|
| Agentic AI / multi-agent systems | **Not implemented by design** | The safety decision is a calibrated numeric model. Adding agents would not improve the current proof and could blur accountability. |
| Geospatial intelligence and plant-layout analytics | **Implemented on simulated geometry** | Custom SVG plus deterministic plant-local polygon/distance engine and reproducible GeoEvidenceBench artifact. Review radii are authored analytic thresholds, not physical contours. |
| RAG over incident and regulatory corpora | **Partial** | Local cited BM25 retrieval over five project-authored reference patterns; no generative model or normative full text. |
| Computer vision and CCTV analytics | **Interface only / simulated** | Privacy-preserving analytics-metadata schema and fusion path are implemented and tested; no image/video model or feed. |
| IoT / SCADA data integration | **Partial** | Typed normalized signal contract and simulated data; no protocol connector. |
| Knowledge graph | **Partial / visual** | Typed evidence nodes/edges communicate equipment-permit-risk relationships; no persistent temporal graph database or graph inference engine. |

## Expected deliverables

| Deliverable | Status | Location / note |
|---|---|---|
| Working prototype | **Implemented** | React command centre plus FastAPI/model service; run them independently using `docs/runbook.md` |
| Architecture diagram | **Implemented** | `docs/architecture.md` |
| Presentation deck | **Outside this trace at time of writing** | Must be verified in the final submission package before upload |
| 3–4 minute demo video | **Production package in progress** | Locked script/storyboard and encoding guide exist in `docs/demo-video-script.md`, `docs/demo-storyboard.md` and `video/README.md`; final MP4 must be verified before upload |

## Evaluation focus

| Evaluation item | Status | Evidence | Limitation |
|---|---|---|---|
| Compound-risk accuracy versus single-sensor baseline | **Implemented on simulated data** | Held-out event recall: full fusion `1.00`, device baseline `0.20`; row average precision: `0.997` vs `0.813` | Authored scenarios; not field performance |
| Prediction lead time before incident threshold | **Implemented on simulated data** | Median held-out lead: full fusion `12 min`, device baseline `5 min` | Lead is relative to authored ScenarioBench event timing |
| Robustness / scenario-family transfer | **Measured on simulated diagnostic tests** | Nine-fold scenario-type LOSO: pooled event recall `0.800` (256/320) across five event-bearing folds; held-out `process_drift` recall `0.000` (0/64). Missing process or barrier-plus-shift streams each reduce base-holdout recall to `0.800` (52/65). Gaussian `σ=0.05` noise preserves event recall but raises false-alarm episodes from `1.153846` to `47.884615` per simulated 24 h | One authored generator is not a proxy for real distribution shift. Missing-value substitutions are diagnostic, not a production failure policy. The `process_drift` miss and alert-load sensitivity are explicit blockers for field use |
| Geospatial evidence quality | **Measured on simulated conformance fixtures** | GeoEvidenceBench: 337 boundary-heavy cases; uncertainty-aware review recall `1.000` versus point-only `0.816`, FNR `0.000` versus `0.184`, certain-exposure precision `1.000`, nearest-hazard distance MAE `0.907 m`; case/layout SHA-256 receipts | Authored fictional geometry whose declared error bounds contain the simulated truth; conservative review FPR is `0.454` versus `0.168` point-only. Not surveyed validation, representative prevalence, probabilistic confidence or plume physics |
| Regulatory compliance coverage | **Metadata only** | OISD catalogue, India Code and ISO overview links | No normative corpus, control-by-control coverage or certification claim |
| False-negative reduction | **Implemented on simulated data** | Event FNR `0.00` for full fusion versus `0.80` for device baseline: `0.80` absolute reduction | Test contains 65 authored event groups |

## Judging-criteria coverage

| Criterion | Weight | Compound Zero evidence | Remaining proof needed |
|---|---:|---|---|
| Innovation | 25% | Compound interaction detection, explicit baselines, model-replay-backed UI, evidence graph, metadata-only CCTV fusion, cited retrieval and counterfactual dry-run controls | Move live scoring and counterfactual evaluation fully server-side |
| Business impact | 25% | Earlier intervention story, reduced false-negative and false-alarm burden metrics, auditable workflow | Quantified site economics and pilot feedback, clearly labelled assumptions |
| Technical excellence | 20% | Reproducible generator, disjoint split, separate calibration, persisted model/API, true scenario-type holdouts, frozen-model missing/noise stresses, fixed-seed UI integration, strict privacy metadata contract, cited retrieval, deterministic audit/approval gates and tests | Resolve the published unseen-`process_drift` miss; add live connectors, performance/security tests and real-data evaluation |
| Scalability | 15% | Versioned artifacts and stateless inference foundation; site-local scale architecture | Load test, event bus, model registry, deployment automation and SLOs |
| User experience | 15% | Five polished workspaces, replay controls, evidence drill-down, cross-system intelligence, response studio and evidence export | Accessibility audit, operator usability test and production data receipts |

## Actual evaluation artifact

Source: `artifacts/metrics.json`, model version `compound-zero-scenariobench-v1`.

| Method | Event recall | Event FNR | Earlier than device, among 13 device-alarm groups | Detected among 52 no-device-alarm groups | Median lead | False alarms / simulated 24 h | Average precision | Brier |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Single sensor | 0.200 | 0.800 | 0.000 | 0.000 | 5 min | 7.500 | 0.8131 | 0.2421 |
| Process only | 1.000 | 0.000 | 1.000 | 1.000 | 12 min | 8.6538 | 0.9467 | 0.0701 |
| Full fusion | 1.000 | 0.000 | 1.000 | 1.000 | 12 min | 1.1538 | 0.9970 | 0.0146 |

The device comparison window ends at each authored harmful-state onset: 13 of 65 event groups have a device alarm by then, while 52 have none. The two rates above are intentionally separated instead of folding “no device alarm” into “detected earlier.” Full fusion's event false-negative improvement versus the device baseline is **80 percentage points**. Its false-alarm improvement versus process-only is **7.5 episodes per simulated 24 hours** (approximately 86.7% relative).

### Robustness artifact

Source: `artifacts/robustness_metrics.json`. Every row is an authored **SIMULATED ScenarioBench diagnostic**.

| Diagnostic | Event recall | Detected / event groups | Median lead | False alarms / simulated 24 h | Interpretation |
|---|---:|---:|---:|---:|---|
| Frozen model, base whole-seed holdout | 1.000 | 65 / 65 | 12 min | 1.153846 | Base result only; not evidence of site transfer |
| Scenario-type LOSO, pooled | 0.800 | 256 / 320 | 12 min | 8.671875 | Each scenario type is absent from fitting and threshold calibration; pooled across five event-bearing folds |
| Scenario-type LOSO, `process_drift` fold | 0.000 | 0 / 64 | — | — | Known unseen-family failure; blocks deployment claims |
| Missing process-sensor stream | 0.800 | 52 / 65 | 12 min | 7.500000 | Diagnostic neutral-value substitution, not a production imputation policy |
| Missing barrier + shift stream | 0.800 | 52 / 65 | 7 min | 1.153846 | Diagnostic neutral-value substitution, not a production imputation policy |
| Gaussian sensor noise, `σ=0.05` | 1.000 | 65 / 65 | 12 min | 47.884615 | Recall survives while review burden increases sharply |

The base model's 65/65 result and LOSO's 256/320 result answer different questions and must never be merged into one “accuracy” claim. LOSO is still bounded to the same authored generator; it is stronger synthetic evidence, not field validation.

## Verified claim corrections

The organiser brief is authoritative for what to build, but not every contextual claim is supported by the cited primary material.

| Brief statement | Verification | Submission rule |
|---|---|---|
| Eight deaths at Visakhapatnam Steel Plant in January 2025 in a coke-oven gas event | The official [Ministry of Steel release](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2270473&lang=1&reg=48) confirms eight deaths and six injuries on 8 June 2026 after an explosion and fireball during casting at Caster-2, Steel Melt Shop-1. It records preliminary findings rather than a final root-cause determination. | Use the verified date, location and conservative wording. Do not repeat the January 2025/coke-oven narrative. |
| More than 6,500 fatal workplace accidents in FY2023, attributed to DGFASLI | The [DGFASLI Standard Reference Note 2024](https://dgfasli.gov.in/public/Admin/Cms/AllPdf/685e62eb37da23.32721872.pdf) factory table does not support that number. | Do not use the statistic without a primary source with matching scope, definition and period. |

## Definition of done for a field pilot

The prototype is not field-ready until all of the following are satisfied:

- Authorized site data and schemas with documented provenance and retention.
- Read-only historian, PTW and CMMS adapters with event-time/freshness tests.
- Site-specific thresholds, calibration and held-out shadow-mode evaluation.
- Demonstrated recovery from the published unseen-`process_drift` failure plus approved behavior for missing critical streams and sensor-noise alert floods.
- Hazard analysis and sign-off from plant safety, controls and operations owners.
- Independent physical alarms/SIS path verified unaffected by AI failure.
- Authenticated roles, dual approval for high-impact workflows and no model-to-actuator shortcut.
- Signed, durable and redacted evidence storage with tested incident retrieval.
- Cybersecurity review, network segmentation, failover/recovery exercises and operational runbooks.
- Regulatory/licensing review using authorized normative text; no certification inferred from metadata mapping.
