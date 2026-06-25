"use client";

import { useEffect, useRef } from "react";
import { Copy, Crosshair, MapPin } from "lucide-react";

export interface MapContextMenuPosition {
  x: number;
  y: number;
}

export interface MapLngLat {
  lng: number;
  lat: number;
}

export interface MapContextMenuProps {
  position: MapContextMenuPosition;
  lngLat: MapLngLat;
  onClose: () => void;
  onCopyCoordinates: (lngLat: MapLngLat) => void;
  onCenterHere: (lngLat: MapLngLat) => void;
  /** When omitted, "Use this location" is hidden (e.g. on /scenario). */
  onUseLocation?: (lngLat: MapLngLat) => void;
}

export function MapContextMenu({
  position,
  lngLat,
  onClose,
  onCopyCoordinates,
  onCenterHere,
  onUseLocation,
}: MapContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handlePointerDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const handleScroll = () => onClose();
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("scroll", handleScroll, true);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("scroll", handleScroll, true);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  const coordLabel = `${lngLat.lat.toFixed(5)}, ${lngLat.lng.toFixed(5)}`;

  return (
    <div
      ref={menuRef}
      role="menu"
      aria-label="Map actions"
      data-testid="map-context-menu"
      className="glass-strong absolute z-40 min-w-[200px] rounded-lg py-1 shadow-lg"
      style={{ left: position.x, top: position.y }}
    >
      <div className="px-3 py-2 border-b border-border/60">
        <span className="text-[10px] uppercase tracking-wider text-text-muted block mb-0.5">
          Location
        </span>
        <span className="text-xs font-mono text-foreground">{coordLabel}</span>
      </div>
      <button
        type="button"
        role="menuitem"
        className="w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-surface-elevated transition-colors"
        onClick={() => {
          onCopyCoordinates(lngLat);
          onClose();
        }}
      >
        <Copy className="w-4 h-4 text-text-muted shrink-0" aria-hidden="true" />
        Copy coordinates
      </button>
      <button
        type="button"
        role="menuitem"
        className="w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-surface-elevated transition-colors"
        onClick={() => {
          onCenterHere(lngLat);
          onClose();
        }}
      >
        <Crosshair className="w-4 h-4 text-text-muted shrink-0" aria-hidden="true" />
        Center here
      </button>
      {onUseLocation && (
        <button
          type="button"
          role="menuitem"
          className="w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-surface-elevated transition-colors"
          onClick={() => {
            onUseLocation(lngLat);
            onClose();
          }}
        >
          <MapPin className="w-4 h-4 text-text-muted shrink-0" aria-hidden="true" />
          Use this location
        </button>
      )}
    </div>
  );
}
