import { ConfidenceChip, toConfidenceLevel } from "@/components/ConfidenceChip";
import type { ProvenanceData } from "@/components/InspectDrawer";

/** One DIMENSION_RESULT rendered as a glass-box metric card. */
export interface ResultCardData {
  key: string;
  dimension: string;
  metric: string;
  value: string;
  unit: string;
  conf: string;
  range: string;
  provData: ProvenanceData;
}

interface ResultCardProps {
  card: ResultCardData;
  onInspect: () => void;
  /**
   * "panel" = the main results list: streaming reveal, print styles, and the
   * range / Inspect-affordance footer. "drawer" = the compact copy inside the
   * Inspect drawer's Category Breakdown (no reveal, no footer, not printed).
   */
  variant?: "panel" | "drawer";
}

export function ResultCard({ card, onInspect, variant = "panel" }: ResultCardProps) {
  const isPanel = variant === "panel";
  return (
    <div
      className={
        "border border-border rounded-xl p-4 bg-surface-elevated hover:border-primary/50 transition-all active:scale-[0.99] cursor-pointer group " +
        (isPanel ? "card-reveal print:border-black print:bg-white print:break-inside-avoid print:animate-none" : "")
      }
      onClick={onInspect}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium print:text-black">{card.metric}</span>
        <ConfidenceChip level={toConfidenceLevel(card.conf)} compact />
      </div>
      <div className="flex items-end gap-2 mb-1">
        <span className="text-2xl font-bold font-mono tracking-tight print:text-black">{card.value}</span>
        <span className="text-xs text-text-muted mb-1 print:text-black">{card.unit}</span>
      </div>
      {isPanel && (
        <div className="text-xs text-text-muted font-mono flex justify-between print:text-black">
          <span>R: {card.range}</span>
          <span className="opacity-0 group-hover:opacity-100 text-primary transition-opacity print:hidden">
            Inspect →
          </span>
        </div>
      )}
    </div>
  );
}
