/**
 * Honest "where we edited the net" helpers for the results map.
 *
 * Overlay + camera follow the honest corridor when the kernel sets overlay_honest.
 * Fallback and facility-demand stay on the city default — no gazetteer fly/pin.
 */

import type { EdgesFeatureCollection, Feature, LonLat } from "./types";

export const AFFECTED_BUFFER_M = 300;

/** ~meters per degree latitude (WGS84 sphere). */
const M_PER_DEG_LAT = 111_320;

export function isHonestEdgeResolution(method: string | null | undefined): boolean {
  if (!method || typeof method !== "string") return false;
  if (method === "facility-demand") return false;
  return !method.startsWith("busiest-baseline-fallback");
}

/** Prefer kernel overlay_honest when present; else parse edge_resolution (legacy). */
export function overlayHonest(
  overlayHonestFlag: boolean | null | undefined,
  resolution: string | null | undefined,
): boolean {
  if (typeof overlayHonestFlag === "boolean") return overlayHonestFlag;
  return isHonestEdgeResolution(resolution);
}

export function honestAffectedEdgeIds(
  resolution: string | null | undefined,
  ids: unknown,
  overlayHonestFlag?: boolean | null,
): string[] {
  if (!overlayHonest(overlayHonestFlag, resolution)) return [];
  if (!Array.isArray(ids)) return [];
  return ids.filter((id): id is string => typeof id === "string" && id.length > 0);
}

export function filterAffectedFeatures(
  edges: EdgesFeatureCollection | null | undefined,
  edgeIds: string[],
): EdgesFeatureCollection | null {
  if (!edges || edgeIds.length === 0) return null;
  const want = new Set(edgeIds);
  const features = edges.features.filter((f) => {
    const id = f?.properties?.edge_id;
    return typeof id === "string" && want.has(id);
  });
  if (features.length === 0) return null;
  return { type: "FeatureCollection", features };
}

function walkCoords(coords: unknown, out: LonLat[]): void {
  if (!Array.isArray(coords) || coords.length === 0) return;
  if (typeof coords[0] === "number" && typeof coords[1] === "number") {
    out.push([coords[0], coords[1]]);
    return;
  }
  for (const c of coords) walkCoords(c, out);
}

export function expandBboxByMeters(
  bbox: [number, number, number, number],
  bufferM: number = AFFECTED_BUFFER_M,
): [number, number, number, number] {
  const [minLng, minLat, maxLng, maxLat] = bbox;
  const midLat = (minLat + maxLat) / 2;
  const dLat = bufferM / M_PER_DEG_LAT;
  const cos = Math.cos((midLat * Math.PI) / 180);
  const dLng = cos === 0 ? dLat : bufferM / (M_PER_DEG_LAT * Math.abs(cos));
  return [minLng - dLng, minLat - dLat, maxLng + dLng, maxLat + dLat];
}

/** [minLng, minLat, maxLng, maxLat] of affected lines, plus buffer — or null. */
export function affectedBounds(
  collection: EdgesFeatureCollection | null,
  bufferM: number = AFFECTED_BUFFER_M,
): [number, number, number, number] | null {
  if (!collection) return null;
  const pts: LonLat[] = [];
  for (const f of collection.features as Feature[]) {
    walkCoords(f.geometry?.coordinates, pts);
  }
  if (pts.length === 0) return null;
  let minLng = pts[0][0], minLat = pts[0][1], maxLng = pts[0][0], maxLat = pts[0][1];
  for (const [lng, lat] of pts) {
    if (lng < minLng) minLng = lng;
    if (lat < minLat) minLat = lat;
    if (lng > maxLng) maxLng = lng;
    if (lat > maxLat) maxLat = lat;
  }
  return expandBboxByMeters([minLng, minLat, maxLng, maxLat], bufferM);
}

export type ResultsCameraFly =
  | { kind: "stay" }
  | { kind: "corridor"; bbox: [number, number, number, number] };

/** Camera follows the corridor box only (CONTEXT.md Q6). */
export function resultsCameraFly(
  collection: EdgesFeatureCollection | null,
): ResultsCameraFly {
  const bbox = affectedBounds(collection);
  if (bbox) return { kind: "corridor", bbox };
  return { kind: "stay" };
}

/** Unpadded corridor midpoint for the location marker. Null when there is no overlay. */
export function corridorAnchorLonLat(
  collection: EdgesFeatureCollection | null,
): [number, number] | null {
  const bbox = affectedBounds(collection, 0);
  if (!bbox) return null;
  return [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2];
}

/** Pin: honest corridor midpoint only — no gazetteer fallback. */
export function resultsMapPin(corridorAnchor: LonLat | null): LonLat | null {
  return corridorAnchor;
}

export function parseLonLat(value: unknown): LonLat | null {
  if (
    Array.isArray(value) &&
    value.length === 2 &&
    typeof value[0] === "number" &&
    Number.isFinite(value[0]) &&
    typeof value[1] === "number" &&
    Number.isFinite(value[1])
  ) {
    return [value[0], value[1]];
  }
  return null;
}

/** Live run always; hydrate only while the camera is still the city default. */
export function shouldAutoFly(liveSimulation: boolean, atCityDefault: boolean): boolean {
  return liveSimulation || atCityDefault;
}

/** Pan/zoom-in to fit a corridor; never pull the camera farther out. */
export function zoomWithoutPullingOut(currentZoom: number, fittedZoom: number): number {
  return Math.max(currentZoom, fittedZoom);
}

/** Rough Web-Mercator zoom so `spanDeg` fills ~70% of a 800px view. */
export function zoomForBbox(
  bbox: [number, number, number, number],
  minZoom = 11,
  maxZoom = 16,
): number {
  const span = Math.max(bbox[2] - bbox[0], bbox[3] - bbox[1], 1e-6);
  const z = Math.log2(360 / span) - 1.2;
  return Math.min(maxZoom, Math.max(minZoom, z));
}
