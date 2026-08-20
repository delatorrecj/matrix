import { describe, expect, it } from "vitest";
import type { ResultCardData } from "@/components/ResultCard";
import { interpretDimension, overallHeadline } from "@/lib/interpret";

function card(overrides: Partial<ResultCardData> = {}): ResultCardData {
  return {
    key: "behavioral:BEH-2:0",
    dimension: "behavioral",
    metric: "mode-share shift (jeepney)",
    equationId: "BEH-2",
    unit: "%-points",
    conf: "M",
    rawValue: 0,
    rawRange: [0, 0],
    directional: false,
    applicability: "not_modeled",
    provData: {
      metric: "mode-share shift (jeepney)",
      value: "0",
      range: "0..0",
      confidence: "M",
      confidenceBasis: "Computed",
      equationId: "BEH-2",
      inputs: [],
      assumptions: [],
      references: [],
    },
    ...overrides,
  };
}

describe("interpret skips N/A cards", () => {
  it("does not tally not_modeled as about the same", () => {
    expect(interpretDimension("behavioral", [card()])).toMatch(/no computed measures/i);
    expect(overallHeadline([card()])).toMatch(/no modeled impact/i);
  });

  it("still describes computed siblings", () => {
    const computed = card({
      key: "economic:ECON-3:0",
      dimension: "economic",
      equationId: "ECON-3",
      metric: "Employment Δ",
      rawValue: -0.7,
      applicability: "computed",
      conf: "M",
    });
    const text = interpretDimension("economic", [card(), computed]);
    expect(text).not.toMatch(/about the same/);
    expect(text).toMatch(/worsen/);
  });
});
