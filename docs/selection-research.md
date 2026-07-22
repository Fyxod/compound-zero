# Problem Statement Selection Research

Research date: 22 July 2026  
Decision: **Select PS1 - AI-Powered Industrial Safety Intelligence for Zero-Harm Operations.**  
Runner-up: **PS5 - AI-Powered Urban Air Quality Intelligence for Smart City Intervention.**

See [research-sources.md](research-sources.md) for provenance, licensing notes, and URLs.

## Evidence standard

- **Official** means stated by the organiser in the 17-page problem-statement PDF or on the live Unstop competition page.
- **Verified** means independently supported by a government, standards body, dataset owner, or research institution.
- **Inference** means a comparative product judgement, not an organiser claim.

The PDF applies the same weighted rubric to all eight statements: Innovation 25%, Business Impact 25%, Technical Excellence 20%, Scalability 15%, and User Experience 15%. The live Unstop page names closely aligned criteria: problem relevance, innovation, technical implementation, business viability, presentation, and impact/scalability. It also requires original work, authorised use of licensed tools and datasets, and public, accessible submission links.

The **Win Index is a relative selection score, not a literal probability**. Absolute odds cannot be calculated because the number and quality of Phase 2 submissions are not public. Scores deliberately include data-access and proof-credibility risk.

## Decision matrix

All component scores are out of 10. Every score and ranking in this table is an inference.

| Rank | Problem statement | Win Index /100 | Novelty | Data availability | Demo impact | Feasibility | Credibility | Principal constraint |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | **PS1 Industrial Safety** | **91** | 9.3 | 6.8 | 9.8 | 8.6 | 8.1 | No public dataset joins plant telemetry, permits, maintenance, worker location, and incidents |
| 2 | **PS5 Urban Air Quality** | **87** | 7.8 | 9.6 | 9.5 | 8.8 | 8.5 | Defensible source attribution requires inventories, monitoring, and uncertainty treatment; the space is increasingly crowded |
| 3 | PS7 Cyber Resilience | 81 | 7.3 | 9.1 | 8.9 | 8.3 | 8.7 | Mature SOC/UEBA/SOAR category; common benchmarks are old and not representative of Indian IT/OT infrastructure |
| 4 | PS3 Industrial EV Intelligence | 79 | 7.7 | 8.8 | 8.4 | 8.4 | 8.7 | Credible battery data exists, but the brief spans both fleet operations and manufacturing supply chains |
| 5 | PS2 Energy Supply Resilience | 76 | 8.7 | 7.5 | 9.2 | 6.9 | 7.3 | Public maritime signals exist; executable procurement needs commercial cargo, grade, price, and refinery-compatibility data |
| 6 | PS6 Digital Public Safety | 74 | 8.5 | 4.7 | 9.7 | 6.6 | 6.0 | Authentic labelled scam-call audio, transaction graphs, and lawful real-time phone integration are not generally available |
| 7 | PS4 Data Centre EPC | 72 | 8.3 | 5.8 | 8.3 | 7.2 | 7.0 | Data-centre specifications, submittals, schedules, RFIs, and commissioning records are mostly proprietary |
| 8 | PS8 Industrial Knowledge Brain | 68 | 5.7 | 8.0 | 7.3 | 9.4 | 8.3 | Straightforward to prototype, but generic RAG and document chat are now table stakes |

## Why PS1 has the strongest winning profile

**Inference:** PS1 maximises the two 25% categories simultaneously. Preventing a compound industrial incident is an immediate, high-value business outcome, while correlating individually non-critical signals is more distinctive than another single-stream classifier or chatbot. It also creates the strongest three-to-four-minute story: normal operations, weak signals, an emerging compound hazard, an explained intervention, and a counterfactual replay.

### Recommended product thesis: Compound Zero

Compound Zero should be a **compound-risk industrial digital twin**, not a safety chatbot.

Signature scenario:

1. Gas and pressure remain below their individual alarm thresholds.
2. A ventilation asset enters maintenance isolation.
3. A hot-work permit activates in an adjacent zone.
4. A worker enters the overlapping hazard radius.
5. The fusion engine predicts critical 15/30/60-minute risk even though no single sensor has alarmed.
6. The interface identifies the interacting evidence and proposes permit suspension, worker withdrawal, and ventilation restoration.
7. A counterfactual replay demonstrates how risk changes when one condition is removed.

This directly answers the official requirement to demonstrate compound-risk accuracy and lead time against a single-sensor baseline.

### Technical proof, not agent theatre

- Train and test the compound-risk model on the repository's deterministic ScenarioBench corpus, with whole-seed holdout, calibrated thresholds, ablation baselines and an explicit robustness suite. Tennessee Eastman remains a possible future external benchmark after licence and fit review; it is not bundled evidence.
- Add a deterministic, versioned simulator for permits, maintenance states, worker positions, and hazard-zone relationships. Label this data as simulated.
- Build a typed, timestamped visual evidence graph connecting equipment, zones, pseudonymous workers, permits, maintenance and hazards. A persistent temporal graph store remains production-roadmap work.
- Fuse temporal anomaly scores and graph features into a calibrated risk model.
- Use retrieval only to attach source-grounded procedures and evidence; do not let an LLM invent risk scores or regulatory requirements.
- Apply human approval gates to evacuation, shutdown, and access-control actions. Only bounded, low-impact notifications should execute automatically.

Required evaluation:

- False-negative rate at a fixed false-alarm rate.
- Area under the precision-recall curve, not accuracy alone.
- Median and distribution of prediction lead time.
- Calibration/Brier score.
- Sensor-only vs sensor+permit vs full-fusion ablation.
- Results on a held-out, reproducible scenario suite.

### Demo and UX advantage

The primary screen should combine an isometric plant map, animated risk propagation, time scrubber, active permits, worker positions, and a compact evidence graph. A selected event should expose model confidence, contributing signals, recommended actions, human approval state, and the exact source used for procedural guidance. Replay and counterfactual modes convert technical depth into a visually legible jury narrative.

### PS1 risks and mitigations

| Risk | Mitigation |
|---|---|
| Integrated real plant data is unavailable | Use a named public process benchmark plus a transparent deterministic scenario simulator; publish the generator and data manifest |
| A polished simulation may be mistaken for a production claim | Persistently label simulation mode and separate measured, inferred, and generated fields in the UI |
| Full OISD standards are paid | Use only authorised/public material; do not reproduce unlicensed standards or claim full compliance coverage |
| Existing vendors already put AI into permit-to-work workflows | Differentiate on cross-source compound-risk prediction, calibrated lead time, evidence graphs, ablations, and counterfactual intervention |
| Autonomous action can create a larger hazard | Ship no actuator path, require human gates, export review receipts, and treat durable or tamper-evident audit storage plus fail-safe degraded operation as production gates |

## Runner-up: PS5

PS5 is the best fallback because CPCB station observations, Sentinel-5P products, and ERA5 weather provide unusually strong public inputs. A strong concept would be **PranaOps**, a city intervention operating system that forecasts pollutant concentrations, exposes uncertainty, ranks actions by expected exposure reduction, dispatches inspection routes, and generates ward-level advisories.

**Why it remains second:** public and research platforms already offer forecasting, source-receptor modelling, and intervention analysis for India. A forecast heatmap alone is not novel. Furthermore, official source-apportionment guidance calls for validated emission inventories, chemical monitoring, source profiles, QA/QC, and explicit uncertainty. The product must present attribution as probabilistic prioritisation rather than legal proof.

## Saturation and differentiation assessment

Competitor entries below are market signals based on public product/research descriptions; they are not independently validated capability assessments.

| Problem | Saturation signal | Implication for a hackathon entry |
|---|---|---|
| PS1 | AI-enabled permit-to-work and industrial safety products already exist | Win on compound multi-source prediction, baselines, causal evidence, and counterfactuals rather than digitising permits |
| PS2 | IMF PortWatch already monitors and simulates maritime disruption | Procurement orchestration must add explicit, testable assumptions rather than another geopolitical map |
| PS3 | Battery SOH/RUL prediction is a mature research task | Connect prediction to an operational decision and quantify avoided downtime or lifecycle value |
| PS4 | Dedicated data-centre commissioning and construction platforms exist | A prototype needs measurable specification/commissioning verification, not document chat |
| PS5 | PAVITRA and Delhi source-apportionment initiatives already cover intervention analysis | Differentiate with a closed-loop intervention optimiser, uncertainty, and outcome measurement |
| PS6 | Indian consumer scam-defence products claim real-time detection | Avoid an unverifiable staged call; prove data provenance, privacy boundaries, and false-positive performance |
| PS7 | SIEM, UEBA, MITRE mapping, and SOAR are established categories | Demonstrate a real detector, realistic replay, and safe response gates rather than an LLM SOC copilot |
| PS8 | Agentic RAG and cited document answers are widely commoditised | Only specialised drawing/P&ID understanding plus benchmarked cross-document reasoning would be distinctive |

## Verified corrections and claim policy

The organiser brief is authoritative for requirements but **not sufficiently reliable as a factual citation source**. Submission material should not repeat disputed claims.

| Brief claim | Verification result | Submission policy |
|---|---|---|
| Eight workers died at Visakhapatnam Steel Plant in January 2025 in a coke-oven gas event | Government reporting places an eight-worker Visakhapatnam Steel Plant disaster on **8 June 2026**. Preliminary reporting concerns a steel-melting/ladle event and entrapped gases from liquid steel. | Use the verified date and conservative wording, or omit the anecdote. Do not repeat the January 2025/coke-oven version. |
| DGFASLI recorded more than 6,500 fatal workplace accidents in FY2023 | The cited DGFASLI 2024 reference note's factory-injury table does not support that number. Scope differences may exist, but the brief's attribution is unverified. | Do not use the 6,500 figure without an independent primary source that defines scope and period. |
| A pre-exam 2026 CBSE attack compromised student data and forced multi-state shutdowns | Reporting on CBSE's June 2026 post-result portal attacks states that CBSE reported no data breach, confidential-data compromise, or unauthorised database access. | If PS7 is discussed, describe attempted service disruption and avoid claiming a confirmed breach. |

Every statistic in the deck, detailed document, README, and video script should be traceable to the source ledger. Product-model outputs must distinguish observed facts, model estimates, scenario assumptions, and generated explanations.

## Final decision

Proceed with **PS1 / Compound Zero**. Its data weakness is manageable through transparent simulation and rigorous benchmarking; its upside in innovation, business impact, technical storytelling, and visual presentation is higher than the alternatives. PS5 should remain the contingency only if the project cannot produce a credible compound-risk benchmark and evidence trail.
