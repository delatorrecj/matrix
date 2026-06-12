import { render, screen, fireEvent, act, within } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ScenarioSimulation from "@/app/scenario/[id]/page";

// --- Heavy map/WebGL modules are not jsdom-compatible: stub them out
//     (same pattern as ProgressiveRunUi.test.tsx / HomeCockpit.test.tsx). ---
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
// Panels with their own fetches are out of scope here; InspectDrawer and
// SynthesisNarrative stay REAL — the citation→drawer wiring is what's under test.
vi.mock("@/components/ValidationPanel", () => ({ default: () => null }));
vi.mock("@/components/BiasAuditLog", () => ({ default: () => null }));

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
  references: ["Calderon2014"],
  assumptions: ["mode_share=Iloilo-2014"],
};

const SYNTHESIS_EVENT = {
  type: "SYNTHESIS",
  narrative:
    "Mode shift of 4.20 % [BEH-1] dominates the corridor. A later claim cites a result that never arrived [ECO-1].",
  citations: [
    { claim: "Derived from Mode shift", equation_id: "BEH-1", dataset_ids: ["lptrp-2023"] },
  ],
};

describe("Provenance wiring: synthesis citations → InspectDrawer", () => {
  beforeEach(() => {
    FakeWebSocket.instances = [];
    vi.stubGlobal("WebSocket", FakeWebSocket);
    vi.stubGlobal("requestAnimationFrame", () => 0);
    vi.stubGlobal("cancelAnimationFrame", () => {});
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function streamRun() {
    render(<ScenarioSimulation />);
    const ws = FakeWebSocket.instances.at(-1);
    if (!ws) throw new Error("no WebSocket was opened");
    act(() => {
      ws.onopen?.();
      ws.emit({ type: "ACCEPTED", scenario_id: "scn-test" });
      ws.emit(RESULT_BEH_1);
      ws.emit(SYNTHESIS_EVENT);
    });
    return ws;
  }

  it("renders the synthesis narrative with citation chips", () => {
    streamRun();
    const synthesis = screen.getByTestId("synthesis-narrative");
    expect(synthesis).toHaveTextContent("dominates the corridor");
    expect(within(synthesis).getByTestId("cite-BEH-1")).toBeEnabled();
    // ECO-1 never streamed a result — its chip is honest and disabled.
    expect(within(synthesis).getByTestId("cite-ECO-1")).toBeDisabled();
  });

  it("clicking a citation chip opens the InspectDrawer on the matching result", () => {
    streamRun();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("cite-BEH-1"));

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("BEH-1")).toBeInTheDocument();
    expect(within(dialog).getByText("Mode shift")).toBeInTheDocument();
    // The streamed dataset id resolves as a clickable row inside the drawer.
    expect(within(dialog).getByTestId("dataset-row-lptrp-2023")).toBeInTheDocument();
  });

  it("Escape closes the drawer opened from a citation chip", () => {
    streamRun();
    fireEvent.click(screen.getByTestId("cite-BEH-1"));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("a disabled chip never opens a drawer", () => {
    streamRun();
    fireEvent.click(screen.getByTestId("cite-ECO-1"));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
