/** Map data layers — factories, hook, and static-layer loader. See README.md. */

export { congestionLayer, CONGESTION_LAYER_ID } from "./congestionLayer";
export {
  confidenceLayer,
  confidenceCellsFromGeoJSON,
  normalizeConfidenceTier,
  CONFIDENCE_POLYGON_LAYER_ID,
  CONFIDENCE_GRID_LAYER_ID,
} from "./confidenceLayer";
export type { ConfidenceLayerOptions } from "./confidenceLayer";
export { floodLayer, FLOOD_LAYER_ID } from "./floodLayer";
export { useMapLayers } from "./useMapLayers";
export { fetchStaticLayer, isFeatureCollection } from "./fetchStaticLayer";
export type { StaticLayerName } from "./fetchStaticLayer";
export {
  TOKEN_RGB,
  CONFIDENCE_RGB,
  NO_DATA_RGBA,
  sequentialCongestionRGB,
  divergingCongestionRGB,
  lerpRGB,
  withAlpha,
} from "./colors";
export type { RGB, RGBA } from "./colors";
export type {
  ConfidenceCell,
  ConfidenceTier,
  EdgeCounts,
  EdgeFeature,
  EdgesFeatureCollection,
  Feature,
  FeatureCollection,
  Geometry,
  LonLat,
  MapLayerData,
  MapLayerToggles,
} from "./types";
