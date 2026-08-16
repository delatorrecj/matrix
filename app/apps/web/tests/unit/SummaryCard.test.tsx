import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SummaryCard } from "@/components/SummaryCard";
import type { ResultCardData } from "@/components/ResultCard";

function card(overrides: Partial<ResultCardData> = {}): ResultCardData {
  return {
    key: "behavioral:BEH-1:0",
    dimension: "behavioral",
    metric: "Δ trips on affected corridor (AM-peak)",
    equationId: "BEH-1",
    unit: "trips/window",
    conf: "L",
    rawValue: -14,
    rawRange: [-17, -10],
    directional: true,
    provData: {
      metric: "Δ trips on affected corridor (AM-peak)",
      value: "-14",
      range: "-17..-10",
      confidence: "L",
      confidenceBasis: "Computed",
      equationId: "BEH-1",
      inputs: [],
      assumptions: [
        "confidence capped at L: VAL-01 published FAIL — corridor volumes are directional, not city-calibrated",
      ],
      references: [],
    },
    ...overrides,
  };
}

describe("SummaryCard", () => {
  it("shows directional / uncalibrated notice instead of a High-confidence magnitude", () => {
    render(<SummaryCard card={card()} onInspect={vi.fn()} />);
    expect(screen.getByText(/directional only/i)).toBeInTheDocument();
    expect(screen.getByText(/not a precise estimate/i)).toBeInTheDocument();
    expect(screen.queryByText("-14")).not.toBeInTheDocument();
    expect(screen.queryByText("High")).not.toBeInTheDocument();
  });
});
