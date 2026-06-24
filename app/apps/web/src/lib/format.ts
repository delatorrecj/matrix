/**
 * Presentation-layer number & language formatter (CR-010).
 *
 * The kernel streams raw floats (e.g. -0.7000000000000001, -0.0069731280430000014).
 * This module turns them into honest, readable strings WITHOUT mutating the data:
 * the raw value always survives in the Inspect drawer (glass box, PRD-F14).
 *
 * Two precisions:
 *   • Summary  — registry decimals; near-zero collapses to "No meaningful change".
 *   • Analytics (precise) — ~6 significant figures, trimmed; never collapses.
 */

import { getMetricMeta, type Polarity } from "@/lib/metrics";
import { toConfidenceLevel, type ConfidenceLevel } from "@/components/ConfidenceChip";

export interface FormattedValue {
  /** Display string, e.g. "+0.07", "−700", "No meaningful change". */
  display: string;
  /** True when the value fell inside the metric's negligible band (Summary only). */
  negligible: boolean;
}

const NEGLIGIBLE_LABEL = "No meaningful change";

/** −0 → 0; keeps real values intact. */
function normalizeZero(n: number): number {
  return Object.is(n, -0) ? 0 : n;
}

/** Round to a fixed number of decimals and group thousands, with an optional sign. */
function fixed(value: number, decimals: number, signed: boolean): string {
  const v = normalizeZero(Number(value.toFixed(decimals)));
  const body = v.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  if (signed && v > 0) return `+${body}`;
  return body; // toLocaleString already renders the minus sign for negatives
}

/** ~`sig` significant figures, trailing zeros trimmed — for the Analytics detail. */
function significant(value: number, sig: number, signed: boolean): string {
  const v = normalizeZero(value);
  if (v === 0) return "0";
  // toPrecision keeps it readable (no 17-digit float artifacts) but detailed.
  let body = Number(v.toPrecision(sig)).toLocaleString("en-US", {
    maximumFractionDigits: 20,
  });
  if (signed && v > 0) body = `+${body}`;
  return body;
}

/**
 * Format a single metric value.
 * @param precise  Analytics detail (more sig figs, no negligible collapse).
 * @param signed   Prefix non-negative values with "+" (deltas).
 */
export function formatMetricValue(
  value: number,
  equationId: string | undefined,
  opts: { precise?: boolean; signed?: boolean } = {},
): FormattedValue {
  const { precise = false, signed = true } = opts;
  if (!Number.isFinite(value)) return { display: "—", negligible: false };

  const meta = getMetricMeta(equationId);
  const decimals = meta?.decimals ?? defaultDecimals(value);
  const band = meta?.negligible ?? 0;

  if (!precise && band > 0 && Math.abs(value) < band) {
    return { display: NEGLIGIBLE_LABEL, negligible: true };
  }

  if (precise) {
    return { display: significant(value, 6, signed), negligible: false };
  }
  return { display: fixed(value, decimals, signed), negligible: false };
}

/** Heuristic decimals when a metric isn't in the registry. */
function defaultDecimals(value: number): number {
  const a = Math.abs(value);
  if (a === 0 || a >= 10) return 0; // whole-ish magnitudes read cleaner without a decimal
  if (a >= 1) return 1;
  if (a >= 0.01) return 2;
  return 4;
}

/** Format a [lo, hi] range as "lo to hi" (GOV.UK style — "to", not a hyphen). */
export function formatRange(
  range: [number, number] | null | undefined,
  equationId: string | undefined,
  opts: { precise?: boolean } = {},
): string {
  if (!range || range.length !== 2 || !range.every(Number.isFinite)) return "";
  const lo = formatMetricValue(range[0], equationId, { precise: opts.precise, signed: false }).display;
  const hi = formatMetricValue(range[1], equationId, { precise: opts.precise, signed: false }).display;
  return `${lo} to ${hi}`;
}

export type DirectionTone = "good" | "bad" | "neutral";

export interface Direction {
  word: string;
  tone: DirectionTone;
}

/**
 * Plain-language direction for the Summary "so what" line. Uses the metric's
 * polarity so we never imply a value judgment for a neutral metric (e.g. land
 * value rising is good for owners, bad for renters → just "rises").
 */
export function directionFor(value: number, equationId: string | undefined, negligible: boolean): Direction {
  if (negligible || value === 0) return { word: "about the same", tone: "neutral" };
  const polarity: Polarity = getMetricMeta(equationId)?.polarity ?? "neutral";
  const up = value > 0;
  if (polarity === "neutral") return { word: up ? "rises" : "falls", tone: "neutral" };
  const better = (polarity === "good-up" && up) || (polarity === "good-down" && !up);
  return better ? { word: "improves", tone: "good" } : { word: "worsens", tone: "bad" };
}

/** Spelled-out confidence label (GOV.UK Analysis Function — never a bare letter). */
export function confidenceWord(conf: string | undefined): ConfidenceLevel {
  return toConfidenceLevel(conf);
}

/** Plain-language explanation of a confidence level for tooltips/captions. */
export function confidenceSentence(level: ConfidenceLevel): string {
  switch (level) {
    case "High":
      return "We're confident in this estimate.";
    case "Medium":
      return "A reasonable estimate — treat it as indicative, not exact.";
    case "Low":
      return "A rough indication only — not precise enough to rank options.";
  }
}
