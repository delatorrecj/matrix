import { describe, expect, it } from "vitest";
import { buildProvenanceData } from "@/lib/provenance";

describe("buildProvenanceData", () => {
  it("enriches wire fields with equation text and dataset metadata from registries", () => {
    const prov = buildProvenanceData({
      metric: "Δ trips on affected corridor (AM-peak)",
      value: "42",
      range: "30..55",
      confidence: "H",
      equationId: "BEH-1",
      input_dataset_ids: ["OSM-ILO", "OVERTURE"],
      assumptions: ["sim window = AM peak"],
      references: ["Calderon2014"],
    });

    expect(prov.equationText).toContain("ΔT_c");
    expect(prov.inputs[0]?.name).toMatch(/OpenStreetMap/i);
    expect(prov.inputs[0]?.url).toContain("overpass");
    expect(prov.inputs[1]?.name).toMatch(/Overture/i);
  });

  it("passes applicability through to Inspect", () => {
    const prov = buildProvenanceData({
      metric: "mode-share shift (jeepney)",
      value: "0",
      range: "0..0",
      confidence: "M",
      equationId: "BEH-2",
      input_dataset_ids: ["PERSONA-POOL"],
      assumptions: ["not modeled"],
      references: [],
      applicability: "not_modeled",
    });
    expect(prov.applicability).toBe("not_modeled");
  });

  it("leaves unknown dataset ids as bare id rows", () => {
    const prov = buildProvenanceData({
      metric: "test",
      value: "1",
      range: "0..2",
      confidence: "L",
      equationId: "BEH-1",
      input_dataset_ids: ["UNKNOWN-DS"],
      assumptions: [],
      references: [],
    });

    expect(prov.inputs).toEqual([{ id: "UNKNOWN-DS" }]);
  });
});
