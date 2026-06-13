/**
 * Flood-zone overlay — translucent fill + outline for flood-zone polygons.
 *
 * Data contract (see public/layers/README.md): a GeoJSON FeatureCollection of
 * Polygon / MultiPolygon features. When a feature carries
 * `properties.severity` ("high" | "medium"), high-severity zones are filled
 * slightly stronger; anything else gets the default fill — severity is a
 * rendering hint, never invented.
 *
 * Color: the app's primary blue (--color-primary #1D4ED8, mirrored in
 * colors.ts as TOKEN_RGB.primary) — translucent so the basemap reads through.
 */

import { GeoJsonLayer } from "@deck.gl/layers";
import { TOKEN_RGB, withAlpha } from "./colors";
import type { FeatureCollection } from "./types";

export const FLOOD_LAYER_ID = "flood-zones";

// deck.gl invokes accessors with its own generic feature (properties typed
// `any`); type against the minimal shape we read so the accessor signature
// accepts it (a narrower local `Feature` is rejected by contravariance).
type FloodAccessorFeature = { properties?: { severity?: unknown } | null };

const FILL_ALPHA_DEFAULT = 60;
const FILL_ALPHA_HIGH = 95;
const OUTLINE_ALPHA = 180;

/**
 * Build the flood-zone overlay layer.
 * Returns null when there is nothing renderable (no features).
 */
export function floodLayer(
  floodGeoJSON: FeatureCollection
): GeoJsonLayer | null {
  const features = Array.isArray(floodGeoJSON?.features)
    ? floodGeoJSON.features
    : [];
  if (features.length === 0) return null;

  return new GeoJsonLayer({
    id: FLOOD_LAYER_ID,
    data: floodGeoJSON,
    filled: true,
    stroked: true,
    getFillColor: (f: FloodAccessorFeature) =>
      withAlpha(
        TOKEN_RGB.primary,
        f?.properties?.severity === "high" ? FILL_ALPHA_HIGH : FILL_ALPHA_DEFAULT
      ),
    getLineColor: withAlpha(TOKEN_RGB.primary, OUTLINE_ALPHA),
    getLineWidth: 1,
    lineWidthUnits: "pixels",
    lineWidthMinPixels: 1,
    pickable: true,
  });
}
