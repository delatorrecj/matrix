import { describe, it, expect, beforeEach } from "vitest";
import { savePromptHandoff, takePromptHandoff } from "@/lib/promptHandoff";

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
});
