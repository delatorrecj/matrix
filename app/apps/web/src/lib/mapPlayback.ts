/**
 * Unified playback state from live WS EDGE_COUNTS or GET latest-run hydrate.
 * One interface; two adapters (live stream + Redis cache).
 */
import type { EdgeCounts, EdgesFeatureCollection } from "@/components/map/types";
import { overlayHonest, parseLonLat } from "@/components/map/affectedCorridor";
import { framesToTrips } from "@/lib/playbackTrips";

export type MapPlaybackState = {
  edgeCounts: EdgeCounts;
  affectedEdges: string[];
  edgeResolution: string | null;
  overlayHonest: boolean;
  locationOfInterest: [number, number] | null;
  affectedEdgeGeoms: EdgesFeatureCollection | null;
  fromCross: string | null;
  toCross: string | null;
  corridor: string | null;
  trips: ReturnType<typeof framesToTrips>["trips"];
  maxTime: number;
  playbackExpired: boolean;
};

export type LatestRunPlayback = {
  edge_counts?: EdgeCounts;
  frames?: Array<{ tick: number; agents: Array<{ id: string; lon: number; lat: number }> }>;
  // Some API payloads (and legacy caches) may return `null` instead of omitting the field.
  // `mapPlaybackFromLatestRun` already handles this safely via `Array.isArray(...)`.
  affected_edges?: string[] | null;
  edge_resolution?: string | null;
  overlay_honest?: boolean;
  location_of_interest?: [number, number] | null;
  affected_edge_geoms?: unknown;
  from_cross?: string | null;
  to_cross?: string | null;
  corridor?: string | null;
};

export type WsEdgeCounts = {
  edge_counts?: EdgeCounts;
  affected_edges?: unknown;
  edge_resolution?: string;
  overlay_honest?: boolean;
  location_of_interest?: unknown;
  affected_edge_geoms?: unknown;
  from_cross?: unknown;
  to_cross?: unknown;
  corridor?: unknown;
};

function parseEdgeGeoms(raw: unknown): EdgesFeatureCollection | null {
  if (!raw) return null;
  if (Array.isArray(raw) && raw.length > 0) {
    return { type: "FeatureCollection", features: raw as EdgesFeatureCollection["features"] };
  }
  if (
    typeof raw === "object" &&
    raw !== null &&
    (raw as { type?: string }).type === "FeatureCollection" &&
    Array.isArray((raw as { features?: unknown }).features)
  ) {
    const features = (raw as EdgesFeatureCollection).features;
    return features.length > 0 ? (raw as EdgesFeatureCollection) : null;
  }
  return null;
}

function parseName(raw: unknown): string | null {
  return typeof raw === "string" && raw.trim() ? raw.trim() : null;
}

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
      affectedEdgeGeoms: honest ? parseEdgeGeoms(playback.affected_edge_geoms) : null,
      fromCross: parseName(playback.from_cross),
      toCross: parseName(playback.to_cross),
      corridor: parseName(playback.corridor),
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
    affectedEdgeGeoms: null,
    fromCross: null,
    toCross: null,
    corridor: null,
    trips: [],
    maxTime: 0,
    playbackExpired: true,
  };
}

export function mapPlaybackFromWs(msg: WsEdgeCounts): Pick<
  MapPlaybackState,
  | "edgeCounts"
  | "affectedEdges"
  | "edgeResolution"
  | "overlayHonest"
  | "locationOfInterest"
  | "affectedEdgeGeoms"
  | "fromCross"
  | "toCross"
  | "corridor"
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
    affectedEdgeGeoms: honest ? parseEdgeGeoms(msg.affected_edge_geoms) : null,
    fromCross: parseName(msg.from_cross),
    toCross: parseName(msg.to_cross),
    corridor: parseName(msg.corridor),
  };
}
