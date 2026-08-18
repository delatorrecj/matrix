export type TripPath = { id: string; path: [number, number][]; timestamps: number[] };

function isValidAgent(a: { id: string; lon: number; lat: number }): boolean {
  return typeof a.id === "string" && a.id !== "" && Number.isFinite(a.lon) && Number.isFinite(a.lat);
}

export function accumulateTripFrame(
  prev: TripPath[],
  tick: number,
  agents: Array<{ id: string; lon: number; lat: number }>,
): TripPath[] {
  const next = [...prev];
  for (const a of agents) {
    if (!isValidAgent(a)) continue;
    const idx = next.findIndex((t) => t.id === a.id);
    if (idx >= 0) {
      next[idx] = {
        ...next[idx],
        path: [...next[idx].path, [a.lon, a.lat]],
        timestamps: [...next[idx].timestamps, tick],
      };
    } else {
      next.push({
        id: a.id,
        path: [[a.lon, a.lat]],
        timestamps: [tick],
      });
    }
  }
  return next;
}

export function framesToTrips(
  frames: Array<{ tick: number; agents: Array<{ id: string; lon: number; lat: number }> }>,
): { trips: TripPath[]; maxTime: number } {
  let trips: TripPath[] = [];
  const ticks = frames.map((f) => f.tick);
  const maxTime = ticks.length > 0 ? Math.max(0, ...ticks) : 0;
  for (const frame of frames) {
    trips = accumulateTripFrame(trips, frame.tick, frame.agents);
  }
  return { trips, maxTime };
}
