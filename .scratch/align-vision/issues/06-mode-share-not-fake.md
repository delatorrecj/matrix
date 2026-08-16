# 06 — Mode-share shift is not a fake measurement

**What to build:** BEH-2 no longer looks like MATRIX measured a jeepney mode-share change. The live kernel still does not model congestion elasticity (Δ is zero); the product must say **not modeled** so a planner does not treat “No meaningful change” as an empirical finding. This ticket does not add a mode-choice model.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] BEH-2 on cards, analytics, and Inspect is labeled as not modeled / N/A for this milestone, with the existing assumption text preserved in provenance.
- [ ] Presentation formatting does not imply a calibrated 0.0 %-point shift (avoid “no change” that reads as a result of behavior).
- [ ] Bias-auditor VAL-03 remains a check of personas vs the literature anchor, not a claim that BEH-2 was validated.
- [ ] A reviewer can demo: finish a closure run → BEH-2 cannot be quoted as “mode share held steady.”
