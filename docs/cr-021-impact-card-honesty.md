# CR-021 — Impact-card honesty and type-aware scoring

**Change Record ID:** CR-021
**Status:** Applied
**Date opened:** 2026-08-20
**Owner:** Yushin
**Trigger:** Summary and Analytics cards treated every intervention as a v1 lane-closure corridor. A school, a flood, and a road diet all produced a full deck of numbers, including fake `0.0` at Medium/High (BEH-2, ECO-3, unarmed ECO-4). Volume-derived cards (ECO-1, ECON, SOC, SOCI) stamped H/M from the dataset list while VAL-01 is a published FAIL.

## Decision

Honesty first. Do not stamp High on BEH-1 / BEH-3 while VAL-01 is FAIL ([CR-019](cr-019-credibility-next-steps.md)). Locked methods stay H/M/L for **computed** results.

1. **`DimensionResult.applicability`:** `computed` | `not_modeled` | `not_applicable`. Streamed on DIMENSION_RESULT. N/A is not Low. Inspect still resolves (`equation_id` + datasets).
2. **Module emission:** BEH-2 always `not_modeled`. ECO-3 `not_applicable` until a construction footprint exists. ECO-4 `not_applicable` unless `flood_hazard`. SOC-2 `not_applicable` on non-closures. BEH-4 `not_applicable` unless `demand_delta` (always emitted so 4/4 behavioral fills).
3. **Scoring aperture:** `site_delta` vs `network_delta` / `impacted_edges`. ECO-1 uses real edge lengths (or a named 150 m fallback). Every volume child uses `volume_confidence` (VAL-01 is a worst factor). Assumptions name the 900 s → 365 expansion and the baseline/scenario rerouting asymmetry.
4. **BEH-3 type-aware denominator:** no phantom lane on `full_closure`; `capacity_factor` in the `capacity_change` denominator; `speed_change` uses geometric lanes and does not claim capacity changed.
5. **Facility / flood meta:** `new_facility` resolves k-nearest live-net edges for **scoring and overlay only** (`facility-adjacent`); TraCI still does not add lanes. Orchestrator `flood_hazard` arms ECO-4. No new flood geometry this cycle.

## Out of scope

VAL-01 PASS / demand calibration. Raising chips. Facility 80-vehicle TraCI cap. Adding physical lanes at runtime. Builder structured bypass. Matching baseline rerouting to the scenario device. Named-span resolution (CR-020).

## Files

- Kernel: `results.py`, `scoring_aperture.py` (new), five modules, `runner.py`, `orchestrator.py`, `scenario.py`
- API: `_result_payload`, persistence pack/unpack of `applicability`, `flood_hazard` on the scenario record
- Web: `ConfidenceChip` N/A, Summary/Result/Inspect/interpret
- This index. **No Locked-doc rewrite.**

## Guardrail

BEH-1 / BEH-3 remain **L** while VAL-01 is FAIL. ECO-1 no longer publishes H from `SUMO-NET` + `WHO-EMEP` alone.
