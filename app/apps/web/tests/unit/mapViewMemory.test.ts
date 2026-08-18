import { afterEach, describe, expect, it } from "vitest";
import { isCityDefaultView, loadMapView, saveMapView } from "@/components/map/mapViewMemory";

const SAMPLE = {
  longitude: 122.55,
  latitude: 10.70,
  zoom: 15,
  pitch: 45,
  bearing: 0,
};

afterEach(() => {
  sessionStorage.clear();
});

describe("mapViewMemory", () => {
  it("round-trips a camera for a scenario", () => {
    saveMapView("s1", SAMPLE);
    expect(loadMapView("s1")).toEqual(SAMPLE);
  });

  it("does not leak cameras across scenarios", () => {
    saveMapView("s1", SAMPLE);
    expect(loadMapView("s2")).toBeNull();
  });

  it("ignores corrupt payloads", () => {
    sessionStorage.setItem("matrix:map-view:s1", "{not-json");
    expect(loadMapView("s1")).toBeNull();
  });

  it("treats the Iloilo city overview as the default camera", () => {
    expect(
      isCityDefaultView({ longitude: 122.56, latitude: 10.72, zoom: 13 }),
    ).toBe(true);
    expect(isCityDefaultView(SAMPLE)).toBe(false);
  });
});
