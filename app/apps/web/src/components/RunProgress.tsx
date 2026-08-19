import { useEffect, useRef, useState } from "react";
import {
  RunState,
  formatMs,
  formatProgress,
  isTerminal,
  progressPercent,
} from "@/lib/simulationRun";

/**
 * Progress line while the run streams (phase-weighted percent + stage/result copy)
 * and, once DONE, the stage-timing summary (SUMO / modules / Azure OpenAI breakdown when
 * the server provides `timings`; legacy `duration_ms` otherwise).
 *
 * A cosmetic trickle keeps the bar moving during long waits (SUMO simulation)
 * so the UI never looks frozen. The trickle never exceeds the real progress
 * and never reaches 100 — it just fills the gap between real milestones.
 */
interface RunProgressProps {
  runState: RunState;
}

/** Smoothly trickle toward `target` so the bar always appears alive. */
function useTrickleProgress(target: number, active: boolean): number {
  const [display, setDisplay] = useState(target);
  const rafRef = useRef<number>(0);
  const prevTarget = useRef(target);

  useEffect(() => {
    if (!active) {
      setDisplay(target);
      return;
    }

    if (target > prevTarget.current) {
      setDisplay((d) => Math.max(d, prevTarget.current));
    }
    prevTarget.current = target;

    let last = performance.now();

    const tick = (now: number) => {
      const dt = (now - last) / 1000;
      last = now;

      setDisplay((d) => {
        if (d >= target) return target;
        const gap = target - d;
        const step = Math.max(0.05, gap * 0.04) * (dt / 0.016);
        return Math.min(target, d + step);
      });

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, active]);

  return Math.round(display);
}

export default function RunProgress({ runState }: RunProgressProps) {
  const realPct = progressPercent(runState);
  const active = !isTerminal(runState.phase) && runState.phase !== "disconnected";
  const pct = useTrickleProgress(realPct, active);

  if (runState.phase === "done") {
    return <DoneSummary runState={runState} />;
  }

  return (
    <div data-testid="run-progress">
      <div className="flex items-center justify-between text-xs font-mono text-text-muted">
        <span data-testid="progress-line">{formatProgress(runState)}</span>
        <span>{pct}%</span>
      </div>
      <div className="mt-1 h-1.5 rounded-full bg-secondary overflow-hidden">
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-150"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function DoneSummary({ runState }: { runState: RunState }) {
  const { timings, durationMs } = runState;
  const totalMs = timings?.total_ms ?? durationMs;

  const stages: { label: string; ms: number | undefined }[] = [
    { label: "SUMO", ms: timings?.sumo_ms },
    { label: "Modules", ms: timings?.modules_ms },
    { label: "Azure OpenAI", ms: timings?.llm_ms },
  ];
  const knownStages = stages.filter(
    (s): s is { label: string; ms: number } => typeof s.ms === "number",
  );

  return (
    <div
      className="border border-success/30 bg-success/10 rounded-lg p-3"
      role="status"
      data-testid="done-summary"
    >
      <div className="flex items-center justify-between text-sm">
        <span className="font-semibold text-success">Run complete</span>
        {totalMs !== null && totalMs !== undefined && (
          <span className="font-mono text-xs text-foreground">
            {formatMs(totalMs)} total
          </span>
        )}
      </div>
      {knownStages.length > 0 && (
        <div
          className="mt-2 grid grid-cols-3 gap-2"
          data-testid="stage-timings"
        >
          {knownStages.map((s) => (
            <div
              key={s.label}
              className="rounded-md bg-surface border border-border px-2 py-1.5 text-center"
            >
              <div className="text-[10px] uppercase tracking-wider text-text-muted">
                {s.label}
              </div>
              <div className="font-mono text-xs text-foreground">
                {formatMs(s.ms)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
