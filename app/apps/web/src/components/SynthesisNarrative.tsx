"use client";

import React from "react";
import { Zap } from "lucide-react";
import { GlossaryTooltip } from "./GlossaryTooltip";

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

const GLOSSARY: Record<string, string> = {
  "mode-share": "The percentage of travelers using a particular type of transportation.",
  "peak-hour saturation": "The point at which a transport network has reached its maximum capacity during the busiest time.",
  "gini-style access inequality": "A measure of inequality in access to urban services, adapted from the economic Gini coefficient.",
  "v/c ratio": "Volume-to-capacity ratio; indicates how close a road is to its maximum capacity.",
  "carbon emission delta": "The net difference in carbon dioxide equivalent emissions between the baseline and the proposed scenario.",
  "trip generation": "The number of new trips that start or end in a specific area due to new development."
};

function renderTextWithGlossary(text: string) {
  const terms = Object.keys(GLOSSARY);
  const regex = new RegExp(`\\b(${terms.join('|')})\\b`, 'gi');
  const parts = text.split(regex);
  return parts.map((part, i) => {
    const lower = part.toLowerCase();
    if (GLOSSARY[lower]) {
      return <GlossaryTooltip key={i} term={part} definition={GLOSSARY[lower]} />;
    }
    return <span key={i}>{part}</span>;
  });
}

function CitationChip({
  equationId,
  resolvable,
  onCiteClick,
  trend,
}: {
  equationId: string;
  resolvable: boolean;
  onCiteClick?: (equationId: string) => void;
  trend?: "up" | "down";
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
          : `Citation ${equationId}, no matching result received`
      }
      data-testid={`cite-${equationId}`}
      className={
        "inline-flex items-center align-baseline mx-0.5 px-1.5 rounded-full border text-[10px] font-mono leading-4 transition-colors print:border-black print:text-black " +
        (enabled
          ? "border-primary/30 bg-primary/10 text-primary hover:bg-primary/20 cursor-pointer"
          : "border-border bg-secondary text-text-muted cursor-not-allowed opacity-70")
      }
    >
      {trend === "up" && <span className="mr-0.5 text-green-600 font-bold print:text-black">↑</span>}
      {trend === "down" && <span className="mr-0.5 text-red-600 font-bold print:text-black">↓</span>}
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
      className="p-5 bg-gradient-to-br from-primary/10 to-transparent border-l-4 border-l-primary border-y border-r border-primary/20 rounded-r-lg mt-4 shadow-sm backdrop-blur-sm print:bg-white print:border-black print:text-black print:shadow-none"
      data-testid="synthesis-narrative"
    >
      <div className="flex items-center gap-2 mb-3">
        <Zap className="w-5 h-5 text-primary print:text-black" aria-hidden="true" />
        <h4 className="text-sm font-bold text-primary uppercase tracking-wide print:text-black">Synthesis &amp; Interpretations</h4>
      </div>
      <div className="text-[15px] text-foreground leading-relaxed whitespace-pre-wrap print:text-black">
        {segments.map((segment, i) => {
          if (i % 2 === 1) {
            const prevText = segments[i - 1]?.toLowerCase() || "";
            let trend: "up" | "down" | undefined;
            if (prevText.match(/\b(increase|increased|higher|gain|rise|up|added)\b/)) trend = "up";
            else if (prevText.match(/\b(decrease|decreased|lower|loss|fall|down|reduced)\b/)) trend = "down";
            
            return (
              <CitationChip
                key={`cite-${i}`}
                equationId={segment}
                resolvable={resolvable.has(segment)}
                onCiteClick={onCiteClick}
                trend={trend}
              />
            );
          } else {
            return (
              <span key={`text-${i}`}>
                {segment.split(/(EXECUTIVE SUMMARY|ACTIONABLE RECOMMENDATIONS|PERSONA PERSPECTIVES)/).map((part, j) => {
                  if (['EXECUTIVE SUMMARY', 'ACTIONABLE RECOMMENDATIONS', 'PERSONA PERSPECTIVES'].includes(part)) {
                    return <strong key={j} className="block mt-4 mb-1 text-primary/80 font-bold tracking-wide print:text-black">{part}</strong>;
                  }
                  return <React.Fragment key={j}>{renderTextWithGlossary(part)}</React.Fragment>;
                })}
              </span>
            );
          }
        })}
      </div>

      {footerCitations.length > 0 && (
        <div className="mt-3 pt-3 border-t border-primary/15 print:border-black" data-testid="synthesis-citations">
          <h5 className="text-[10px] uppercase tracking-wider text-text-muted mb-2 print:text-black">Citations</h5>
          <ul className="space-y-1">
            {footerCitations.map((c, i) => (
              <li key={`${c.equation_id}-${i}`} className="flex items-start gap-2 text-xs print:text-black">
                <CitationChip
                  equationId={c.equation_id}
                  resolvable={resolvable.has(c.equation_id)}
                  onCiteClick={onCiteClick}
                />
                <span className="text-text-muted print:text-black">
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
