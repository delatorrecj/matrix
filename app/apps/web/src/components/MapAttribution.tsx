/**
 * Map attribution rendered inside our own panels instead of MapLibre's default
 * floating control (which paints a jarring white box over the dark map). Disable
 * the built-in control with `attributionControl={false}` on <Map> and place this
 * at the bottom of a panel. Keeps the OpenStreetMap (ODbL), OpenMapTiles, and
 * OpenFreeMap credits visible and linked, as their licenses require.
 */
export function MapAttribution({ className = "" }: { className?: string }) {
  const link =
    "underline-offset-2 hover:text-text-muted hover:underline transition-colors";
  return (
    <p className={`text-[10px] leading-tight text-text-muted/70 ${className}`}>
      ©{" "}
      <a
        href="https://www.openstreetmap.org/copyright"
        target="_blank"
        rel="noopener noreferrer"
        className={link}
      >
        OpenStreetMap
      </a>{" "}
      contributors,{" "}
      <a
        href="https://openmaptiles.org/"
        target="_blank"
        rel="noopener noreferrer"
        className={link}
      >
        OpenMapTiles
      </a>
      ,{" "}
      <a
        href="https://openfreemap.org/"
        target="_blank"
        rel="noopener noreferrer"
        className={link}
      >
        OpenFreeMap
      </a>
    </p>
  );
}
