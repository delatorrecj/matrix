/**
 * Halo on the SUMO edges the scenario actually edited. Magenta
 * (`TOKEN_RGB.affected`) so it does not read as agent trajectories or
 * the old location marker (both primary cobalt). Square caps so a
 * segment end is not a circular "pin". Not pickable — Inspect stays
 * on metrics. Congestion choropleth stays underneath.
 */

import { GeoJsonLayer } from "@deck.gl/layers";
import { TOKEN_RGB, withAlpha } from "./colors";
import type { EdgesFeatureCollection } from "./types";

export const AFFECTED_EDGES_LAYER_ID = "affected-edges-halo";
/** Translucent wash so congestion/agents read through — a halo, not a solid stroke. */
export const AFFECTED_HALO_ALPHA = 96;

export function affectedEdgesLayer(
  data: EdgesFeatureCollection | null,
): GeoJsonLayer | null {
  if (!data || data.features.length === 0) return null;
  return new GeoJsonLayer({
    id: AFFECTED_EDGES_LAYER_ID,
    data,
    filled: false,
    stroked: true,
    getLineColor: withAlpha(TOKEN_RGB.affected, AFFECTED_HALO_ALPHA),
    getLineWidth: 12,
    lineWidthUnits: "pixels",
    lineWidthMinPixels: 6,
    lineCapRounded: false,
    pickable: false,
  });
}
