import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import SynthesisNarrative from "@/components/SynthesisNarrative";

describe("SynthesisNarrative", () => {
  it("renders a plain narrative without citations verbatim", () => {
    render(<SynthesisNarrative narrative="No quantitative claims here." />);
    expect(screen.getByTestId("synthesis-narrative")).toHaveTextContent(
      "No quantitative claims here."
    );
    expect(screen.queryByTestId("synthesis-citations")).not.toBeInTheDocument();
  });

  it("parses [EQN-ID] brackets into inline chips and keeps surrounding text", () => {
    render(
      <SynthesisNarrative
        narrative="Trips increased by 450 [BEH-1]. Emissions fell [ECO-2]."
        resolvableEquationIds={["BEH-1", "ECO-2"]}
        onCiteClick={() => {}}
      />
    );
    expect(screen.getByTestId("cite-BEH-1")).toBeInTheDocument();
    expect(screen.getByTestId("cite-ECO-2")).toBeInTheDocument();
    expect(screen.getByText(/Trips increased by 450/)).toBeInTheDocument();
    expect(screen.getByText(/Emissions fell/)).toBeInTheDocument();
    // The raw bracket text is replaced by the chip.
    expect(screen.queryByText("[BEH-1]")).not.toBeInTheDocument();
  });

  it("fires onCiteClick with the equation id for a resolvable chip", () => {
    const onCiteClick = vi.fn();
    render(
      <SynthesisNarrative
        narrative="Mode shift of 4.2% [BEH-1]."
        resolvableEquationIds={["BEH-1"]}
        onCiteClick={onCiteClick}
      />
    );
    fireEvent.click(screen.getByTestId("cite-BEH-1"));
    expect(onCiteClick).toHaveBeenCalledTimes(1);
    expect(onCiteClick).toHaveBeenCalledWith("BEH-1");
  });

  it("renders a citation with no matching result as a disabled chip that never fires", () => {
    const onCiteClick = vi.fn();
    render(
      <SynthesisNarrative
        narrative="A claim citing a result we never received [SOCI-4]."
        resolvableEquationIds={["BEH-1"]}
        onCiteClick={onCiteClick}
      />
    );
    const chip = screen.getByTestId("cite-SOCI-4");
    expect(chip).toBeDisabled();
    fireEvent.click(chip);
    expect(onCiteClick).not.toHaveBeenCalled();
  });

  it("surfaces citations-array entries absent from the text in a footer", () => {
    render(
      <SynthesisNarrative
        narrative="Inline claim [BEH-1]."
        citations={[
          { claim: "Derived from Mode shift", equation_id: "BEH-1", dataset_ids: ["lptrp-2023"] },
          { claim: "Derived from CO2 delta", equation_id: "ECO-1", dataset_ids: ["cchain"] },
        ]}
        resolvableEquationIds={["BEH-1", "ECO-1"]}
        onCiteClick={() => {}}
      />
    );
    // BEH-1 already appears inline — only ECO-1 lands in the footer.
    const footer = screen.getByTestId("synthesis-citations");
    expect(footer).toHaveTextContent("Derived from CO2 delta");
    expect(footer).toHaveTextContent("datasets: cchain");
    expect(footer).not.toHaveTextContent("Derived from Mode shift");
    expect(screen.getAllByTestId("cite-BEH-1")).toHaveLength(1);
  });

  it("does not turn arbitrary bracketed text into chips", () => {
    render(<SynthesisNarrative narrative="A [note] and a [BEH-1] citation." />);
    expect(screen.getByText(/A \[note\] and a/)).toBeInTheDocument();
    expect(screen.getByTestId("cite-BEH-1")).toBeInTheDocument();
  });
});
