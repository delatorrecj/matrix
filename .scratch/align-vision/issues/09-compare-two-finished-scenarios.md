# 09 — Compare two finished scenarios

**What to build:** A planner can put two completed runs next to each other (do-nothing vs intervention, or site A vs site B) and see the 17 metrics and briefs without exporting to a spreadsheet. Ranking can be a simple, disclosed rule or a manual pick; it must not invent a sixth dimension.

**Blocked by:** 02 — Reload restores the full run (comparison needs persisted playback/results/synthesis, not a live double-SUMO).

**Status:** ready-for-agent

- [ ] User can select two done scenario/run ids and see dimension results side by side, each still Inspect-able.
- [ ] Comparison does not originate numbers; it only places kernel DimensionResults next to each other (and optionally a delta that cites both equation ids).
- [ ] If one run is directional/L, that bound stays visible in the comparison.
- [ ] A reviewer can demo: two hydrated runs → compare → pick a preferred site with cited metrics.
