import type { RunState } from "@/lib/simulationRun";

/**
 * Lifecycle banners for the simulation run. Renders exactly one of:
 *  - QUEUED notice (position in queue)
 *  - ERROR banner (stage + message + recoverable hint + retry)
 *  - Disconnected banner (WS dropped mid-run, or never connected) + reconnect
 *  - Cancelled notice (user-initiated; deliberately distinct from error)
 * Renders nothing while connecting / running / done.
 */
interface RunStatusBannerProps {
  runState: RunState;
  onRetry: () => void;
}

export default function RunStatusBanner({ runState, onRetry }: RunStatusBannerProps) {
  switch (runState.phase) {
    case "queued":
      return (
        <div
          className="border border-border bg-secondary rounded-lg p-3 text-sm text-text-muted"
          role="status"
          data-testid="queued-notice"
        >
          <span className="font-medium text-foreground">Queued</span>
          {runState.queuePosition !== null
            ? ` at position ${runState.queuePosition}`
            : ""}
          {" — the run will start automatically."}
        </div>
      );

    case "error": {
      const err = runState.error;
      return (
        <div
          className="border border-error/30 bg-error/10 rounded-lg p-3 text-sm"
          role="alert"
          data-testid="error-banner"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold text-error">
              Simulation error
              {err ? ` — ${err.stage} stage` : ""}
            </span>
            <button
              onClick={onRetry}
              className="shrink-0 px-3 py-1 rounded-md bg-error text-white text-xs font-medium hover:opacity-90 transition-opacity"
            >
              Retry run
            </button>
          </div>
          {err && <p className="mt-1 text-foreground">{err.message}</p>}
          <p className="mt-1 text-xs text-text-muted">
            {err?.recoverable
              ? "The server marked this error as recoverable — retrying is likely to succeed."
              : "The server marked this error as non-recoverable — retrying may fail again."}
          </p>
        </div>
      );
    }

    case "disconnected": {
      const neverConnected = !runState.wsOpened;
      return (
        <div
          className="border border-warning/30 bg-warning/10 rounded-lg p-3 text-sm"
          role="alert"
          data-testid="disconnect-banner"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold text-warning">
              {neverConnected
                ? "Could not reach the simulation API"
                : "Connection lost mid-run"}
            </span>
            <button
              onClick={onRetry}
              className="shrink-0 px-3 py-1 rounded-md bg-warning text-white text-xs font-medium hover:opacity-90 transition-opacity"
            >
              Reconnect
            </button>
          </div>
          <p className="mt-1 text-xs text-text-muted">
            {neverConnected
              ? "The WebSocket connection could not be opened. Check that the API is up, then reconnect."
              : "The stream dropped before the run finished. Reconnecting restarts the simulation stream."}
          </p>
        </div>
      );
    }

    case "cancelled":
      return (
        <div
          className="border border-border bg-secondary rounded-lg p-3 text-sm"
          role="status"
          data-testid="cancelled-notice"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold text-foreground">Run cancelled</span>
            <button
              onClick={onRetry}
              className="shrink-0 px-3 py-1 rounded-md border border-border bg-surface text-xs font-medium hover:border-primary hover:text-primary transition-colors"
            >
              Re-run
            </button>
          </div>
          <p className="mt-1 text-xs text-text-muted">
            You stopped this run — results above are partial, not a failure.
          </p>
        </div>
      );

    default:
      return null;
  }
}
