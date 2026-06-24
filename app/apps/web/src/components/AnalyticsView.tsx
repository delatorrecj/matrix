import { ResultCard, type ResultCardData } from "@/components/ResultCard";
import DimensionCardSkeleton from "@/components/DimensionCardSkeleton";
import SynthesisNarrative, { type SynthesisCitation } from "@/components/SynthesisNarrative";
import ValidationPanel from "@/components/ValidationPanel";
import BiasAuditLog from "@/components/BiasAuditLog";
import { DIMENSIONS, EXPECTED_RESULTS, type DimensionId } from "@/lib/simulationRun";
import { DIMENSION_LABELS, DIMENSION_DOT } from "@/lib/metrics";
import { interpretDimension } from "@/lib/interpret";

/**
 * Full Analytics view (CR-010) — the comprehensive, *interpreted* detail.
 * Each dimension opens with a plain-language "what this means" line, then the
 * full metric cards (values, ranges, equation ids). The synthesis narrative,
 * validation back-tests and public bias-audit log live here, not on the Summary.
 * Reads the already-streamed results — no re-run.
 */
export function AnalyticsView({
  results,
  synthesis,
  scenarioId,
  isRunActive,
  onInspect,
  onCiteClick,
}: {
  results: ResultCardData[];
  synthesis: { narrative: string; citations: SynthesisCitation[] } | null;
  scenarioId: string;
  isRunActive: boolean;
  onInspect: (card: ResultCardData) => void;
  onCiteClick: (equationId: string) => void;
}) {
  return (
    <div className="flex flex-col gap-6" data-testid="analytics-view">
      {DIMENSIONS.map((dim: DimensionId) => {
        const dimResults = results.filter((r) => r.dimension === dim);
        return (
          <div key={dim} className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${DIMENSION_DOT[dim]} print:bg-black`} />
              <h3 className="text-sm font-semibold print:text-black">{DIMENSION_LABELS[dim]}</h3>
              <span className="text-xs font-mono text-text-muted ml-auto print:text-black">
                {dimResults.length}/{EXPECTED_RESULTS[dim]} results
              </span>
            </div>
            <p className="text-sm text-text-muted leading-relaxed print:text-black">
              {interpretDimension(dim, dimResults)}
            </p>
            {dimResults.length > 0 ? (
              <div className="flex flex-col gap-2">
                {dimResults.map((card) => (
                  <ResultCard key={card.key} card={card} variant="panel" onInspect={() => onInspect(card)} />
                ))}
              </div>
            ) : (
              <div className="print:hidden">
                <DimensionCardSkeleton
                  dimId={dim}
                  name={DIMENSION_LABELS[dim]}
                  colorClass={DIMENSION_DOT[dim]}
                  expectedResults={EXPECTED_RESULTS[dim]}
                  active={isRunActive}
                />
              </div>
            )}
          </div>
        );
      })}

      {synthesis && (
        <SynthesisNarrative
          narrative={synthesis.narrative}
          citations={synthesis.citations}
          resolvableEquationIds={results.map((r) => r.provData.equationId)}
          onCiteClick={onCiteClick}
        />
      )}

      <ValidationPanel />
      <BiasAuditLog runId={scenarioId} />
    </div>
  );
}
