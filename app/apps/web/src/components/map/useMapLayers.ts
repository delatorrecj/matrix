/**
 * useMapLayers — assemble the active map DATA layers from toggle state.
 *
 * Owns exactly three layers: flood zones, congestion choropleth, confidence
 * heatmap (bottom → top in that order, so area underlays sit beneath the road
 * choropleth and the confidence overlay reads on top). The `buildings` and
 * `agents` toggles are owned by the pages (PolygonLayer / TripsLayer) and are
 * ignored here, as is any unknown toggle id — the LayerLegend can grow
 * additively without touching this hook.
 *
 * Honesty rules (PRD-F14):
 *   - A toggled-on layer whose data is absent/empty is simply omitted — no
 *     crash, no placeholder rendering.
 *   - Factories never invent values for unkeyed features (see each factory).
 *
 * Per-run caching note: callers hold the data (edge counts, cells, GeoJSON) in
 * their own state. The scenario page resets its accumulated state on every
 * `runAttempt` (src/lib/simulationRun.ts) — pass the post-reset values in and
 * this hook re-assembles automatically; nothing is cached here across runs.
 */

import { useMemo } from "react";
import type { Layer } from "@deck.gl/core";
import { congestionLayer } from "./congestionLayer";
import { confidenceLayer } from "./confidenceLayer";
import { floodLayer } from "./floodLayer";
import type { MapLayerData, MapLayerToggles } from "./types";

export function useMapLayers(
  toggles: MapLayerToggles,
  data: MapLayerData
): Layer[] {
  const { congestion, confidence, flood } = toggles ?? {};
  const { edgesGeoJSON, edgeCounts, baselineCounts, confidenceCells, floodGeoJSON } =
    data ?? {};

  return useMemo(() => {
    const layers: Layer[] = [];

    if (flood && floodGeoJSON) {
      const layer = floodLayer(floodGeoJSON);
      if (layer) layers.push(layer);
    }

    if (congestion && edgesGeoJSON && edgeCounts) {
      const layer = congestionLayer(
        edgesGeoJSON,
        edgeCounts,
        baselineCounts ?? undefined
      );
      if (layer) layers.push(layer);
    }

    if (confidence && confidenceCells && confidenceCells.length > 0) {
      layers.push(...confidenceLayer(confidenceCells));
    }

    return layers;
  }, [
    congestion,
    confidence,
    flood,
    edgesGeoJSON,
    edgeCounts,
    baselineCounts,
    confidenceCells,
    floodGeoJSON,
  ]);
}
