import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RunStatusBanner from "@/components/RunStatusBanner";
import RunProgress from "@/components/RunProgress";
import DimensionCardSkeleton from "@/components/DimensionCardSkeleton";
import ScenarioSimulation from "@/app/scenario/[id]/page";
import { getLatestRun, getScenario } from "@/lib/api";
import { TripsLayer } from "@deck.gl/geo-layers";
import { savePromptHandoff } from "@/lib/promptHandoff";
import {
  RunEvent,
  initialRunState,
  reduceRunEvent,
} from "@/lib/simulationRun";

// --- Heavy map/WebGL modules are not jsdom-compatible: stub them out
//     (same pattern as HomeCockpit.test.tsx). ---
const { pushMock, replaceMock, assignMock, SCENARIO_RECORD } = vi.hoisted(() => ({
  pushMock: vi.fn(),
  replaceMock: vi.fn(),
  assignMock: vi.fn(),
  SCENARIO_RECORD: {
    scenario_id: "scn-test",
    description: "close one lane on Diversion Rd",
    raw_input: "Close a lane on Diversion Road",
    intervention_type: "lane_closure",
    location: "Diversion Road",
    parameters: { lanes_closed: 1 },
    geometry: null,
    location_of_interest: [122.5621, 10.7202],
  },
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "scn-test" }),
  useRouter: () => ({
    push: pushMock,
    replace: replaceMock,
  }),
}));
vi.mock("react-map-gl/maplibre", () => ({
  Map: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="basemap">{children}</div>
  ),
  Marker: ({
    longitude,
    latitude,
  }: {
    longitude: number;
    latitude: number;
  }) => (
    <div
      data-testid="map-pin"
      data-lng={String(longitude)}
      data-lat={String(latitude)}
    />
  ),
  useControl: () => ({ setProps: vi.fn() }),
}));
vi.mock("maplibre-gl", () => ({ default: {} }));
vi.mock("@/components/map/DeckGLOverlay", () => ({
  DeckGLOverlay: () => null,
}));
vi.mock("@deck.gl/mapbox", () => ({
  MapboxOverlay: class {
    setProps() {}
  },
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
// CR-013 bootstrap awaits getScenario/getLatestRun before opening the WS — stub them so
// the page's own effect resolves in a microtask instead of racing a real network call.
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getScenario: vi.fn().mockResolvedValue(SCENARIO_RECORD),
    getLatestRun: vi.fn().mockResolvedValue(null),
  };
});
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
    expect(banner).toHaveTextContent(/recoverable\. Retrying is likely to succeed/i);

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
  it("shows the n/5 · m/18 progress line while streaming", () => {
    const mid = stateAfter([
      { type: "ACCEPTED" },
      { type: "DIMENSION_RESULT", dimension: "behavioral", metric: "a" },
      { type: "DIMENSION_RESULT", dimension: "behavioral", metric: "b" },
      { type: "DIMENSION_RESULT", dimension: "ecological", metric: "c" },
    ]);
    render(<RunProgress runState={mid} />);
    expect(screen.getByTestId("progress-line")).toHaveTextContent(
      "2/5 dimensions · 3/18 results",
    );
  });

  it("starts honestly at zero", () => {
    // CR-013 (44631f3): a fresh run never claims placeholder progress — it's
    // "Connecting…" until the socket opens, not "0/5 · 0/18 results".
    render(<RunProgress runState={initialRunState()} />);
    expect(screen.getByTestId("progress-line")).toHaveTextContent("Connecting…");
  });

  it("shows the per-stage breakdown when DONE carries timings", () => {
    const done = stateAfter([
      { type: "ACCEPTED" },
      {
        type: "DONE",
        duration_ms: 84210,
        timings: { sumo_ms: 41000, modules_ms: 18300, llm_ms: 12100, total_ms: 84210 },
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
    expect(stages).toHaveTextContent("Azure OpenAI");
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
    pushMock.mockReset();
    replaceMock.mockReset();
    assignMock.mockReset();
    vi.stubGlobal("WebSocket", FakeWebSocket);
    // Keep the playback rAF loop inert in jsdom.
    vi.stubGlobal("requestAnimationFrame", () => 0);
    vi.stubGlobal("cancelAnimationFrame", () => {});
    // jsdom's Location.assign is non-configurable; stub the whole location for hard-nav.
    vi.stubGlobal("location", { assign: assignMock, pathname: "/scenario/scn-test" });
    sessionStorage.clear();
    vi.mocked(getScenario).mockReset();
    vi.mocked(getScenario).mockResolvedValue(SCENARIO_RECORD);
    vi.mocked(getLatestRun).mockReset();
    vi.mocked(getLatestRun).mockResolvedValue(null);
    vi.mocked(TripsLayer).mockClear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function lastSocket(): FakeWebSocket {
    const ws = FakeWebSocket.instances.at(-1);
    if (!ws) throw new Error("no WebSocket was opened");
    return ws;
  }

  /** Render + flush the async CR-013 bootstrap (getScenario/getLatestRun) before the
   *  WS-opening effect runs, so the socket is deterministically present afterward. */
  async function renderScenario() {
    render(<ScenarioSimulation />);
    await act(async () => {});
  }

  it("shows the prompt card from GET /scenario", async () => {
    await renderScenario();
    expect(await screen.findByTestId("scenario-prompt-review")).toHaveTextContent(
      "Close a lane on Diversion Road",
    );
  });

  it("pins the map at GET /scenario LoI when there is no honest corridor overlay", async () => {
    await renderScenario();
    const pin = await screen.findByTestId("map-pin");
    expect(pin).toHaveAttribute("data-lng", "122.5621");
    expect(pin).toHaveAttribute("data-lat", "10.7202");
  });

  it("shows the prompt card from session handoff when GET /scenario fails", async () => {
    savePromptHandoff("scn-test", {
      rawInput: "Close a lane on Diversion Road",
      description: "close one lane on Diversion Rd",
      interventionType: "lane_closure",
      location: "Diversion Road",
      parameters: { lanes_closed: 1 },
    });
    vi.mocked(getScenario).mockRejectedValue(new Error("not found"));

    await renderScenario();

    expect(await screen.findByTestId("scenario-prompt-review")).toHaveTextContent(
      "Close a lane on Diversion Road",
    );
  });

  it("keeps the handoff question when GET /scenario returns empty raw_input", async () => {
    savePromptHandoff("scn-test", {
      rawInput: "Close a lane on Diversion Road",
      description: "close one lane on Diversion Rd",
      interventionType: "lane_closure",
      location: "Diversion Road",
      parameters: { lanes_closed: 1 },
    });
    vi.mocked(getScenario).mockResolvedValue({
      ...SCENARIO_RECORD,
      raw_input: "",
      description: "",
    });

    await renderScenario();

    expect(await screen.findByTestId("scenario-prompt-review")).toHaveTextContent(
      "Close a lane on Diversion Road",
    );
  });

  it("connects to the scenario's simulate stream via the WS URL builder", async () => {
    await renderScenario();
    expect(FakeWebSocket.instances).toHaveLength(1);
    expect(lastSocket().url).toBe("ws://localhost:8000/simulate/scn-test");
  });

  it("shows initializing state while the run is active, then summary cards after DONE", async () => {
    await renderScenario();
    const ws = lastSocket();
    act(() => {
      ws.onopen?.();
      ws.emit({ type: "ACCEPTED", scenario_id: "scn-test" });
    });

    // CR-010: active runs show InitializingState, not per-dimension skeletons.
    expect(screen.getByTestId("initializing-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("initializing-pill")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confidence" })).not.toBeInTheDocument();
    expect(screen.queryByRole("slider")).not.toBeInTheDocument();
    expect(screen.queryByTestId("skeleton-behavioral")).not.toBeInTheDocument();
    // CR-013 (44631f3): zero results reads as "Running traffic simulation…", not a
    // "0/5 · 0/18" placeholder.
    expect(screen.getByTestId("progress-line")).toHaveTextContent(
      "Running traffic simulation…",
    );

    act(() => ws.emit(RESULT_BEH_1));

    // The first real result flips the panel from InitializingState straight to
    // SummaryView — it doesn't wait for DONE (page.tsx: `results.length === 0`).
    expect(screen.queryByTestId("initializing-panel")).not.toBeInTheDocument();
    expect(screen.getByText("Mode shift")).toBeInTheDocument();
    expect(screen.queryByTestId("skeleton-behavioral")).not.toBeInTheDocument();
    expect(screen.getByTestId("skeleton-ecological")).toBeInTheDocument();
    expect(screen.getByTestId("progress-line")).toHaveTextContent(
      "1/5 dimensions · 1/18 results",
    );

    act(() => ws.emit({ type: "DONE", scenario_id: "scn-test", duration_ms: 1000 }));

    expect(screen.queryByTestId("initializing-panel")).not.toBeInTheDocument();
    expect(screen.getByText("Mode shift")).toBeInTheDocument();
    expect(screen.queryByTestId("skeleton-behavioral")).not.toBeInTheDocument();
    expect(screen.getByTestId("skeleton-ecological")).toBeInTheDocument();
  });

  it("renders the map layer legend and ingests EDGE_COUNTS without disrupting the run", async () => {
    await renderScenario();
    const ws = lastSocket();

    // Layer toggles are present (congestion/confidence/flood are assembled by useMapLayers).
    expect(screen.getByText("Congestion")).toBeInTheDocument();
    expect(screen.getByText("Flood Zones")).toBeInTheDocument();

    act(() => {
      ws.onopen?.();
      ws.emit({ type: "ACCEPTED", scenario_id: "scn-test" });
      ws.emit({ type: "EDGE_COUNTS", edge_counts: { "edge-1": 12, "edge-2": 3 } });
      ws.emit(RESULT_BEH_1);
    });

    // EDGE_COUNTS is a no-op for run progress; the header chip uses the compact label.
    expect(screen.getByTestId("ws-status")).toHaveTextContent("Running…");
    expect(screen.getByTestId("progress-line")).toHaveTextContent("1/18 results");

    // Toggling a layer must not crash the page.
    fireEvent.click(screen.getByText("Flood Zones"));
    expect(screen.getByTestId("ws-status")).toHaveTextContent("Running…");
  });

  it("survives unknown event types without losing state", async () => {
    await renderScenario();
    const ws = lastSocket();
    act(() => {
      ws.onopen?.();
      ws.emit({ type: "ACCEPTED", scenario_id: "scn-test" });
      ws.emit(RESULT_BEH_1);
      ws.emit({ type: "TELEMETRY_V9", payload: { surprise: true } });
    });
    expect(screen.getByTestId("ws-status")).toHaveTextContent("Running…");
    expect(screen.getByTestId("progress-line")).toHaveTextContent("1/18 results");
  });

  it("shows the queue position while QUEUED", async () => {
    await renderScenario();
    const ws = lastSocket();
    act(() => {
      ws.onopen?.();
      ws.emit({ type: "ACCEPTED", scenario_id: "scn-test" });
      ws.emit({ type: "QUEUED", scenario_id: "scn-test", position: 2 });
    });
    expect(screen.getByTestId("queued-notice")).toHaveTextContent("at position 2");
    expect(screen.getByTestId("ws-status")).toHaveTextContent("Queued #2");
  });

  it("cancel closes the socket and marks the run cancelled (not failed, not done)", async () => {
    await renderScenario();
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
    // Cancel stays on the scenario page — it is not an exit.
    expect(replaceMock).not.toHaveBeenCalled();
    expect(assignMock).not.toHaveBeenCalled();
  });

  it("Home mid-run opens a confirm dialog and does not exit until Leave", async () => {
    await renderScenario();
    const ws = lastSocket();
    act(() => {
      ws.onopen?.();
      ws.emit({ type: "ACCEPTED", scenario_id: "scn-test" });
    });

    fireEvent.click(screen.getByRole("button", { name: "Home" }));

    expect(screen.getByRole("dialog", { name: /leave this scenario/i })).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
    expect(ws.closed).toBe(false);

    fireEvent.click(screen.getByRole("button", { name: "Stay" }));
    expect(screen.queryByRole("dialog", { name: /leave this scenario/i })).not.toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Home" }));
    fireEvent.click(screen.getByRole("button", { name: "Leave" }));

    expect(ws.closed).toBe(true);
    expect(screen.getByTestId("cancelled-notice")).toBeInTheDocument();
    expect(replaceMock).toHaveBeenCalledWith("/app");
    expect(assignMock).toHaveBeenCalledWith("/app");
  });

  it("logo Home mid-run also confirms before exiting to /app", async () => {
    await renderScenario();
    const ws = lastSocket();
    act(() => {
      ws.onopen?.();
      ws.emit({ type: "ACCEPTED", scenario_id: "scn-test" });
    });

    fireEvent.click(screen.getByRole("button", { name: "MATRIX home" }));
    expect(replaceMock).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Leave" }));

    expect(ws.closed).toBe(true);
    expect(screen.getByTestId("cancelled-notice")).toBeInTheDocument();
    expect(replaceMock).toHaveBeenCalledWith("/app");
    expect(assignMock).toHaveBeenCalledWith("/app");
  });

  it("Home after DONE still confirms, then exits to /app without requiring Cancel", async () => {
    await renderScenario();
    const ws = lastSocket();
    act(() => {
      ws.onopen?.();
      ws.emit({ type: "ACCEPTED", scenario_id: "scn-test" });
      ws.emit(RESULT_BEH_1);
      ws.emit({ type: "DONE", scenario_id: "scn-test", duration_ms: 1000 });
    });

    expect(screen.queryByTestId("cancel-run")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Home" }));
    expect(replaceMock).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Leave" }));

    expect(replaceMock).toHaveBeenCalledWith("/app");
    expect(assignMock).toHaveBeenCalledWith("/app");
  });

  it("hides the confidence map toggle and the map initializing overlay while the run is active", async () => {
    await renderScenario();
    const ws = lastSocket();
    act(() => {
      ws.onopen?.();
      ws.emit({ type: "ACCEPTED", scenario_id: "scn-test" });
    });

    expect(screen.getByTestId("initializing-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("initializing-pill")).not.toBeInTheDocument();
    expect(screen.getByTestId("map-layer-legend")).toBeInTheDocument();
    expect(screen.getByText("Agent Trajectories")).toBeInTheDocument();
    expect(screen.getByText("Congestion")).toBeInTheDocument();
    expect(screen.getByText("Flood Zones")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confidence" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/playback/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("slider")).not.toBeInTheDocument();

    act(() => {
      ws.emit(RESULT_BEH_1);
      ws.emit({ type: "DONE", scenario_id: "scn-test", duration_ms: 1000 });
    });

    expect(screen.queryByTestId("initializing-panel")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confidence" })).not.toBeInTheDocument();
    expect(screen.queryByRole("slider")).not.toBeInTheDocument();
  });

  it("renders the ERROR banner and retry opens a fresh socket", async () => {
    await renderScenario();
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

  it("shows a disconnect banner when the socket drops mid-run, and reconnects", async () => {
    await renderScenario();
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
    expect(screen.getByTestId("progress-line")).toHaveTextContent("1/18 results");

    fireEvent.click(screen.getByRole("button", { name: /reconnect/i }));
    expect(FakeWebSocket.instances).toHaveLength(2);
    // Accumulated stream state resets for the fresh run, back to "Connecting…"
    // (CR-013, 44631f3) until the new socket opens.
    expect(screen.getByTestId("progress-line")).toHaveTextContent("Connecting…");
  });

  it("on DONE shows the duration and per-stage timings, never a disconnect banner", async () => {
    await renderScenario();
    const ws = lastSocket();
    act(() => {
      ws.onopen?.();
      ws.emit({ type: "ACCEPTED", scenario_id: "scn-test" });
      ws.emit(RESULT_BEH_1);
      ws.emit({
        type: "DONE",
        scenario_id: "scn-test",
        duration_ms: 84210,
        timings: { sumo_ms: 41000, modules_ms: 18300, llm_ms: 12100, total_ms: 84210 },
      });
    });

    // The page closes the socket after DONE; duration lives in done-summary, chip stays compact.
    expect(ws.closed).toBe(true);
    expect(screen.getByTestId("ws-status")).toHaveTextContent("Done");
    const summary = screen.getByTestId("done-summary");
    expect(summary).toHaveTextContent("84.2s total");
    expect(screen.getByTestId("stage-timings")).toHaveTextContent("SUMO");
    expect(screen.queryByTestId("disconnect-banner")).not.toBeInTheDocument();
    expect(screen.queryByTestId("cancel-run")).not.toBeInTheDocument();
  });

  it("hydrates trips from latest-run playback without opening a WebSocket", async () => {
    vi.mocked(getLatestRun).mockResolvedValueOnce({
      run_id: "run-1",
      scenario_id: "scn-test",
      status: "done",
      results: [
        {
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
        },
      ],
      affected_edges: ["edge-1"],
      edge_resolution: "keyword-match",
      playback: {
        edge_counts: { "edge-1": 12 },
        frames: [{ tick: 1, agents: [{ id: "a", lon: 122.5, lat: 10.7 }] }],
        affected_edges: ["edge-1"],
        edge_resolution: "keyword-match",
      },
    });

    await renderScenario();

    expect(FakeWebSocket.instances).toHaveLength(0);
    expect(screen.queryByTestId("ws-status")).not.toHaveTextContent("Connecting…");
    expect(screen.queryByTestId("ws-status")).not.toHaveTextContent("Running…");
    expect(screen.getByText("Mode shift")).toBeInTheDocument();
    const lastProps = vi.mocked(TripsLayer).mock.calls.at(-1)?.[0] as
      | { data?: Array<{ id: string; path: [number, number][]; timestamps: number[] }> }
      | undefined;
    expect(lastProps?.data).toEqual([
      { id: "a", path: [[122.5, 10.7]], timestamps: [1] },
    ]);
    expect(screen.queryByText("Map playback expired. Re-run to restore trajectories.")).not.toBeInTheDocument();
  });

  it("shows a muted expired notice when latest-run playback is null", async () => {
    vi.mocked(getLatestRun).mockResolvedValueOnce({
      run_id: "run-1",
      scenario_id: "scn-test",
      status: "done",
      results: [
        {
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
        },
      ],
      affected_edges: ["edge-1"],
      edge_resolution: "keyword-match",
      playback: null,
    });

    await renderScenario();

    expect(FakeWebSocket.instances).toHaveLength(0);
    expect(screen.getByText("Mode shift")).toBeInTheDocument();
    expect(
      screen.getByText("Map playback expired. Re-run to restore trajectories."),
    ).toBeInTheDocument();
    const lastProps = vi.mocked(TripsLayer).mock.calls.at(-1)?.[0] as
      | { data?: Array<{ id: string }> }
      | undefined;
    expect(lastProps?.data).toEqual([]);
  });
});
