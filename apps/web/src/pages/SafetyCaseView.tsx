import {
  AlertTriangle,
  BadgeCheck,
  Check,
  ClipboardCheck,
  Download,
  ExternalLink,
  FileCheck2,
  Fingerprint,
  KeyRound,
  LockKeyhole,
  ShieldCheck,
  UserCheck,
} from "lucide-react";
import type { SimulationController } from "../hooks/useSimulation";

const PUBLIC_REFERENCES = [
  {
    ref: "OISD-STD-105",
    title: "Work Permit System",
    mapping: "Permit identity, validity and simultaneous-work context",
    status: "metadata",
    url: "https://www.oisd.gov.in/en-in/oisd-standards-list",
  },
  {
    ref: "Factories Act 1948",
    title: "Hazardous process duties",
    mapping: "Evidence retention, imminent-danger escalation and worker protection",
    status: "public law",
    url: "https://www.indiacode.nic.in/handle/123456789/18133?locale=en",
  },
  {
    ref: "ISO 45001:2018",
    title: "OH&S management system",
    mapping: "Hazard identification, risk controls, incident learning and continual improvement",
    status: "overview",
    url: "https://www.iso.org/standard/63787.html",
  },
];

export function SafetyCaseView({ simulation }: { simulation: SimulationController }) {
  const snapshot = simulation.snapshot;
  const exportPack = () => {
    const pack = {
      schema: "compound-zero.evidence-pack.v1",
      disclosure: "SIMULATED REPLAY - NOT FIELD VALIDATION",
      generatedAt: new Date().toISOString(),
      model: snapshot.modelVersion,
      engineSource: snapshot.engineSource,
      auditIntegrity: "FNV-1a linked demo receipts; SHA-256 production adapter",
      snapshot,
      references: PUBLIC_REFERENCES,
    };
    const href = URL.createObjectURL(new Blob([JSON.stringify(pack, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = href;
    link.download = `compound-zero-safety-case-${snapshot.tick}.json`;
    link.click();
    URL.revokeObjectURL(href);
  };

  return (
    <div className="view safety-case-view">
      <div className="view-heading compact-heading">
        <div>
          <div className="view-heading__kicker"><ClipboardCheck size={14} /> AUDITABLE BY CONSTRUCTION</div>
          <h1>One decision. Every receipt.</h1>
          <p>Inputs, model version, operator approval and control outcome travel together as a verifiable evidence pack.</p>
        </div>
        <button type="button" className="button button--primary" onClick={exportPack}><Download size={16} /> Export evidence pack</button>
      </div>

      <div className="safety-case-grid">
        <section className="panel audit-timeline-panel">
          <header className="panel-header">
            <div><span className="eyebrow">HASH-LINKED TIMELINE</span><h2>Case CZ-2026-071</h2></div>
            <span className="chain-status"><Fingerprint size={14} /> Links valid</span>
          </header>
          <div className="audit-timeline">
            {snapshot.audit.map((event, index) => (
              <div className={`audit-event tone-${event.tone}`} key={event.id}>
                <div className="audit-event__rail"><span>{index + 1}</span><i /></div>
                <time>{event.time}</time>
                <div className="audit-event__copy"><span>{event.actor}</span><strong>{event.action}</strong><p>{event.detail}</p></div>
                <code>{event.hash}</code>
              </div>
            ))}
          </div>
          <footer className="audit-timeline-panel__foot"><LockKeyhole size={14} /> FNV-1a linked demo receipts · SHA-256 production adapter</footer>
        </section>

        <section className="panel approval-panel">
          <header className="panel-header"><div><span className="eyebrow">POLICY GATE</span><h2>Machine proposes. People authorize.</h2></div></header>
          <div className="approval-lanes">
            {[
              { icon: ShieldCheck, title: "Advisory alert", actor: "May auto-notify", state: "allowed", detail: "No physical-world change" },
              { icon: UserCheck, title: "Permit hold", actor: "Single operator", state: "approved", detail: "Reversible workflow action" },
              { icon: KeyRound, title: "Process isolation", actor: "Dual authorization", state: "locked", detail: "Material blast-radius control" },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div className={`approval-lane is-${item.state}`} key={item.title}>
                  <span className="approval-lane__icon"><Icon size={18} /></span>
                  <div><strong>{item.title}</strong><span>{item.actor} · {item.detail}</span></div>
                  <span className="approval-lane__state">{item.state === "locked" ? <LockKeyhole size={13} /> : <Check size={13} />}{item.state}</span>
                </div>
              );
            })}
          </div>
          <div className="approval-rule"><AlertTriangle size={16} /><div><strong>Fail-safe default</strong><span>Loss of the AI layer never disables physical alarms, SIS logic or existing emergency procedures.</span></div></div>
        </section>

        <section className="panel standards-panel">
          <header className="panel-header"><div><span className="eyebrow">PUBLIC REFERENCE MAP</span><h2>Traceability without false certification</h2></div><BadgeCheck size={17} /></header>
          <div className="standards-list">
            {PUBLIC_REFERENCES.map((item) => (
              <a href={item.url} target="_blank" rel="noreferrer" className="standard-row" key={item.ref}>
                <span className="standard-row__icon"><FileCheck2 size={16} /></span>
                <div><span>{item.ref}</span><strong>{item.title}</strong><p>{item.mapping}</p></div>
                <span className="reference-status">{item.status}</span>
                <ExternalLink size={14} />
              </a>
            ))}
          </div>
          <div className="standards-disclaimer"><AlertTriangle size={15} /> Prototype mappings are not a claim of regulatory certification or complete OISD coverage. Customer-licensed standards stay in the customer environment.</div>
        </section>

        <section className="panel evidence-inventory">
          <header className="panel-header"><div><span className="eyebrow">PACK CONTENTS</span><h2>Ready for investigation</h2></div></header>
          <div className="inventory-grid">
            {[
              ["Sensor window", "5 channels · 48 minutes", "CSV + Parquet"],
              ["Permit records", "2 signed revisions", "JSON + source IDs"],
              ["Spatial snapshot", "zones, workers, contour", "GeoJSON"],
              ["Model receipt", "features, score, calibration", "JSON"],
              ["Operator controls", "approval + outcome", "append-only log"],
              ["Reference map", "public metadata + links", "manifest"],
            ].map(([title, detail, format]) => (
              <div className="inventory-item" key={title}><Check size={13} /><div><strong>{title}</strong><span>{detail}</span></div><code>{format}</code></div>
            ))}
          </div>
          <div className="inventory-footer"><ShieldCheck size={15} /><span>Worker identity is pseudonymized in exported packs by default.</span></div>
        </section>
      </div>
    </div>
  );
}
