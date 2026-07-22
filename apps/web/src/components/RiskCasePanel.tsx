import {
  ArrowDownRight,
  ArrowRight,
  Check,
  ChevronRight,
  Clock3,
  GitBranch,
  ShieldAlert,
  Siren,
  Sparkles,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useMemo, useState } from "react";
import { clsx } from "clsx";
import { formatSimulationTime, projectedScore } from "../lib/simulation";
import type { InterventionId, SimulationSnapshot } from "../types/domain";
import { RiskGauge } from "./RiskGauge";
import { SeverityPill } from "./SeverityPill";

export function RiskCasePanel({
  snapshot,
  onRecordDryRun,
  onOpenEvidence,
}: {
  snapshot: SimulationSnapshot;
  onRecordDryRun: (id: InterventionId) => void;
  onOpenEvidence: () => void;
}) {
  const [studioOpen, setStudioOpen] = useState(false);
  const [selected, setSelected] = useState<InterventionId>("hold-permit");
  const exposed = snapshot.workers.filter((worker) => worker.status === "exposed").length;
  const hasHotWork = snapshot.factors.some(
    (factor) => factor.id.includes("hot-work") || factor.category === "permit",
  );
  const hasPeople = snapshot.factors.some((factor) => factor.category === "people") || exposed > 0;
  const caseTitle = hasHotWork && hasPeople
    ? "Ignition + personnel exposure"
    : hasHotWork
      ? "Ignition-source overlap"
      : hasPeople
        ? "Process drift + personnel exposure"
        : "Barrier loss + correlated process drift";
  const eventMinute = snapshot.eventMinute ?? snapshot.tick;
  const thresholdWindow = `${formatSimulationTime(Math.max(0, eventMinute - 1)).slice(0, 5)}–${formatSimulationTime(eventMinute + 1).slice(0, 5)}`;
  const selectedIntervention = useMemo(
    () => snapshot.interventions.find((item) => item.id === selected)!,
    [selected, snapshot.interventions],
  );
  const noRiskYet = !snapshot.predictionActive;

  return (
    <section className={clsx("panel risk-case", snapshot.predictionActive && "has-alert")}>
      <header className="panel-header risk-case__header">
        <div>
          <span className="eyebrow">COMPOUND RISK CASE</span>
          <h2>{noRiskYet ? "No active compound risk" : caseTitle}</h2>
        </div>
        <SeverityPill
          severity={snapshot.severity}
          pulse={snapshot.severity === "critical"}
          label={noRiskYet ? "Monitoring" : snapshot.severity.toUpperCase()}
        />
      </header>

      <div className="risk-case__hero">
        <RiskGauge
          score={snapshot.score}
          severity={snapshot.severity}
          confidence={snapshot.confidence}
          confidenceLabel={snapshot.counterfactualApplied ? "dry-run score" : snapshot.engineSource === "model-api" ? "model probability" : "UX fixture"}
        />
        <div className="risk-case__forecast">
          <div className="forecast-kicker"><Sparkles size={14} /> MODEL FORECAST</div>
          {snapshot.leadTimeMinutes !== null ? (
            <>
              <strong>{snapshot.leadTimeMinutes}<span> min</span></strong>
              <p>before modeled harmful-state onset; device alarms are evaluated separately</p>
            </>
          ) : (
            <>
              <strong>—</strong>
              <p>Risk fusion is watching for interacting process and work-context signals.</p>
            </>
          )}
          <div className="legacy-comparison">
            <div>
              <span className="status-led is-online" />
              <span>Legacy alarms</span>
            </div>
            <strong>{snapshot.baselineAlarm ? "1 ACTIVE" : "0 · ALL CLEAR"}</strong>
          </div>
        </div>
      </div>

      {snapshot.predictionActive ? (
        <>
          <div className="risk-case__impact-strip">
            <div><Clock3 size={15} /><span>Harmful-state window</span><strong>{thresholdWindow}</strong></div>
            <div><ShieldAlert size={15} /><span>People exposed</span><strong>{exposed}</strong></div>
            <div><GitBranch size={15} /><span>Evidence signals</span><strong>{snapshot.factors.length}</strong></div>
          </div>

          <div className="factor-list">
            <div className="section-label-row">
              <span className="eyebrow">WHY THE SCORE MOVED</span>
              <button type="button" onClick={onOpenEvidence}>Full evidence graph <ChevronRight size={13} /></button>
            </div>
            {snapshot.factors.slice(0, 4).map((factor, index) => (
              <motion.div
                key={factor.id}
                className="factor-row"
                initial={{ opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.06 }}
              >
                <span className={clsx("factor-row__rank", `is-${factor.category}`)}>{index + 1}</span>
                <div className="factor-row__copy">
                  <strong>{factor.label}</strong>
                  <span>{factor.detail}</span>
                </div>
                <div className="factor-row__contribution">
                  <ArrowDownRight size={13} /> {factor.contribution}/100
                </div>
              </motion.div>
            ))}
          </div>
        </>
      ) : (
        <div className="empty-risk-state">
          <div className="empty-risk-state__orb"><Siren size={22} /></div>
          <strong>Context is quiet. The graph is still working.</strong>
          <p>Start the replay to watch weak signals become a compound risk before any individual alarm crosses its limit.</p>
        </div>
      )}

      <div className="risk-case__actions">
        <button
          className="button button--primary"
          type="button"
          onClick={() => setStudioOpen(true)}
          disabled={!snapshot.predictionActive}
        >
          Open response studio <ArrowRight size={16} />
        </button>
        <button className="button button--ghost" type="button" onClick={onOpenEvidence}>
          Inspect evidence
        </button>
      </div>

      <AnimatePresence>
        {studioOpen && (
          <>
            <motion.button
              type="button"
              className="drawer-backdrop"
              aria-label="Close response studio"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setStudioOpen(false)}
            />
            <motion.aside
              className="response-studio"
              initial={{ x: "105%" }}
              animate={{ x: 0 }}
              exit={{ x: "105%" }}
              transition={{ type: "spring", stiffness: 240, damping: 28 }}
              aria-label="Response studio"
            >
              <header>
                <div>
                  <span className="eyebrow">HUMAN-GATED CONTROL</span>
                  <h2>Response studio</h2>
                  <p>Compare a non-causal heuristic score adjustment before recording a dry run.</p>
                </div>
                <button className="icon-button subtle" type="button" onClick={() => setStudioOpen(false)}>×</button>
              </header>

              <div className="risk-before-after">
                <div><span>Current</span><strong>{snapshot.score}</strong><small>{snapshot.severity}</small></div>
                <ArrowRight size={22} />
                <div className="is-projected"><span>Dry-run heuristic</span><strong>{projectedScore(snapshot, selected)}</strong><small>not a causal model result</small></div>
              </div>

              <div className="response-options">
                {snapshot.interventions.map((intervention) => (
                  <button
                    key={intervention.id}
                    type="button"
                    className={clsx(
                      "response-option",
                      selected === intervention.id && "is-selected",
                      intervention.status === "approved-dry-run" && "is-complete",
                    )}
                    onClick={() => setSelected(intervention.id)}
                  >
                    <span className="response-option__radio">
                      {intervention.status === "approved-dry-run" ? <Check size={13} /> : null}
                    </span>
                    <span className="response-option__copy">
                      <strong>{intervention.label}</strong>
                      <span>{intervention.description}</span>
                      <small>{intervention.etaMinutes} min ETA · {intervention.reversible ? "Reversible" : "Dual approval"}</small>
                    </span>
                    <span className="response-option__impact">−{intervention.riskReduction}</span>
                  </button>
                ))}
              </div>

              <div className="response-assurance">
                <ShieldAlert size={17} />
                <div>
                  <strong>Dry-run and approval enforced</strong>
                  <span>Compound Zero will never autonomously evacuate or isolate process equipment.</span>
                </div>
              </div>
              <button
                type="button"
                className="button button--primary response-studio__execute"
                disabled={selectedIntervention.status === "approved-dry-run"}
                onClick={() => {
                  onRecordDryRun(selected);
                  window.setTimeout(() => setStudioOpen(false), 350);
                }}
              >
                {selectedIntervention.status === "approved-dry-run" ? "Dry-run already recorded" : "Record approved dry run"}
                <ArrowRight size={16} />
              </button>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </section>
  );
}
