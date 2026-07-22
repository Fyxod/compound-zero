import { PRIMARY_SCENARIO } from "../data/plant";
import type {
  AuditEvent,
  Intervention,
  InterventionId,
  Permit,
  RiskFactor,
  SensorReading,
  Severity,
  SimulationSnapshot,
  WorkerMarker,
  ZoneRisk,
} from "../types/domain";
import type { ModelReplayPoint } from "../types/api";

const BASE_TIME_HOURS = 14;
const BASE_TIME_MINUTES = 7;

export const clamp = (value: number, min = 0, max = 100) =>
  Math.min(max, Math.max(min, value));

export function severityFor(score: number): Severity {
  if (score >= 76) return "critical";
  if (score >= 52) return "elevated";
  if (score >= 28) return "watch";
  return "nominal";
}

export function formatSimulationTime(tick: number): string {
  const total = BASE_TIME_HOURS * 60 + BASE_TIME_MINUTES + tick;
  const hours = Math.floor(total / 60) % 24;
  const minutes = total % 60;
  return `${hours.toString().padStart(2, "0")}:${minutes
    .toString()
    .padStart(2, "0")}:00`;
}

function sensorStatus(
  value: number,
  alarmAt: number,
  direction: "above" | "below",
): Severity {
  const fraction = direction === "above" ? value / alarmAt : alarmAt / value;
  if (fraction >= 1) return "critical";
  if (fraction >= 0.82) return "elevated";
  if (fraction >= 0.62) return "watch";
  return "nominal";
}

function makeSensors(
  tick: number,
  controls: Set<InterventionId>,
  modelPoint?: ModelReplayPoint,
): SensorReading[] {
  const escalation = Math.max(0, tick - 5);
  const ventilationRestored = controls.has("restore-ventilation");
  const fuelIsolated = controls.has("isolate-fuel");
  const decay = ventilationRestored ? Math.max(0, tick - 5) * 0.32 : 0;
  const isolationDecay = fuelIsolated ? Math.max(0, tick - 5) * 0.5 : 0;
  const modelReduction = ventilationRestored ? 0.72 : fuelIsolated ? 0.78 : 1;
  const lel = modelPoint
    ? clamp(modelPoint.sensors.lel_ratio * 20 * modelReduction, 0, 28)
    : clamp(2.1 + escalation * 0.43 - decay - isolationDecay, 0, 28);
  const h2s = modelPoint
    ? clamp(modelPoint.sensors.h2s_ratio * 10 * modelReduction, 0, 16)
    : clamp(1.8 + escalation * 0.19 - decay * 0.38, 0, 16);
  const co = modelPoint
    ? clamp(modelPoint.sensors.co_ratio * 35 * modelReduction, 0, 42)
    : clamp(7 + escalation * 0.55 - decay * 0.6, 0, 42);
  const oxygen = modelPoint
    ? clamp(20.9 - (modelPoint.sensors.oxygen_deficit_ratio * 1.4) * modelReduction, 18.7, 21)
    : clamp(20.9 - escalation * 0.035 + decay * 0.03, 18.7, 21);
  const pressure = modelPoint
    ? clamp(modelPoint.sensors.pressure_ratio * 3.8 * modelReduction, 1.8, 4.2)
    : clamp(2.2 + escalation * 0.028 - decay * 0.02, 1.8, 4.2);
  const slopes = modelPoint?.slopes;

  const readings: Array<Omit<SensorReading, "status">> = [
    {
      id: "lel-401",
      label: "Combustible gas",
      zoneId: "coke-oven-4",
      value: Number(lel.toFixed(1)),
      unit: "% LEL",
      alarmAt: 20,
      direction: "above",
      trend: slopes ? slopes.lel_slope * 20 : ventilationRestored ? -0.32 : 0.43,
    },
    {
      id: "h2s-402",
      label: "Hydrogen sulphide",
      zoneId: "coke-oven-4",
      value: Number(h2s.toFixed(1)),
      unit: "ppm",
      alarmAt: 10,
      direction: "above",
      trend: slopes ? slopes.h2s_slope * 10 : ventilationRestored ? -0.12 : 0.19,
    },
    {
      id: "co-403",
      label: "Carbon monoxide",
      zoneId: "coke-oven-4",
      value: Number(co.toFixed(0)),
      unit: "ppm",
      alarmAt: 35,
      direction: "above",
      trend: slopes ? slopes.co_slope * 35 : ventilationRestored ? -0.25 : 0.55,
    },
    {
      id: "o2-404",
      label: "Oxygen",
      zoneId: "coke-oven-4",
      value: Number(oxygen.toFixed(1)),
      unit: "% vol",
      alarmAt: 19.5,
      direction: "below",
      trend: slopes ? -slopes.oxygen_slope * 1.4 : ventilationRestored ? 0.02 : -0.04,
    },
    {
      id: "pressure-412",
      label: "Gallery pressure",
      zoneId: "gas-gallery",
      value: Number(pressure.toFixed(2)),
      unit: "kPa",
      alarmAt: 3.8,
      direction: "above",
      trend: slopes ? slopes.pressure_slope * 3.8 : 0.03,
    },
  ];

  return readings.map((sensor) => ({
    ...sensor,
    status: sensorStatus(sensor.value, sensor.alarmAt, sensor.direction),
  }));
}

function makePermits(tick: number, controls: Set<InterventionId>): Permit[] {
  const isHeld = controls.has("hold-permit");
  return [
    {
      id: "PTW-2841",
      type: "HOT WORK",
      work: "Replace ascension-pipe flange",
      zoneId: "gas-gallery",
      startsAt: "14:21",
      expiresAt: "18:00",
      status: isHeld ? "held" : tick >= 14 ? "active" : "planned",
      workers: 4,
    },
    {
      id: "PTW-2837",
      type: "MECHANICAL ISOLATION",
      work: "Extract fan EF-04 bearing service",
      zoneId: "coke-oven-4",
      startsAt: "13:40",
      expiresAt: "16:30",
      status: controls.has("restore-ventilation") ? "held" : "active",
      workers: 2,
    },
  ];
}

function makeWorkers(
  tick: number,
  controls: Set<InterventionId>,
  modelPoint?: ModelReplayPoint,
): WorkerMarker[] {
  const evacuated = controls.has("evacuate-zone");
  const progress = modelPoint?.context.workers_in_zone
    ? 1
    : clamp((tick - 12) / 8, 0, 1);
  const people = [
    { id: "W-118", label: "AK", role: "Welder", dx: -12, dy: -8 },
    { id: "W-204", label: "RS", role: "Fitter", dx: 11, dy: -2 },
    { id: "W-311", label: "MN", role: "Fire watch", dx: -4, dy: 13 },
    { id: "W-409", label: "DJ", role: "Supervisor", dx: 16, dy: 16 },
  ];

  return people.map((worker, index) => {
    const startX = 470 + index * 10;
    const startY = 360 + index * 7;
    const targetX = 182 + worker.dx;
    const targetY = 318 + worker.dy;
    const musterX = 697 + (index % 2) * 32;
    const musterY = 515 + Math.floor(index / 2) * 12;
    const evacuationProgress = evacuated ? clamp((tick - 5) / 8, 0, 1) : 0;
    const currentX = startX + (targetX - startX) * progress;
    const currentY = startY + (targetY - startY) * progress;
    return {
      ...worker,
      x: evacuated
        ? currentX + (musterX - currentX) * evacuationProgress
        : currentX,
      y: evacuated
        ? currentY + (musterY - currentY) * evacuationProgress
        : currentY,
      zoneId: evacuated ? "muster-a" : progress > 0.72 ? "gas-gallery" : "maintenance",
      status: evacuated ? (evacuationProgress >= 0.95 ? "safe" : "moving") : progress > 0.72 ? "exposed" : "safe",
    } satisfies WorkerMarker;
  });
}

function makeFactors(
  tick: number,
  controls: Set<InterventionId>,
  modelPoint?: ModelReplayPoint,
): RiskFactor[] {
  if (modelPoint) {
    return modelPoint.factors
      .filter((factor) => {
        if (controls.has("hold-permit") && factor.evidence_type === "permit") return false;
        if (controls.has("evacuate-zone") && factor.evidence_type === "people") return false;
        if (controls.has("restore-ventilation") && factor.id === "barrier-loss") return false;
        return true;
      })
      .map((factor) => ({
        id: factor.id,
        category: factor.evidence_type,
        label: factor.label,
        detail: factor.detail,
        contribution: Math.round(clamp(factor.value * 100)),
        observedAt: formatSimulationTime(tick),
      }));
  }
  const factors: RiskFactor[] = [];
  const time = formatSimulationTime(tick);
  if (tick >= 6 && !controls.has("restore-ventilation")) {
    factors.push({
      id: "fan-isolated",
      category: "asset",
      label: "Extraction barrier unavailable",
      detail: "EF-04 isolated under maintenance permit PTW-2837",
      contribution: 17,
      observedAt: time,
    });
  }
  if (tick >= 10) {
    factors.push({
      id: "gas-trend",
      category: "sensor",
      label: "Correlated gas trend",
      detail: "LEL, H₂S and CO rising together for 5 consecutive windows",
      contribution: controls.has("restore-ventilation") ? 5 : 19,
      observedAt: time,
    });
  }
  if (tick >= 14 && !controls.has("hold-permit")) {
    factors.push({
      id: "hot-work",
      category: "permit",
      label: "Ignition source within plume",
      detail: "Hot-work permit PTW-2841 is active 14 m downwind",
      contribution: 29,
      observedAt: time,
    });
  }
  if (tick >= 18 && !controls.has("evacuate-zone")) {
    factors.push({
      id: "workers-exposed",
      category: "people",
      label: "Personnel exposure",
      detail: "Four pseudonymous contractor badges entered the illustrative exposure field",
      contribution: 13,
      observedAt: time,
    });
  }
  if (tick >= 21 && tick <= 29) {
    factors.push({
      id: "handover",
      category: "operations",
      label: "Shift handover window",
      detail: "Permit ownership and board operator changed within 8 minutes",
      contribution: 7,
      observedAt: time,
    });
  }
  return factors.sort((a, b) => b.contribution - a.contribution);
}

function makeInterventions(controls: Set<InterventionId>): Intervention[] {
  const items: Array<Omit<Intervention, "status">> = [
    {
      id: "hold-permit",
      label: "Hold hot-work permit",
      description: "Freeze PTW-2841 and notify issuer, receiver and fire watch.",
      riskReduction: 29,
      etaMinutes: 1,
      reversible: true,
    },
    {
      id: "restore-ventilation",
      label: "Restore extraction barrier",
      description: "Return EF-04 or switch to the verified standby extraction path.",
      riskReduction: 24,
      etaMinutes: 4,
      reversible: true,
    },
    {
      id: "evacuate-zone",
      label: "Clear exposure contour",
      description: "Push geofenced evacuation route to four affected worker badges.",
      riskReduction: 13,
      etaMinutes: 3,
      reversible: true,
    },
    {
      id: "isolate-fuel",
      label: "Isolate coke-oven gas",
      description: "Request dual-authorized process isolation at the nearest block valve.",
      riskReduction: 42,
      etaMinutes: 6,
      reversible: false,
    },
  ];
  return items.map((item) => ({
    ...item,
    status: controls.has(item.id) ? "approved-dry-run" : "available",
  }));
}

function shortHash(seed: string): string {
  let hash = 2166136261;
  for (let index = 0; index < seed.length; index += 1) {
    hash ^= seed.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return Math.abs(hash >>> 0).toString(16).padStart(8, "0").toUpperCase();
}

function makeAudit(
  tick: number,
  controls: Set<InterventionId>,
  predictionActive: boolean,
  modelBacked: boolean,
): AuditEvent[] {
  const drafts: Array<Omit<AuditEvent, "hash">> = [
    {
      id: "stream-ok",
      time: "14:07:00",
      actor: "INGEST",
      action: "Telemetry synchronized",
      detail: "23 sensor, PTW and badge streams passed freshness checks.",
      tone: "neutral",
    },
    {
      id: "fan-maintenance",
      time: "14:13:00",
      actor: "CMMS",
      action: "Safety barrier impaired",
      detail: "Extraction fan EF-04 isolated for bearing maintenance.",
      tone: "warning",
    },
  ];
  if (predictionActive) {
    drafts.push({
      id: "risk-raised",
      time: formatSimulationTime(modelBacked ? 9 : 18),
      actor: "FUSION",
      action: "Compound risk raised",
      detail: "Risk crossed the cost-sensitive intervention threshold before any device alarm.",
      tone: "warning",
    });
  }
  for (const control of controls) {
    const intervention = makeInterventions(new Set()).find((item) => item.id === control)!;
    drafts.push({
      id: `control-${control}`,
      time: formatSimulationTime(tick),
      actor: "OPERATOR",
      action: `${intervention.label} dry run`,
      detail: `Human-approved dry run recorded. Non-causal heuristic score adjustment ${intervention.riskReduction} points; no field action executed.`,
      tone: "success",
    });
  }
  let previousHash = "CZ-GENESIS";
  return drafts.map((event) => {
    const hash = shortHash(
      `${previousHash}|${event.id}|${event.time}|${event.actor}|${event.action}|${event.detail}`,
    );
    previousHash = hash;
    return { ...event, hash };
  });
}

function makeZoneRisks(score: number): ZoneRisk[] {
  const values = [
    ["coke-oven-4", score],
    ["gas-gallery", clamp(score + 8)],
    ["by-product", clamp(13 + score * 0.08)],
    ["compressor", clamp(9 + score * 0.04)],
    ["maintenance", clamp(8 + score * 0.12)],
    ["control-room", 4],
    ["muster-a", 2],
  ] as const;
  return values.map(([zoneId, zoneScore]) => ({
    zoneId,
    score: Math.round(zoneScore),
    severity: severityFor(zoneScore),
  }));
}

export function buildSnapshot(
  tick: number,
  controlIds: Iterable<InterventionId> = [],
  modelPoint?: ModelReplayPoint,
  modelVersion = "ux-fixture-v1",
  modelDecisionThreshold = 0.52,
): SimulationSnapshot {
  const controls = new Set(controlIds);
  const naturalCurve = 8 + 87 / (1 + Math.exp(-(tick - 25) / 5.1));
  const permitEffect = tick >= 14 ? 9 : 0;
  const peopleEffect = tick >= 18 ? 5 : 0;
  const compoundInteraction = tick >= 18 ? 13 : 0;
  const reduction = Array.from(controls).reduce((sum, control) => {
    const value = makeInterventions(new Set()).find((item) => item.id === control)?.riskReduction ?? 0;
    return sum + value;
  }, 0);
  const unmitigatedScore =
    modelPoint?.risk_score ?? naturalCurve + permitEffect + peopleEffect + compoundInteraction;
  const score = Math.round(clamp(unmitigatedScore - reduction));
  const severity = severityFor(score);
  const sensors = makeSensors(tick, controls, modelPoint);
  const baselineAlarm =
    modelPoint?.single_sensor_alarm ?? sensors.some((sensor) => sensor.status === "critical");
  const predictionActive = controls.size
    ? score >= modelDecisionThreshold * 100
    : modelPoint?.prediction_active ?? score >= 52;
  const eventMinute =
    modelPoint && modelPoint.event_minute >= 0
      ? modelPoint.event_minute
      : PRIMARY_SCENARIO.baselineTriggerMinute;
  const leadTimeMinutes = predictionActive && controls.size === 0
    ? Math.max(0, eventMinute - tick)
    : null;

  return {
    tick,
    timestamp: formatSimulationTime(tick),
    score,
    confidence: controls.size
      ? score
      : modelPoint
      ? modelPoint.risk_probability * 100
      : clamp(74 + tick * 0.72 - controls.size * 1.4, 74, 96.4),
    severity,
    leadTimeMinutes,
    baselineAlarm,
    predictionActive,
    sensors,
    workers: makeWorkers(tick, controls, modelPoint),
    permits: makePermits(tick, controls),
    zoneRisks: makeZoneRisks(score),
    factors: makeFactors(tick, controls, modelPoint),
    interventions: makeInterventions(controls),
    audit: makeAudit(tick, controls, predictionActive, Boolean(modelPoint)),
    eventMinute,
    harmfulState: controls.size ? null : modelPoint?.harmful_state ?? baselineAlarm,
    modelProbability: controls.size ? null : modelPoint?.risk_probability ?? null,
    decisionThreshold: modelDecisionThreshold,
    modelVersion,
    engineSource: modelPoint ? "model-api" : "ux-fallback",
    counterfactualApplied: controls.size > 0,
  };
}

export function projectedScore(
  snapshot: SimulationSnapshot,
  interventionId: InterventionId,
): number {
  const reduction = snapshot.interventions.find(
    (item) => item.id === interventionId,
  )?.riskReduction;
  return Math.round(clamp(snapshot.score - (reduction ?? 0)));
}
