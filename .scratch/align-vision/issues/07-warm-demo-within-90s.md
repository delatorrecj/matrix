# 07 — Warm demo finishes inside 90 seconds

**What to build:** The advertised 90-second path holds for the seeded demo scenario on a warm box (baseline and trajectory cache already present). If a cold SUMO run misses the budget, the product says so instead of implying every click is &lt;90 s.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] A documented warm demo path (cached trajectory and/or baseline already in Redis) completes ACCEPTED → DONE with total_ms ≤ 90_000 on the reference scenario.
- [ ] DONE timings still break out sumo / modules / llm so a miss is diagnosable.
- [ ] Cold-run over-budget is an explicit notice (or health/queue copy), not a silent hang and not a fake 90 s claim.
- [ ] A reviewer can demo: simulate-up (or equivalent warm) → demo scenario → clock under 90 s, or an honest over-budget banner.
