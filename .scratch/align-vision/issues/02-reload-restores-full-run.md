# 02 — Reload restores the full run

**What to build:** Reopening a scenario that already finished does not throw away the movie or the brief. The planner sees agent playback, corridor/edge counts, the 17 dimension results, and the synthesis narrative they already paid for — without starting SUMO again.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Latest-run hydrate restores playback frames (or an equivalent trips payload) and edge counts, not only dimension cards.
- [ ] Latest-run hydrate restores the synthesis brief (English + Hiligaynon delimiter) when it was produced.
- [ ] Refresh / new tab on the same scenario id does not open a live WebSocket simulate if a done run exists, unless the user explicitly re-runs.
- [ ] A reviewer can demo: finish a run → refresh → map still animates and the brief is still there.
