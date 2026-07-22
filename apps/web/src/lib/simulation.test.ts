import { describe, expect, it } from "vitest";
import { buildSnapshot, projectedScore, severityFor } from "./simulation";

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

  it("uses stable severity boundaries", () => {
    expect(severityFor(27)).toBe("nominal");
    expect(severityFor(28)).toBe("watch");
    expect(severityFor(52)).toBe("elevated");
    expect(severityFor(76)).toBe("critical");
  });
});
