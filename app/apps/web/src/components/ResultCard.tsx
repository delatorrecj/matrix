import { ConfidenceChip, chipLevel, applicabilityLabel } from "@/components/ConfidenceChip";
import type { ProvenanceData } from "@/components/InspectDrawer";
import { formatMetricValue, formatRange } from "@/lib/format";

/** One DIMENSION_RESULT rendered as a glass-box metric card (Analytics / Inspect). */
export interface ResultCardData {
  key: string;
  dimension: string;
  /** Raw kernel metric name (canonical — shown in Analytics/Inspect, not Summary). */
  metric: string;
  /** Kernel equation id, e.g. "BEH-1" — the glass-box key and registry lookup. */
  equationId: string;
  unit: string;
  conf: string;
  /** Raw numeric value off the stream — formatted at render, never pre-stringified. */
  rawValue: number;
  /** Raw [lo, hi] range, or null when the stream omitted it. */
  rawRange: [number, number] | null;
  /** Low-confidence / directional-only (PRD-F5) — never present a precise headline. */
  directional?: boolean;
  /** Kernel applicability: computed | not_modeled | not_applicable. */
  applicability?: string;
  provData: ProvenanceData;
}

interface ResultCardProps {
  card: ResultCardData;
  onInspect: () => void;
  /**
   * "panel" = the Analytics detail list: streaming reveal, print styles, range +
   * Inspect footer. "drawer" = the compact copy inside the Inspect drawer's
   * Category Breakdown (no reveal, no footer, not printed).
   */
  variant?: "panel" | "drawer";
}

export function ResultCard({ card, onInspect, variant = "panel" }: ResultCardProps) {
  const isPanel = variant === "panel";
  const level = chipLevel(card.conf, card.applicability);
  const naLabel = applicabilityLabel(card.applicability);
  const directionalOnly =
    !naLabel && (card.directional === true || level === "Low");
  const value = formatMetricValue(card.rawValue, card.equationId, { precise: true }).display;
  const range = formatRange(card.rawRange, card.equationId, { precise: true });

  return (
    <div
      className={
        "border border-border rounded-xl p-4 bg-surface-elevated hover:border-primary/50 transition-all active:scale-[0.99] cursor-pointer group " +
        (isPanel ? "card-reveal print:border-black print:bg-white print:break-inside-avoid print:animate-none" : "")
      }
      onClick={onInspect}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-sm font-medium print:text-black">{card.metric}</span>
        <ConfidenceChip level={level} compact />
      </div>
      {naLabel ? (
        <div className="text-base font-semibold text-text-muted mb-1 print:text-black">{naLabel}</div>
      ) : directionalOnly ? (
        <div className="text-base font-semibold text-text-muted mb-1 print:text-black">
          Directional only — not a precise estimate
        </div>
      ) : (
      <div className="flex items-end gap-2 mb-1">
        <span className="text-2xl font-bold font-mono tabular-nums tracking-tight print:text-black">{value}</span>
        <span className="text-xs text-text-muted mb-1 print:text-black">{card.unit}</span>
      </div>
      )}
      {isPanel && (
        <div className="text-xs text-text-muted font-mono flex items-center justify-between gap-2 print:text-black">
          <span className="truncate">
            {range && <>Range: {range}</>}
            {card.equationId && (
              <span className="ml-2 px-1 rounded border border-border text-[10px] align-middle print:border-black">
                {card.equationId}
              </span>
            )}
          </span>
          <span className="opacity-0 group-hover:opacity-100 text-primary transition-opacity print:hidden shrink-0">
            Inspect →
          </span>
        </div>
      )}
    </div>
  );
}
