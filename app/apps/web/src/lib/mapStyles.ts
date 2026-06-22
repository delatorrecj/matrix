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
        "fill-extrusion-base": ["get", "render_min_height"],
        "fill-extrusion-color": color,
        "fill-extrusion-height": ["get", "render_height"],
        "fill-extrusion-opacity": 0.8,
      },
    });
  } else {
    map.setPaintProperty(BUILDING_3D_LAYER_ID, "fill-extrusion-color", color);
  }

  map.setLayoutProperty(BUILDING_3D_LAYER_ID, "visibility", visible ? "visible" : "none");
}
