/** Per-scenario camera so a refresh does not reset pan/zoom. */

export type PersistedMapView = {
  longitude: number;
  latitude: number;
  zoom: number;
  pitch: number;
  bearing: number;
};

const KEY_PREFIX = "matrix:map-view:";

function key(scenarioId: string): string {
  return `${KEY_PREFIX}${scenarioId}`;
}

function isPersistedMapView(value: unknown): value is PersistedMapView {
  if (value === null || typeof value !== "object") return false;
  if (
    !("longitude" in value) ||
    !("latitude" in value) ||
    !("zoom" in value) ||
    !("pitch" in value) ||
    !("bearing" in value)
  ) {
    return false;
  }
  return (
    typeof value.longitude === "number" &&
    typeof value.latitude === "number" &&
    typeof value.zoom === "number" &&
    typeof value.pitch === "number" &&
    typeof value.bearing === "number"
  );
}

export function isCityDefaultView(
  view: { longitude: number; latitude: number; zoom: number },
  city: { longitude: number; latitude: number; zoom: number } = {
    longitude: 122.56,
    latitude: 10.72,
    zoom: 13,
  },
): boolean {
  return (
    Math.abs(view.longitude - city.longitude) < 1e-4 &&
    Math.abs(view.latitude - city.latitude) < 1e-4 &&
    Math.abs(view.zoom - city.zoom) < 1e-4
  );
}

export function loadMapView(scenarioId: string): PersistedMapView | null {
  if (typeof sessionStorage === "undefined" || !scenarioId) return null;
  try {
    const raw = sessionStorage.getItem(key(scenarioId));
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    return isPersistedMapView(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function saveMapView(scenarioId: string, view: PersistedMapView): void {
  if (typeof sessionStorage === "undefined" || !scenarioId) return;
  try {
    sessionStorage.setItem(key(scenarioId), JSON.stringify(view));
  } catch {
    // Quota / private mode — camera memory is best-effort.
  }
}
