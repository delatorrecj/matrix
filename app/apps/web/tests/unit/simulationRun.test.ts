import { describe, it, expect, afterEach, vi } from "vitest";
import {
  RunEvent,
  TOTAL_DIMENSIONS,
  TOTAL_EXPECTED_RESULTS,
  buildSimulationWsUrl,
  dimensionsReported,
  formatMs,
  formatProgress,
  initialRunState,
  isDimensionComplete,
  reduceRunEvent,
  statusLabel,
} from "@/lib/simulationRun";

function stateAfter(events: RunEvent[]) {
  return events.reduce(reduceRunEvent, initialRunState());
}

describe("reduceRunEvent lifecycle", () => {
  it("starts connecting and moves to running on ACCEPTED", () => {
    expect(initialRunState().phase).toBe("connecting");
    expect(stateAfter([{ type: "ACCEPTED" }]).phase).toBe("running");
  });

  it("expects 5 dimensions and 17 results in total", () => {
    expect(TOTAL_DIMENSIONS).toBe(5);
    expect(TOTAL_EXPECTED_RESULTS).toBe(17);
  });

  it("tracks the QUEUED position and clears it on the first PLAYBACK_FRAME", () => {
    const queued = stateAfter([{ type: "ACCEPTED" }, { type: "QUEUED", position: 4 }]);
    expect(queued.phase).toBe("queued");
    expect(queued.queuePosition).toBe(4);

    const running = reduceRunEvent(queued, { type: "PLAYBACK_FRAME", tick: 0 });
    expect(running.phase).toBe("running");
    expect(running.queuePosition).toBeNull();
  });

  it("counts DIMENSION_RESULT events per dimension and in total", () => {
    const s = stateAfter([
      { type: "ACCEPTED" },
      { type: "DIMENSION_RESULT", dimension: "behavioral" },
      { type: "DIMENSION_RESULT", dimension: "behavioral" },
      { type: "DIMENSION_RESULT", dimension: "ecological" },
    ]);
    expect(s.resultsByDimension.behavioral).toBe(2);
    expect(s.resultsByDimension.ecological).toBe(1);
    expect(s.resultCount).toBe(3);
    expect(dimensionsReported(s)).toBe(2);
    expect(formatProgress(s)).toBe("2/5 dimensions · 3/17 results");
  });

  it("counts a result with an unknown dimension toward the total only", () => {
    const s = stateAfter([
      { type: "ACCEPTED" },
      { type: "DIMENSION_RESULT", dimension: "futuristic" },
    ]);
    expect(s.resultCount).toBe(1);
    expect(dimensionsReported(s)).toBe(0);
  });

  it("marks a dimension complete only at its expected count", () => {
    const two = stateAfter([
      { type: "DIMENSION_RESULT", dimension: "behavioral" },
      { type: "DIMENSION_RESULT", dimension: "behavioral" },
    ]);
    expect(isDimensionComplete(two, "behavioral")).toBe(false);
    const three = reduceRunEvent(two, { type: "DIMENSION_RESULT", dimension: "behavioral" });
    expect(isDimensionComplete(three, "behavioral")).toBe(true);
  });

  it("parses DONE with duration and per-stage timings", () => {
    const s = stateAfter([
      { type: "ACCEPTED" },
      {
        type: "DONE",
        duration_ms: 84210,
        timings: { sumo_ms: 41000, modules_ms: 18300, gemini_ms: 12100, total_ms: 84210 },
      },
    ]);
    expect(s.phase).toBe("done");
    expect(s.durationMs).toBe(84210);
    expect(s.timings).toEqual({
      sumo_ms: 41000,
      modules_ms: 18300,
      gemini_ms: 12100,
      total_ms: 84210,
    });
  });

  it("tolerates DONE without timings (older server) and malformed timings", () => {
    expect(stateAfter([{ type: "DONE", duration_ms: 950 }]).timings).toBeNull();
    expect(stateAfter([{ type: "DONE", duration_ms: 950, timings: "fast" }]).timings).toBeNull();
    expect(
      stateAfter([{ type: "DONE", duration_ms: 950, timings: { sumo_ms: "soon" } }]).timings,
    ).toBeNull();
  });

  it("captures ERROR stage/message/recoverable with safe defaults", () => {
    const s = stateAfter([
      { type: "ERROR", stage: "sumo", message: "TraCI crashed", recoverable: true },
    ]);
    expect(s.phase).toBe("error");
    expect(s.error).toEqual({ stage: "sumo", message: "TraCI crashed", recoverable: true });

    const bare = stateAfter([{ type: "ERROR" }]);
    expect(bare.error).toEqual({
      stage: "unknown",
      message: "Unknown server error",
      recoverable: false,
    });
  });

  it("ignores unknown and malformed event types (never crashes)", () => {
    const base = stateAfter([{ type: "ACCEPTED" }]);
    expect(reduceRunEvent(base, { type: "RUN_PLAN_V2" })).toBe(base);
    expect(reduceRunEvent(base, {})).toBe(base);
    expect(reduceRunEvent(base, { type: 42 })).toBe(base);
  });

  it("keeps terminal phases sticky (late close or events never relabel them)", () => {
    const done = stateAfter([{ type: "DONE", duration_ms: 1 }, { type: "WS_CLOSED" }]);
    expect(done.phase).toBe("done");

    const cancelled = stateAfter([
      { type: "ACCEPTED" },
      { type: "CANCEL" },
      { type: "WS_CLOSED" },
      { type: "DIMENSION_RESULT", dimension: "social" },
    ]);
    expect(cancelled.phase).toBe("cancelled");
    expect(cancelled.resultCount).toBe(0);

    const errored = stateAfter([
      { type: "ERROR", stage: "modules", message: "x", recoverable: false },
      { type: "DONE", duration_ms: 5 },
    ]);
    expect(errored.phase).toBe("error");
  });

  it("treats a close before open as unreachable, mid-run close as disconnected", () => {
    const neverConnected = stateAfter([{ type: "WS_CLOSED" }]);
    expect(neverConnected.phase).toBe("disconnected");
    expect(neverConnected.wsOpened).toBe(false);
    expect(statusLabel(neverConnected)).toBe("Unreachable");

    const dropped = stateAfter([{ type: "WS_OPEN" }, { type: "ACCEPTED" }, { type: "WS_CLOSED" }]);
    expect(dropped.phase).toBe("disconnected");
    expect(dropped.wsOpened).toBe(true);
    expect(statusLabel(dropped)).toBe("Disconnected");
  });

  it("labels each phase for the header chip", () => {
    expect(statusLabel(initialRunState())).toBe("Connecting…");
    expect(statusLabel(stateAfter([{ type: "QUEUED", position: 2 }]))).toBe(
      "Queued (position 2)",
    );
    expect(statusLabel(stateAfter([{ type: "ACCEPTED" }]))).toBe("Running simulation…");
    expect(statusLabel(stateAfter([{ type: "DONE", duration_ms: 84210 }]))).toBe("Done (84.2s)");
    expect(statusLabel(stateAfter([{ type: "CANCEL" }]))).toBe("Cancelled");
    expect(statusLabel(stateAfter([{ type: "ERROR" }]))).toBe("Error");
  });
});

describe("formatMs", () => {
  it("uses ms below a second and one-decimal seconds above", () => {
    expect(formatMs(950)).toBe("950ms");
    expect(formatMs(1000)).toBe("1.0s");
    expect(formatMs(84210)).toBe("84.2s");
  });
});

describe("buildSimulationWsUrl", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("falls back to the local dev API and encodes the scenario id", () => {
    vi.stubEnv("NEXT_PUBLIC_API_WS_URL", "");
    expect(buildSimulationWsUrl("scn 1/x")).toBe(
      "ws://localhost:8000/simulate/scn%201%2Fx",
    );
  });

  it("uses NEXT_PUBLIC_API_WS_URL and strips trailing slashes", () => {
    vi.stubEnv("NEXT_PUBLIC_API_WS_URL", "wss://api.matrix.example/");
    expect(buildSimulationWsUrl("scn-1")).toBe(
      "wss://api.matrix.example/simulate/scn-1",
    );
  });

  it("appends the env-gated api_key parameter when provided", () => {
    vi.stubEnv("NEXT_PUBLIC_API_WS_URL", "ws://localhost:8000");
    expect(buildSimulationWsUrl("scn-1", "k&y")).toBe(
      "ws://localhost:8000/simulate/scn-1?api_key=k%26y",
    );
  });
});
