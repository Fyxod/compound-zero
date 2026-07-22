import { describe, expect, it } from "vitest";
import type { ModelReplayPoint } from "../types/api";
import { buildSnapshot, projectedScore, severityFor } from "./simulation";

function modelPoint(overrides: Partial<ModelReplayPoint> = {}): ModelReplayPoint {
  return {
    minute: 47,
    risk_probability: 0.91,
    risk_score: 91,
    severity: "critical",
    prediction_active: true,
    single_sensor_alarm: false,
    harmful_state: true,
    risk_within_horizon: true,
    event_minute: 47,
    sensors: {
      lel_ratio: 0.6,
      h2s_ratio: 0.4,
      co_ratio: 0.3,
      oxygen_deficit_ratio: 0.5,
      pressure_ratio: 0.55,
    },
    slopes: {
      lel_slope: 0.03,
      h2s_slope: 0.02,
      co_slope: 0.01,
      oxygen_slope: 0.01,
      pressure_slope: 0.02,
    },
    stream_quality: 1,
    context: {
      ventilation_impaired: true,
      hot_work_active: true,
      confined_space_active: false,
      workers_in_zone: 4,
      min_worker_distance_m: 6.5,
      shift_handover: false,
      permit_overlap_count: 1,
    },
    factors: [],
    ...overrides,
  };
}

describe("compound risk simulation", () => {
  it("raises fused risk before any individual sensor alarm", () => {
    const snapshot = buildSnapshot(18);
    expect(snapshot.predictionActive).toBe(true);
    expect(snapshot.baselineAlarm).toBe(false);
    expect(snapshot.leadTimeMinutes).toBe(24);
  });

  it("reduces projected risk for explicit interventions", () => {
    const snapshot = buildSnapshot(28);
    const held = projectedScore(snapshot, "hold-permit");
    expect(held).toBeLessThan(snapshot.score);
    expect(buildSnapshot(28, ["hold-permit"]).score).toBe(held);
  });

  it("keeps the final T+47 replay frame model-backed", () => {
    const snapshot = buildSnapshot(47, [], modelPoint(), "model-v-test", 0.155);
    expect(snapshot.engineSource).toBe("model-api");
    expect(snapshot.modelVersion).toBe("model-v-test");
    expect(snapshot.score).toBe(91);
    expect(snapshot.harmfulState).toBe(true);
  });

  it("improves oxygen after the ventilation dry-run transformation", () => {
    const point = modelPoint({ minute: 18, event_minute: 22, harmful_state: false });
    const original = buildSnapshot(18, [], point, "model-v-test", 0.155);
    const controlled = buildSnapshot(
      18,
      ["restore-ventilation"],
      point,
      "model-v-test",
      0.155,
    );
    const oxygen = (snapshot: typeof original) =>
      snapshot.sensors.find((sensor) => sensor.id === "o2-404")!.value;
    expect(oxygen(controlled)).toBeGreaterThan(oxygen(original));
  });

  it("does not preserve model outcome truth after a heuristic dry run", () => {
    const controlled = buildSnapshot(
      18,
      ["hold-permit"],
      modelPoint({ minute: 18, event_minute: 22, harmful_state: false }),
      "model-v-test",
      0.155,
    );
    expect(controlled.counterfactualApplied).toBe(true);
    expect(controlled.leadTimeMinutes).toBeNull();
    expect(controlled.harmfulState).toBeNull();
    expect(controlled.modelProbability).toBeNull();
    expect(controlled.predictionActive).toBe(true);
  });

  it("uses stable severity boundaries", () => {
    expect(severityFor(27)).toBe("nominal");
    expect(severityFor(28)).toBe("watch");
    expect(severityFor(52)).toBe("elevated");
    expect(severityFor(76)).toBe("critical");
  });
});
