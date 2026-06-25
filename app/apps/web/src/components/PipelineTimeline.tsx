import { PIPELINE_STAGES } from "@/lib/marketing-content";
import { cn } from "@/lib/utils";

const BUDGET_SEC = 90;

/** 90-second pipeline timeline with honest current-state note. */
export function PipelineTimeline() {
  return (
    <div className="space-y-6">
      <ol className="space-y-0 divide-y divide-border/60">
        {PIPELINE_STAGES.map((stage, i) => {
          const widthPct =
            ((stage.endSec - stage.startSec) / BUDGET_SEC) * 100;
          return (
            <li
              key={stage.label}
              className="grid gap-4 py-6 first:pt-0 sm:grid-cols-[5rem_1fr] sm:gap-8"
            >
              <div className="flex items-baseline gap-3 sm:flex-col sm:gap-1">
                <span className="font-mono text-2xl font-semibold tabular-nums text-primary/50">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="font-mono text-xs font-medium tabular-nums text-primary">
                  {stage.startSec}-{stage.endSec}s
                </span>
              </div>

              <div className="min-w-0">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h3 className="font-semibold">{stage.label}</h3>
                  <span className="text-xs text-text-muted">
                    {Math.round(widthPct)}% of budget
                  </span>
                </div>
                <p className="mt-2 max-w-[65ch] text-sm leading-relaxed text-text-muted">
                  {stage.detail}
                </p>
                <div
                  aria-hidden="true"
                  className="mt-3 h-1 overflow-hidden rounded-full bg-surface-elevated"
                >
                  <div
                    className={cn("h-full rounded-full bg-primary/55")}
                    style={{ width: `${widthPct}%` }}
                  />
                </div>
              </div>
            </li>
          );
        })}
      </ol>

      <div className="rounded-xl border border-warning/30 bg-warning/5 px-4 py-3 text-sm">
        <p className="font-semibold text-warning">Honest status</p>
        <p className="mt-1 max-w-[65ch] text-text-muted">
          The target budget is{" "}
          <strong className="whitespace-nowrap text-text">90 seconds</strong>{" "}
          end-to-end. Cold runs currently land around{" "}
          <strong className="whitespace-nowrap text-text">123 s</strong>,
          while repeated runs served from the trajectory cache return in{" "}
          <strong className="whitespace-nowrap text-text">under 1 s</strong>.
          Per-stage timings are shown in-product to guide optimization.
        </p>
      </div>
    </div>
  );
}
