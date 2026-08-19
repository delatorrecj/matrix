import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { formatScenarioPlan, ScenarioPromptReview } from "@/components/ScenarioPromptReview";

describe("formatScenarioPlan", () => {
  it("joins type, location, kind and capacity", () => {
    expect(
      formatScenarioPlan({
        interventionType: "new_facility",
        location: "Molo",
        parameters: { facility_kind: "school", capacity: 3000 },
      }),
    ).toBe("New facility · Molo · school · 3,000 seats");
  });

  it("returns null when nothing is known", () => {
    expect(formatScenarioPlan({})).toBeNull();
  });

  it("shows from/to crosses without stuffing them into location", () => {
    expect(
      formatScenarioPlan({
        interventionType: "full_closure",
        location: "Cuartero Street",
        parameters: { from_cross: "Fajardo Street", to_cross: "El 98 Street" },
      }),
    ).toBe("Full closure · Cuartero Street, segment from Fajardo Street to El 98 Street");
  });
});

describe("ScenarioPromptReview", () => {
  it("shows the original question and parsed plan", () => {
    render(
      <ScenarioPromptReview
        rawInput="What if we build a 3,000-seat school in Molo?"
        interventionType="new_facility"
        location="Molo"
        parameters={{ facility_kind: "school", capacity: 3000 }}
      />,
    );
    expect(screen.getByTestId("scenario-prompt-review")).toHaveTextContent(
      "What if we build a 3,000-seat school in Molo?",
    );
    expect(screen.getByText("Plan")).toBeInTheDocument();
    expect(screen.getByText("New facility · Molo · school · 3,000 seats")).toBeInTheDocument();
  });

  it("renders nothing when both question and plan are empty", () => {
    const { container } = render(<ScenarioPromptReview />);
    expect(container).toBeEmptyDOMElement();
  });
});
