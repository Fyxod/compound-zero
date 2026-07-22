import {
  Activity,
  ArrowRight,
  BadgeCheck,
  Braces,
  CheckCircle2,
  CircleDot,
  Database,
  FileCheck2,
  GitBranch,
  MapPinned,
  Network,
  ShieldAlert,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { EvidenceGraph } from "../components/EvidenceGraph";
import { SeverityPill } from "../components/SeverityPill";
import { EVIDENCE_EDGES, EVIDENCE_NODES } from "../data/plant";
import type { SimulationController } from "../hooks/useSimulation";

export function EvidenceView({ simulation }: { simulation: SimulationController }) {
  const snapshot = simulation.snapshot;
  const firstPredictionMinute =
    simulation.history.find((point) => point.predictionActive)?.tick ??
    (snapshot.engineSource === "model-api" ? 9 : 18);
  const strongestEvidence = Math.max(1, ...snapshot.factors.map((factor) => factor.contribution));
  const chartData = Array.from({ length: Math.max(28, snapshot.tick + 1) }, (_, tick) => {
    const point = simulation.history[Math.min(tick, simulation.history.length - 1)] ?? snapshot;
    const lel = point.sensors.find((sensor) => sensor.id === "lel-401")?.value ?? 0;
    const h2s = point.sensors.find((sensor) => sensor.id === "h2s-402")?.value ?? 0;
    const co = point.sensors.find((sensor) => sensor.id === "co-403")?.value ?? 0;
    return { tick, lel, h2s, co: co / 3.5 };
  });

  return (
    <div className="view evidence-view">
      <div className="view-heading compact-heading">
        <div>
          <div className="view-heading__kicker"><GitBranch size={14} /> SAFETY CASE CZ-2026-071</div>
          <h1>Why now?</h1>
          <p>Every score resolves to timestamped evidence. No opaque narrative and no LLM in the decision path.</p>
        </div>
        <div className="evidence-heading-score">
          <div><span>FUSED RISK</span><strong>{snapshot.score}</strong></div>
          <SeverityPill
            severity={snapshot.severity}
            label={`${snapshot.confidence.toFixed(1)}% ${snapshot.counterfactualApplied ? "dry-run score" : "model probability"}`}
          />
        </div>
      </div>

      <div className="evidence-grid">
        <section className="panel graph-panel">
          <header className="panel-header">
            <div>
              <span className="eyebrow">TEMPORAL SAFETY GRAPH</span>
              <h2>Weak facts become one reviewable risk case.</h2>
            </div>
            <div className="graph-health"><Network size={15} /> {EVIDENCE_NODES.length} nodes · {EVIDENCE_EDGES.length} typed edges</div>
          </header>
          <EvidenceGraph />
          <footer className="graph-panel__footer">
            <div><span>Inference rule</span><strong>Ignition source ∩ flammable trend ∩ exposed people</strong></div>
            <div><span>Graph snapshot</span><strong>{snapshot.timestamp} · timestamped receipt</strong></div>
            <button type="button" className="text-button">Open graph inspector <ArrowRight size={14} /></button>
          </footer>
        </section>

        <section className="panel contribution-panel">
          <header className="panel-header">
            <div>
              <span className="eyebrow">STRUCTURED MODEL EVIDENCE</span>
              <h2>Evidence strength</h2>
            </div>
            <span className="model-chip"><Braces size={13} /> HGB + SIGMOID</span>
          </header>
          <div className="contribution-list">
            {snapshot.factors.length ? snapshot.factors.map((factor) => (
              <div key={factor.id} className="contribution-row">
                <div className="contribution-row__topline">
                  <span>{factor.label}</span><strong>{factor.contribution}/100</strong>
                </div>
                <div className="contribution-row__bar"><span style={{ width: `${(factor.contribution / strongestEvidence) * 100}%` }} /></div>
                <small>{factor.category} · {factor.observedAt}</small>
              </div>
            )) : (
              <div className="contribution-empty">Advance the replay to populate structured model evidence.</div>
            )}
          </div>
          <div className="calibration-note">
            <BadgeCheck size={16} />
            <div><strong>Evidence, not causal attribution</strong><span>These strengths expose deterministic feature evidence. They are not additive score points or causal SHAP claims.</span></div>
          </div>
        </section>

        <section className="panel traces-panel">
          <header className="panel-header">
            <div>
              <span className="eyebrow">RAW SENSOR EVIDENCE</span>
              <h2>Individually safe. Jointly abnormal.</h2>
            </div>
            <div className="trace-legend">
              <span><i className="trace-dot is-lel" /> % LEL</span>
              <span><i className="trace-dot is-h2s" /> H₂S ppm</span>
              <span><i className="trace-dot is-co" /> CO normalized</span>
            </div>
          </header>
          <div className="traces-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
                <CartesianGrid stroke="#b8c8c2" strokeOpacity={0.07} vertical={false} />
                <XAxis dataKey="tick" axisLine={false} tickLine={false} tick={{ fill: "#71817c", fontSize: 10 }} tickFormatter={(value) => `T+${value}`} />
                <YAxis domain={[0, 22]} axisLine={false} tickLine={false} tick={{ fill: "#71817c", fontSize: 10 }} />
                <Tooltip contentStyle={{ background: "#111817", border: "1px solid rgba(170,190,182,.15)", borderRadius: 10 }} />
                <ReferenceLine y={20} stroke="#ff625f" strokeDasharray="5 6" label={{ value: "LEL DEVICE ALARM", fill: "#9baaa5", fontSize: 9 }} />
                <Line dataKey="lel" type="monotone" stroke="#ff9b54" strokeWidth={2.2} dot={false} />
                <Line dataKey="h2s" type="monotone" stroke="#f1d06f" strokeWidth={1.8} dot={false} />
                <Line dataKey="co" type="monotone" stroke="#79b9ff" strokeWidth={1.8} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="trace-callout"><CircleDot size={13} /> Fusion threshold crossed at T+{firstPredictionMinute}m; no individual device threshold crossed in this replay.</div>
        </section>

        <section className="panel provenance-panel">
          <header className="panel-header">
            <div><span className="eyebrow">DATA PROVENANCE</span><h2>Inputs that can stand up to review</h2></div>
          </header>
          <div className="provenance-list">
            {[
              { icon: Activity, source: "SCADA historian", record: "5 synchronized channels", quality: "0.8s fresh", hash: "A4D9:77E1" },
              { icon: FileCheck2, source: "Permit to work", record: "PTW-2841 + PTW-2837", quality: "signed", hash: "6E21:0C94" },
              { icon: MapPinned, source: "UWB badge gateway", record: "4 consented worker badges", quality: "±1.2 m", hash: "EF71:43B8" },
              { icon: Database, source: "CMMS adapter", record: "WO-44812 / EF-04", quality: "current", hash: "4B02:11DA" },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div className="provenance-row" key={item.source}>
                  <span className="provenance-row__icon"><Icon size={16} /></span>
                  <div><strong>{item.source}</strong><span>{item.record}</span></div>
                  <span className="quality-stamp"><CheckCircle2 size={12} /> {item.quality}</span>
                  <code>{item.hash}</code>
                </div>
              );
            })}
          </div>
          <div className="provenance-footnote"><ShieldAlert size={15} /> Demo records are explicitly simulated. The evidence model and audit behavior are production-oriented; field validation is not claimed.</div>
        </section>
      </div>
    </div>
  );
}
