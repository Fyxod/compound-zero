# Compound Zero — judge Q&A

These answers are intentionally narrow and evidence-based. The presenter should answer the question first, then add the limitation without being prompted.

## 1. “Is the 100% recall a real-world result?”

No. It is **100% event recall across 65 held-out, simulated positive event replays** in the base ScenarioBench whole-seed split. The single-sensor baseline detected 13 of 65, while full fusion detected 65 of 65. At row level, full-fusion recall is 99.804%, with 4 false-negative rows out of 2,041 positive test rows. A harder scenario-type holdout reaches only 80% pooled event recall and misses the held-out `process_drift` family entirely. We treat the base result as evidence that the integration hypothesis is worth further evaluation—not as field validation or a safety guarantee.

## 2. “Synthetic data is easy to fit. Why should we trust this benchmark?”

You should trust it only for what it tests: whether a reproducible pipeline can learn interactions between process trends and operational context under controlled scenarios. All 64 seeds are partitioned whole into training, probability-calibration, and test sets; no seed or time window crosses partitions. The dataset, configuration, metrics, model, and SHA-256 are reproducible with `python -m ml.train`. We also publish `python -m ml.robustness_bench`: nine scenario-type holdouts produce 80% pooled event recall across the five event-bearing folds, including a 0/64 failure when `process_drift` is unseen. That result makes generator bias visible rather than solved. Production entry therefore remains blocked on authorized local history, site calibration and prospective shadow-mode validation.

## 3. “If process-only already reaches 100% event recall, what does context add?”

It makes the warning operationally usable. In the same held-out simulated test, process-only produces 8.653846 false-alarm episodes per simulated 24 hours; full fusion produces 1.153846, an 86.7% relative reduction. Full fusion also raises AUPRC from 0.946734 to 0.997010 and lowers row false-positive rate from 22.210% to 4.615%. Context distinguishes a process drift that is merely unusual from one that overlaps an impaired barrier, ignition source, or exposed people.

## 4. “Why is this more than another safety dashboard?”

The dashboard is the interaction surface, not the core innovation. Compound Zero represents typed, time-bounded relationships among sensor trends, permits, maintenance barriers, people, zones, and controls; scores their interactions; exposes the evidence behind a warning; previews control impact; and preserves the human authorization receipt. The differentiator is the full loop from fragmented weak signals to a reviewable safety case—not a new chart for an existing alarm.

## 5. “Why not use an LLM or multi-agent system for the safety decision?”

Because a safety trigger needs deterministic inputs, bounded behavior, testable thresholds, and reproducible outputs. The current risk path is a calibrated scikit-learn gradient-boosting model plus structured factors; `/health` explicitly reports `llm_in_risk_path: false`. A future RAG assistant could retrieve incident reports or public guidance for a human, but its output would remain source-cited, advisory, and outside scoring and control authorization.

## 6. “How was the decision threshold selected?”

The base model is trained on training seeds, sigmoid-calibrated on different calibration seeds, and its threshold is selected on calibration data only using F2, which weights recall more heavily than precision for safety screening. The full-fusion threshold is 0.155. The held-out test seeds are not used to fit the model, calibrate probability, or select the threshold.

In the hero replay, the model first crosses that threshold at T+09, one minute before the authored 12-minute target window begins for the T+22 harmful state. Under the row label that is a false positive, which we do not hide; at the scenario level it is an early advisory on an event that later occurs. At T+09 the evidence is the correlated process rise plus impaired extraction barrier. The hot-work and worker-exposure evidence is added only when it actually appears at T+14 and T+18.

## 7. “Your AUPRC rounds to 1.00. Is the model overfit?”

The exact base-test AUPRC is 0.997010, not a claim of perfection. The high value partly reflects a controlled synthetic generator with strong interaction structure. Whole-seed separation reduces temporal leakage, but it does not remove generator bias. The harder scenario-type holdout confirms that: pooled event recall falls to 80%, and held-out `process_drift` recall is 0%. We publish both results, the base calibration Brier score of 0.014616, confusion matrices and limitations, and we expect performance to change on real out-of-distribution data.

## 8. “What happens when a feed is stale, missing, or corrupted?”

The API abstains when caller-supplied `stream_quality` is below 0.80 and returns a reason for manual review; it does not silently convert bad data into a confident recommendation. That scalar is not a complete production policy. In simulated sensitivity tests, removing either the process-sensor stream or the combined barrier-and-shift stream lowers event recall from 65/65 to 52/65. Gaussian `σ=0.05` sensor noise retains 65/65 event recall but raises false-alarm episodes from 1.15 to 47.88 per simulated 24 hours. Production adapters therefore need per-source freshness/schema/range/clock checks, explicit degraded mode and human escalation. Physical alarms, SIS logic and emergency procedures remain independent.

## 9. “Can Compound Zero shut down equipment or order an evacuation?”

Not autonomously. It can generate an advisory and compare simulated controls. In the prototype policy, a reversible permit hold requires an operator and a material process isolation requires dual authorization. The demo button explicitly approves a **dry-run control** in a simulated replay. A production deployment would integrate through existing permit and control governance, never bypass the SIS or plant emergency chain.

## 10. “Are you claiming OISD, OSH&WC Code, DGMS, or ISO compliance?”

No. The prototype maps evidence categories to public reference metadata for traceability. It does not include the full licensed text of paid standards, certify a site, or claim complete regulatory coverage. Compliance determination remains with the facility's competent safety and legal authorities. A production deployment would use customer-licensed material inside the customer's environment and maintain versioned control mappings.

## 11. “How do you protect worker-location privacy?”

The product design uses consented, pseudonymous badges and needs only zone membership, anonymous count, and minimum distance for risk scoring—not a worker's name or continuous off-shift trail. The UI's failure policy excludes identity when consent is missing, and exported packs use pseudonymous identifiers. The prototype demonstrates that boundary; a pilot still needs role-based access, retention limits, encryption, labor consultation, and site-specific privacy review before real badge data is ingested.

## 12. “Is the explanation causal, or just a plausible story?”

It is structured evidence, not proof of causality. The current factors are deterministic interaction values tied to source fields, and the UI links them to timestamped sensor, permit, asset, and people receipts. No LLM fabricates the explanation. For production we would add model-specific attribution stability tests, counterfactual validation, and expert review; operators should treat the graph as the basis for inspection and action, not as an automated root-cause verdict.

## 13. “How does this scale across plants with different systems and thresholds?”

The scalable unit is a site adapter feeding a normalized contract for sensor, permit, maintenance, zone, and exposure context. The repository already separates the React operator experience, typed FastAPI scoring/replay endpoints, deterministic feature pipeline, model artifacts, and dataset metadata. Models and thresholds must be calibrated per site and operating mode. We would deploy at the edge in shadow mode, then federate only approved aggregate metrics—not assume one global threshold fits every plant.

## 14. “What is the business case if you cannot claim prevented accidents?”

We would not price an unverified “lives saved” number. The measurable pilot case is reduced time spent reconciling systems, earlier review of simultaneous-operations conflicts, fewer nuisance escalations, faster evidence assembly, and higher closure rate for corrective actions. ScenarioBench gives a testable hypothesis—7.5 fewer false-alarm episodes per simulated 24 hours versus process-only—not a financial forecast. A pilot would baseline alert burden, intervention lead, operator acceptance, near-miss discovery, and investigation cycle time.

## 15. “What exactly would you do in the first 90 days at a real site?”

Days 0–30: select one bounded unit and two high-value scenarios; complete hazard, privacy, cyber, and data-quality reviews; ingest historical signals and permits read-only. Days 31–60: calibrate locally, run time-split backtests and operator tabletop exercises, and document failure modes. Days 61–90: operate prospectively in shadow mode with no control writes; compare warnings with operator judgments and physical alarms. Only a jointly approved safety case can unlock a limited, reversible workflow integration. Physical isolation remains separately governed.

## 16. “What is the most important failure your testing found?”

When every `process_drift` replay is withheld from both fitting and threshold calibration, that fold detects 0 of 64 simulated events. Pooled across all five event-bearing scenario-type holdouts, recall is 256 of 320, or 80%. This does not tell us the field miss rate; it tells us the current model is not ready to claim transfer to an unseen risk family. We made that failure visible in the UI and artifact, and it becomes a pilot acceptance gate: add representative authorized local scenarios, recalibrate, test by operating mode and time, and require prospective shadow evidence before any workflow integration.

## Numbers the presenter must know

| Measure | Exact current artifact value | Safe spoken form |
|---|---:|---|
| Dataset | 27,648 rows, 576 scenario groups, 64 seeds | “27,648 simulated rows across 576 deterministic replays” |
| Test partition | 5,616 rows, 13 seeds, zero seed overlap | “A disjoint whole-seed holdout” |
| Held-out event groups | 65 | “65 held-out simulated event replays” |
| Single-sensor event recall / FNR | 0.20 / 0.80 | “13 of 65 detected; 80% missed” |
| Full-fusion event recall / FNR | 1.00 / 0.00 | “65 of 65 detected in this simulated holdout” |
| Full-fusion row recall / FNR | 0.998040 / 0.001960 | “99.804% row recall; four positive rows missed” |
| Median event lead | 12 minutes | “12-minute median on held-out positive replays” |
| False alarms, process-only → fusion | 8.653846 → 1.153846 episodes / simulated 24h | “8.65 to 1.15; 86.7% lower” |
| AUPRC, process-only → fusion | 0.946734 → 0.997010 | “0.947 to 0.997” |
| Brier score, fusion | 0.014616 | “0.0146 on the simulated holdout” |
| Full-fusion threshold | 0.155 | “Selected on calibration seeds with an F2 objective” |
| Scenario-type LOSO pooled event recall | 0.800 (256 / 320) | “80% across five event-bearing held-out scenario families” |
| Held-out `process_drift` event recall | 0.000 (0 / 64) | “A known simulated transfer failure and deployment blocker” |
| Missing critical-stream event recall | 0.800 (52 / 65) | “80% when process or barrier-plus-shift context is removed” |
| Gaussian `σ=0.05` false alarms | 47.884615 / simulated 24 h | “Recall held, but review load rose from 1.15 to 47.88” |

## Claims to refuse

- “This would have prevented a named historical accident.”
- “The model is 100% accurate.”
- “The system is OISD / DGMS / OSH&WC Code / ISO certified.”
- “Compound Zero can autonomously shut down a plant.”
- “The dashboard is processing live plant data.”
- “The prototype has proven ROI or reduced injuries in the field.”
- “The explanation proves root cause.”
