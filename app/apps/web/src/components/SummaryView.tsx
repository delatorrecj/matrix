"use client";

import { BarChart3 } from "lucide-react";
import { SummaryCard } from "@/components/SummaryCard";
import DimensionCardSkeleton from "@/components/DimensionCardSkeleton";
import type { ResultCardData } from "@/components/ResultCard";
import { DIMENSIONS, EXPECTED_RESULTS, type DimensionId } from "@/lib/simulationRun";
import { DIMENSION_LABELS, DIMENSION_DOT } from "@/lib/metrics";
import { narrativeLead, overallHeadline } from "@/lib/interpret";
import { useLanguage } from "@/components/LanguageProvider";

/**
 * Summary dock (CR-010) — the default scenario view. A plain-language headline
 * plus humanized per-dimension cards. No equation codes, raw floats, ranges,
 * validation or bias log — those live one click away in the Analytics view.
 */
export function SummaryView({
  results,
  narrative,
  isRunActive,
  onInspect,
  onOpenAnalytics,
}: {
  results: ResultCardData[];
  narrative?: string;
  isRunActive: boolean;
  onInspect: (card: ResultCardData) => void;
  onOpenAnalytics: () => void;
}) {
  const { language } = useLanguage();
  const headline = narrativeLead(narrative, 2, language) || overallHeadline(results);

  return (
    <div className="flex flex-col gap-4">
      {/* BLUF headline */}
      {headline && (
        <div className="p-4 rounded-xl border border-primary/20 bg-gradient-to-br from-primary/10 to-transparent print:border-black print:bg-white">
          <p className="text-[15px] leading-relaxed text-foreground print:text-black">{headline}</p>
        </div>
      )}

      {DIMENSIONS.map((dim: DimensionId) => {
        const dimResults = results.filter((r) => r.dimension === dim);
        if (dimResults.length === 0) {
          // Empty dimension: honest skeleton ("awaiting" while running, "no results
          // received" once terminal). Hidden from the printed brief.
          return (
            <div className="print:hidden" key={dim}>
              <DimensionCardSkeleton
                dimId={dim}
                name={DIMENSION_LABELS[dim]}
                colorClass={DIMENSION_DOT[dim]}
                expectedResults={EXPECTED_RESULTS[dim]}
                active={isRunActive}
              />
            </div>
          );
        }
        return (
          <div className="flex flex-col gap-2" key={dim}>
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${DIMENSION_DOT[dim]} print:bg-black`} />
              <span className="text-sm font-semibold print:text-black">{DIMENSION_LABELS[dim]}</span>
            </div>
            {dimResults.map((card) => (
              <SummaryCard key={card.key} card={card} onInspect={() => onInspect(card)} />
            ))}
          </div>
        );
      })}

      {results.some(
        (c) => c.directional && (c.equationId === "BEH-1" || c.equationId === "BEH-3")
      ) && (
        <p
          className="text-xs leading-relaxed text-foreground bg-warning/10 border border-warning/30 rounded-xl px-3 py-2"
          data-testid="uncalibrated-demand-notice"
        >
          Iloilo corridor volumes are directional, not city-calibrated. VAL-01 vs
          Calderon 2014 is a published FAIL — open Analytics for the live NRMSE and
          pass threshold.
        </p>
      )}
      {results.length > 0 && (
        <button
          type="button"
          onClick={onOpenAnalytics}
          className="mt-1 inline-flex items-center justify-center gap-2 rounded-lg border border-border bg-surface-elevated px-4 py-2.5 text-sm font-medium text-text hover:border-primary hover:text-primary transition-colors active:scale-[0.99] print:hidden"
        >
          <BarChart3 className="w-4 h-4" />
          View full analytics
          <span aria-hidden="true">→</span>
        </button>
      )}
    </div>
  );
}
