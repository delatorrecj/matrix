/**
 * Congestion choropleth — colors road segments by the kernel's per-edge
 * vehicle counts (`Trajectory.edge_counts`), or by the delta against the
 * nightly baseline when `baselineCounts` is provided.
 *
 * Data contract (see public/layers/README.md):
 *   - `edgesGeoJSON`: FeatureCollection of LineString / MultiLineString
 *     features, each carrying the SUMO edge id in `properties.edge_id`
 *     matching the keys of `edge_counts`.
 *   - An edge id absent from the counts means SUMO recorded no vehicle
 *     entering that edge → rendered as count 0 (calm), not skipped.
 *   - A feature WITHOUT `properties.edge_id` cannot be keyed to any count and
 *     is rendered fully transparent (NO_DATA_RGBA) — never given a guessed
 *     color (glass box, PRD-F14).
 *
 * Encoding (token mapping documented in colors.ts):
 *   - Absolute mode: sequential success→warning→error, normalized by the max
 *     count across the supplied features.
 *   - Delta mode: diverging success←neutral→warning→error, normalized by the
 *     max |delta| across the supplied features.
 *   - Line width and opacity also scale with the normalized value so calm
 *     edges stay subtle over the basemap.
 */

import { GeoJsonLayer } from "@deck.gl/layers";
import {
  NO_DATA_RGBA,
  RGBA,
  divergingCongestionRGB,
  sequentialCongestionRGB,
  withAlpha,
} from "./colors";
import type { EdgeCounts, EdgesFeatureCollection } from "./types";

export const CONGESTION_LAYER_ID = "congestion-choropleth";

// deck.gl invokes accessors with its own generic feature (properties typed
// `any`), so they are typed against the minimal structural shape we actually
// read rather than the narrower `EdgeFeature` — a narrower parameter is rejected
// by the GeoJsonLayer accessor signature (contravariance). The edge id is read
// defensively, so a feature without `edge_id` is handled without a guessed
// colour (glass box, PRD-F14).
type EdgeAccessorFeature = { properties?: { edge_id?: unknown } | null };

function edgeIdOf(feature: EdgeAccessorFeature | undefined): string | null {
  const id = feature?.properties?.edge_id;
  return typeof id === "string" && id.length > 0 ? id : null;
}

function countOf(counts: EdgeCounts, id: string): number {
  const v = counts[id];
  return typeof v === "number" && Number.isFinite(v) ? v : 0;
}

/**
 * Build the congestion choropleth layer.
 * Returns null when there is nothing renderable (no features).
 */
export function congestionLayer(
  edgesGeoJSON: EdgesFeatureCollection,
  edgeCounts: EdgeCounts,
  baselineCounts?: EdgeCounts
): GeoJsonLayer | null {
  const features = Array.isArray(edgesGeoJSON?.features)
    ? edgesGeoJSON.features
    : [];
  if (features.length === 0) return null;

  const deltaMode = baselineCounts !== undefined;

  // Normalized value per edge id, computed once over the *rendered* features.
  const values = new Map<string, number>();
  let maxAbs = 0;
  for (const f of features) {
    const id = edgeIdOf(f);
    if (id === null || values.has(id)) continue;
    const value = deltaMode
      ? countOf(edgeCounts, id) - countOf(baselineCounts, id)
      : countOf(edgeCounts, id);
    values.set(id, value);
    const abs = Math.abs(value);
    if (abs > maxAbs) maxAbs = abs;
  }

  /** Normalized t: [0,1] absolute, [-1,1] delta. 0 everywhere when flat. */
  const tOf = (id: string): number => {
    const value = values.get(id) ?? 0;
    return maxAbs === 0 ? 0 : value / maxAbs;
  };

  const getLineColor = (f: EdgeAccessorFeature): RGBA => {
    const id = edgeIdOf(f);
    if (id === null) return NO_DATA_RGBA;
    const t = tOf(id);
    const rgb = deltaMode
      ? divergingCongestionRGB(t)
      : sequentialCongestionRGB(t);
    // Calm edges stay subtle (alpha 70); the busiest edge is near-opaque (220).
    return withAlpha(rgb, 70 + 150 * Math.abs(t));
  };

  const getLineWidth = (f: EdgeAccessorFeature): number => {
    const id = edgeIdOf(f);
    if (id === null) return 0;
    return 2 + 6 * Math.abs(tOf(id));
  };

  return new GeoJsonLayer({
    id: CONGESTION_LAYER_ID,
    data: edgesGeoJSON,
    filled: false,
    stroked: true,
    getLineColor,
    getLineWidth,
    lineWidthUnits: "pixels",
    lineWidthMinPixels: 1,
    lineCapRounded: true,
    pickable: true,
    updateTriggers: {
      getLineColor: [edgeCounts, baselineCounts ?? null],
      getLineWidth: [edgeCounts, baselineCounts ?? null],
    },
  });
}
