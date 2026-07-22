import {
  AlertOctagon,
  ArrowDown,
  BadgeCheck,
  BarChart3,
  Boxes,
  Braces,
  CheckCircle2,
  DatabaseZap,
  FlaskConical,
  Gauge,
  Info,
  LockKeyhole,
  ShieldCheck,
  Split,
  TimerReset,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BENCHMARKS, VALIDATION_META } from "../data/validation";

const COLORS = ["#566761", "#c7a65b", "#78e9c2"];

function percent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export function ValidationView() {
  const best = BENCHMARKS.find((row) => row.recommended)!;
  const baseline = BENCHMARKS[0];
  const fnrReduction = Math.round(
    ((baseline.falseNegativeRate - best.falseNegativeRate) / baseline.falseNegativeRate) * 100,
  );
  const processBaseline = BENCHMARKS.find((row) => row.short === "PROCESS")!;
  const falseAlarmReduction = Math.round(
    ((processBaseline.falseAlarmsPer24h - best.falseAlarmsPer24h) /
      processBaseline.falseAlarmsPer24h) * 100,
  );

  return (
    <div className="view validation-view">
      <div className="view-heading compact-heading">
        <div>
          <div className="view-heading__kicker"><FlaskConical size={14} /> REPRODUCIBLE EVALUATION</div>
          <h1>Show the model. Show its limits.</h1>
          <p>Group-held-out replay metrics, calibration-set thresholds, explicit synthetic-data disclosure.</p>
        </div>
        <div className="run-stamp">
          <span className="run-stamp__icon"><BadgeCheck size={17} /></span>
          <div><span>MODEL RUN</span><strong>{VALIDATION_META.runId}</strong></div>
          <span className="run-status is-verified">REPRODUCED</span>
        </div>
      </div>

      <div className="fixture-disclosure">
        <Info size={16} />
        <strong>SIMULATED benchmark:</strong> generated results from a deterministic pipeline, not field validation or a production-safety claim. Dataset SHA <code>{VALIDATION_META.sha256.slice(0, 12)}…</code>
      </div>

      <div className="validation-kpis">
        <article>
          <span className="validation-kpi__icon"><ArrowDown size={18} /></span>
          <div><span>EVENT FNR REDUCTION</span><strong>{fnrReduction}%</strong><small>65 held-out simulated event groups</small></div>
        </article>
        <article>
          <span className="validation-kpi__icon"><TimerReset size={18} /></span>
          <div><span>MEDIAN WARNING LEAD</span><strong>{best.leadMinutes}<em> min</em></strong><small>held-out positive scenarios</small></div>
        </article>
        <article>
          <span className="validation-kpi__icon"><Gauge size={18} /></span>
          <div><span>AUPRC</span><strong>{best.auprc.toFixed(2)}</strong><small>class-imbalance aware</small></div>
        </article>
        <article>
          <span className="validation-kpi__icon"><Braces size={18} /></span>
          <div><span>FALSE-ALARM REDUCTION</span><strong>{falseAlarmReduction}%</strong><small>vs process-only / simulated 24h</small></div>
        </article>
      </div>

      <div className="validation-grid">
        <section className="panel benchmark-panel">
          <header className="panel-header">
            <div><span className="eyebrow">ABLATION STUDY</span><h2>Context closes the safety blind spot</h2></div>
            <div className="metric-toggle"><button type="button" className="is-active">Recall</button><button type="button">AUPRC</button><button type="button">Lead time</button></div>
          </header>
          <div className="benchmark-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={BENCHMARKS} layout="vertical" margin={{ top: 4, left: 10, right: 24, bottom: 4 }}>
                <CartesianGrid stroke="#b8c8c2" strokeOpacity={0.07} horizontal={false} />
                <XAxis type="number" domain={[0, 1]} axisLine={false} tickLine={false} tickFormatter={(value) => `${value * 100}%`} tick={{ fill: "#71817c", fontSize: 10 }} />
                <YAxis type="category" dataKey="short" width={88} axisLine={false} tickLine={false} tick={{ fill: "#a8b6b1", fontSize: 10, fontFamily: "JetBrains Mono Variable" }} />
                <Tooltip formatter={(value) => [percent(Number(value)), "Recall"]} contentStyle={{ background: "#111817", border: "1px solid rgba(170,190,182,.15)", borderRadius: 10 }} />
                <Bar dataKey="recall" radius={[0, 5, 5, 0]} barSize={22}>
                  {BENCHMARKS.map((row, index) => <Cell key={row.short} fill={COLORS[index]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="benchmark-callout">
            <ShieldCheck size={17} />
            <div><strong>Context suppresses noisy process alerts</strong><span>{processBaseline.falseAlarmsPer24h.toFixed(2)} → {best.falseAlarmsPer24h.toFixed(2)} false-alarm episodes per simulated 24 hours.</span></div>
          </div>
        </section>

        <section className="panel scorecard-panel">
          <header className="panel-header">
            <div><span className="eyebrow">HELD-OUT SCORECARD</span><h2>Metric by model family</h2></div>
            <BarChart3 size={17} />
          </header>
          <div className="scorecard-table-wrap">
            <table className="scorecard-table">
              <thead><tr><th>Model</th><th>Recall</th><th>FNR</th><th>AUPRC</th><th>Lead</th><th>FA/24h</th></tr></thead>
              <tbody>
                {BENCHMARKS.map((row) => (
                  <tr key={row.short} className={row.recommended ? "is-recommended" : undefined}>
                    <td><span className="model-status-dot" /> <div><strong>{row.short}</strong><small>{row.model}</small></div></td>
                    <td>{percent(row.recall)}</td>
                    <td>{percent(row.falseNegativeRate)}</td>
                    <td>{row.auprc.toFixed(2)}</td>
                    <td>{row.leadMinutes}m</td>
                    <td>{row.falseAlarmsPer24h.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="scorecard-panel__foot"><CheckCircle2 size={14} /> Full fusion is the only variant meeting the prototype gate.</div>
        </section>

        <section className="panel evaluation-design">
          <header className="panel-header"><div><span className="eyebrow">EVALUATION DESIGN</span><h2>Leakage-resistant by construction</h2></div></header>
          <div className="design-flow">
            {[
              { icon: DatabaseZap, label: "Generate", detail: "Versioned process + work context", tag: `${VALIDATION_META.samples.toLocaleString()} rows` },
              { icon: Split, label: "Group split", detail: "Disjoint seeds; zero overlap", tag: `${VALIDATION_META.groups} replays` },
              { icon: Boxes, label: "Calibrate", detail: "Probability on calibration only", tag: "sigmoid" },
              { icon: LockKeyhole, label: "Freeze", detail: "Hash model and metrics", tag: "SHA-256" },
            ].map((item, index) => {
              const Icon = item.icon;
              return (
                <div className="design-step" key={item.label}>
                  <span className="design-step__index">0{index + 1}</span>
                  <span className="design-step__icon"><Icon size={18} /></span>
                  <div><strong>{item.label}</strong><span>{item.detail}</span></div>
                  <code>{item.tag}</code>
                </div>
              );
            })}
          </div>
          <div className="dataset-disclosure">
            <AlertOctagon size={17} />
            <div><strong>{VALIDATION_META.disclosure}</strong><span>These metrics demonstrate the pipeline and interaction-learning hypothesis. They are not evidence of performance at a real plant.</span></div>
          </div>
        </section>

        <section className="panel failure-modes">
          <header className="panel-header"><div><span className="eyebrow">SAFE FAILURE</span><h2>When the model must not decide</h2></div></header>
          <div className="failure-list">
            {[
              ["Stale process stream", "Abstain + retain physical alarm path", "< 3s"],
              ["Unknown operating mode", "Lower confidence + operator review", "OOD"],
              ["Missing worker consent", "Exclude identity; use anonymous count", "Privacy"],
              ["Action above blast radius", "Require two-person authorization", "Gate"],
            ].map(([title, response, badge]) => (
              <div className="failure-row" key={title}>
                <span className="failure-row__marker" />
                <div><strong>{title}</strong><span>{response}</span></div>
                <code>{badge}</code>
              </div>
            ))}
          </div>
          <footer><FlaskConical size={14} /> Model version compound-zero-scenariobench-v1 · no LLM in the risk path.</footer>
        </section>
      </div>
    </div>
  );
}
