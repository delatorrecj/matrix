/** Map data layers — factories, hook, and static-layer loader. See README.md. */

export { congestionLayer, CONGESTION_LAYER_ID } from "./congestionLayer";
export { affectedEdgesLayer, AFFECTED_EDGES_LAYER_ID } from "./affectedEdgesLayer";
export {
  AFFECTED_BUFFER_M,
  affectedBounds,
  filterAffectedFeatures,
  honestAffectedEdgeIds,
  isHonestEdgeResolution,
  LOI_FOCUS_ZOOM,
  resultsCameraFly,
  resultsMapPin,
  parseLonLat,
  corridorAnchorLonLat,
  overlayHonest,
  shouldAutoFly,
  zoomForBbox,
  zoomWithoutPullingOut,
} from "./affectedCorridor";
export type { ResultsCameraFly } from "./affectedCorridor";
export { floodLayer, FLOOD_LAYER_ID } from "./floodLayer";
export { useMapLayers } from "./useMapLayers";
export { fetchStaticLayer, isFeatureCollection } from "./fetchStaticLayer";
export type { StaticLayerName } from "./fetchStaticLayer";
export {
  TOKEN_RGB,
  NO_DATA_RGBA,
  sequentialCongestionRGB,
  divergingCongestionRGB,
  lerpRGB,
  withAlpha,
} from "./colors";
export type { RGB, RGBA } from "./colors";
export type {
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
