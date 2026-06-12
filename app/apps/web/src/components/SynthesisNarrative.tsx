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
      className="p-4 bg-primary/5 border border-primary/20 rounded-lg mt-2"
      data-testid="synthesis-narrative"
    >
      <h4 className="text-xs font-bold text-primary mb-2 uppercase">Synthesis</h4>
      <p className="text-sm text-foreground leading-relaxed">
        {segments.map((segment, i) =>
          i % 2 === 1 ? (
            <CitationChip
              key={`cite-${i}`}
              equationId={segment}
              resolvable={resolvable.has(segment)}
              onCiteClick={onCiteClick}
            />
          ) : (
            <span key={`text-${i}`}>{segment}</span>
          )
        )}
      </p>

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
