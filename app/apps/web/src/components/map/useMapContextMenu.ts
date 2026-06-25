"use client";

import { useCallback, useRef, useState, type RefObject } from "react";
import type { MapRef } from "react-map-gl/maplibre";
import type { MapContextMenuPosition, MapLngLat } from "./MapContextMenu";

interface UseMapContextMenuOptions {
  mapRef: RefObject<MapRef | null>;
}

export function useMapContextMenu({ mapRef }: UseMapContextMenuOptions) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [menuPosition, setMenuPosition] = useState<MapContextMenuPosition | null>(null);
  const [menuLngLat, setMenuLngLat] = useState<MapLngLat | null>(null);

  const closeMenu = useCallback(() => {
    setMenuPosition(null);
    setMenuLngLat(null);
  }, []);

  const handleContextMenu = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const map = mapRef.current?.getMap();
      const container = containerRef.current;
      if (!map || !container) return;

      e.preventDefault();
      e.stopPropagation();

      const rect = container.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const lngLatPoint = map.unproject([x, y]);

      setMenuPosition({ x, y });
      setMenuLngLat({ lng: lngLatPoint.lng, lat: lngLatPoint.lat });
    },
    [mapRef]
  );

  return {
    containerRef,
    menuPosition,
    menuLngLat,
    closeMenu,
    handleContextMenu,
  };
}
