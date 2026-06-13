/**
 * fetchStaticLayer — load a static GeoJSON layer from `public/layers/`.
 *
 * Tries `/layers/{name}.geojson` (served by Next.js from `public/`) and
 * resolves to the parsed FeatureCollection, or to `null` for ANY miss:
 * invalid name, network failure, non-2xx response, unparseable JSON, or a
 * body that is not a FeatureCollection. A missing optional layer is a
 * graceful no-op, never a crash — `useMapLayers` then simply omits the layer.
 *
 * Expected files and their schemas are documented in public/layers/README.md.
 */

import type { Feature, FeatureCollection } from "./types";

/** Known static layer names shipped under public/layers/ (open set). */
export type StaticLayerName = "edges" | "flood" | "confidence" | (string & {});

const NAME_RE = /^[a-z0-9][a-z0-9_-]*$/i;

export function isFeatureCollection(value: unknown): value is FeatureCollection {
  if (value === null || typeof value !== "object") return false;
  const fc = value as Record<string, unknown>;
  if (fc.type !== "FeatureCollection" || !Array.isArray(fc.features)) {
    return false;
  }
  return (fc.features as unknown[]).every((f) => {
    if (f === null || typeof f !== "object") return false;
    const feat = f as Partial<Feature>;
    return feat.type === "Feature" && typeof feat.geometry === "object";
  });
}

export async function fetchStaticLayer(
  name: StaticLayerName
): Promise<FeatureCollection | null> {
  if (typeof name !== "string" || !NAME_RE.test(name)) return null;

  let response: Response;
  try {
    response = await fetch(`/layers/${name}.geojson`);
  } catch {
    return null; // network failure → graceful no-op
  }
  if (!response.ok) return null; // 404 (layer not shipped) etc.

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return null; // not JSON
  }
  return isFeatureCollection(body) ? body : null;
}
