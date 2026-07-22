import type {
  ApprovalRole,
  ModelReplayResponse,
  OperationalIntelligence,
  PatternSearchResponse,
  PermitAuditResponse,
  ResponsePlan,
  VisionFusionResponse,
} from "../types/api";

const DEFAULT_API_BASE = "http://127.0.0.1:8000";

function apiBase(): string {
  return (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? DEFAULT_API_BASE;
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${apiBase()}${path}`, {
    ...init,
    headers: { Accept: "application/json", "Content-Type": "application/json", ...init.headers },
  });
  if (!response.ok) throw new Error(`${path} returned ${response.status}`);
  return (await response.json()) as T;
}

export async function fetchModelReplay(signal?: AbortSignal): Promise<ModelReplayResponse> {
  const replay = await requestJson<ModelReplayResponse>(
    "/v1/scenarios/compound_hot_work/replay?seed=24001",
    { signal },
  );
  if (replay.data_classification !== "SIMULATED" || replay.snapshots.length < 24) {
    throw new Error("Replay API returned an invalid disclosure or incomplete series");
  }
  return replay;
}

function processPayload() {
  return {
    data_classification: "SIMULATED",
    scenario_id: "compound-intelligence-c7",
    lel_ratio: 0.62,
    h2s_ratio: 0.42,
    co_ratio: 0.35,
    oxygen_deficit_ratio: 0.21,
    pressure_ratio: 0.56,
    lel_slope: 0.03,
    h2s_slope: 0.02,
    co_slope: 0.015,
    oxygen_slope: 0.01,
    pressure_slope: 0.02,
    ventilation_impaired: true,
    hot_work_active: true,
    workers_in_zone: 0,
    min_worker_distance_m: 120,
    shift_handover: true,
    permit_overlap_count: 1,
    stream_quality: 1,
  };
}

export async function fetchOperationalIntelligence(signal?: AbortSignal): Promise<OperationalIntelligence> {
  const now = new Date(Math.floor(Date.now() / 60_000) * 60_000);
  const evaluationTime = now.toISOString();
  const observationTime = new Date(now.getTime() - 20_000).toISOString();
  const validFrom = new Date(now.getTime() - 60 * 60_000).toISOString();
  const validUntil = new Date(now.getTime() + 2 * 60 * 60_000).toISOString();

  const visionRequest = requestJson<VisionFusionResponse>("/v1/risk/score-with-cctv", {
    method: "POST",
    signal,
    body: JSON.stringify({
      data_classification: "SIMULATED",
      evaluation_time: evaluationTime,
      target_zone_id: "ZONE-C7",
      process: processPayload(),
      observations: [
        {
          observation_id: "obs-c7-occupancy",
          observed_at: observationTime,
          camera_ref: "CAM-C7-WEST",
          zone_id: "ZONE-C7",
          event_type: "occupancy",
          entity_count: 4,
          confidence: 0.96,
        },
        {
          observation_id: "obs-c7-proximity",
          observed_at: observationTime,
          camera_ref: "CAM-C7-EAST",
          zone_id: "ZONE-C7",
          event_type: "unsafe_proximity",
          entity_count: 2,
          min_hazard_distance_m: 6.5,
          confidence: 0.94,
        },
        {
          observation_id: "obs-c7-egress",
          observed_at: observationTime,
          camera_ref: "CAM-C7-EGRESS",
          zone_id: "ZONE-C7",
          event_type: "blocked_egress",
          entity_count: 1,
          confidence: 0.91,
        },
      ],
    }),
  });

  const patternsRequest = requestJson<PatternSearchResponse>("/v1/intelligence/patterns", {
    method: "POST",
    signal,
    body: JSON.stringify({
      data_classification: "SIMULATED",
      query: "hot work ignition while ventilation extraction is impaired",
      context_signals: ["flammable gas trend", "workers in zone", "permit overlap"],
      top_k: 3,
    }),
  });

  const auditRequest = requestJson<PermitAuditResponse>("/v1/audit/permits", {
    method: "POST",
    signal,
    body: JSON.stringify({
      data_classification: "SIMULATED",
      permit: {
        permit_id: "PTW-2841",
        work_type: "hot_work",
        zone_id: "ZONE-C7",
        status: "ACTIVE",
        valid_from: validFrom,
        valid_until: validUntil,
        overlapping_permit_ids: ["PTW-2837"],
        isolation_confirmed: false,
      },
      context: {
        evaluated_at: evaluationTime,
        ventilation_impaired: true,
        lel_ratio: 0.62,
        workers_in_zone: 4,
        shift_handover: true,
        blocked_egress_observed: true,
      },
      evidence: [
        {
          evidence_id: "ev-permit-2841",
          evidence_type: "permit",
          permit_id: "PTW-2841",
          zone_id: "ZONE-C7",
          source_system: "SIMULATED PTW",
          observed_at: evaluationTime,
        },
        {
          evidence_id: "ev-vision-blocked-egress",
          evidence_type: "vision_metadata",
          permit_id: "PTW-2841",
          zone_id: "ZONE-C7",
          source_system: "SIMULATED CCTV METADATA",
          observed_at: observationTime,
        },
      ],
    }),
  });

  const [vision, patterns, audit] = await Promise.all([
    visionRequest,
    patternsRequest,
    auditRequest,
  ]);

  const responsePlan = await requestJson<ResponsePlan>("/v1/response/plans", {
    method: "POST",
    signal,
    body: JSON.stringify({
      data_classification: "SIMULATED",
      idempotency_key: `cz-2026-071-${now.getTime()}`,
      risk_case_id: "CZ-2026-071",
      requested_at: evaluationTime,
      severity: "critical",
      actions: ["NOTIFY_SAFETY_TEAM", "CONTROLLED_EVACUATION", "PROCESS_SHUTDOWN"],
      rationale: `Case CZ-2026-071 joins ${vision.vision_context.observations_used} anonymous vision events, ${patterns.results.length} cited patterns and audit ${audit.audit_id}; present a bounded plan for manual execution only.`,
    }),
  });
  return { vision, patterns, audit, responsePlan };
}

export async function approveResponsePlan(planId: string, role: ApprovalRole): Promise<ResponsePlan> {
  return requestJson<ResponsePlan>(`/v1/response/plans/${planId}/approvals`, {
    method: "POST",
    body: JSON.stringify({
      data_classification: "SIMULATED",
      approver_ref: `simulated-${role.toLowerCase()}`,
      approver_role: role,
      decision: "APPROVE",
      decided_at: new Date().toISOString(),
      reason: "Reviewed the simulated evidence and authorise manual execution only.",
    }),
  });
}
