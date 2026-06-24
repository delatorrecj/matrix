/**
 * Plain-language interpretation helpers (CR-010).
 *
 * Client-side "what this means" wording derived from the streamed results.
 * Phase 1 stop-gap: the deeper BLUF prose comes from the kernel synthesis
 * rewrite in Phase 2. Nothing here invents numbers — it only describes the
 * direction/tone the formatter already computed.
 */
import type { ResultCardData } from "@/components/ResultCard";
import { directionFor, formatMetricValue } from "@/lib/format";
import { getMetricMeta, DIMENSION_LABELS } from "@/lib/metrics";
import type { DimensionId } from "@/lib/simulationRun";

const CITATION = /\s*\[[A-Z]{2,8}-\d+\]/g;

/** First 1–2 sentences of the synthesis EXECUTIVE SUMMARY, equation codes stripped. */
export function narrativeLead(narrative: string | undefined, maxSentences = 2): string {
  if (!narrative) return "";
  const m = narrative.match(
    /EXECUTIVE SUMMARY([\s\S]*?)(ACTIONABLE RECOMMENDATIONS|PERSONA PERSPECTIVES|$)/i,
  );
  const lead = (m?.[1] ?? narrative).replace(CITATION, "").trim();
  const sentences = lead.split(/(?<=[.!?])\s+/).filter(Boolean);
  return sentences.slice(0, maxSentences).join(" ").trim();
}

interface Tally {
  good: number;
  bad: number;
  neutral: number;
  total: number;
}

function tally(cards: ResultCardData[]): Tally {
  let good = 0,
    bad = 0,
    neutral = 0;
  for (const c of cards) {
    const { negligible } = formatMetricValue(c.rawValue, c.equationId);
    const d = directionFor(c.rawValue, c.equationId, negligible);
    if (negligible || d.tone === "neutral") neutral++;
    else if (d.tone === "good") good++;
    else bad++;
  }
  return { good, bad, neutral, total: cards.length };
}

/** The metric most worth calling out: a concern first, then an improvement. */
function pickStandout(cards: ResultCardData[]): ResultCardData | null {
  const meaningful = cards.filter((c) => !formatMetricValue(c.rawValue, c.equationId).negligible);
  const bad = meaningful.find((c) => directionFor(c.rawValue, c.equationId, false).tone === "bad");
  if (bad) return bad;
  const good = meaningful.find((c) => directionFor(c.rawValue, c.equationId, false).tone === "good");
  return good ?? meaningful[0] ?? null;
}

/** One plain sentence describing a dimension's results, for the Analytics view. */
export function interpretDimension(dim: DimensionId, cards: ResultCardData[]): string {
  if (cards.length === 0) return "No results yet for this area.";
  const t = tally(cards);
  const parts: string[] = [];
  if (t.good) parts.push(`${t.good} measure${t.good > 1 ? "s" : ""} improve${t.good > 1 ? "" : "s"}`);
  if (t.bad) parts.push(`${t.bad} worsen${t.bad > 1 ? "" : "s"}`);
  if (t.neutral) parts.push(`${t.neutral} ${t.neutral > 1 ? "are" : "is"} about the same`);
  const body = parts.length ? parts.join(", ") : "all measures are about the same";

  const standout = pickStandout(cards);
  let tail = "";
  if (standout) {
    const label = (getMetricMeta(standout.equationId)?.humanLabel ?? standout.metric).toLowerCase();
    const { display } = formatMetricValue(standout.rawValue, standout.equationId);
    tail = ` The most notable is ${label} (${display}${standout.unit ? ` ${standout.unit}` : ""}).`;
  }
  return `In ${DIMENSION_LABELS[dim]}, ${body}.${tail}`;
}

/** A one-line headline for the Summary dock when no synthesis narrative is available. */
export function overallHeadline(cards: ResultCardData[]): string {
  const t = tally(cards);
  if (t.total === 0) return "Your simulation results will appear here.";
  if (t.bad === 0 && t.good > 0)
    return `Broadly positive — ${t.good} of ${t.total} measures improve and none worsen.`;
  if (t.good === 0 && t.bad > 0)
    return `Proceed with caution — ${t.bad} of ${t.total} measures worsen and none improve.`;
  if (t.good === 0 && t.bad === 0) return "Little overall change — most measures hold steady.";
  return `Mixed outcome — ${t.good} measure${t.good === 1 ? "" : "s"} improve and ${t.bad} worsen, of ${t.total}.`;
}
