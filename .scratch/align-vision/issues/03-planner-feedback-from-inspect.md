# 03 — Planner flags a result from Inspect

**What to build:** From Inspect on a dimension result, a CPDO-style planner can mark that metric as implausible, leave a short observation, and see that feedback stored against the run. This is the product loop for PRD-F20; the HTTP seam already exists and must be used rather than a parallel store.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Inspect (or the result card) offers submit + list feedback for that equation / dimension result.
- [ ] Submitted notes persist and reload with the scenario/run (in-memory fallback still acceptable if Postgres is down, same as the rest of persistence).
- [ ] Feedback never invents or overwrites kernel numbers; it is commentary on a cited result.
- [ ] A reviewer can demo: open Inspect on BEH-1 → flag it → refresh → the note is still there.
