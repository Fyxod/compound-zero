import {
  AlertTriangle,
  ArrowUpRight,
  BadgeCheck,
  BrainCircuit,
  Camera,
  Check,
  ChevronRight,
  ClipboardCheck,
  DatabaseZap,
  EyeOff,
  FileSearch,
  Fingerprint,
  KeyRound,
  LoaderCircle,
  LockKeyhole,
  Network,
  RefreshCw,
  ScanSearch,
  ShieldCheck,
  UserCheck,
  Users,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { approveResponsePlan, fetchOperationalIntelligence } from "../lib/api";
import type { ApprovalRole, OperationalIntelligence, ResponsePlan } from "../types/api";

const ROLE_LABELS: Record<ApprovalRole, string> = {
  AREA_AUTHORITY: "Area authority",
  SAFETY_OFFICER: "Safety officer",
  INCIDENT_COMMANDER: "Incident commander",
};

function LoadingState() {
  return (
    <div className="intelligence-loading panel">
      <span className="intelligence-loading__glyph"><LoaderCircle size={22} /></span>
      <div><strong>Correlating four decision layers</strong><span>Vision metadata · pattern corpus · permit evidence · human policy gate</span></div>
    </div>
  );
}

export function IntelligenceView() {
  const [data, setData] = useState<OperationalIntelligence | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState<ApprovalRole | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchOperationalIntelligence(signal);
      setData(result);
    } catch (caught) {
      if ((caught as Error).name !== "AbortError") {
        setError(caught instanceof Error ? caught.message : "Intelligence API unavailable");
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const nextRole = useMemo(() => {
    if (!data) return null;
    const approved = new Set(data.responsePlan.approvals.map((approval) => approval.approver_role));
    return data.responsePlan.required_approval_roles.find((role) => !approved.has(role)) ?? null;
  }, [data]);

  const approve = async (role: ApprovalRole) => {
    if (!data || approving) return;
    setApproving(role);
    setError(null);
    try {
      const responsePlan = await approveResponsePlan(data.responsePlan.plan_id, role);
      setData((current) => current ? { ...current, responsePlan } : current);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Approval could not be recorded");
    } finally {
      setApproving(null);
    }
  };

  return (
    <div className="view intelligence-view">
      <div className="view-heading compact-heading intelligence-heading">
        <div>
          <div className="view-heading__kicker"><BrainCircuit size={14} /> CROSS-SYSTEM INTELLIGENCE</div>
          <h1>Sensors are only one witness.</h1>
          <p>Compound Zero joins anonymous vision events, permit evidence and source-attributed patterns—then stops at a human gate.</p>
        </div>
        <div className="intelligence-heading__status">
          <span className={`status-led ${data ? "is-online" : "is-watch"}`} />
          <div><span>{data ? "4/4 DEMO SERVICES RESPONDED" : "CONNECTING"}</span><strong>{data ? "Unified simulated API case" : "Building safety case"}</strong></div>
          <button type="button" className="icon-button" aria-label="Refresh intelligence" onClick={() => void load()} disabled={loading}><RefreshCw size={15} /></button>
        </div>
      </div>

      {error && (
        <div className="intelligence-error"><AlertTriangle size={15} /><span>{error}. The deterministic replay remains available; retry this workspace when the API is online.</span></div>
      )}
      {loading && !data ? <LoadingState /> : data && (
        <div className="intelligence-grid">
          <section className="panel intelligence-flow-panel">
            <div className="intelligence-flow">
              {[
                { icon: Camera, label: "Observe", detail: "anonymous events", state: "METADATA ONLY" },
                { icon: Network, label: "Correlate", detail: "numeric fusion", state: "NO LLM" },
                { icon: FileSearch, label: "Interrogate", detail: "cited patterns", state: "LOCAL BM25" },
                { icon: UserCheck, label: "Authorize", detail: "three human roles", state: "MANUAL ONLY" },
              ].map((step, index) => {
                const Icon = step.icon;
                return (
                  <div className="intelligence-flow__step" key={step.label}>
                    <span className="intelligence-flow__index">0{index + 1}</span>
                    <span className="intelligence-flow__icon"><Icon size={17} /></span>
                    <div><strong>{step.label}</strong><span>{step.detail}</span></div>
                    <code>{step.state}</code>
                    {index < 3 && <ChevronRight className="intelligence-flow__arrow" size={14} />}
                  </div>
                );
              })}
            </div>
          </section>

          <section className="panel vision-panel">
            <header className="panel-header">
              <div><span className="eyebrow">CCTV EVENT FUSION</span><h2>Privacy before prediction</h2></div>
              <span className="live-contract"><ShieldCheck size={13} /> CONTRACT ENFORCED</span>
            </header>
            <div className="vision-score">
              <div className="vision-score__value"><span>FUSED SCORE</span><strong>{data.vision.score.risk_score}</strong><small>/ 100</small></div>
              <div className="vision-score__meta">
                <span className="critical-tag">{data.vision.score.severity}</span>
                <strong>{(data.vision.score.risk_probability * 100).toFixed(1)}% calibrated probability</strong>
                <span>{data.vision.score.single_sensor_alarm ? "Device alarm active" : "0 device alarms"}</span>
              </div>
            </div>
            <div className="vision-observations">
              <div><Users size={15} /><span>Occupancy</span><strong>{data.vision.vision_context.max_observed_people} people</strong></div>
              <div><ScanSearch size={15} /><span>Nearest hazard</span><strong>{data.vision.vision_context.min_observed_hazard_distance_m?.toFixed(1)} m</strong></div>
              <div><DatabaseZap size={15} /><span>Events used</span><strong>{data.vision.vision_context.observations_used}/{data.vision.vision_context.observations_received}</strong></div>
            </div>
            <div className="privacy-rails">
              <div><EyeOff size={14} /><strong>No raw frames</strong><span>Schema rejects media payloads</span></div>
              <div><Fingerprint size={14} /><strong>No biometrics</strong><span>No identity tracking accepted</span></div>
              <div><LockKeyhole size={14} /><strong>Ephemeral</strong><span>Only structured event metadata</span></div>
            </div>
            <footer className="intelligence-footnote"><BadgeCheck size={13} /> {data.vision.integration_method}</footer>
          </section>

          <section className="panel pattern-panel">
            <header className="panel-header">
              <div><span className="eyebrow">INCIDENT PATTERN INTELLIGENCE</span><h2>Evidence retrieval that can cite itself</h2></div>
              <span className="model-chip"><DatabaseZap size={13} /> {data.patterns.retrieval_method}</span>
            </header>
            <div className="pattern-query"><FileSearch size={14} /><span>hot work + impaired extraction + flammable trend</span><code>TOP 3</code></div>
            <div className="pattern-results">
              {data.patterns.results.map((pattern, index) => (
                <article className={index === 0 ? "is-primary" : ""} key={pattern.pattern_id}>
                  <div className="pattern-rank"><span>0{index + 1}</span><i /></div>
                  <div className="pattern-result__copy">
                    <div><strong>{pattern.title}</strong><code>BM25 {pattern.score.toFixed(2)}</code></div>
                    <p>{pattern.pattern_summary}</p>
                    <div className="matched-terms">{pattern.matched_terms.slice(0, 5).map((term) => <span key={term}>{term}</span>)}</div>
                    <div className="source-links">
                      {pattern.sources.map((source) => (
                        <a href={source.url} target="_blank" rel="noreferrer" key={source.source_id}>{source.publisher}<ArrowUpRight size={11} /></a>
                      ))}
                    </div>
                  </div>
                </article>
              ))}
            </div>
            <footer className="intelligence-footnote"><ShieldCheck size={13} /> Project-authored summaries over public reference metadata · generative model used: no · licensed OISD text not bundled.</footer>
          </section>

          <section className="panel permit-audit-panel">
            <header className="panel-header">
              <div><span className="eyebrow">DIGITAL PERMIT AUDIT</span><h2>PTW-2841 · Case CZ-2026-071</h2></div>
              <span className="critical-tag">human review</span>
            </header>
            <div className="audit-result">
              <span className="audit-result__glyph"><ClipboardCheck size={21} /></span>
              <div><span>DETERMINISTIC RESULT</span><strong>{data.audit.result.replaceAll("_", " ")}</strong><small>{data.audit.findings.length} evidence-linked findings · LLM used: no</small></div>
              <code>{data.audit.audit_id.slice(-8)}</code>
            </div>
            <div className="permit-findings">
              {data.audit.findings.slice(0, 4).map((finding) => (
                <div className={`permit-finding tone-${finding.severity.toLowerCase()}`} key={finding.finding_id}>
                  <span>{finding.severity}</span>
                  <div><strong>{finding.title}</strong><p>{finding.recommended_action}</p></div>
                  <code>{finding.evidence_refs.length} refs</code>
                </div>
              ))}
            </div>
            <div className="evidence-manifest"><Fingerprint size={13} /><span>Evidence manifest</span><code>{data.audit.evidence_manifest_sha256.slice(0, 18)}…</code><strong>{data.audit.evidence_complete ? "complete" : "gaps visible"}</strong></div>
            <footer className="intelligence-footnote"><AlertTriangle size={13} /> {data.audit.compliance_boundary}</footer>
          </section>

          <ResponsePanel plan={data.responsePlan} nextRole={nextRole} approving={approving} onApprove={approve} />
        </div>
      )}
    </div>
  );
}

function ResponsePanel({
  plan,
  nextRole,
  approving,
  onApprove,
}: {
  plan: ResponsePlan;
  nextRole: ApprovalRole | null;
  approving: ApprovalRole | null;
  onApprove: (role: ApprovalRole) => void;
}) {
  const approvedRoles = new Set(plan.approvals.map((approval) => approval.approver_role));
  const authorized = plan.status === "AUTHORIZED_FOR_MANUAL_EXECUTION";
  return (
    <section className="panel response-orchestrator-panel">
      <header className="panel-header">
        <div><span className="eyebrow">EMERGENCY RESPONSE ORCHESTRATOR</span><h2>Authority stays with the plant</h2></div>
        <span className={`response-state ${authorized ? "is-authorized" : ""}`}><KeyRound size={13} /> {authorized ? "MANUAL EXECUTION AUTHORIZED" : "AWAITING HUMANS"}</span>
      </header>
      <div className="response-plan-summary">
        <div><span>PLAN</span><code>{plan.plan_id}</code></div>
        <div><span>ACTIONS PROPOSED</span><strong>{plan.actions.length}</strong></div>
        <div><span>ACTUATION</span><strong>{plan.actuation_performed ? "performed" : "none"}</strong></div>
        <div><span>MODE</span><strong>{plan.execution_mode}</strong></div>
      </div>
      <div className="approval-rail">
        {plan.required_approval_roles.map((role, index) => {
          const approved = approvedRoles.has(role);
          const active = role === nextRole;
          return (
            <div className={`approval-stop ${approved ? "is-approved" : active ? "is-active" : ""}`} key={role}>
              <span className="approval-stop__marker">{approved ? <Check size={14} /> : index + 1}</span>
              <div><strong>{ROLE_LABELS[role]}</strong><span>{approved ? "Recorded simulated approval" : active ? "Review required" : "Waiting in sequence"}</span></div>
              {active && !authorized ? (
                <button type="button" onClick={() => onApprove(role)} disabled={Boolean(approving)}>
                  {approving === role ? <LoaderCircle size={13} /> : <UserCheck size={13} />} Approve
                </button>
              ) : <code>{approved ? "APPROVED" : "LOCKED"}</code>}
            </div>
          );
        })}
      </div>
      <div className="response-actions">
        {plan.actions.map((action) => <span key={action}>{action.replaceAll("_", " ")}</span>)}
      </div>
      <footer className="intelligence-footnote"><LockKeyhole size={13} /> Record authorization never actuates equipment, isolation, shutdown or evacuation. Production roles require plant IAM.</footer>
    </section>
  );
}
