import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ValidationPanel, { ValidationGate } from "@/components/ValidationPanel";
import { apiFetch } from "@/lib/api";

// The panel goes through the centralized API client — mock it at the seam.
vi.mock("@/lib/api", () => ({
  apiFetch: vi.fn(),
}));

const mockApiFetch = vi.mocked(apiFetch);

function jsonOk(body: unknown): Promise<Response> {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve(body),
  } as unknown as Response);
}

/** Mirrors matrix_kernel/validation.py::GateResult.to_dict(). */
const PASS_GATE: ValidationGate = {
  gate_id: "VAL-01",
  name: "Behavioral corridor back-test (Calderon 2014, Ungka–Iloilo corridors)",
  metric: "normalized_rmse",
  value: 0.27,
  unit: "fraction of mean observed volume",
  threshold: 0.3,
  comparator: "<=",
  status: "PASS",
  fixture_id: "LIT-CALDERON",
  fixture_provenance: "Calderon et al. (2014, TSSP) JICA STRADA 3 transit-model values.",
  fixture_provisional: false,
  simulated_source: "live-baseline:redis",
  n_points: 4,
  threshold_provenance: "FHWA Travel Model Validation Manual (2nd ed., 2010).",
  details: {},
  notes: "",
};

const FAIL_GATE: ValidationGate = {
  ...PASS_GATE,
  gate_id: "VAL-02",
  name: "Flood redistribution back-test (2024 Iloilo flood closures)",
  metric: "length_weighted_iou",
  value: 0.31,
  unit: "IoU over closed road segments (0–1)",
  threshold: 0.5,
  comparator: ">=",
  status: "FAIL",
  fixture_id: "S1-GFM",
  fixture_provenance:
    "PROVISIONAL — replace with sourced data: placeholder closure set pending Copernicus GFM.",
  fixture_provisional: true,
  notes: "PROVISIONAL — replace with sourced data: do not publish as validation.",
};

const NOT_RUN_GATE: ValidationGate = {
  ...PASS_GATE,
  gate_id: "VAL-01",
  value: null,
  status: "NOT_RUN",
  simulated_source: null,
  notes: "no simulated corridor values supplied — needs a kernel run",
};

describe("ValidationPanel", () => {
  beforeEach(() => {
    mockApiFetch.mockReset();
  });

  it("renders without crashing and shows a loading state first", () => {
    mockApiFetch.mockReturnValue(new Promise(() => {})); // never resolves
    render(<ValidationPanel />);
    expect(screen.getByText(/Validation & Back-Testing/i)).toBeInTheDocument();
    expect(screen.getByTestId("validation-loading")).toBeInTheDocument();
  });

  it("fetches GET /validation and renders a PASS gate with value vs threshold", async () => {
    mockApiFetch.mockReturnValue(jsonOk({ gates: [PASS_GATE] }));
    render(<ValidationPanel />);

    expect(await screen.findByTestId("gate-VAL-01")).toBeInTheDocument();
    expect(mockApiFetch).toHaveBeenCalledWith("/validation");

    expect(screen.getByTestId("status-VAL-01")).toHaveTextContent("PASS");
    expect(screen.getByText(/normalized_rmse:/)).toHaveTextContent("0.27");
    expect(screen.getByText(/threshold ≤ 0.3/)).toBeInTheDocument();
    // Provenance shows on the always-visible line and inside the details expansion.
    expect(screen.getAllByText(/Calderon et al\./).length).toBeGreaterThan(0);
    // No hardcoded theater numbers from the old panel.
    expect(screen.queryByText(/0\.082/)).not.toBeInTheDocument();
    expect(screen.queryByText(/89%/)).not.toBeInTheDocument();
  });

  it("renders a FAIL gate as FAIL and flags a provisional fixture", async () => {
    mockApiFetch.mockReturnValue(jsonOk({ gates: [FAIL_GATE] }));
    render(<ValidationPanel />);

    expect(await screen.findByTestId("gate-VAL-02")).toBeInTheDocument();
    expect(screen.getByTestId("status-VAL-02")).toHaveTextContent("FAIL");
    expect(screen.getByTestId("provisional-VAL-02")).toHaveTextContent(/provisional/i);
    expect(screen.getByText(/threshold ≥ 0.5/)).toBeInTheDocument();
  });

  it("renders NOT_RUN honestly: no value, the reason shown, no PASS/FAIL claim", async () => {
    mockApiFetch.mockReturnValue(
      jsonOk({ gates: [NOT_RUN_GATE], source: "matrix_kernel.validation", note: "live module results" })
    );
    render(<ValidationPanel />);

    const gate = await screen.findByTestId("gate-VAL-01");
    expect(screen.getByTestId("status-VAL-01")).toHaveTextContent("NOT RUN");
    expect(gate).toHaveTextContent("not computed");
    expect(gate).toHaveTextContent(/no simulated corridor values supplied/);
    expect(gate).not.toHaveTextContent(/\bPASS\b/);
    expect(screen.getByTestId("validation-note")).toHaveTextContent("matrix_kernel.validation");
  });

  it("shows an honest empty state when no gates are reported", async () => {
    mockApiFetch.mockReturnValue(jsonOk({ gates: [], note: "validation module not available" }));
    render(<ValidationPanel />);

    const empty = await screen.findByTestId("validation-empty");
    expect(empty).toHaveTextContent(/has not yet been run/i);
    expect(empty).toHaveTextContent("validation module not available");
  });

  it("shows an error state with a working retry when the API is unreachable", async () => {
    mockApiFetch
      .mockRejectedValueOnce(new Error("Could not reach the MATRIX API at http://localhost:8000"))
      .mockReturnValueOnce(jsonOk({ gates: [PASS_GATE] }));
    render(<ValidationPanel />);

    const error = await screen.findByTestId("validation-error");
    expect(error).toHaveTextContent(/could not load validation gates/i);
    expect(error).toHaveTextContent(/could not reach the MATRIX API/i);

    fireEvent.click(screen.getByRole("button", { name: /retry/i }));

    expect(await screen.findByTestId("gate-VAL-01")).toBeInTheDocument();
    expect(mockApiFetch).toHaveBeenCalledTimes(2);
  });

  it("treats a non-2xx response as an error, not as data", async () => {
    mockApiFetch.mockReturnValue(
      Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) } as unknown as Response)
    );
    render(<ValidationPanel />);

    expect(await screen.findByTestId("validation-error")).toHaveTextContent("HTTP 500");
  });
});
