"use client";

import { useLanguage } from "@/components/LanguageProvider";
import type { ResultCardData } from "@/components/ResultCard";
import { DIMENSIONS, type DimensionId } from "@/lib/simulationRun";
import { DIMENSION_LABELS, getMetricMeta } from "@/lib/metrics";
import {
  confidenceWord,
  directionFor,
  formatMetricValue,
} from "@/lib/format";
import { narrativeForLanguage, parseBlufSections } from "@/lib/bilingual";
import { overallHeadline } from "@/lib/interpret";

/**
 * Dedicated one-page executive brief (CR-010, WS-5 T5.4). Replaces the old
 * `window.print()`-of-the-whole-panel: this is a print-scoped DOM
 * (`hidden print:block`) that the scenario page reveals at print time while the
 * rest of the UI is `print:hidden`. BLUF order: HEADLINE → WHAT WE SIMULATED →
 * KEY FINDINGS → RECOMMENDATION → KEY RISK → EVIDENCE appendix.
 *
 * Glass box (PRD-F14): the headline numbers are the kernel's (formatted, never
 * invented) and the EVIDENCE appendix lists every result's equation id + datasets,
 * so each number in the brief traces to its source. Honors the language toggle:
 * the prose is the chosen-language half of the synthesis brief; the data rows are
 * language-neutral. Nothing here computes a confidence — it spells out the kernel's.
 */
export function ScenarioBrief({
  results,
  narrative,
  scenarioId,
}: {
  results: ResultCardData[];
  narrative?: string;
  scenarioId: string;
}) {
  const { language } = useLanguage();
  const shown = narrativeForLanguage(narrative, language);
  const sections = parseBlufSections(shown);

  // The headline: prefer the synthesis HEADLINE; else a client-built one-liner.
  const headline = stripCodes(sections.HEADLINE) || overallHeadline(results);

  // KEY FINDINGS rows — the most notable metric per dimension that produced results,
  // each as: plain interpretation + the formatted headline number + spelled-out confidence.
  const findings = DIMENSIONS.map((dim) => buildFinding(dim, results)).filter(
    (f): f is Finding => f !== null,
  );

  return (
    <div className="hidden print:block text-black bg-white" data-testid="scenario-brief">
      <header className="mb-4 border-b border-black pb-2">
        <h1 className="text-xl font-bold">MATRIX — Infrastructure Impact Brief</h1>
        <p className="text-xs font-mono">Scenario {scenarioId}</p>
        <p className="text-[10px] uppercase tracking-wider mt-1">
          Pre-construction simulation · Iloilo City · confidence-bounded estimates
        </p>
      </header>

      {/* HEADLINE */}
      {headline && (
        <section className="mb-3">
          <h2 className="text-[11px] font-bold uppercase tracking-wider mb-1">Headline</h2>
          <p className="text-sm leading-relaxed font-medium">{headline}</p>
        </section>
      )}

      {/* WHAT WE SIMULATED */}
      {sections["WHAT WE SIMULATED"] && (
        <section className="mb-3">
          <h2 className="text-[11px] font-bold uppercase tracking-wider mb-1">What we simulated</h2>
          <p className="text-sm leading-relaxed">{stripCodes(sections["WHAT WE SIMULATED"])}</p>
        </section>
      )}

      {/* KEY FINDINGS — plain sentence + headline number + spelled-out confidence */}
      {findings.length > 0 && (
        <section className="mb-3">
          <h2 className="text-[11px] font-bold uppercase tracking-wider mb-1">Key findings</h2>
          <ul className="text-sm leading-relaxed list-disc pl-5 space-y-1">
            {findings.map((f) => (
              <li key={f.dim}>
                {f.sentence}{" "}
                <span className="font-semibold tabular-nums">
                  {f.value}
                  {f.unit ? ` ${f.unit}` : ""}
                </span>{" "}
                <span className="text-[11px]">({f.confidence} confidence)</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* RECOMMENDATION */}
      {sections.RECOMMENDATION && (
        <section className="mb-3">
          <h2 className="text-[11px] font-bold uppercase tracking-wider mb-1">Recommendation</h2>
          <p className="text-sm leading-relaxed">{stripCodes(sections.RECOMMENDATION)}</p>
        </section>
      )}

      {/* KEY RISK */}
      {sections["KEY RISK"] && (
        <section className="mb-3">
          <h2 className="text-[11px] font-bold uppercase tracking-wider mb-1">Key risk</h2>
          <p className="text-sm leading-relaxed">{stripCodes(sections["KEY RISK"])}</p>
        </section>
      )}

      {/* EVIDENCE appendix — every number traces to its equation + datasets (glass box). */}
      {results.length > 0 && (
        <section className="mt-4 border-t border-black pt-2">
          <h2 className="text-[11px] font-bold uppercase tracking-wider mb-1">
            Evidence (traceability)
          </h2>
          <table className="w-full text-[10px] border-collapse">
            <thead>
              <tr className="border-b border-black text-left">
                <th className="py-0.5 pr-2 font-semibold">Equation</th>
                <th className="py-0.5 pr-2 font-semibold">Measure</th>
                <th className="py-0.5 pr-2 font-semibold">Value</th>
                <th className="py-0.5 font-semibold">Datasets</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => {
                const { display } = formatMetricValue(r.rawValue, r.equationId, { precise: true });
                const datasets = r.provData?.inputs?.map((d) => d.id).filter(Boolean) ?? [];
                return (
                  <tr key={r.key} className="border-b border-black/40 align-top">
                    <td className="py-0.5 pr-2 font-mono">{r.equationId || "—"}</td>
                    <td className="py-0.5 pr-2">{r.metric}</td>
                    <td className="py-0.5 pr-2 font-mono tabular-nums">
                      {display}
                      {r.unit ? ` ${r.unit}` : ""}
                    </td>
                    <td className="py-0.5 font-mono">{datasets.length ? datasets.join(", ") : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="text-[9px] mt-1 leading-snug">
            Every figure is computed by the MATRIX kernel from the datasets above (glass box,
            PRD-F14); confidence levels are computed, not assigned. Full provenance and ranges are
            available in the application&rsquo;s Inspect drawer.
          </p>
        </section>
      )}
    </div>
  );
}

const CITATION = /\s*\[[A-Z]{2,8}-\d+\]/g;

/** Drop inline equation codes from prose for the human-facing brief. */
function stripCodes(text: string): string {
  return (text ?? "").replace(CITATION, "").trim();
}

interface Finding {
  dim: DimensionId;
  sentence: string;
  value: string;
  unit: string;
  confidence: string;
}

/** The most notable result in a dimension, as a plain finding row. Null if no results. */
function buildFinding(dim: DimensionId, results: ResultCardData[]): Finding | null {
  const cards = results.filter((r) => r.dimension === dim);
  if (cards.length === 0) return null;

  // Prefer a meaningful concern, then an improvement, else the first card.
  const meaningful = cards.filter((c) => !formatMetricValue(c.rawValue, c.equationId).negligible);
  const standout =
    meaningful.find((c) => directionFor(c.rawValue, c.equationId, false).tone === "bad") ??
    meaningful.find((c) => directionFor(c.rawValue, c.equationId, false).tone === "good") ??
    meaningful[0] ??
    cards[0];

  const meta = getMetricMeta(standout.equationId);
  const label = meta?.humanLabel ?? standout.metric;
  const { display, negligible } = formatMetricValue(standout.rawValue, standout.equationId);
  const dir = directionFor(standout.rawValue, standout.equationId, negligible);

  const sentence = negligible
    ? `In ${DIMENSION_LABELS[dim].toLowerCase()}, ${label.toLowerCase()} shows no meaningful change.`
    : `In ${DIMENSION_LABELS[dim].toLowerCase()}, ${label.toLowerCase()} ${dir.word}, at`;

  return {
    dim,
    sentence,
    value: negligible ? "" : display,
    unit: negligible ? "" : standout.unit,
    confidence: confidenceWord(standout.conf),
  };
}

export default ScenarioBrief;
