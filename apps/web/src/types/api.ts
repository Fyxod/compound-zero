export interface ModelReplayFactor {
  id: string;
  label: string;
  detail: string;
  value: number;
  evidence_type: "sensor" | "permit" | "asset" | "people" | "operations";
}

export interface ModelReplayPoint {
  minute: number;
  risk_probability: number;
  risk_score: number;
  severity: "nominal" | "watch" | "elevated" | "critical";
  prediction_active: boolean;
  single_sensor_alarm: boolean;
  harmful_state: boolean;
  risk_within_horizon: boolean;
  event_minute: number;
  sensors: {
    lel_ratio: number;
    h2s_ratio: number;
    co_ratio: number;
    oxygen_deficit_ratio: number;
    pressure_ratio: number;
  };
  slopes?: {
    lel_slope: number;
    h2s_slope: number;
    co_slope: number;
    oxygen_slope: number;
    pressure_slope: number;
  };
  stream_quality?: number;
  context: {
    ventilation_impaired: boolean;
    hot_work_active: boolean;
    confined_space_active: boolean;
    workers_in_zone: number;
    min_worker_distance_m: number;
    shift_handover: boolean;
    permit_overlap_count: number;
  };
  factors: ModelReplayFactor[];
}

export interface ModelReplayResponse {
  scenario_id: string;
  scenario_type: string;
  seed: number;
  data_classification: "SIMULATED";
  disclaimer: string;
  model_version: string;
  decision_threshold: number;
  snapshots: ModelReplayPoint[];
}

export type EngineState = "connecting" | "model-api" | "ux-fallback";

export interface VisionFusionResponse {
  data_classification: "SIMULATED";
  score: {
    model_version: string;
    risk_probability: number;
    risk_score: number;
    severity: "nominal" | "watch" | "elevated" | "critical";
    prediction_active: boolean;
    single_sensor_alarm: boolean;
  };
  vision_context: {
    observations_received: number;
    observations_used: number;
    observations_discarded: number;
    max_observed_people: number;
    min_observed_hazard_distance_m: number | null;
    event_counts: Record<string, number>;
    privacy_contract: Record<string, boolean | string>;
    caveats: string[];
  };
  integration_method: string;
  llm_in_risk_path: false;
}

export interface PatternSource {
  source_id: string;
  publisher: string;
  title: string;
  url: string;
  locator: string;
  access_scope: string;
  note: string;
}

export interface PatternMatch {
  pattern_id: string;
  title: string;
  classification: "REFERENCE";
  score: number;
  matched_terms: string[];
  pattern_summary: string;
  signals: string[];
  review_prompts: string[];
  sources: PatternSource[];
}

export interface PatternSearchResponse {
  data_classification: "REFERENCE";
  corpus_name: string;
  corpus_version: string;
  corpus_sha256: string;
  retrieval_method: "LOCAL_BM25";
  generative_model_used: false;
  results: PatternMatch[];
  corpus_scope_note: string;
  licensing_note: string;
}

export interface PermitAuditFinding {
  finding_id: string;
  severity: "INFO" | "REVIEW" | "HIGH" | "CRITICAL";
  title: string;
  evidence_refs: string[];
  rationale: string;
  recommended_action: string;
  references: Array<{ source_id: string; title: string; url: string; locator: string }>;
}

export interface PermitAuditResponse {
  data_classification: "SIMULATED";
  audit_id: string;
  result: "NO_FINDINGS" | "HUMAN_REVIEW_REQUIRED" | "CRITICAL_HUMAN_REVIEW";
  evaluated_at: string;
  permit_id: string;
  evidence_manifest_sha256: string;
  evidence_complete: boolean;
  resolved_evidence_refs: Record<string, string | null>;
  derived_gas_test_age_minutes: number | null;
  findings: PermitAuditFinding[];
  proposed_response_actions: string[];
  compliance_boundary: string;
  llm_used: false;
}

export type ApprovalRole = "AREA_AUTHORITY" | "SAFETY_OFFICER" | "INCIDENT_COMMANDER";

export interface ResponsePlan {
  data_classification: "SIMULATED";
  plan_id: string;
  idempotency_key: string | null;
  retention_ttl_seconds: number;
  risk_case_id: string;
  severity: string;
  actions: string[];
  rationale: string;
  required_approval_roles: ApprovalRole[];
  approvals: Array<{
    approver_ref: string;
    approver_role: ApprovalRole;
    decision: "APPROVE" | "REJECT";
    decided_at: string;
    reason: string;
  }>;
  status: "AWAITING_HUMAN_APPROVAL" | "REJECTED" | "AUTHORIZED_FOR_MANUAL_EXECUTION";
  execution_mode: "MANUAL_ONLY";
  actuation_performed: false;
  autonomous_shutdown_or_evacuation: false;
  boundary: string;
}

export interface OperationalIntelligence {
  vision: VisionFusionResponse;
  patterns: PatternSearchResponse;
  audit: PermitAuditResponse;
  responsePlan: ResponsePlan;
}
