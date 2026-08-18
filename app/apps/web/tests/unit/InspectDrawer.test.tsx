import { render, screen, fireEvent, within } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import InspectDrawer, { ProvenanceData } from "@/components/InspectDrawer";

const DATA: ProvenanceData = {
  metric: "Mode shift",
  value: "+4.2",
  range: "3.1..5.3",
  confidence: "M",
  confidenceBasis: "Computed from input dataset confidences per methods §2",
  equationId: "BEH-1",
  inputs: [
    { id: "lptrp-2023" }, // bare id — only thing the stream carries today
    {
      id: "cchain",
      name: "Project CCHAIN",
      vintage: "2024",
      confidence: "High",
      license: "CC-BY-4.0",
      tier: "A",
      sourceNote: "Barangay-level Iloilo data.",
    },
  ],
  assumptions: ["mode_share=Iloilo-2014"],
  references: ["Calderon2014"],
};

function renderDrawer(overrides: Partial<React.ComponentProps<typeof InspectDrawer>> = {}) {
  const onClose = vi.fn();
  const utils = render(
    <InspectDrawer isOpen onClose={onClose} metricId="BEH-1" data={DATA} {...overrides} />
  );
  return { onClose, ...utils };
}

function expandDrawerDetails() {
  fireEvent.click(screen.getByRole("button", { name: /Show details/i }));
}

describe("InspectDrawer", () => {
  it("renders nothing when closed", () => {
    const { container } = render(
      <InspectDrawer isOpen={false} onClose={() => {}} metricId={null} data={null} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("is an ARIA modal dialog labelled by the metric", () => {
    renderDrawer();
    const dialog = screen.getByRole("region");
    expect(dialog).toHaveAttribute("aria-labelledby", "inspect-drawer-title");
    expect(within(dialog).getByText("Mode shift")).toHaveAttribute("id", "inspect-drawer-title");
    expect(within(dialog).getByText("BEH-1")).toBeInTheDocument();
  });

  it("moves focus into the dialog on open", () => {
    renderDrawer();
    const dialog = screen.getByTestId("inspect-drawer");
    expect(dialog.contains(document.activeElement)).toBe(true);
  });

  it("closes on Escape", () => {
    const { onClose } = renderDrawer();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does not clip the close button behind overflow-hidden on the dialog root", () => {
    renderDrawer();
    const dialog = screen.getByTestId("inspect-drawer");
    const close = screen.getByRole("button", { name: /Close inspector/i });
    expect(close).toBeVisible();
    expect(dialog.className.split(/\s+/)).not.toContain("overflow-hidden");
    expect(dialog.className.split(/\s+/)).not.toContain("top-44");
    expect(dialog.className.split(/\s+/)).not.toContain("top-48");
  });



  it("traps Tab focus inside the dialog (wraps last → first and first → last)", () => {
    renderDrawer();
    const dialog = screen.getByTestId("inspect-drawer");
    const focusables = Array.from(
      dialog.querySelectorAll<HTMLElement>("button:not([disabled])")
    );
    const first = focusables[0];
    const last = focusables[focusables.length - 1];

    last.focus();
    fireEvent.keyDown(dialog, { key: "Tab" });
    expect(document.activeElement).toBe(first);

    first.focus();
    fireEvent.keyDown(dialog, { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(last);
  });

  it("expands a dataset row on click and shows honest fallbacks for missing metadata", () => {
    renderDrawer();
    expandDrawerDetails();
    const row = screen.getByTestId("dataset-row-lptrp-2023");
    expect(row).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(row);
    expect(row).toHaveAttribute("aria-expanded", "true");

    const meta = screen.getByTestId("dataset-meta-lptrp-2023");
    // Nothing was provided for this dataset — every field falls back honestly.
    expect(within(meta).getAllByText("not provided")).toHaveLength(5);

    // Toggle closed again.
    fireEvent.click(row);
    expect(screen.queryByTestId("dataset-meta-lptrp-2023")).not.toBeInTheDocument();
  });

  it("renders provided dataset metadata without inventing anything", () => {
    renderDrawer();
    expandDrawerDetails();
    fireEvent.click(screen.getByTestId("dataset-row-cchain"));

    const meta = screen.getByTestId("dataset-meta-cchain");
    expect(within(meta).getByText("2024")).toBeInTheDocument();
    expect(within(meta).getByText("High")).toBeInTheDocument();
    expect(within(meta).getByText("CC-BY-4.0")).toBeInTheDocument();
    expect(within(meta).getByText("A")).toBeInTheDocument();
    expect(within(meta).getByText("Barangay-level Iloilo data.")).toBeInTheDocument();
    expect(within(meta).queryByText("not provided")).not.toBeInTheDocument();
  });

  it("only keeps one dataset row expanded at a time", () => {
    renderDrawer();
    expandDrawerDetails();
    fireEvent.click(screen.getByTestId("dataset-row-lptrp-2023"));
    fireEvent.click(screen.getByTestId("dataset-row-cchain"));
    expect(screen.queryByTestId("dataset-meta-lptrp-2023")).not.toBeInTheDocument();
    expect(screen.getByTestId("dataset-meta-cchain")).toBeInTheDocument();
  });

  it("surfaces a VAL-01 uncalibrated-volume notice for corridor metrics", () => {
    renderDrawer({
      data: {
        ...DATA,
        confidence: "L",
        equationId: "BEH-1",
        assumptions: [
          "confidence capped at L: VAL-01 published FAIL — corridor volumes are directional, not city-calibrated",
        ],
      },
    });
    expect(screen.getByTestId("inspect-fidelity-notice")).toHaveTextContent(
      /directional/i
    );
    expect(screen.getByTestId("inspect-fidelity-notice")).toHaveTextContent(/VAL-01/);
    expect(screen.getByTestId("inspect-fidelity-notice")).not.toHaveTextContent(/withheld/i);
  });

  it("shows the computed confidence level — not a hardcoded label", () => {
    renderDrawer();
    expandDrawerDetails();
    expect(screen.getByText("Medium confidence (computed)")).toBeInTheDocument();

    renderDrawer({ data: { ...DATA, confidence: "H" } });
    expandDrawerDetails();
    expect(screen.getByText("High confidence (computed)")).toBeInTheDocument();
  });

  it("falls back honestly when no equation text is provided", () => {
    renderDrawer();
    expandDrawerDetails();
    expect(
      screen.getByText(/Equation text not provided over the stream/)
    ).toBeInTheDocument();
    expect(screen.getByText(/methods-matrix §3/)).toBeInTheDocument();
  });

  it("renders equation text when it is actually provided", () => {
    renderDrawer({ data: { ...DATA, equationText: "Δtrips = Σ(reroute) / baseline" } });
    expandDrawerDetails();
    expect(screen.getByText("Δtrips = Σ(reroute) / baseline")).toBeInTheDocument();
    expect(screen.queryByText(/Equation text not provided/)).not.toBeInTheDocument();
  });

  it("renders dataset source links and reference links when provided", () => {
    renderDrawer({
      data: {
        ...DATA,
        inputs: [
          {
            id: "OSM-ILO",
            name: "OpenStreetMap Iloilo extract",
            url: "https://overpass-api.de/api/interpreter",
            license: "ODbL",
          },
        ],
        references: ["Calderon2014"],
      },
    });
    expandDrawerDetails();
    // Sources section renders the dataset name (not the raw URL) as the link label.
    expect(screen.getByRole("link", { name: /OpenStreetMap/i })).toHaveAttribute(
      "href",
      "https://overpass-api.de/api/interpreter"
    );
    expect(screen.getByRole("link", { name: /Calderon 2014/i })).toHaveAttribute(
      "href",
      expect.stringContaining("Calderon14.pdf")
    );
  });

  it("lists references when present", () => {
    renderDrawer();
    expandDrawerDetails();
    expect(screen.getByRole("link", { name: /Calderon 2014/i })).toBeInTheDocument();
  });
});
