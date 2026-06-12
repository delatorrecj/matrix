import {
  RunState,
  TOTAL_EXPECTED_RESULTS,
  formatMs,
  formatProgress,
} from "@/lib/simulationRun";

/**
 * Progress line while the run streams ("n/5 dimensions · m/17 results") and,
 * once DONE, the stage-timing summary (SUMO / modules / Gemini breakdown when
 * the server provides `timings`; legacy `duration_ms` otherwise).
 * All numbers shown are received counts/timings — nothing is estimated.
 */
interface RunProgressProps {
  runState: RunState;
}

export default function RunProgress({ runState }: RunProgressProps) {
  if (runState.phase === "done") {
    return <DoneSummary runState={runState} />;
  }

  // Counters stay visible on error/cancel/disconnect so partial progress is legible.
  const pct = Math.min(
    100,
    Math.round((runState.resultCount / TOTAL_EXPECTED_RESULTS) * 100),
  );

  return (
    <div data-testid="run-progress">
      <div className="flex items-center justify-between text-xs font-mono text-text-muted">
        <span data-testid="progress-line">{formatProgress(runState)}</span>
        <span>{pct}%</span>
      </div>
      <div className="mt-1 h-1.5 rounded-full bg-secondary overflow-hidden">
        <div
          className="h-full rounded-full bg-primary transition-all duration-300"
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
    { label: "Gemini", ms: timings?.gemini_ms },
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
