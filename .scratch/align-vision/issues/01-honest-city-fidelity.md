# 01 — Honest city-fidelity on the results screen

**What to build:** After a simulation, a planner can see that Iloilo corridor volumes are directional, not city-calibrated. The in-product validation view shows VAL-01 as a published FAIL against the Calderon 2014 back-test (with the live NRMSE and the pass threshold), not as “withheld” or as a passing calibration. Copy on results, Inspect, the technology/validation surfaces, and the kernel-adjacent docs that a demo audience will read all say the same thing.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [x] A finished run shows a clear directional / uncalibrated-demand notice, not a silent High-confidence magnitude for corridor volumes that VAL-01 has failed.
- [x] VAL-01 status, value, and threshold in the product match the generated validation ledger (FAIL is FAIL).
- [x] No user-facing string still claims the headline RMSE is withheld or that uncalibrated demand means “no RMSE yet.”
- [x] A reviewer can demo: run (or hydrate) a scenario → open validation → read FAIL without contradicting the summary cards.
