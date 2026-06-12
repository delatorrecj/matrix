/**
 * Pure state machine for the progressive simulation run (WS /simulate/{id}).
 *
 * Server events (matrix_api/main.py EVENT_TYPES — RFC matrix-rfc-001 §3 plus the
 * additive QUEUED/ERROR hardening events; order is never changed, only extended):
 *   ACCEPTED -> [QUEUED] -> PLAYBACK_FRAME* -> DIMENSION_RESULT*17 -> SYNTHESIS -> DONE
 *   ERROR may arrive at any stage. Unknown event types are ignored (never crash).
 *
 * Local control events (WS_OPEN / WS_CLOSED / CANCEL) are folded into the same
 * reducer so the whole lifecycle is unit-testable as plain data.
 *
 * Glass-box note: counters here only ever count *received* DIMENSION_RESULT events —
 * no placeholder numbers are fabricated for dimensions that have not reported.
 */

export const DIMENSIONS = [
  "behavioral",
  "ecological",
  "social",
  "economic",
  "societal",
] as const;

export type DimensionId = (typeof DIMENSIONS)[number];

/** Expected result (metric) count per dimension — methods-matrix Phase 3 equations. */
export const EXPECTED_RESULTS: Record<DimensionId, number> = {
  behavioral: 3, // BEH-1..3
  ecological: 4, // ECO-1..4
  social: 3, // SOC-1..3
  economic: 3, // ECON-1..3
  societal: 4, // SOCI-1..4
};

export const TOTAL_DIMENSIONS = DIMENSIONS.length; // 5
export const TOTAL_EXPECTED_RESULTS = Object.values(EXPECTED_RESULTS).reduce(
  (a, b) => a + b,
  0,
); // 17

export function isKnownDimension(id: unknown): id is DimensionId {
  return typeof id === "string" && (DIMENSIONS as readonly string[]).includes(id);
}

/**
 * Run lifecycle phases. Terminal phases (done / error / cancelled) are sticky:
 * a late WS close must not relabel a finished run as "disconnected", and
 * cancelled is deliberately distinct from both error and done.
 */
export type RunPhase =
  | "connecting"
  | "queued"
  | "running"
  | "done"
  | "error"
  | "cancelled"
  | "disconnected";

export interface RunError {
  stage: string;
  message: string;
  recoverable: boolean;
}

/** DONE per-stage breakdown (matrix_api.runtime.StageTimer — keys are a contract). */
export interface RunTimings {
  sumo_ms?: number;
  modules_ms?: number;
  gemini_ms?: number;
  total_ms?: number;
}

export interface RunState {
  phase: RunPhase;
  /** True once the socket opened — distinguishes connect-failure from a mid-run drop. */
  wsOpened: boolean;
  /** Queue position from the latest QUEUED event (null once running). */
  queuePosition: number | null;
  /** Received DIMENSION_RESULT count per known dimension. */
  resultsByDimension: Record<DimensionId, number>;
  /** Total DIMENSION_RESULT events received (incl. unknown dimension ids). */
  resultCount: number;
  /** True once SYNTHESIS arrived. */
  synthesisReceived: boolean;
  /** From DONE: total duration (also present inside timings as total_ms). */
  durationMs: number | null;
  /** From DONE: per-stage breakdown (absent on older servers). */
  timings: RunTimings | null;
  error: RunError | null;
}

const TERMINAL_PHASES: ReadonlySet<RunPhase> = new Set<RunPhase>([
  "done",
  "error",
  "cancelled",
]);

export function isTerminal(phase: RunPhase): boolean {
  return TERMINAL_PHASES.has(phase);
}

export function initialRunState(): RunState {
  return {
    phase: "connecting",
    wsOpened: false,
    queuePosition: null,
    resultsByDimension: {
      behavioral: 0,
      ecological: 0,
      social: 0,
      economic: 0,
      societal: 0,
    },
    resultCount: 0,
    synthesisReceived: false,
    durationMs: null,
    timings: null,
    error: null,
  };
}

/** Local (client-side) lifecycle events folded into the reducer. */
export type LocalRunEvent =
  | { type: "WS_OPEN" }
  | { type: "WS_CLOSED" }
  | { type: "CANCEL" };

/** Any message: server events come off the wire as untyped JSON — treat defensively. */
export type RunEvent = LocalRunEvent | { type?: unknown; [key: string]: unknown };

function asFiniteNumber(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function parseTimings(raw: unknown): RunTimings | null {
  if (raw === null || typeof raw !== "object") return null;
  const t = raw as Record<string, unknown>;
  const timings: RunTimings = {};
  const sumo = asFiniteNumber(t.sumo_ms);
  const modules = asFiniteNumber(t.modules_ms);
  const gemini = asFiniteNumber(t.gemini_ms);
  const total = asFiniteNumber(t.total_ms);
  if (sumo !== null) timings.sumo_ms = sumo;
  if (modules !== null) timings.modules_ms = modules;
  if (gemini !== null) timings.gemini_ms = gemini;
  if (total !== null) timings.total_ms = total;
  return Object.keys(timings).length > 0 ? timings : null;
}

/**
 * Reduce one event (server or local) into the next run state.
 * Pure: never throws on malformed input; unknown event types are a no-op.
 */
export function reduceRunEvent(state: RunState, event: RunEvent): RunState {
  const type = typeof event?.type === "string" ? event.type : null;
  if (type === null) return state;

  // Terminal phases are sticky (incl. a late WS_CLOSED after DONE/ERROR/CANCEL).
  if (isTerminal(state.phase)) return state;

  switch (type) {
    case "WS_OPEN":
      // Still "connecting" until the server ACCEPTs the run.
      return { ...state, wsOpened: true };

    case "WS_CLOSED":
      return { ...state, phase: "disconnected" };

    case "CANCEL":
      return { ...state, phase: "cancelled" };

    case "ACCEPTED":
      return { ...state, phase: "running" };

    case "QUEUED": {
      const position = asFiniteNumber((event as Record<string, unknown>).position);
      return { ...state, phase: "queued", queuePosition: position };
    }

    case "PLAYBACK_FRAME":
      // First frame means we are out of the queue and simulating.
      return { ...state, phase: "running", queuePosition: null };

    case "DIMENSION_RESULT": {
      const dim = (event as Record<string, unknown>).dimension;
      const resultsByDimension = { ...state.resultsByDimension };
      if (isKnownDimension(dim)) {
        resultsByDimension[dim] += 1;
      }
      return {
        ...state,
        phase: "running",
        queuePosition: null,
        resultsByDimension,
        resultCount: state.resultCount + 1,
      };
    }

    case "SYNTHESIS":
      return { ...state, synthesisReceived: true };

    case "DONE": {
      const e = event as Record<string, unknown>;
      return {
        ...state,
        phase: "done",
        queuePosition: null,
        durationMs: asFiniteNumber(e.duration_ms),
        timings: parseTimings(e.timings),
      };
    }

    case "ERROR": {
      const e = event as Record<string, unknown>;
      return {
        ...state,
        phase: "error",
        error: {
          stage: typeof e.stage === "string" ? e.stage : "unknown",
          message:
            typeof e.message === "string" ? e.message : "Unknown server error",
          recoverable: e.recoverable === true,
        },
      };
    }

    default:
      // Unknown / future event types must never crash the page.
      return state;
  }
}

/** Dimensions that have reported at least one result. */
export function dimensionsReported(state: RunState): number {
  return DIMENSIONS.filter((d) => state.resultsByDimension[d] > 0).length;
}

/** True once a dimension has all the results we expect from it. */
export function isDimensionComplete(state: RunState, dim: DimensionId): boolean {
  return state.resultsByDimension[dim] >= EXPECTED_RESULTS[dim];
}

/** "n/5 dimensions · m/17 results" progress line. */
export function formatProgress(state: RunState): string {
  return `${dimensionsReported(state)}/${TOTAL_DIMENSIONS} dimensions · ${state.resultCount}/${TOTAL_EXPECTED_RESULTS} results`;
}

/** Short status label for the header chip. */
export function statusLabel(state: RunState): string {
  switch (state.phase) {
    case "connecting":
      return "Connecting…";
    case "queued":
      return state.queuePosition !== null
        ? `Queued (position ${state.queuePosition})`
        : "Queued";
    case "running":
      return "Running simulation…";
    case "done":
      return state.durationMs !== null
        ? `Done (${formatMs(state.durationMs)})`
        : "Done";
    case "error":
      return "Error";
    case "cancelled":
      return "Cancelled";
    case "disconnected":
      return state.wsOpened ? "Disconnected" : "Unreachable";
  }
}

export function formatMs(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`;
}

/**
 * Build the simulation WebSocket URL.
 *
 * Single place where the WS origin (NEXT_PUBLIC_API_WS_URL, falling back to the
 * local dev API) and the env-gated `?api_key=` parameter (matrix_api/auth.py —
 * browser WebSocket() can't set headers) are applied.
 */
export function buildSimulationWsUrl(scenarioId: string, apiKey?: string): string {
  const base = (process.env.NEXT_PUBLIC_API_WS_URL || "ws://localhost:8000").replace(
    /\/+$/,
    "",
  );
  const url = `${base}/simulate/${encodeURIComponent(scenarioId)}`;
  return apiKey ? `${url}?api_key=${encodeURIComponent(apiKey)}` : url;
}
