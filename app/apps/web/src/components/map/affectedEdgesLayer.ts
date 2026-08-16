/**
 * Halo on the SUMO edges the scenario actually edited. Not pickable —
 * Inspect stays on metrics. Congestion choropleth stays underneath.
 */

import { GeoJsonLayer } from "@deck.gl/layers";
import { TOKEN_RGB, withAlpha } from "./colors";
import type { EdgesFeatureCollection } from "./types";

export const AFFECTED_EDGES_LAYER_ID = "affected-edges-halo";

export function affectedEdgesLayer(
  data: EdgesFeatureCollection | null,
): GeoJsonLayer | null {
  if (!data || data.features.length === 0) return null;
  return new GeoJsonLayer({
    id: AFFECTED_EDGES_LAYER_ID,
    data,
    filled: false,
    stroked: true,
    getLineColor: withAlpha(TOKEN_RGB.primary, 230),
    getLineWidth: 8,
    lineWidthUnits: "pixels",
    lineWidthMinPixels: 4,
    lineCapRounded: true,
    pickable: false,
  });
}
