/** Shared map view defaults for the scenario results page. */
export const SCENARIO_DEFAULT_VIEW = {
  longitude: 122.56,
  latitude: 10.72,
  zoom: 13,
  pitch: 45,
  bearing: 0,
};

export const ILOILO_MAP_BOUNDS = {
  minLng: 122.48,
  maxLng: 122.62,
  minLat: 10.64,
  maxLat: 10.79,
  minZoom: 11,
};

/** Clamp pan/zoom to the Iloilo pilot bbox. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function clampScenarioViewState({ viewState }: any) {
  return {
    ...viewState,
    longitude: Math.min(
      Math.max(viewState.longitude, ILOILO_MAP_BOUNDS.minLng),
      ILOILO_MAP_BOUNDS.maxLng,
    ),
    latitude: Math.min(
      Math.max(viewState.latitude, ILOILO_MAP_BOUNDS.minLat),
      ILOILO_MAP_BOUNDS.maxLat,
    ),
    zoom: Math.max(viewState.zoom, ILOILO_MAP_BOUNDS.minZoom),
  };
}
