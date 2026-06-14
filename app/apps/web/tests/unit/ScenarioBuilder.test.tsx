import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import ScenarioBuilder from "@/components/ScenarioBuilder";
import { API_BASE_URL } from "@/lib/api";

// --- Heavy map/WebGL modules are not jsdom-compatible: stub them out
//     (same pattern as HomeCockpit.test.tsx). ---
const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
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
vi.mock("@deck.gl/layers", () => ({
  ScatterplotLayer: vi.fn(),
  PolygonLayer: vi.fn(),
  PathLayer: vi.fn(),
}));
vi.mock("@deck.gl/core", () => ({}));

const SCENARIO_OK = {
  scenario_id: "scn-789",
  description: "lane closure",
  corridor: "diversion",
  lanes_closed: 2,
};

function jsonResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

/** Advance the wizard to a given step by clicking "Next" repeatedly. */
function clickNext() {
  fireEvent.click(screen.getByRole("button", { name: /^Next$/i }));
}

describe("ScenarioBuilder", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    pushMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("starts on the intervention-type step with lane closure selected", () => {
    render(<ScenarioBuilder />);
    expect(screen.getByText(/What kind of intervention/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Lane closure/i })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
  });

  it("requires a location before advancing past the Location step", () => {
    render(<ScenarioBuilder />);
    clickNext(); // → Location
    const next = screen.getByRole("button", { name: /^Next$/i });
    expect(next).toBeDisabled();

    fireEvent.change(screen.getByLabelText(/Street \/ corridor name/i), {
      target: { value: "Diversion Road" },
    });
    expect(next).toBeEnabled();
  });

  it("builds and submits a lane-closure query, then navigates to the scenario page", async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, SCENARIO_OK));
    render(<ScenarioBuilder />);

    // Step 0 → 1 (lane_closure is the default)
    clickNext();
    fireEvent.change(screen.getByLabelText(/Street \/ corridor name/i), {
      target: { value: "Diversion Road" },
    });
    // Step 1 → 2 (parameters)
    clickNext();
    fireEvent.change(screen.getByLabelText(/Lanes to close/i), { target: { value: "2" } });
    // Step 2 → 3 (review)
    clickNext();

    // Review shows the exact query (glass box).
    expect(screen.getByTestId("review-query")).toHaveTextContent(
      "Close 2 lanes on Diversion Road."
    );

    fireEvent.click(screen.getByRole("button", { name: /Submit scenario/i }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/scenario/scn-789"));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/scenario`);
    expect(JSON.parse(init.body)).toEqual({
      query: "Close 2 lanes on Diversion Road.",
      input_type: "nl",
    });
  });

  it("builds a facility query with the right unit per kind", async () => {
    render(<ScenarioBuilder />);

    // Pick new_facility on step 0
    fireEvent.click(screen.getByRole("button", { name: /New facility/i }));
    clickNext(); // → Location
    fireEvent.change(screen.getByLabelText(/Street \/ corridor name/i), {
      target: { value: "Molo" },
    });
    clickNext(); // → Parameters
    fireEvent.change(screen.getByLabelText(/Facility kind/i), { target: { value: "market" } });
    fireEvent.change(screen.getByLabelText(/Capacity/i), { target: { value: "250" } });
    clickNext(); // → Review

    expect(screen.getByTestId("review-query")).toHaveTextContent(
      "Build a 250-stall market at Molo."
    );
  });

  it("captures a manual lon/lat point and embeds GeoJSON in the review", () => {
    render(<ScenarioBuilder />);
    clickNext(); // → Location

    fireEvent.change(screen.getByLabelText(/Longitude/i), { target: { value: "122.561" } });
    fireEvent.change(screen.getByLabelText(/Latitude/i), { target: { value: "10.712" } });
    fireEvent.click(screen.getByRole("button", { name: /Set point/i }));

    expect(screen.getByTestId("geometry-summary")).toHaveTextContent(
      "Point at [122.56100, 10.71200]"
    );

    // With a geometry present, the location requirement is satisfied.
    clickNext(); // → Parameters
    clickNext(); // → Review

    expect(screen.getByTestId("review-geojson")).toHaveTextContent('"Point"');
    expect(screen.getByTestId("review-query")).toHaveTextContent("Geometry (GeoJSON):");
  });

  it("renders the clarification message inline on a 400 ambiguous response", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(400, { error: "Which corridor do you mean?", is_ambiguous: true })
    );
    render(<ScenarioBuilder />);

    clickNext();
    fireEvent.change(screen.getByLabelText(/Street \/ corridor name/i), {
      target: { value: "somewhere" },
    });
    clickNext();
    clickNext();
    fireEvent.click(screen.getByRole("button", { name: /Submit scenario/i }));

    expect(await screen.findByText("Which corridor do you mean?")).toBeInTheDocument();
    expect(screen.getByText(/Clarification needed/i)).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("surfaces an error when the API is unreachable", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    render(<ScenarioBuilder />);

    clickNext();
    fireEvent.change(screen.getByLabelText(/Street \/ corridor name/i), {
      target: { value: "Diversion Road" },
    });
    clickNext();
    clickNext();
    fireEvent.click(screen.getByRole("button", { name: /Submit scenario/i }));

    expect(await screen.findByText(/Could not reach the MATRIX API/i)).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("shows a loading state while the submit request is in flight", async () => {
    let resolveFetch!: (value: Response) => void;
    fetchMock.mockReturnValue(new Promise<Response>((resolve) => { resolveFetch = resolve; }));
    render(<ScenarioBuilder />);

    clickNext();
    fireEvent.change(screen.getByLabelText(/Street \/ corridor name/i), {
      target: { value: "Diversion Road" },
    });
    clickNext();
    clickNext();
    fireEvent.click(screen.getByRole("button", { name: /Submit scenario/i }));

    const pending = await screen.findByRole("button", { name: /Submitting scenario/i });
    expect(pending).toBeDisabled();

    resolveFetch(jsonResponse(200, SCENARIO_OK));
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/scenario/scn-789"));
  });

  it("lets the user go back and change the intervention type", () => {
    render(<ScenarioBuilder />);
    // default lane_closure → advance, then go back and switch to speed_change
    clickNext();
    fireEvent.click(screen.getByRole("button", { name: /^Back$/i }));

    fireEvent.click(screen.getByRole("button", { name: /Speed change/i }));
    clickNext();
    fireEvent.change(screen.getByLabelText(/Street \/ corridor name/i), {
      target: { value: "Jalandoni Street" },
    });
    clickNext();
    fireEvent.change(screen.getByLabelText(/Target speed/i), { target: { value: "40" } });
    clickNext();

    expect(screen.getByTestId("review-query")).toHaveTextContent(
      "Reduce speed to 40 km/h on Jalandoni Street."
    );
  });

  it("does not present any unlabeled simulation results (glass box)", () => {
    render(<ScenarioBuilder />);
    // The builder composes queries; it never fabricates dimension numbers.
    expect(screen.queryByText(/Economic/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/tCO/i)).not.toBeInTheDocument();
  });
});
