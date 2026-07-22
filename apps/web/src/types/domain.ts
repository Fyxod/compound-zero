export type Severity = "nominal" | "watch" | "elevated" | "critical";

export type ZoneKind =
  | "process"
  | "utility"
  | "support"
  | "safe"
  | "control";

export interface PlantZone {
  id: string;
  name: string;
  shortName: string;
  kind: ZoneKind;
  x: number;
  y: number;
  width: number;
  height: number;
  sensorIds: string[];
}

export interface SensorReading {
  id: string;
  label: string;
  zoneId: string;
  value: number;
  unit: string;
  alarmAt: number;
  direction: "above" | "below";
  trend: number;
  status: Severity;
}

export interface WorkerMarker {
  id: string;
  label: string;
  role: string;
  x: number;
  y: number;
  zoneId: string;
  status: "safe" | "exposed" | "moving";
}

export interface Permit {
  id: string;
  type: string;
  work: string;
  zoneId: string;
  startsAt: string;
  expiresAt: string;
  status: "planned" | "active" | "held";
  workers: number;
}

export interface RiskFactor {
  id: string;
  category: "sensor" | "permit" | "asset" | "people" | "operations";
  label: string;
  detail: string;
  contribution: number;
  observedAt: string;
}

export interface EvidenceNode {
  id: string;
  label: string;
  type: "signal" | "context" | "risk" | "control";
  x: number;
  y: number;
  active: boolean;
}

export interface EvidenceEdge {
  from: string;
  to: string;
  label: string;
  active: boolean;
}

export interface ZoneRisk {
  zoneId: string;
  score: number;
  severity: Severity;
}

export type InterventionId =
  | "hold-permit"
  | "restore-ventilation"
  | "evacuate-zone"
  | "isolate-fuel";

export interface Intervention {
  id: InterventionId;
  label: string;
  description: string;
  riskReduction: number;
  etaMinutes: number;
  reversible: boolean;
  status: "available" | "executing" | "complete";
}

export interface AuditEvent {
  id: string;
  time: string;
  actor: string;
  action: string;
  detail: string;
  hash: string;
  tone: "neutral" | "warning" | "success";
}

export interface SimulationSnapshot {
  tick: number;
  timestamp: string;
  score: number;
  confidence: number;
  severity: Severity;
  leadTimeMinutes: number | null;
  baselineAlarm: boolean;
  predictionActive: boolean;
  sensors: SensorReading[];
  workers: WorkerMarker[];
  permits: Permit[];
  zoneRisks: ZoneRisk[];
  factors: RiskFactor[];
  interventions: Intervention[];
  audit: AuditEvent[];
  eventMinute: number | null;
  harmfulState: boolean;
  modelProbability: number | null;
  decisionThreshold: number;
  modelVersion: string;
  engineSource: "model-api" | "ux-fallback";
  counterfactualApplied: boolean;
}

export interface ScenarioDefinition {
  id: string;
  name: string;
  location: string;
  summary: string;
  durationMinutes: number;
  baselineTriggerMinute: number;
  fusedTriggerMinute: number;
  outcomeWithoutIntervention: string;
}

export type AppView = "command" | "evidence" | "intelligence" | "validation" | "safety-case";
