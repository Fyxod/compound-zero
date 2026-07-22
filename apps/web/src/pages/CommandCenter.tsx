import {
  AlarmClock,
  BellRing,
  Eye,
  ShieldCheck,
  UsersRound,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { PRIMARY_SCENARIO } from "../data/plant";
import type { SimulationController } from "../hooks/useSimulation";
import { MetricCard } from "../components/MetricCard";
import { PermitMatrix } from "../components/PermitMatrix";
import { PlantMap } from "../components/PlantMap";
import { RiskCasePanel } from "../components/RiskCasePanel";
import { RiskHistoryChart } from "../components/RiskHistoryChart";
import { SimulationControls } from "../components/SimulationControls";
import { TelemetryPanel } from "../components/TelemetryPanel";

export function CommandCenter({
  simulation,
  onOpenEvidence,
}: {
  simulation: SimulationController;
  onOpenEvidence: () => void;
}) {
  const { snapshot } = simulation;
  const exposedWorkers = snapshot.workers.filter((worker) => worker.status === "exposed").length;
  const activePermits = snapshot.permits.filter((permit) => permit.status === "active").length;

  return (
    <div className="view command-view">
      <div className="view-heading">
        <div>
          <div className="view-heading__kicker">
            <span className="status-led is-online" /> SIMULATED OPERATING PICTURE · {snapshot.timestamp} IST
          </div>
          <h1>See the accident <em>before</em> the alarm.</h1>
          <p>{PRIMARY_SCENARIO.summary}</p>
        </div>
        <div className="view-heading__assurance">
          <ShieldCheck size={16} />
          <div><strong>Decision-safe by design</strong><span>Human approval · local inference · reviewable demo receipts</span></div>
        </div>
      </div>

      <SimulationControls
        tick={snapshot.tick}
        running={simulation.running}
        speed={simulation.speed}
        onToggle={simulation.toggle}
        onReset={simulation.reset}
        onSpeed={simulation.setSpeed}
        onScrub={simulation.scrub}
        engine={simulation.engine}
      />

      <AnimatePresence>
        {snapshot.predictionActive && (
          <motion.div
            className="priority-banner"
            initial={{ opacity: 0, height: 0, y: -8 }}
            animate={{ opacity: 1, height: "auto", y: 0 }}
            exit={{ opacity: 0, height: 0 }}
          >
            <span className="priority-banner__icon"><BellRing size={18} /></span>
            <div>
              <span className="eyebrow">PREDICTIVE SAFETY CASE CZ-2026-071</span>
              <strong>{snapshot.counterfactualApplied ? "Dry-run recorded; residual heuristic score remains above the review threshold. No field control was executed." : "Calibrated risk crossed the intervention threshold while every device alarm remains clear."}</strong>
            </div>
            <span className="priority-banner__lead"><AlarmClock size={15} /> {snapshot.counterfactualApplied ? "NON-CAUSAL DRY RUN" : `${snapshot.leadTimeMinutes} min lead`}</span>
            <button type="button" onClick={onOpenEvidence}>Explain this alert</button>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="metrics-grid">
        <MetricCard
          label="Plant risk index"
          value={snapshot.score}
          suffix="/ 100"
          meta={<><span className={`metric-trend is-${snapshot.severity}`}>{snapshot.counterfactualApplied ? "counterfactual estimate" : snapshot.engineSource === "model-api" ? "calibrated API" : "UX fallback"}</span><span>{snapshot.severity}</span></>}
          icon={<Eye size={18} />}
          tone={snapshot.severity === "critical" ? "critical" : snapshot.severity === "elevated" ? "warning" : "safe"}
        />
        <MetricCard
          label="Prediction lead"
          value={snapshot.leadTimeMinutes ?? "—"}
          suffix={snapshot.leadTimeMinutes !== null ? "minutes" : undefined}
          meta={<><span>vs simulated harmful-state onset</span><strong>{snapshot.predictionActive ? "Actionable" : "Observing"}</strong></>}
          icon={<AlarmClock size={18} />}
          tone={snapshot.predictionActive ? "warning" : "neutral"}
        />
        <MetricCard
          label="Legacy alarms"
          value={snapshot.baselineAlarm ? 1 : 0}
          meta={<><span>5 device channels</span><strong>{snapshot.baselineAlarm ? "Alarmed" : "All clear"}</strong></>}
          icon={<BellRing size={18} />}
          tone={snapshot.baselineAlarm ? "critical" : "safe"}
        />
        <MetricCard
          label="People exposed"
          value={exposedWorkers}
          meta={<><span>{snapshot.workers.length} badges tracked</span><strong>{exposedWorkers ? "Inside contour" : "Clear"}</strong></>}
          icon={<UsersRound size={18} />}
          tone={exposedWorkers ? "critical" : "safe"}
        />
        <MetricCard
          label="Active permits"
          value={activePermits}
          meta={<><span>{snapshot.permits.length} in unit</span><strong>1 SIMOPS overlap</strong></>}
          icon={<ShieldCheck size={18} />}
          tone={snapshot.predictionActive ? "warning" : "neutral"}
        />
      </div>

      <div className="command-grid">
        <PlantMap snapshot={snapshot} />
        <RiskCasePanel snapshot={snapshot} onRecordDryRun={simulation.recordDryRun} onOpenEvidence={onOpenEvidence} />
        <RiskHistoryChart history={simulation.history} />
        <TelemetryPanel sensors={snapshot.sensors} />
        <PermitMatrix permits={snapshot.permits} severity={snapshot.severity} />
      </div>
    </div>
  );
}
