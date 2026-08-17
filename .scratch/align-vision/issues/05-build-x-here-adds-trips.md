# 05 — “Build X here” actually adds trips

**What to build:** Asking what happens if a school, station, or similar facility is built at a place runs facility demand (BEH-4) into the same SUMO trajectory the five modules score. The landing-page siting story matches the kernel: new trips appear, BEH-4 is streamed as a glass-box result, and the intervention is not smuggled through as a lane closure.

**Blocked by:** 04 — Named places hit real network edges (siting must land on a real edge/geometry, not a hashed busy corridor).

**Status:** ready-for-agent

- [ ] Orchestrator maps facility / new-generator language to a facility intervention, not lane_closure-by-default.
- [ ] Live `/simulate` applies BEH-4 demand onto the trajectory before (or as part of) the SUMO run; BEH-4 is not tests-only.
- [ ] The WebSocket run emits a BEH-4 DimensionResult with equation_id, datasets, computed confidence, and PROVISIONAL constants disclosed.
- [ ] A reviewer can demo: “3,000-seat school at [resolved place]” → extra demand on nearby edges → BEH-4 card in Inspect, plus the other dimensions scoring that same trajectory.
