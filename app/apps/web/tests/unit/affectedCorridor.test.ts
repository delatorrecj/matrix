import { describe, it, expect } from "vitest";
import {
  AFFECTED_BUFFER_M,
  affectedBounds,
  expandBboxByMeters,
  filterAffectedFeatures,
  honestAffectedEdgeIds,
  isHonestEdgeResolution,
} from "@/components/map/affectedCorridor";
import type { EdgesFeatureCollection } from "@/components/map/types";

const EDGES: EdgesFeatureCollection = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      geometry: {
        type: "LineString",
        coordinates: [
          [122.54, 10.69],
          [122.55, 10.70],
        ],
      },
      properties: { edge_id: "e1" },
    },
    {
      type: "Feature",
      geometry: {
        type: "LineString",
        coordinates: [
          [122.56, 10.71],
          [122.57, 10.72],
        ],
      },
      properties: { edge_id: "e2" },
    },
  ],
};

describe("honestAffectedEdgeIds", () => {
  it("returns ids for keyword/gazetteer/geometry matches", () => {
    expect(isHonestEdgeResolution("keyword-match")).toBe(true);
    expect(honestAffectedEdgeIds("gazetteer-match (PROVISIONAL-id)", ["a", "b"])).toEqual([
      "a",
      "b",
    ]);
    expect(honestAffectedEdgeIds("geometry", ["e1"])).toEqual(["e1"]);
  });

  it("returns nothing for busiest-baseline fallback", () => {
    expect(
      honestAffectedEdgeIds("busiest-baseline-fallback (no edge named like 'molo')", [
        "busy-1",
      ]),
    ).toEqual([]);
  });
});

describe("filterAffectedFeatures", () => {
  it("keeps only matching edge_id features", () => {
    const fc = filterAffectedFeatures(EDGES, ["e1"]);
    expect(fc?.features).toHaveLength(1);
    expect(fc?.features[0].properties.edge_id).toBe("e1");
  });

  it("returns null when none match", () => {
    expect(filterAffectedFeatures(EDGES, ["nope"])).toBeNull();
  });
});

describe("affectedBounds", () => {
  it("expands the line bbox by ~300 m", () => {
    const raw = affectedBounds(filterAffectedFeatures(EDGES, ["e1"]), 0)!;
    const padded = affectedBounds(filterAffectedFeatures(EDGES, ["e1"]), AFFECTED_BUFFER_M)!;
    expect(padded[0]).toBeLessThan(raw[0]);
    expect(padded[1]).toBeLessThan(raw[1]);
    expect(padded[2]).toBeGreaterThan(raw[2]);
    expect(padded[3]).toBeGreaterThan(raw[3]);
    const expanded = expandBboxByMeters(raw, AFFECTED_BUFFER_M);
    expect(padded).toEqual(expanded);
  });
});
