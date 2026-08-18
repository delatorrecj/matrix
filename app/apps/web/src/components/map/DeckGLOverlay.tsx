"use client";

import { useControl } from "react-map-gl/maplibre";
import { MapboxOverlay, type MapboxOverlayProps } from "@deck.gl/mapbox";

/**
 * deck.gl overlay on a MapLibre map (single basemap GL context).
 * Map is the parent so tiles paint even when overlay layers are empty.
 */
export function DeckGLOverlay(props: MapboxOverlayProps) {
  const overlay = useControl<MapboxOverlay>(() => new MapboxOverlay(props));
  overlay.setProps(props);
  return null;
}
