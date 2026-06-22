"use client";

/**
 * Synthesis narrative with interactive citation chips (glass box, PRD-F14).
 *
 * The kernel's citation guard guarantees every quantitative claim in the
 * narrative carries an `[EQN-ID]` bracket (e.g. "[BEH-1]") that resolves to a
 * DimensionResult. This component parses those brackets into chips; clicking a
 * chip fires `onCiteClick(equationId)` so the page can open the Inspect drawer
 * on the matching result. A citation with no matching received result renders
 * as a DISABLED chip — never a dead link, never an invented target.
 */

export interface SynthesisCitation {
  claim?: string;
  equation_id: string;
  dataset_ids?: string[];
}

export interface SynthesisNarrativeProps {
  narrative: string;
  /** The SYNTHESIS event's citations array (equation_id-keyed). */
  citations?: SynthesisCitation[];
  /** Equation ids that resolve to a received DimensionResult. */
  resolvableEquationIds?: string[];
  onCiteClick?: (equationId: string) => void;
}

// Kernel equation ids: BEH-1, ECO-2, ECON-3, SOC-1, SOCI-4, VAL-01, ...
const CITATION_PATTERN = /\[([A-Z]{2,8}-\d+)\]/g;

function CitationChip({
  equationId,
  resolvable,
  onCiteClick,
}: {
  equationId: string;
  resolvable: boolean;
  onCiteClick?: (equationId: string) => void;
}) {
  const enabled = resolvable && !!onCiteClick;
  return (
    <button
      type="button"
      disabled={!enabled}
      onClick={enabled ? () => onCiteClick?.(equationId) : undefined}
      title={
        enabled
          ? `Open the Inspect drawer for ${equationId}`
          : `No matching dimension result received for ${equationId}`
      }
      aria-label={
        enabled
          ? `Inspect provenance for ${equationId}`
          : `Citation ${equationId} — no matching result received`
      }
      data-testid={`cite-${equationId}`}
      className={
        "inline-flex items-center align-baseline mx-0.5 px-1.5 rounded-full border text-[10px] font-mono leading-4 transition-colors " +
        (enabled
          ? "border-primary/30 bg-primary/10 text-primary hover:bg-primary/20 cursor-pointer"
          : "border-border bg-secondary text-text-muted cursor-not-allowed opacity-70")
      }
    >
      {equationId}
    </button>
  );
}

export default function SynthesisNarrative({
  narrative,
  citations,
  resolvableEquationIds,
  onCiteClick,
}: SynthesisNarrativeProps) {
  const resolvable = new Set(resolvableEquationIds ?? []);

  // split() with a capture group alternates [text, id, text, id, ..., text].
  const segments = narrative.split(CITATION_PATTERN);
  const inlineIds = new Set<string>(
    segments.filter((_, i) => i % 2 === 1)
  );

  // Citations the guard returned but the narrative text doesn't carry inline —
  // still surfaced (footer) so no provenance link is ever silently dropped.
  const footerCitations = (citations ?? []).filter(
    (c) => typeof c.equation_id === "string" && !inlineIds.has(c.equation_id)
  );

  return (
    <div
      className="p-5 bg-gradient-to-br from-primary/10 to-transparent border-l-4 border-l-primary border-y border-r border-primary/20 rounded-r-lg mt-4 shadow-sm backdrop-blur-sm"
      data-testid="synthesis-narrative"
    >
      <div className="flex items-center gap-2 mb-3">
        <svg className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        <h4 className="text-sm font-bold text-primary uppercase tracking-wide">Synthesis & Interpretations</h4>
      </div>
      <div className="text-[15px] text-foreground leading-relaxed whitespace-pre-wrap">
        {segments.map((segment, i) =>
          i % 2 === 1 ? (
            <CitationChip
              key={`cite-${i}`}
              equationId={segment}
              resolvable={resolvable.has(segment)}
              onCiteClick={onCiteClick}
            />
          ) : (
            <span key={`text-${i}`}>
              {segment.split(/(EXECUTIVE SUMMARY|ACTIONABLE RECOMMENDATIONS|PERSONA PERSPECTIVES)/).map((part, j) => {
                if (['EXECUTIVE SUMMARY', 'ACTIONABLE RECOMMENDATIONS', 'PERSONA PERSPECTIVES'].includes(part)) {
                  return <strong key={j} className="block mt-4 mb-1 text-primary/80 font-bold tracking-wide">{part}</strong>;
                }
                return <span key={j}>{part}</span>;
              })}
            </span>
          )
        )}
      </div>

      {footerCitations.length > 0 && (
        <div className="mt-3 pt-3 border-t border-primary/15" data-testid="synthesis-citations">
          <h5 className="text-[10px] uppercase tracking-wider text-text-muted mb-2">Citations</h5>
          <ul className="space-y-1">
            {footerCitations.map((c, i) => (
              <li key={`${c.equation_id}-${i}`} className="flex items-start gap-2 text-xs">
                <CitationChip
                  equationId={c.equation_id}
                  resolvable={resolvable.has(c.equation_id)}
                  onCiteClick={onCiteClick}
                />
                <span className="text-text-muted">
                  {c.claim || "Cited result"}
                  {c.dataset_ids && c.dataset_ids.length > 0 && (
                    <span className="font-mono"> · datasets: {c.dataset_ids.join(", ")}</span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
