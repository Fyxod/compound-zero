import { describe, expect, it } from "vitest";
import { PUBLIC_REFERENCES } from "./SafetyCaseView";

describe("safety-case current-law reference map", () => {
  it("preserves commencement and repeal-with-savings context", () => {
    const commencement = PUBLIC_REFERENCES.find((item) => item.ref === "S.O. 5321(E)");
    const code = PUBLIC_REFERENCES.find((item) => item.ref === "OSH&WC Code 2020");

    expect(commencement?.mapping).toContain("21 Nov 2025");
    expect(commencement?.url).toContain("e-noti-osh-1.pdf");
    expect(code?.mapping).toContain("s143 repeals the Factories Act 1948 subject to savings");
  });

  it("labels final-rules pointers as scoped risk mappings", () => {
    const rules = PUBLIC_REFERENCES.find(
      (item) => item.ref === "OSH&WC Central Rules 2026",
    );

    expect(rules?.status).toBe("final · 8 May 2026");
    expect(rules?.mapping).toContain("r23(ii), r24(i)–(iii)");
    expect(rules?.mapping).toContain("r46");
    expect(rules?.mapping).toContain("not a PTW/hot-work rule");
  });
});
