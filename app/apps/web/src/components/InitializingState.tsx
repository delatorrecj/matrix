"use client";

import { Loader2 } from "lucide-react";

/**
 * Shown in the results dock while a run is still computing (connecting /
 * queued / running) and no dimension results have arrived yet.
 *
 * Honors prefers-reduced-motion: the spinner / ping stop animating (motion-reduce).
 * No fabricated numbers — glass-box rule (PRD-F14) — only a neutral status.
 */
export function InitializingState({
  label = "Initializing simulation…",
  hint,
}: {
  label?: string;
  hint?: string;
}) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border bg-surface/60 px-6 py-10 text-center"
      role="status"
      aria-live="polite"
      data-testid="initializing-panel"
    >
      <div className="relative flex items-center justify-center">
        <span
          className="absolute inline-flex h-10 w-10 rounded-full bg-primary/15 motion-safe:animate-ping"
          aria-hidden="true"
        />
        <Loader2
          className="relative w-6 h-6 animate-spin motion-reduce:animate-none text-primary"
          aria-hidden="true"
        />
      </div>
      <div>
        <p className="text-sm font-semibold text-foreground">{label}</p>
        <p className="mt-1 text-xs text-text-muted max-w-[34ch]">
          {hint ??
            "Warming the kernel, running the agent simulation, and scoring all five impact dimensions."}
        </p>
      </div>
    </div>
  );
}

export default InitializingState;
