import { describe, it, expect } from "vitest";

import {
  buildScenarioQuery,
  buildGeometrySuffix,
  INITIAL_BUILDER_STATE,
  type BuilderState,
  type DrawnGeometry,
} from "@/components/ScenarioBuilder";

/** Spread over the shared default so each case only sets what it cares about. */
function state(overrides: Partial<BuilderState>): BuilderState {
  return { ...INITIAL_BUILDER_STATE, ...overrides };
}

describe("buildScenarioQuery — per-type NL grammar", () => {
  it("lane_closure: singular", () => {
    expect(
      buildScenarioQuery(
        state({ interventionType: "lane_closure", lanesClosed: 1, locationName: "Diversion Road" })
      )
    ).toBe("Close 1 lane on Diversion Road.");
  });

  it("lane_closure: plural", () => {
    expect(
      buildScenarioQuery(
        state({ interventionType: "lane_closure", lanesClosed: 2, locationName: "Diversion Road" })
      )
    ).toBe("Close 2 lanes on Diversion Road.");
  });

  it("full_closure: names the corridor directly (no doubled 'on')", () => {
    expect(
      buildScenarioQuery(
        state({ interventionType: "full_closure", locationName: "Jalandoni Street" })
      )
    ).toBe("Fully close Jalandoni Street.");
  });

  it("speed_change: target speed in km/h", () => {
    expect(
      buildScenarioQuery(
        state({ interventionType: "speed_change", maxSpeedKph: 30, locationName: "Jalandoni Street" })
      )
    ).toBe("Reduce speed to 30 km/h on Jalandoni Street.");
  });

  it("capacity_change: percent of baseline", () => {
    expect(
      buildScenarioQuery(
        state({ interventionType: "capacity_change", capacityPct: 120, locationName: "Iznart Street" })
      )
    ).toBe("Change capacity to 120% on Iznart Street.");
  });

  it("new_facility: school in seats, thousands-separated, 'at'", () => {
    expect(
      buildScenarioQuery(
        state({
          interventionType: "new_facility",
          facilityKind: "school",
          facilityCapacity: 3000,
          locationName: "Molo",
        })
      )
    ).toBe("Build a 3,000-seat school at Molo.");
  });

  it("new_facility: market in stalls", () => {
    expect(
      buildScenarioQuery(
        state({
          interventionType: "new_facility",
          facilityKind: "market",
          facilityCapacity: 250,
          locationName: "La Paz",
        })
      )
    ).toBe("Build a 250-stall market at La Paz.");
  });

  it("new_facility: terminal in bays", () => {
    expect(
      buildScenarioQuery(
        state({
          interventionType: "new_facility",
          facilityKind: "terminal",
          facilityCapacity: 12,
          locationName: "Tagbak",
        })
      )
    ).toBe("Build a 12-bay terminal at Tagbak.");
  });
});

describe("buildScenarioQuery — location fallbacks", () => {
  it("uses a coordinate clause when no street name is given (point)", () => {
    const geometry: DrawnGeometry = { kind: "point", point: [122.561, 10.712] };
    const q = buildScenarioQuery(
      state({ interventionType: "new_facility", facilityCapacity: 3000, locationName: "", geometry })
    );
    expect(q).toContain("Build a 3,000-seat school at [122.561, 10.712].");
    // and the GeoJSON suffix rides along
    expect(q).toContain("Geometry (GeoJSON):");
  });

  it("trims whitespace-only names and falls back to the geometry", () => {
    const geometry: DrawnGeometry = { kind: "point", point: [122.5, 10.7] };
    const q = buildScenarioQuery(
      state({ interventionType: "lane_closure", lanesClosed: 1, locationName: "   ", geometry })
    );
    expect(q).toContain("Close 1 lane at [122.5, 10.7].");
  });

  it("prefers the typed name over geometry for the sentence", () => {
    const geometry: DrawnGeometry = { kind: "point", point: [122.561, 10.712] };
    const q = buildScenarioQuery(
      state({ interventionType: "lane_closure", lanesClosed: 2, locationName: "Diversion Road", geometry })
    );
    expect(q).toMatch(/^Close 2 lanes on Diversion Road\./);
    // geometry still attached for deterministic recovery
    expect(q).toContain("Geometry (GeoJSON):");
  });

  it("uses the centroid of polygon vertices for the coordinate clause", () => {
    const geometry: DrawnGeometry = {
      kind: "polygon",
      vertices: [
        [122.0, 10.0],
        [122.2, 10.0],
        [122.1, 10.3],
      ],
    };
    const q = buildScenarioQuery(
      state({ interventionType: "full_closure", locationName: "", geometry })
    );
    // centroid = (122.1, 10.1); coordinates always read with "at"
    expect(q).toContain("Fully close at [122.1, 10.1].");
  });
});

describe("buildGeometrySuffix — GeoJSON embedding", () => {
  it("returns empty string when no geometry", () => {
    expect(buildGeometrySuffix(null)).toBe("");
  });

  it("emits a Point Feature with 5-dp lon/lat", () => {
    const suffix = buildGeometrySuffix({ kind: "point", point: [122.5612345, 10.7126789] });
    expect(suffix.startsWith(" Geometry (GeoJSON): ")).toBe(true);
    const json = suffix.replace(" Geometry (GeoJSON): ", "");
    const feature = JSON.parse(json);
    expect(feature.type).toBe("Feature");
    expect(feature.geometry.type).toBe("Point");
    expect(feature.geometry.coordinates).toEqual([122.56123, 10.71268]);
  });

  it("emits a closed-ring Polygon Feature for 3+ vertices", () => {
    const suffix = buildGeometrySuffix({
      kind: "polygon",
      vertices: [
        [122.0, 10.0],
        [122.2, 10.0],
        [122.1, 10.3],
      ],
    });
    const feature = JSON.parse(suffix.replace(" Geometry (GeoJSON): ", ""));
    expect(feature.geometry.type).toBe("Polygon");
    const ring = feature.geometry.coordinates[0];
    // ring is closed: last vertex repeats the first
    expect(ring).toHaveLength(4);
    expect(ring[0]).toEqual(ring[3]);
    expect(ring[0]).toEqual([122, 10]);
  });

  it("emits no suffix for an incomplete polygon (<3 vertices)", () => {
    expect(
      buildGeometrySuffix({ kind: "polygon", vertices: [[122.0, 10.0], [122.2, 10.0]] })
    ).toBe("");
  });
});

describe("buildScenarioQuery — robustness", () => {
  it("always ends the sentence with a period before any suffix", () => {
    const q = buildScenarioQuery(state({ interventionType: "speed_change", maxSpeedKph: 40, locationName: "X" }));
    expect(q).toBe("Reduce speed to 40 km/h on X.");
  });

  it("clamps lane count to a minimum of 1", () => {
    expect(
      buildScenarioQuery(state({ interventionType: "lane_closure", lanesClosed: 0, locationName: "X" }))
    ).toBe("Close 1 lane on X.");
  });

  it("rounds fractional parameter inputs", () => {
    expect(
      buildScenarioQuery(state({ interventionType: "speed_change", maxSpeedKph: 29.6, locationName: "X" }))
    ).toBe("Reduce speed to 30 km/h on X.");
  });

  it("default state with no location reads as a generic full sentence per type", () => {
    // lane_closure default, no name, no geometry → location clause omitted
    expect(buildScenarioQuery(INITIAL_BUILDER_STATE)).toBe("Close 1 lane.");
  });
});
