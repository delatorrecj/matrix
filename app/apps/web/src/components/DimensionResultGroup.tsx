import DimensionCardSkeleton from "@/components/DimensionCardSkeleton";
import { ResultCard, type ResultCardData } from "@/components/ResultCard";

/**
 * One dimension's block in the results panel: a hue-dot header with the
 * received/expected count, then either the streamed ResultCards or, until any
 * arrive, the honest skeleton. Rendered identically in the docked panel and the
 * Inspect drawer's Category Breakdown (the `variant` only toggles print styles +
 * the streaming reveal, which belong to the panel context).
 */
interface DimensionResultGroupProps {
  dim: string;
  dimResults: ResultCardData[];
  expectedResults: number;
  isRunActive: boolean;
  colorClass: string;
  onInspect: (card: ResultCardData) => void;
  variant?: "panel" | "drawer";
}

export function DimensionResultGroup({
  dim,
  dimResults,
  expectedResults,
  isRunActive,
  colorClass,
  onInspect,
  variant = "panel",
}: DimensionResultGroupProps) {
  const isPanel = variant === "panel";

  if (dimResults.length === 0) {
    const skeleton = (
      <DimensionCardSkeleton
        name={dim}
        colorClass={colorClass}
        expectedResults={expectedResults}
        active={isRunActive}
      />
    );
    // Empty dimensions are omitted from the printed brief.
    return isPanel ? <div className="print:hidden">{skeleton}</div> : skeleton;
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className={`w-3 h-3 rounded-full ${colorClass} ${
              isPanel ? "print:border print:border-black print:bg-black" : ""
            }`}
          />
          <span className={`text-sm font-semibold capitalize ${isPanel ? "print:text-black" : ""}`}>
            {dim}
          </span>
        </div>
        <span className={`text-xs font-mono text-text-muted ${isPanel ? "print:text-black" : ""}`}>
          {dimResults.length}/{expectedResults} results
        </span>
      </div>

      {dimResults.map((card) => (
        <ResultCard key={card.key} card={card} variant={variant} onInspect={() => onInspect(card)} />
      ))}
    </div>
  );
}
