import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { ConfidenceChip, toConfidenceLevel } from "@/components/ConfidenceChip";
import { formatMetricValue, directionFor, confidenceSentence } from "@/lib/format";
import { getMetricMeta } from "@/lib/metrics";
import type { ResultCardData } from "@/components/ResultCard";

/**
 * Plain-language summary card (CR-010). Human label, a rounded headline number
 * (or "No meaningful change"), a polarity-aware direction word, and a spelled-out
 * confidence. No equation codes, no ranges, no raw floats — those live in the
 * Analytics view and the Inspect drawer. Clicking still opens Inspect (glass box).
 */
export function SummaryCard({ card, onInspect }: { card: ResultCardData; onInspect: () => void }) {
  const meta = getMetricMeta(card.equationId);
  const label = meta?.humanLabel ?? card.metric;
  const { display, negligible } = formatMetricValue(card.rawValue, card.equationId);
  const dir = directionFor(card.rawValue, card.equationId, negligible);
  const level = toConfidenceLevel(card.conf);
  const directionalOnly = card.directional === true || level === "L";

  const toneClass =
    dir.tone === "good" ? "text-success" : dir.tone === "bad" ? "text-error" : "text-text-muted";
  const Arrow = card.rawValue > 0 ? ArrowUpRight : ArrowDownRight;

  return (
    <button
      type="button"
      onClick={onInspect}
      title={`${label} — ${confidenceSentence(level)}`}
      className="w-full text-left border border-border rounded-xl p-4 bg-surface-elevated hover:border-primary/50 transition-all active:scale-[0.99] card-reveal print:border-black print:bg-white print:break-inside-avoid print:animate-none"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="text-sm font-medium leading-snug print:text-black">{label}</span>
        <ConfidenceChip level={level} className="shrink-0" />
      </div>

      {negligible ? (
        <div className="text-base font-semibold text-text-muted print:text-black">No meaningful change</div>
      ) : directionalOnly ? (
        <>
          <div className="text-base font-semibold text-text-muted print:text-black">Directional only</div>
          <div className={`mt-1 inline-flex items-center gap-1 text-xs font-medium ${toneClass} print:text-black`}>
            <Arrow className="w-3.5 h-3.5" aria-hidden="true" />
            <span className="capitalize">{dir.word}</span>
            <span className="text-text-muted font-normal">· not a precise estimate</span>
          </div>
        </>
      ) : (
        <>
          <div className="flex items-end gap-2">
            <span className="text-3xl font-bold font-mono tabular-nums tracking-tight print:text-black">
              {display}
            </span>
            {card.unit && <span className="text-xs text-text-muted mb-1 print:text-black">{card.unit}</span>}
          </div>
          <div className={`mt-1 inline-flex items-center gap-1 text-xs font-medium ${toneClass} print:text-black`}>
            <Arrow className="w-3.5 h-3.5" aria-hidden="true" />
            <span className="capitalize">{dir.word}</span>
          </div>
        </>
      )}
    </button>
  );
}
