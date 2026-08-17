# CR-013 — Credibility Phases 2–4 (demand Tier-B, BIR/CCHAIN wiring, data refresh)

**Change Record ID:** CR-013  
**Status:** Applied  
**Date opened:** 2026-08-05  
**Owner:** Team ATLAN  
**Trigger:** Continue Path-1 credibility spine after Phase 1 (honest labels + `GET /credibility`).

## Summary

| Phase | Deliverable |
|-------|-------------|
| **2** | Tier-B demand volume calibration from CCHAIN WorldPop (`demand_calibration.py`, `build_demand.py --calibrate`, `MATRIX_DEMAND_SCALE`). **Not** fitted to Calderon VAL-01 targets. |
| **3** | Wire on-disk BIR CSV into ECON-1; CCHAIN RWI/amenity/NOAH into SOC-1/2/3 and ECO-4 flood path (`datasets.py`). |
| **4** | `data/fetch/refresh_dynamic.py` force-refresh for OSM / PSA / CCHAIN (+ subset). |

## Locked-doc impact

- `docs/methods-matrix.md` §3.3/§3.4/§3.6 + Appendix A re-locked for wired equations.
- `data/READINESS.md` updated for wired modules + refresh entrypoint.

## Out of scope (still deferred)

- LTFRB FOI / live mode-share survey (Tier A)
- VAL-02 Sentinel-1 flood ground truth
- UI credibility panel
- Live TomTom/HERE twin
