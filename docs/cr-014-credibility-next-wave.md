# CR-014 — Credibility Next Wave (live VAL-01 + FOI + VAL-02 path + stand-ins + SOC-1)

**Change Record ID:** CR-014  
**Status:** Applied  
**Date opened:** 2026-08-05  
**Owner:** Team ATLAN  
**Trigger:** Credibility Next Wave plan — publish honest VAL-01 after Tier-B demand + Redis baseline; FOI status; VAL-02 acquisition path; finish scalar stand-ins; SOC-1 isochrones.

## VAL-01 live result (2026-08-05)

After `build_demand.py --calibrate` (WorldPop Tier-B, period=0.5s, target capped 8000 veh/h) + `run_nightly_baseline()`:

| Gate | Status | Value | Notes |
|------|--------|-------|-------|
| VAL-01 | **FAIL** | NRMSE = **4.488** (threshold ≤ 0.30) | Live Redis baseline; lopez_jaena sim 1033 vs obs 90; diversion 948 vs 275. Honest FAIL — not massaged. |
| VAL-02 | NOT_RUN | — | Awaiting S1-GFM non-provisional fixture |

Published to `app/validation_report.json`. Residual gap is demand/proxy scale vs Calderon transit loads — independent Tier-B anchor deliberately not fitted to Calderon targets (CR-012 §4).
