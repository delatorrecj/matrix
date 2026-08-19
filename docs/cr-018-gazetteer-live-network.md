# CR-018 — Gazetteer vs live SUMO network

**Change Record ID:** CR-018
**Status:** Applied
**Date opened:** 2026-08-20
**Owner:** Yushin
**Trigger:** Hiligaynon gazetteer still stored fake `E_*` / `way/12345678` ids. Kernel comparison was already exact membership (CR-013); those placeholders never existed in `iloilo.net.xml`, so named-place queries hashed onto a busy baseline edge.

## Decision

Do not rebuild the SUMO net. Verify every gazetteer alias against the deployed net:

1. live `sumo_edge` / `sumo_edges` membership → `gazetteer-match`
2. OSM lane `origId` → `gazetteer-osmid`
3. curated `street_name` alias → `gazetteer-alias`
4. capped coordinate snap → `gazetteer-snap`
5. unchanged `busiest-baseline-fallback` hash for unmatched strings

Districts are a plaza-street proxy (not a polygon). Confidence letters are unchanged (VAL-01 / dataset tiers).

## Files

- `app/packages/kernel/matrix_kernel/gazetteer.py` + `gazetteer_iloilo.json`
- `app/packages/kernel/matrix_kernel/geometry.py` (`nearest_edges`)
- `app/packages/kernel/matrix_kernel/runner.py` (`_gazetteer_edges`)
- `app/packages/data/verify_gazetteer.py`
- `docs/methods-matrix.md` §4.2 (Locked, re-locked here)

## Out of scope

VAL-01 PASS, demand calibration, removing the hash fallback, `new_facility` corridor closures. Queued in [CR-019](cr-019-credibility-next-steps.md).
