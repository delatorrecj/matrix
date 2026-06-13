/**
 * Color ramps for the map data layers.
 *
 * deck.gl colors are RGBA arrays — CSS variables don't reach WebGL — so the
 * design tokens from `src/app/globals.css` (@theme) are mirrored here as RGB.
 * Keep the two in sync; the token name is recorded next to each value.
 *
 * Token → meaning mapping (documented contract):
 *   --color-success #15803D → High confidence / calm traffic / improvement
 *   --color-warning #B45309 → Medium confidence / moderate congestion
 *   --color-error   #B91C1C → Low confidence / heavy congestion / worsening
 *   --color-primary #1D4ED8 → flood water (matches the app's primary blue)
 *   --color-text-muted #71717A → neutral "no change" midpoint (delta mode)
 */

export type RGB = [number, number, number];
export type RGBA = [number, number, number, number];

export const TOKEN_RGB: Record<
  "success" | "warning" | "error" | "primary" | "neutral",
  RGB
> = {
  /** --color-success #15803D */
  success: [21, 128, 61],
  /** --color-warning #B45309 */
  warning: [180, 83, 9],
  /** --color-error #B91C1C */
  error: [185, 28, 28],
  /** --color-primary #1D4ED8 */
  primary: [29, 78, 216],
  /** --color-text-muted #71717A */
  neutral: [113, 113, 122],
};

/** Fully transparent — the honest rendering for "no data for this feature". */
export const NO_DATA_RGBA: RGBA = [0, 0, 0, 0];

function clamp01(t: number): number {
  if (!Number.isFinite(t)) return 0;
  return t < 0 ? 0 : t > 1 ? 1 : t;
}

export function lerpRGB(a: RGB, b: RGB, t: number): RGB {
  const k = clamp01(t);
  return [
    Math.round(a[0] + (b[0] - a[0]) * k),
    Math.round(a[1] + (b[1] - a[1]) * k),
    Math.round(a[2] + (b[2] - a[2]) * k),
  ];
}

/**
 * Sequential calm→congested ramp for ABSOLUTE per-edge counts.
 * t in [0, 1]: 0 → success (calm), 0.5 → warning, 1 → error (congested).
 */
export function sequentialCongestionRGB(t: number): RGB {
  const k = clamp01(t);
  return k <= 0.5
    ? lerpRGB(TOKEN_RGB.success, TOKEN_RGB.warning, k * 2)
    : lerpRGB(TOKEN_RGB.warning, TOKEN_RGB.error, (k - 0.5) * 2);
}

/**
 * Diverging ramp for DELTA-vs-baseline counts.
 * t in [-1, 1]: -1 → success (calmer than baseline), 0 → neutral (no change),
 * +0.5 → warning, +1 → error (more congested than baseline).
 */
export function divergingCongestionRGB(t: number): RGB {
  const k = !Number.isFinite(t) ? 0 : t < -1 ? -1 : t > 1 ? 1 : t;
  if (k < 0) return lerpRGB(TOKEN_RGB.neutral, TOKEN_RGB.success, -k);
  if (k === 0) return [...TOKEN_RGB.neutral] as RGB;
  return k <= 0.5
    ? lerpRGB(TOKEN_RGB.neutral, TOKEN_RGB.warning, k * 2)
    : lerpRGB(TOKEN_RGB.warning, TOKEN_RGB.error, (k - 0.5) * 2);
}

/** Confidence tier → token color. H=success, M=warning, L=error. */
export const CONFIDENCE_RGB: Record<"H" | "M" | "L", RGB> = {
  H: TOKEN_RGB.success,
  M: TOKEN_RGB.warning,
  L: TOKEN_RGB.error,
};

export function withAlpha(rgb: RGB, alpha: number): RGBA {
  const a = Math.round(Math.min(255, Math.max(0, alpha)));
  return [rgb[0], rgb[1], rgb[2], a];
}
