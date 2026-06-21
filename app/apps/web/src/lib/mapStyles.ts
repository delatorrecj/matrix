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

/** Dark basemap — CartoDB Dark Matter GL style (free, no API key required). */
export const MAP_STYLE_DARK =
  "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
