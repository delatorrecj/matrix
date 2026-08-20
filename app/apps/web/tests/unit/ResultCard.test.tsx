import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ResultCard, type ResultCardData } from "@/components/ResultCard";

function card(overrides: Partial<ResultCardData> = {}): ResultCardData {
  return {
    key: "behavioral:BEH-1:0",
    dimension: "behavioral",
    metric: "Δ trips on affected corridor (AM-peak)",
    equationId: "BEH-1",
    unit: "trips/window",
    conf: "L",
    rawValue: -14.123456,
    rawRange: [-17, -10],
    directional: true,
    applicability: "computed",
    provData: {
      metric: "Δ trips on affected corridor (AM-peak)",
      value: "-14.123456",
      range: "-17..-10",
      confidence: "L",
      confidenceBasis: "Computed",
      equationId: "BEH-1",
      inputs: [],
      assumptions: [],
      references: [],
    },
    ...overrides,
  };
}

describe("ResultCard", () => {
  it("suppresses the precise headline for Low computed results", () => {
    render(<ResultCard card={card()} onInspect={vi.fn()} />);
    expect(screen.getByText(/directional only/i)).toBeInTheDocument();
    expect(screen.queryByText("-14.1235")).not.toBeInTheDocument();
    expect(screen.queryByText("-14.123456")).not.toBeInTheDocument();
  });

  it("shows Not applicable instead of 0.0", () => {
    render(
      <ResultCard
        card={card({
          equationId: "ECO-3",
          metric: "Green-cover loss",
          conf: "H",
          rawValue: 0,
          directional: false,
          applicability: "not_applicable",
        })}
        onInspect={vi.fn()}
      />,
    );
    expect(screen.getByText("Not applicable to this intervention")).toBeInTheDocument();
    expect(screen.getByText("N/A")).toBeInTheDocument();
  });
});
