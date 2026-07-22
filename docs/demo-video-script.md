# Compound Zero — 3:40 demo film script

**Working title:** *Compound Zero — See the Accident Before the Alarm*  
**Locked duration:** 03:40 (220 seconds)  
**Format:** product film with live, cursor-driven prototype capture  
**Primary audience:** ET AI Hackathon judges  

## Truth rules for the final cut

- Keep this lower-third visible from 00:12 through 03:36, then repeat it on the end card through 03:40: **SIMULATED DATA · PROTOTYPE · NOT FIELD VALIDATION**.
- The authoritative model-backed replay first alerts at **T+09**, **13 minutes before the authored simulated harmful-state onset at T+22**. Do not call T+22 a device-alarm threshold: no individual device alarm fires anywhere in this 48-minute replay.
- Advance to **T+18** for the compound-risk explanation: hot work is active, four workers are in-zone, the model score is 100, all device alarms remain clear, and four minutes remain before the authored harmful state.
- Say **12-minute median warning lead** only for ScenarioBench's held-out positive event replays. Do not imply that every scenario receives 12 minutes.
- Say **100% event recall across 65 held-out simulated event replays**, never “100% accurate,” “zero accidents,” or “field proven.” Row-level recall is 99.804%, and four positive rows were missed.
- Always identify 65/65 as the **base whole-seed holdout**. The harder nine-fold scenario-type LOSO result is **256/320 pooled events (80%)**, including **0/64 held-out `process_drift` events**. Do not merge the two results.
- Missing process or barrier-plus-shift streams each reduce simulated event recall to **52/65 (80%)**. Authored `σ=0.05` noise keeps 65/65 event recall but raises false-alarm episodes from **1.15 to 47.88 per simulated 24 hours**; say that recall and alert load moved differently.
- Say and show **0.997 AUPRC**; never round it to “1.00” or call it perfect.
- Controls shown are a **simulated dry-run requiring human approval**. Compound Zero does not autonomously evacuate workers or isolate equipment.
- The Intelligence workspace uses one unified simulated case, metadata-only CCTV events, local source-attributed BM25 retrieval, deterministic permit checks and a manual-only response plan. It does not ingest raw video, make a legal compliance determination or execute the plan.
- Record only while the interface identifies its engine as **CALIBRATED MODEL API**. The UI has an explicit UX fallback, but fallback footage must not be used for the judged demo.
- References to OISD, the current OSH&WC Code, and ISO 45001 are traceability mappings, not certification or complete compliance coverage. The repealed Factories Act appears only where legacy/saved material must be reviewed by a qualified owner.

## Exact voiceover and on-screen copy

### 00:00–00:12 — Cold open (12s)

**Voiceover**  
“Every device says safe. Extraction is down, hot work is active, and four people enter the gas corridor. Compound Zero connects the weak signals before disaster.”

**On-screen text**

- 00:00: `EVERY ALARM: CLEAR`
- 00:04: `THE SYSTEM IS NOT SAFE.`
- 00:08: `COMPOUND ZERO`
- 00:10: `See the accident before the alarm.`

### 00:12–00:32 — The product thesis (20s)

**Voiceover**  
“Industrial sites already have sensors, permits, maintenance systems, and worker-location data. The blind spot is between them. Compound Zero is a predictive safety layer that turns fragmented evidence into an explainable, human-gated safety case.”

**On-screen text**

- Persistent disclosure begins: `SIMULATED DATA · PROTOTYPE · NOT FIELD VALIDATION`
- Four inputs animate in: `SCADA` · `PERMITS` · `CMMS` · `WORKER LOCATION`
- Resolve to: `ONE TEMPORAL SAFETY GRAPH`

### 00:32–01:05 — Deterministic incident replay (33s)

**Voiceover**  
“This is a deterministic, model-backed simulated replay at Coke Battery Four. Extraction fan EF-zero-four is isolated for maintenance. Gas channels begin rising together. Then a hot-work permit becomes active nearby, and four contractor badges enter the exposure contour.”

**On-screen text**

- `DETERMINISTIC MODEL REPLAY · SEED 24001`
- `EF-04 EXTRACTION: IMPAIRED`
- `PTW-2841 HOT WORK: ACTIVE`
- `4 PSEUDONYMIZED BADGES ENTER CONTOUR`
- Small footer: `No real worker or plant data is shown.`

### 01:05–01:32 — The warning grows with the evidence (27s)

**Voiceover**  
“Fusion first crosses its intervention threshold at T-plus nine—thirteen minutes before the authored harmful state at T-plus twenty-two. Every device alarm is clear. By T-plus eighteen, hot work and four workers expand the evidence; the model score reaches one hundred with four minutes remaining. Combustible gas is still about eight-point-six percent LEL against a twenty-percent threshold.”

**On-screen text**

- `COMPOUND RISK CASE CZ-2026-071`
- `INITIAL ALERT T+09 · 13 MIN TO SIMULATED HARMFUL STATE`
- `T+18 · HOT WORK + 4 WORKERS · RISK 100 · 4 MIN REMAIN`
- `0 INDIVIDUAL DEVICE ALARMS`
- Fine print: `Replay-specific result; not a field-performance claim.`

### 01:32–02:03 — Explainability that an operator can audit (31s)

**Voiceover**  
“The alert is not a generated story. Its evidence graph links the correlated gas trend to the impaired extraction barrier, the ignition-source permit, and exposed people. Every input carries a timestamp and source receipt. The risk path is a calibrated gradient-boosting model with structured evidence—not an LLM.”

**On-screen text**

- `WHY NOW?`
- `SIGNAL + BARRIER + IGNITION + EXPOSURE`
- `NO LLM IN THE RISK PATH`
- `TIMESTAMPED · SOURCE-TRACEABLE · REVIEWABLE`

### 02:03–02:25 — Human-gated counterfactual (22s)

**Voiceover**  
“Compound Zero proposes controls and previews a non-causal simulated estimate. The safety officer selects Hold Hot-Work Permit, sees risk project from one hundred to seventy-one, and records a dry run. Residual risk stays visible. No field action is executed, and existing alarms and safety-instrumented systems remain independent.”

**On-screen text**

- `MACHINE PROPOSES. PEOPLE AUTHORIZE.`
- `HOLD PTW-2841 · SIMULATED DRY RUN`
- `100 → 71 PROJECTED RISK` (use the values visible at T+18)
- `PHYSICAL ALARMS / SIS REMAIN INDEPENDENT`

### 02:25–02:48 — Cross-system intelligence and authority (23s)

**Voiceover**  
“The same simulated case then passes through four bounded services: anonymous CCTV event metadata, numeric fusion, a locally searched and cited incident-pattern corpus, and deterministic permit-evidence checks. Missing evidence remains visible. A response plan can be approved by three simulated roles, but the API records authorization only—actuation stays none and execution stays manual.”

**On-screen text**

- `ONE SIMULATED CASE · FOUR BOUNDED SERVICES`
- `NO RAW FRAMES · NO BIOMETRICS · NO LLM IN RISK PATH`
- `LOCAL BM25 · SOURCE-ATTRIBUTED RESULTS`
- `3 HUMAN ROLES · ACTUATION: NONE · MANUAL ONLY`
- Fine print: `Reference mapping is not a compliance determination.`

### 02:48–03:14 — Reproducible model evidence and the failure gate (26s)

**Voiceover**  
“On a whole-seed holdout, fusion detects all sixty-five simulated events with twelve-minute median lead. A harder scenario-type holdout falls to eighty-percent pooled recall and misses unseen process drift. Missing critical streams also falls to eighty percent; sensor noise preserves recall but multiplies false alarms. That failure keeps deployment behind site-calibrated shadow validation.”

**On-screen text**

- `SCENARIOBENCH v1.0 · SIMULATED`
- `27,648 ROWS · 576 REPLAYS · 64 SEEDS`
- `TRAIN / CALIBRATION / TEST SEED OVERLAP: 0`
- `BASE HOLDOUT: 65/65 · MEDIAN LEAD 12 MIN · AUPRC 0.997`
- `SCENARIO-TYPE LOSO: 256/320 · 80%`
- `KNOWN MISS: PROCESS_DRIFT 0/64`
- `MISSING CRITICAL STREAM: 52/65`
- `σ=0.05 NOISE: RECALL 65/65 · FALSE ALARMS 1.15 → 47.88`
- `FIELD GATE: LOCAL CALIBRATION + PROSPECTIVE SHADOW VALIDATION`

### 03:14–03:28 — Auditability and route to scale (14s)

**Voiceover**  
“The decision, model version, input receipts and dry-run outcome travel together in one unsigned JSON evidence pack. Deployment starts read-only in shadow mode, calibrates locally, and advances only after safety review.”

**On-screen text**

- `ONE DECISION. EVERY RECEIPT.`
- `EDGE-FIRST DESIGN · NORMALIZED CONTRACTS · SHADOW-MODE ENTRY`
- `REFERENCE MAPPING ≠ CERTIFICATION`

### 03:28–03:40 — Close (12s)

**Voiceover**  
“Compound Zero does not replace a plant’s safety systems or its people. It gives them the missing context—and the time—to act before the alarm.”

**On-screen text**

- `COMPOUND ZERO`
- `THE CONTEXT TO SEE RISK. THE TIME TO STOP IT.`
- `AI-Powered Industrial Safety Intelligence for Zero-Harm Operations`
- `SIMULATED PROTOTYPE · BUILT FOR ET AI HACKATHON 2026`

## Narration direction

- Target **125–132 words per minute**. Read with calm authority, not trailer-style urgency; let the cursor-led moments breathe.
- Put the strongest pauses after “Every device says safe,” “every legacy alarm remains clear,” and “not plant claims.”
- Pronounce `EF-04` as “E-F zero four,” `PTW-2841` as “P-T-W twenty-eight forty-one,” `AUPRC` as “A-U-P-R-C,” and `CMMS` as “C-M-M-S.”
- Never sound triumphant while describing a potential casualty scenario. The tone is precise, humane, and operational.

## End-card title and description copy

**Video title**  
`Compound Zero — See the Accident Before the Alarm | ET AI Hackathon 2026`

**One-line description**  
`A simulated prototype for explainable compound-risk detection across process signals, permits, maintenance barriers, and worker exposure—with calibrated evaluation and human-gated response.`

**Required description disclaimer**  
`All replay and ScenarioBench data shown are simulated. Results are not field validation, a production-safety guarantee, regulatory certification, or authorization for autonomous plant control.`
