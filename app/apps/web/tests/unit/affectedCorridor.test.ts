import { describe, it, expect } from "vitest";
import {
  AFFECTED_BUFFER_M,
  affectedBounds,
  corridorAnchorLonLat,
  expandBboxByMeters,
  filterAffectedFeatures,
  honestAffectedEdgeIds,
  isHonestEdgeResolution,
  mergeEdgeFeatures,
  overlayHonest,
  resultsCameraFly,
  resultsMapPin,
  shouldAutoFly,
  zoomWithoutPullingOut,
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
    expect(isHonestEdgeResolution("gazetteer-alias")).toBe(true);
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

  it("returns nothing for facility-demand even if edge ids leak", () => {
    expect(isHonestEdgeResolution("facility-demand")).toBe(false);
    expect(honestAffectedEdgeIds("facility-demand", ["e1"])).toEqual([]);
  });

  it("respects kernel overlay_honest=false over method string", () => {
    expect(honestAffectedEdgeIds("keyword-match", ["e1"], false)).toEqual([]);
    expect(overlayHonest(false, "keyword-match")).toBe(false);
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

  it("paints live closed-edge shapes that the static layer lacks", () => {
    const live: EdgesFeatureCollection = {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: {
            type: "LineString",
            coordinates: [
              [122.554, 10.726],
              [122.5555, 10.7235],
            ],
          },
          properties: { edge_id: "154184307#10" },
        },
      ],
    };
    const merged = mergeEdgeFeatures(EDGES, live);
    const fc = filterAffectedFeatures(merged, ["154184307#10"]);
    expect(fc?.features).toHaveLength(1);
    expect(fc?.features[0].properties.edge_id).toBe("154184307#10");
    expect(filterAffectedFeatures(EDGES, ["154184307#10"])).toBeNull();
  });
});

describe("resultsCameraFly", () => {
  it("stays on the city default when there is no corridor or LoI", () => {
    expect(resultsCameraFly(null)).toEqual({ kind: "stay" });
    expect(resultsCameraFly(filterAffectedFeatures(EDGES, []))).toEqual({ kind: "stay" });
  });

  it("flies to LoI point when no honest corridor", () => {
    expect(resultsCameraFly(null, [122.5446, 10.6969])).toEqual({
      kind: "point",
      lonlat: [122.5446, 10.6969],
    });
  });

  it("flies to corridor box when overlay exists", () => {
    const collection = filterAffectedFeatures(EDGES, ["e1"]);
    const fly = resultsCameraFly(collection);
    const bbox = affectedBounds(collection)!;
    expect(fly).toEqual({ kind: "corridor", bbox });
  });
});

describe("resultsMapPin", () => {
  it("uses LoI when there is no corridor overlay", () => {
    expect(resultsMapPin(null, [122.5446, 10.6969])).toEqual([122.5446, 10.6969]);
  });

  it("prefers corridor midpoint over LoI", () => {
    expect(resultsMapPin([122.545, 10.695], [122.5446, 10.6969])).toEqual([
      122.545, 10.695,
    ]);
  });
});

describe("corridorAnchorLonLat", () => {
  it("is the midpoint of the honest corridor, not a district centroid", () => {
    expect(corridorAnchorLonLat(null)).toBeNull();
    expect(corridorAnchorLonLat(filterAffectedFeatures(EDGES, []))).toBeNull();
    expect(corridorAnchorLonLat(filterAffectedFeatures(EDGES, ["e1"]))).toEqual([
      122.545, 10.695,
    ]);
  });
});

describe("shouldAutoFly", () => {
  it("flies during a live simulation", () => {
    expect(shouldAutoFly(true, false)).toBe(true);
  });

  it("flies a hydrated run that is still on the city default", () => {
    expect(shouldAutoFly(false, true)).toBe(true);
  });

  it("does not override a saved pan on hydrate", () => {
    expect(shouldAutoFly(false, false)).toBe(false);
  });
});

describe("zoomWithoutPullingOut", () => {
  it("keeps the current zoom when the fitted box would zoom out", () => {
    expect(zoomWithoutPullingOut(13, 11)).toBe(13);
  });

  it("allows zooming in to a tighter corridor", () => {
    expect(zoomWithoutPullingOut(13, 15)).toBe(15);
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
