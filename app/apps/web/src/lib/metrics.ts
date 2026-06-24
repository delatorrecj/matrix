/**
 * Metric presentation registry (CR-010).
 *
 * Maps each kernel equation id (BEH-1 … SOCI-4) to its PRESENTATION metadata:
 * a plain-language label, display precision, a "negligible band", and a polarity.
 *
 * GLASS BOX (PRD-F14): this is presentation only. It never redefines a metric's
 * meaning, value, unit, or confidence — those come from the kernel
 * (methods-matrix.md is canonical). The raw value/range/equation_id always
 * survive untouched in the Inspect drawer and the Analytics view. Labels here
 * are human aliases for the Summary surface; the equation id remains the key.
 */

import type { DimensionId } from "@/lib/simulationRun";

/**
 * Whether a positive Δ reads as better, worse, or neither for the city.
 * Drives the Summary "so what" wording — never a value judgment when "neutral".
 */
export type Polarity = "good-up" | "good-down" | "neutral";

export interface MetricMeta {
  equationId: string;
  dimension: DimensionId;
  /** Plain-language name shown on the Summary surface (NOT in Analytics/Inspect). */
  humanLabel: string;
  /** One-clause "what it measures", for the Summary "so what" line / tooltips. */
  blurb: string;
  /** Decimal places at the Summary level. Analytics shows more (see format.ts). */
  decimals: number;
  /** |value| strictly below this collapses to "No meaningful change" on Summary. */
  negligible: number;
  polarity: Polarity;
}

/**
 * Keyed by equation id (what the WS DIMENSION_RESULT carries as `equation_id`).
 * Labels/units/polarity derived from the live kernel output + methods-matrix §3.
 */
export const METRIC_REGISTRY: Record<string, MetricMeta> = {
  // ── Behavioral (BEH-1..3) ──
  "BEH-1": {
    equationId: "BEH-1", dimension: "behavioral",
    humanLabel: "Trips on the affected road (morning rush)",
    blurb: "How many trips use the affected corridor in the AM peak window.",
    decimals: 0, negligible: 0.5, polarity: "neutral",
  },
  "BEH-2": {
    equationId: "BEH-2", dimension: "behavioral",
    humanLabel: "Shift to/from jeepney travel",
    blurb: "Change in the share of travelers choosing jeepneys.",
    decimals: 1, negligible: 0.1, polarity: "good-up",
  },
  "BEH-3": {
    equationId: "BEH-3", dimension: "behavioral",
    humanLabel: "How full the road gets at peak",
    blurb: "Peak volume-to-capacity ratio on the affected corridor.",
    decimals: 2, negligible: 0.005, polarity: "good-down",
  },

  // ── Ecological (ECO-1..4) ──
  "ECO-1": {
    equationId: "ECO-1", dimension: "ecological",
    humanLabel: "Transport carbon emissions",
    blurb: "Net change in transport CO₂-equivalent emissions per year.",
    decimals: 4, negligible: 0.0005, polarity: "good-down",
  },
  "ECO-2": {
    equationId: "ECO-2", dimension: "ecological",
    humanLabel: "Air pollution",
    blurb: "Change in local air-pollutant concentration.",
    decimals: 4, negligible: 0.005, polarity: "good-down",
  },
  "ECO-3": {
    equationId: "ECO-3", dimension: "ecological",
    humanLabel: "Green space lost",
    blurb: "Hectares of green cover removed by the intervention.",
    decimals: 1, negligible: 0.05, polarity: "good-down",
  },
  "ECO-4": {
    equationId: "ECO-4", dimension: "ecological",
    humanLabel: "People exposed to flooding",
    blurb: "Change in the number of residents exposed to flood risk.",
    decimals: 0, negligible: 0.5, polarity: "good-down",
  },

  // ── Social (SOC-1..3) ──
  "SOC-1": {
    equationId: "SOC-1", dimension: "social",
    humanLabel: "Fair access to services",
    blurb: "Equity-weighted change in access to jobs and services.",
    decimals: 3, negligible: 0.002, polarity: "good-up",
  },
  "SOC-2": {
    equationId: "SOC-2", dimension: "social",
    humanLabel: "People at risk of displacement",
    blurb: "Estimated residents at risk of being displaced.",
    decimals: 0, negligible: 0.5, polarity: "good-down",
  },
  "SOC-3": {
    equationId: "SOC-3", dimension: "social",
    humanLabel: "Impact on low-income residents",
    blurb: "How the effect is distributed toward lower-income groups.",
    decimals: 3, negligible: 0.002, polarity: "good-up",
  },

  // ── Economic (ECON-1..3) ──
  "ECON-1": {
    equationId: "ECON-1", dimension: "economic",
    humanLabel: "Nearby land value",
    blurb: "Change in land value within ~1 km of the intervention.",
    decimals: 0, negligible: 1, polarity: "neutral",
  },
  "ECON-2": {
    equationId: "ECON-2", dimension: "economic",
    humanLabel: "Foot traffic for local businesses",
    blurb: "Change in daily visits to businesses in the affected zone.",
    decimals: 1, negligible: 0.5, polarity: "good-up",
  },
  "ECON-3": {
    equationId: "ECON-3", dimension: "economic",
    humanLabel: "Local jobs",
    blurb: "Net change in local employment.",
    decimals: 1, negligible: 0.1, polarity: "good-up",
  },

  // ── Societal (SOCI-1..4) ──
  "SOCI-1": {
    equationId: "SOCI-1", dimension: "societal",
    humanLabel: "Overall wellbeing score",
    blurb: "Composite of the social, economic and environmental effects.",
    decimals: 2, negligible: 0.05, polarity: "good-up",
  },
  "SOCI-2": {
    equationId: "SOCI-2", dimension: "societal",
    humanLabel: "Effect on heritage sites",
    blurb: "Change in proximity/pressure on nearby heritage sites.",
    decimals: 2, negligible: 0.02, polarity: "neutral",
  },
  "SOCI-3": {
    equationId: "SOCI-3", dimension: "societal",
    humanLabel: "Health-risk exposure",
    blurb: "Proxy for residents' exposure to health risks.",
    decimals: 3, negligible: 0.005, polarity: "good-down",
  },
  "SOCI-4": {
    equationId: "SOCI-4", dimension: "societal",
    humanLabel: "Walkability",
    blurb: "Change in how walkable the affected area is.",
    decimals: 2, negligible: 0.02, polarity: "good-up",
  },
};

/** Plain-language names for the five dimensions (Summary surface). */
export const DIMENSION_LABELS: Record<DimensionId, string> = {
  behavioral: "Travel & mobility",
  ecological: "Environment",
  social: "Community & access",
  economic: "Local economy",
  societal: "Equity & wellbeing",
};

/** Hue dot per dimension (matches the --color-dim-* palette in globals.css). */
export const DIMENSION_DOT: Record<DimensionId, string> = {
  behavioral: "bg-[#2563EB]",
  social: "bg-[#DB2777]",
  economic: "bg-[#CA8A04]",
  ecological: "bg-[#16A34A]",
  societal: "bg-[#9333EA]",
};

/**
 * Look up a metric's presentation meta by equation id. Returns `undefined` for
 * unknown ids so callers fall back to the raw kernel label (never invent one).
 */
export function getMetricMeta(equationId: string | undefined): MetricMeta | undefined {
  if (!equationId) return undefined;
  return METRIC_REGISTRY[equationId];
}
