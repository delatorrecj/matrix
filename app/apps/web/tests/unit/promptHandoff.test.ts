import { describe, it, expect, beforeEach } from "vitest";
import { overlayPromptHandoff, savePromptHandoff, takePromptHandoff } from "@/lib/promptHandoff";

const payload = {
  rawInput: "What if we build a 3-storey school in Molo?",
  description: "3-storey school in Molo",
  interventionType: "new_facility",
  location: "Molo",
  parameters: { facility_kind: "school", capacity: 3000 },
};

describe("promptHandoff", () => {
  beforeEach(() => sessionStorage.clear());

  it("round-trips then forgets", () => {
    savePromptHandoff("scn-1", payload);
    expect(takePromptHandoff("scn-1")).toEqual(payload);
    expect(takePromptHandoff("scn-1")).toBeNull();
  });

  it("returns null for a missing or foreign id", () => {
    savePromptHandoff("scn-1", payload);
    expect(takePromptHandoff("scn-other")).toBeNull();
  });

  it("keeps non-empty handoff fields when GET overlay is empty", () => {
    expect(
      overlayPromptHandoff(
        {
          raw_input: "",
          description: "",
          intervention_type: null,
          location: null,
          parameters: {},
        },
        payload,
      ),
    ).toEqual(payload);
  });

  it("prefers non-empty GET fields without inventing parameters", () => {
    expect(
      overlayPromptHandoff(
        {
          raw_input: "Close a lane on Diversion Road",
          description: "close one lane",
          intervention_type: "lane_closure",
          location: "Diversion Road",
          parameters: { lanes_closed: 1 },
        },
        payload,
      ),
    ).toEqual({
      rawInput: "Close a lane on Diversion Road",
      description: "close one lane",
      interventionType: "lane_closure",
      location: "Diversion Road",
      parameters: { lanes_closed: 1 },
    });
  });
});
