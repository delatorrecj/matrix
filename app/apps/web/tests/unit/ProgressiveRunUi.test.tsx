import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RunStatusBanner from "@/components/RunStatusBanner";
import RunProgress from "@/components/RunProgress";
import DimensionCardSkeleton from "@/components/DimensionCardSkeleton";
import ScenarioSimulation from "@/app/scenario/[id]/page";
import {
  RunEvent,
  initialRunState,
  reduceRunEvent,
} from "@/lib/simulationRun";

// --- Heavy map/WebGL modules are not jsdom-compatible: stub them out
//     (same pattern as HomeCockpit.test.tsx). ---
vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "scn-test" }),
}));
vi.mock("react-map-gl/maplibre", () => ({
  Map: () => null,
}));
vi.mock("maplibre-gl", () => ({ default: {} }));
vi.mock("@deck.gl/react", () => ({
  default: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="deckgl">{children}</div>
  ),
}));
vi.mock("@deck.gl/geo-layers", () => ({
  TripsLayer: vi.fn(),
}));
// Sibling panels own their own fetches/markup — not under test here.
vi.mock("@/components/InspectDrawer", () => ({ default: () => null }));
vi.mock("@/components/ValidationPanel", () => ({ default: () => null }));
vi.mock("@/components/BiasAuditLog", () => ({ default: () => null }));

function stateAfter(events: RunEvent[]) {
  return events.reduce(reduceRunEvent, initialRunState());
}

describe("RunStatusBanner", () => {
  it("renders nothing while running or done", () => {
    const running = stateAfter([{ type: "ACCEPTED" }]);
    const { container, rerender } = render(
      <RunStatusBanner runState={running} onRetry={() => {}} />,
    );
    expect(container).toBeEmptyDOMElement();

    const done = stateAfter([{ type: "ACCEPTED" }, { type: "DONE", duration_ms: 1 }]);
    rerender(<RunStatusBanner runState={done} onRetry={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the queue position for QUEUED", () => {
    const queued = stateAfter([{ type: "ACCEPTED" }, { type: "QUEUED", position: 3 }]);
    render(<RunStatusBanner runState={queued} onRetry={() => {}} />);
    expect(screen.getByTestId("queued-notice")).toHaveTextContent("at position 3");
  });

  it("shows stage, message, recoverable hint and a working retry button on ERROR", () => {
    const onRetry = vi.fn();
    const errored = stateAfter([
      { type: "ACCEPTED" },
      { type: "ERROR", stage: "sumo", message: "TraCI crashed", recoverable: true },
    ]);
    render(<RunStatusBanner runState={errored} onRetry={onRetry} />);

    const banner = screen.getByTestId("error-banner");
    expect(banner).toHaveTextContent("sumo stage");
    expect(banner).toHaveTextContent("TraCI crashed");
    expect(banner).toHaveTextContent(/recoverable — retrying is likely to succeed/i);

    fireEvent.click(screen.getByRole("button", { name: /retry run/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("flags non-recoverable errors", () => {
    const errored = stateAfter([
      { type: "ERROR", stage: "synthesis", message: "boom", recoverable: false },
    ]);
    render(<RunStatusBanner runState={errored} onRetry={() => {}} />);
    expect(screen.getByTestId("error-banner")).toHaveTextContent(/non-recoverable/i);
  });

  it("offers reconnect when the socket drops mid-run", () => {
    const onRetry = vi.fn();
    const dropped = stateAfter([
      { type: "WS_OPEN" },
      { type: "ACCEPTED" },
      { type: "WS_CLOSED" },
    ]);
    render(<RunStatusBanner runState={dropped} onRetry={onRetry} />);
    const banner = screen.getByTestId("disconnect-banner");
    expect(banner).toHaveTextContent(/connection lost mid-run/i);
    fireEvent.click(screen.getByRole("button", { name: /reconnect/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("distinguishes a connection that never opened", () => {
    const unreachable = stateAfter([{ type: "WS_CLOSED" }]);
    render(<RunStatusBanner runState={unreachable} onRetry={() => {}} />);
    expect(screen.getByTestId("disconnect-banner")).toHaveTextContent(
      /could not reach the simulation api/i,
    );
  });

  it("labels a cancelled run distinctly from an error", () => {
    const cancelled = stateAfter([{ type: "ACCEPTED" }, { type: "CANCEL" }]);
    render(<RunStatusBanner runState={cancelled} onRetry={() => {}} />);
    const notice = screen.getByTestId("cancelled-notice");
    expect(notice).toHaveTextContent("Run cancelled");
    expect(notice).toHaveTextContent(/not a failure/i);
    expect(screen.queryByTestId("error-banner")).not.toBeInTheDocument();
  });
});

describe("RunProgress", () => {
  it("shows the n/5 · m/17 progress line while streaming", () => {
    const mid = stateAfter([
      { type: "ACCEPTED" },
      { type: "DIMENSION_RESULT", dimension: "behavioral", metric: "a" },
      { type: "DIMENSION_RESULT", dimension: "behavioral", metric: "b" },
      { type: "DIMENSION_RESULT", dimension: "ecological", metric: "c" },
    ]);
    render(<RunProgress runState={mid} />);
    expect(screen.getByTestId("progress-line")).toHaveTextContent(
      "2/5 dimensions · 3/17 results",
    );
  });

  it("starts honestly at zero", () => {
    render(<RunProgress runState={initialRunState()} />);
    expect(screen.getByTestId("progress-line")).toHaveTextContent(
      "0/5 dimensions · 0/17 results",
    );
  });

  it("shows the per-stage breakdown when DONE carries timings", () => {
    const done = stateAfter([
      { type: "ACCEPTED" },
      {
        type: "DONE",
        duration_ms: 84210,
        timings: { sumo_ms: 41000, modules_ms: 18300, gemini_ms: 12100, total_ms: 84210 },
      },
    ]);
    render(<RunProgress runState={done} />);
    const summary = screen.getByTestId("done-summary");
    expect(summary).toHaveTextContent("Run complete");
    expect(summary).toHaveTextContent("84.2s total");
    const stages = screen.getByTestId("stage-timings");
    expect(stages).toHaveTextContent("SUMO");
    expect(stages).toHaveTextContent("41.0s");
    expect(stages).toHaveTextContent("Modules");
    expect(stages).toHaveTextContent("18.3s");
    expect(stages).toHaveTextContent("Gemini");
    expect(stages).toHaveTextContent("12.1s");
  });

  it("falls back to legacy duration_ms when timings are absent", () => {
    const done = stateAfter([{ type: "ACCEPTED" }, { type: "DONE", duration_ms: 950 }]);
    render(<RunProgress runState={done} />);
    expect(screen.getByTestId("done-summary")).toHaveTextContent("950ms total");
    expect(screen.queryByTestId("stage-timings")).not.toBeInTheDocument();
  });
});

describe("DimensionCardSkeleton", () => {
  it("labels the awaited dimension without rendering placeholder numbers", () => {
    render(
      <DimensionCardSkeleton
        name="ecological"
        colorClass="bg-[#16A34A]"
        expectedResults={4}
      />,
    );
    const skeleton = screen.getByTestId("skeleton-ecological");
    expect(skeleton).toHaveTextContent("ecological");
    expect(skeleton).toHaveTextContent("Awaiting 4 results");
    // Glass-box: a skeleton must never show a digit that could read as a value.
    const text = skeleton.textContent ?? "";
    expect(text.replace("Awaiting 4 results", "")).not.toMatch(/\d/);
  });

  it("stops claiming to await results once the run is no longer active", () => {
    render(
      <DimensionCardSkeleton
        name="social"
        colorClass="bg-[#DB2777]"
        expectedResults={3}
        active={false}
      />,
    );
    const skeleton = screen.getByTestId("skeleton-social");
    expect(skeleton).toHaveTextContent("No results received");
    expect(skeleton).not.toHaveTextContent(/awaiting/i);
    expect(skeleton.querySelector(".animate-pulse")).toBeNull();
  });
});

// --- Page-level integration: the scenario page driven through a fake WebSocket. ---

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  close() {
    if (this.closed) return;
    this.closed = true;
    this.onclose?.();
  }

  /** Test helper: deliver a server event as a JSON frame. */
  emit(event: unknown) {
    this.onmessage?.({ data: JSON.stringify(event) });
  }
}

const RESULT_BEH_1 = {
  type: "DIMENSION_RESULT",
  dimension: "behavioral",
  metric: "Mode shift",
  equation_id: "BEH-1",
  value: 4.2,
  range: [3.1, 5.3],
  unit: "%",
  confidence: "M",
  input_dataset_ids: ["lptrp-2023"],
  references: [],
  assumptions: [],
};

describe("ScenarioSimulation page (progressive run UX)", () => {
  beforeEach(() => {
    FakeWebSocket.instances = [];
    vi.stubGlobal("WebSocket", FakeWebSocket);
    // Keep the playback rAF loop inert in jsdom.
    vi.stubGlobal("requestAnimationFrame", () => 0);
    vi.stubGlobal("cancelAnimationFrame", () => {});
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function lastSocket(): FakeWebSocket {
    const ws = FakeWebSocket.instances.at(-1);
    if (!ws) throw new Error("no WebSocket was opened");
    return ws;
  }

  it("connects to the scenario's simulate stream via the WS URL builder", () => {
    render(<ScenarioSimulation />);
    expect(FakeWebSocket.instances).toHaveLength(1);
    expect(lastSocket().url).toBe("ws://localhost:8000/simulate/scn-test");
  });

  it("renders five labeled skeletons before any results, then swaps them per dimension", () => {
    render(<ScenarioSimulation />);
    const ws = lastSocket();
    act(() => {
      ws.onopen?.();
      ws.emit({ type: "ACCEPTED", scenario_id: "scn-test" });
    });

    for (const dim of ["behavioral", "ecological", "social", "economic", "societal"]) {
      expect(screen.getByTestId(`skeleton-${dim}`)).toBeInTheDocument();
    }
    expect(screen.getByTestId("progress-line")).toHaveTextContent(
      "0/5 dimensions · 0/17 results",
    );

    act(() => ws.emit(RESULT_BEH_1));

    expect(screen.queryByTestId("skeleton-behavioral")).not.toBeInTheDocument();
    expect(screen.getByTestId("skeleton-ecological")).toBeInTheDocument();
    expect(screen.getByText("Mode shift")).toBeInTheDocument();
    expect(screen.getByTestId("progress-line")).toHaveTextContent(
      "1/5 dimensions · 1/17 results",
    );
  });

  it("survives unknown event types without losing state", () => {
    render(<ScenarioSimulation />);
    const ws = lastSocket();
    act(() => {
      ws.onopen?.();
      ws.emit({ type: "ACCEPTED", scenario_id: "scn-test" });
      ws.emit(RESULT_BEH_1);
      ws.emit({ type: "TELEMETRY_V9", payload: { surprise: true } });
    });
    expect(screen.getByTestId("ws-status")).toHaveTextContent("Running simulation…");
    expect(screen.getByTestId("progress-line")).toHaveTextContent("1/17 results");
  });

  it("shows the queue position while QUEUED", () => {
    render(<ScenarioSimulation />);
    const ws = lastSocket();
    act(() => {
      ws.onopen?.();
      ws.emit({ type: "ACCEPTED", scenario_id: "scn-test" });
      ws.emit({ type: "QUEUED", scenario_id: "scn-test", position: 2 });
    });
    expect(screen.getByTestId("queued-notice")).toHaveTextContent("at position 2");
    expect(screen.getByTestId("ws-status")).toHaveTextContent("Queued (position 2)");
  });

  it("cancel closes the socket and marks the run cancelled (not failed, not done)", () => {
    render(<ScenarioSimulation />);
    const ws = lastSocket();
    act(() => {
      ws.onopen?.();
      ws.emit({ type: "ACCEPTED", scenario_id: "scn-test" });
    });

    fireEvent.click(screen.getByTestId("cancel-run"));

    expect(ws.closed).toBe(true);
    expect(screen.getByTestId("cancelled-notice")).toBeInTheDocument();
    expect(screen.queryByTestId("error-banner")).not.toBeInTheDocument();
    expect(screen.queryByTestId("done-summary")).not.toBeInTheDocument();
    // Terminal: the cancel control goes away, and skeletons stop "awaiting".
    expect(screen.queryByTestId("cancel-run")).not.toBeInTheDocument();
    expect(screen.getByTestId("skeleton-social")).toHaveTextContent("No results received");
  });

  it("renders the ERROR banner and retry opens a fresh socket", () => {
    render(<ScenarioSimulation />);
    const first = lastSocket();
    act(() => {
      first.onopen?.();
      first.emit({ type: "ACCEPTED", scenario_id: "scn-test" });
      first.emit({
        type: "ERROR",
        scenario_id: "scn-test",
        stage: "sumo",
        message: "stage 'sumo' exceeded its 120s budget",
        recoverable: true,
      });
      first.close();
    });

    const banner = screen.getByTestId("error-banner");
    expect(banner).toHaveTextContent("sumo stage");
    expect(banner).toHaveTextContent("exceeded its 120s budget");
    expect(screen.getByTestId("ws-status")).toHaveTextContent("Error");

    fireEvent.click(screen.getByRole("button", { name: /retry run/i }));

    expect(FakeWebSocket.instances).toHaveLength(2);
    expect(screen.getByTestId("ws-status")).toHaveTextContent("Connecting…");
    expect(screen.queryByTestId("error-banner")).not.toBeInTheDocument();
  });

  it("shows a disconnect banner when the socket drops mid-run, and reconnects", () => {
    render(<ScenarioSimulation />);
    const first = lastSocket();
    act(() => {
      first.onopen?.();
      first.emit({ type: "ACCEPTED", scenario_id: "scn-test" });
      first.emit(RESULT_BEH_1);
      first.close(); // server/network drop — not user cancel, not DONE
    });

    const banner = screen.getByTestId("disconnect-banner");
    expect(banner).toHaveTextContent(/connection lost mid-run/i);
    // Partial progress stays legible.
    expect(screen.getByTestId("progress-line")).toHaveTextContent("1/17 results");

    fireEvent.click(screen.getByRole("button", { name: /reconnect/i }));
    expect(FakeWebSocket.instances).toHaveLength(2);
    // Accumulated stream state resets for the fresh run.
    expect(screen.getByTestId("progress-line")).toHaveTextContent("0/17 results");
  });

  it("on DONE shows the duration and per-stage timings, never a disconnect banner", () => {
    render(<ScenarioSimulation />);
    const ws = lastSocket();
    act(() => {
      ws.onopen?.();
      ws.emit({ type: "ACCEPTED", scenario_id: "scn-test" });
      ws.emit(RESULT_BEH_1);
      ws.emit({
        type: "DONE",
        scenario_id: "scn-test",
        duration_ms: 84210,
        timings: { sumo_ms: 41000, modules_ms: 18300, gemini_ms: 12100, total_ms: 84210 },
      });
    });

    // The page closes the socket after DONE; the late close must not relabel the run.
    expect(ws.closed).toBe(true);
    expect(screen.getByTestId("ws-status")).toHaveTextContent("Done (84.2s)");
    const summary = screen.getByTestId("done-summary");
    expect(summary).toHaveTextContent("84.2s total");
    expect(screen.getByTestId("stage-timings")).toHaveTextContent("SUMO");
    expect(screen.queryByTestId("disconnect-banner")).not.toBeInTheDocument();
    expect(screen.queryByTestId("cancel-run")).not.toBeInTheDocument();
  });
});
