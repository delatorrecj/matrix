# CR-016 — Open-data-only freshness (no government requests)

**Date:** 2026-08-06  
**Status:** Applied  
**Supersedes:** FOI-first track in CR-015 Phase transport/flood human lanes

## Decision

Government FOI / LGU / NHCP / CBMS outreach and household travel surveys are **not feasible**.
MATRIX will not file LTFRB eFOI or CDRRMO closure requests. Credibility = **auditable open-data twin**, not agency-calibrated absolute volumes.

## Implications

| Area | Policy |
|------|--------|
| Mode-share | Literature `ILOILO_MODE_SHARE` (Calderon 2014 + LPTRP context); confidence **M**; never invent |
| VAL-01 | Published FAIL / directional vs Calderon; never fit demand to Calderon (CR-012) |
| Flood | Open LiPAD 10 m + CCHAIN NOAH hazard ∩ network; classic 2024-event VAL-02 stays **NOT_RUN** (GFM urban exclusion) |
| Freshness | Monthly / pre-demo: `refresh_dynamic.py --all` + net/demand/baseline rebuild ([OPEN_REFRESH.md](../data/OPEN_REFRESH.md)) |

## Docs touched

- [data/outreach/FOI_STATUS.md](../data/outreach/FOI_STATUS.md) → WONT-FILE
- [data/READINESS.md](../data/READINESS.md) → open substitutes, no FOI next-steps
- Historical outreach drafts retained under `data/outreach/` for archive only
