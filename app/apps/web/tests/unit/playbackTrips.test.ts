import { describe, it, expect } from "vitest";
import { framesToTrips } from "@/lib/playbackTrips";

describe("framesToTrips", () => {
  it("builds one path per agent id across ticks", () => {
    const { trips, maxTime } = framesToTrips([
      { tick: 0, agents: [{ id: "a", lon: 122.5, lat: 10.7 }] },
      { tick: 5, agents: [{ id: "a", lon: 122.51, lat: 10.71 }, { id: "b", lon: 122.4, lat: 10.6 }] },
    ]);
    expect(maxTime).toBe(5);
    expect(trips).toEqual([
      { id: "a", path: [[122.5, 10.7], [122.51, 10.71]], timestamps: [0, 5] },
      { id: "b", path: [[122.4, 10.6]], timestamps: [5] },
    ]);
  });
});
