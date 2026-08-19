/**
 * Unified playback state from live WS EDGE_COUNTS or GET latest-run hydrate.
 * One interface; two adapters (live stream + Redis cache).
 */
import type { EdgeCounts } from "@/components/map/types";
import { overlayHonest, parseLonLat } from "@/components/map/affectedCorridor";
import { framesToTrips } from "@/lib/playbackTrips";

export type MapPlaybackState = {
  edgeCounts: EdgeCounts;
  affectedEdges: string[];
  edgeResolution: string | null;
  overlayHonest: boolean;
  locationOfInterest: [number, number] | null;
  trips: ReturnType<typeof framesToTrips>["trips"];
  maxTime: number;
  playbackExpired: boolean;
};

export type LatestRunPlayback = {
  edge_counts?: EdgeCounts;
  frames?: Array<{ tick: number; agents: unknown[] }>;
  affected_edges?: string[];
  edge_resolution?: string | null;
  overlay_honest?: boolean;
  location_of_interest?: [number, number] | null;
};

export type WsEdgeCounts = {
  edge_counts?: EdgeCounts;
  affected_edges?: unknown;
  edge_resolution?: string;
  overlay_honest?: boolean;
  location_of_interest?: unknown;
};

export function mapPlaybackFromLatestRun(
  playback: LatestRunPlayback | null | undefined,
  runFallback?: { affected_edges?: string[] | null; edge_resolution?: string | null },
): MapPlaybackState {
  if (playback && typeof playback.edge_counts === "object") {
    const { trips, maxTime } = framesToTrips(
      Array.isArray(playback.frames) ? playback.frames : [],
    );
    const resolution =
      typeof playback.edge_resolution === "string" ? playback.edge_resolution : null;
    const honest = overlayHonest(playback.overlay_honest, resolution);
    return {
      edgeCounts: playback.edge_counts,
      affectedEdges: honest && Array.isArray(playback.affected_edges)
        ? playback.affected_edges.filter((id): id is string => typeof id === "string")
        : [],
      edgeResolution: resolution,
      overlayHonest: honest,
      locationOfInterest: parseLonLat(playback.location_of_interest),
      trips,
      maxTime,
      playbackExpired: false,
    };
  }
  return {
    edgeCounts: {},
    affectedEdges: [],
    edgeResolution: runFallback?.edge_resolution ?? null,
    overlayHonest: false,
    locationOfInterest: null,
    trips: [],
    maxTime: 0,
    playbackExpired: true,
  };
}

export function mapPlaybackFromWs(msg: WsEdgeCounts): Pick<
  MapPlaybackState,
  "edgeCounts" | "affectedEdges" | "edgeResolution" | "overlayHonest" | "locationOfInterest"
> {
  const resolution = typeof msg.edge_resolution === "string" ? msg.edge_resolution : null;
  const honest = overlayHonest(msg.overlay_honest, resolution);
  const edges = Array.isArray(msg.affected_edges)
    ? msg.affected_edges.filter((id): id is string => typeof id === "string")
    : [];
  return {
    edgeCounts: (msg.edge_counts && typeof msg.edge_counts === "object"
      ? msg.edge_counts
      : {}) as EdgeCounts,
    affectedEdges: honest ? edges : [],
    edgeResolution: resolution,
    overlayHonest: honest,
    locationOfInterest: parseLonLat(msg.location_of_interest),
  };
}
