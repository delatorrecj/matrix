import type { Map as MaplibreMap } from "maplibre-gl";

/**
 * Shared map tile style URLs for the MATRIX 3D simulator.
 *
 * Both MAP_STYLE_LIGHT and MAP_STYLE_DARK are exported so every page
 * (main cockpit + scenario) can import them from a single source of truth.
 *
 * Usage:
 *   const { theme } = useTheme();
 *   const mapStyle = theme === "dark" ? MAP_STYLE_DARK : MAP_STYLE_LIGHT;
 *
 * Passing the reactive `mapStyle` to <Map mapStyle={mapStyle} reuseMaps /> causes
 * react-map-gl to call map.setStyle() internally — switching tiles live without
 * resetting pan/zoom or active Deck.gl overlay layers.
 */

/** Light basemap — OpenFreeMap Liberty style (low-saturation, planner-grade). */
export const MAP_STYLE_LIGHT = "https://tiles.openfreemap.org/styles/liberty";

/** Dark basemap — OpenFreeMap Dark style (free, no API key required). */
export const MAP_STYLE_DARK = "https://tiles.openfreemap.org/styles/dark";

export const BUILDING_3D_LAYER_ID = "building-3d";

export type MapTheme = "dark" | "light";

/** Extrusion tint matched to the active basemap theme. */
export function getBuilding3dExtrusionColor(theme: MapTheme): string {
  return theme === "dark" ? "rgb(40, 40, 40)" : "rgb(210, 210, 210)";
}

/**
 * Ensure native OpenMapTiles building extrusions exist and match theme/visibility.
 * Re-run on `style.load` because `setStyle()` drops custom layers.
 */
export function syncBuilding3dLayer(
  map: MaplibreMap,
  theme: MapTheme,
  visible = true,
): void {
  const color = getBuilding3dExtrusionColor(theme);

  if (!map.getLayer(BUILDING_3D_LAYER_ID)) {
    map.addLayer({
      id: BUILDING_3D_LAYER_ID,
      source: "openmaptiles",
      "source-layer": "building",
      type: "fill-extrusion",
      minzoom: 14,
      paint: {
        // Some OpenMapTiles building features carry a null render_min_height /
        // render_height; coalesce to 0 so MapLibre's expression evaluator does not
        // log "Expected value to be of type number, but found null".
        "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0],
        "fill-extrusion-color": color,
        "fill-extrusion-height": ["coalesce", ["get", "render_height"], 0],
        "fill-extrusion-opacity": 0.8,
      },
    });
  } else {
    map.setPaintProperty(BUILDING_3D_LAYER_ID, "fill-extrusion-color", color);
  }

  map.setLayoutProperty(BUILDING_3D_LAYER_ID, "visibility", visible ? "visible" : "none");
}

/**
 * Silence MapLibre "Image '…' could not be loaded" console warnings emitted by
 * basemap styles that reference a sprite image missing from their sprite sheet
 * (e.g. OpenFreeMap Liberty's `wood-pattern`). Registers a 1×1 transparent pixel
 * for any missing image so the style renders identically, minus the console noise.
 *
 * Listener lives on the Map instance (survives setStyle), so register once and
 * call the returned disposer on teardown. No-op-safe if the image already exists.
 */
export function registerMissingImageFallback(map: MaplibreMap): () => void {
  const handler = (e: { id: string }) => {
    if (!map.hasImage(e.id)) {
      map.addImage(e.id, { width: 1, height: 1, data: new Uint8Array(4) });
    }
  };
  map.on("styleimagemissing", handler);
  return () => map.off("styleimagemissing", handler);
}
