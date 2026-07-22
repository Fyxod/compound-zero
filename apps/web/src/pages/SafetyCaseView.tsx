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

export const PUBLIC_REFERENCES = [
  {
    ref: "OISD-STD-105",
    title: "Work Permit System",
    mapping: "Permit identity, validity and simultaneous-work context",
    status: "metadata",
    url: "https://www.oisd.gov.in/en-in/oisd-standards-list",
  },
  {
    ref: "S.O. 5321(E)",
    title: "OSH&WC Code commencement",
    mapping: "All provisions brought into force on 21 Nov 2025",
    status: "official gazette",
    url: "https://labour.gov.in/sites/default/files/e-noti-osh-1.pdf",
  },
  {
    ref: "OSH&WC Code 2020",
    title: "Current-law baseline",
    mapping: "ss84/89 hazardous-process and imminent-danger duties · s143 repeals the Factories Act 1948 subject to savings",
    status: "current law",
    url: "https://labour.gov.in/sites/default/files/osh_gazette.pdf",
  },
  {
    ref: "OSH&WC Central Rules 2026",
    title: "Atmosphere + emergency-lighting context",
    mapping: "r23(ii), r24(i)–(iii): ventilation/exhaust/entry · r46: ordinary + emergency illumination · risk mapping only, not a PTW/hot-work rule",
    status: "final · 8 May 2026",
    url: "https://www.labour.gov.in/static/uploads/2026/05/ee246f790cad0b8e99c3828f34fa09a6.pdf",
  },
  {
    ref: "ISO 45001:2018",
    title: "OH&S management system",
    mapping: "Hazard identification, risk controls, incident learning and continual improvement",
    status: "overview",
    url: "https://www.iso.org/standard/63787.html",
  },
  {
    ref: "DGMS",
    title: "Mining safety framework",
    mapping: "Not assessed for this steelworks demo; applicability requires qualified review",
    status: "not assessed",
    url: "https://dgms.gov.in/",
  },
];

function demoHash(seed: string): string {
  let hash = 2166136261;
  for (let index = 0; index < seed.length; index += 1) {
    hash ^= seed.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return Math.abs(hash >>> 0).toString(16).padStart(8, "0").toUpperCase();
}

function verifyDemoLinks(audit: SimulationController["snapshot"]["audit"]): boolean {
  let previousHash = "CZ-GENESIS";
  return audit.every((event) => {
    const expected = demoHash(`${previousHash}|${event.id}|${event.time}|${event.actor}|${event.action}|${event.detail}`);
    previousHash = event.hash;
    return expected === event.hash;
  });
}

export function SafetyCaseView({ simulation }: { simulation: SimulationController }) {
  const snapshot = simulation.snapshot;
  const demoLinksValid = verifyDemoLinks(snapshot.audit);
  const exportPack = () => {
    const pack = {
      schema: "compound-zero.evidence-pack.v1",
      disclosure: "SIMULATED REPLAY - NOT FIELD VALIDATION",
      generatedAt: new Date().toISOString(),
      model: snapshot.modelVersion,
      engineSource: snapshot.engineSource,
      auditIntegrity: {
        method: "FNV-1a 32-bit demo link sequence",
        linkCheckPassed: demoLinksValid,
        boundary: "Non-cryptographic and not tamper-proof; a signed durable ledger is not implemented.",
      },
      snapshot,
      references: PUBLIC_REFERENCES,
      limitations: [
        "Single JSON bundle from a simulated replay; not a regulatory incident report.",
        "No signed source records, trusted timestamps, durable ledger, CSV, Parquet or GeoJSON are included.",
        "Prototype reference mappings do not establish compliance or certification.",
      ],
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
          <p>Inputs, model version, operator action and limitations travel together in one reviewable JSON bundle.</p>
        </div>
        <button type="button" className="button button--primary" onClick={exportPack}><Download size={16} /> Export evidence pack</button>
      </div>

      <div className="safety-case-grid">
        <section className="panel audit-timeline-panel">
          <header className="panel-header">
            <div><span className="eyebrow">DEMO RECEIPT SEQUENCE</span><h2>Case CZ-2026-071</h2></div>
            <span className="chain-status"><Fingerprint size={14} /> {demoLinksValid ? "Link check passed" : "Link check failed"}</span>
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
          <footer className="audit-timeline-panel__foot"><LockKeyhole size={14} /> Non-cryptographic FNV-1a demo links · tamper-proof ledger not implemented</footer>
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
          <div className="standards-disclaimer"><AlertTriangle size={15} /> Prototype mappings are not legal determinations, regulatory certification, complete OISD coverage, or a claim that rules 23, 24 or 46 prescribe a specific statutory PTW/hot-work control. Applicability of saved instruments and site procedures requires qualified review; customer-licensed standards stay in the customer environment.</div>
        </section>

        <section className="panel evidence-inventory">
          <header className="panel-header"><div><span className="eyebrow">JSON BUNDLE CONTENTS</span><h2>Exactly what the download contains</h2></div></header>
          <div className="inventory-grid">
            {[
              ["Case snapshot", "score, five sensors, context", "JSON"],
              ["Model receipt", "version, probability, threshold", "JSON"],
              ["Spatial state", "simulated zones + workers", "JSON"],
              ["Demo audit", "events + FNV link sequence", "JSON"],
              ["Operator controls", "dry-run action + outcome", "JSON"],
              ["Reference map", "public metadata + boundaries", "JSON"],
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
