# CR-019 — Credibility next steps (post-gazetteer)

**Change Record ID:** CR-019
**Status:** Proposed
**Date opened:** 2026-08-20
**Owner:** Team ATLAN
**Trigger:** After CR-018 (named places resolve onto the live SUMO net), review whether unused inventory files or new calibration must ship to keep results accurate and credible — including whether confidence chips should go up.

## Decision

Keep the current glass-box implementation. Directional + honest H/M/L is the product, not a defect.

- **Ship now:** CR-018 gazetteer ↔ live net (if it is not already on the branch you demo). Geography was the correctness bug; Forbes Bridge overlay is the check.
- **Do not ship before the next demo:** anything whose purpose is to raise chips or “connect remaining datasets.”
- **Later (this file):** ordered work that would actually change a number or a justified chip. Each item needs its own CR when it starts; this record is the queue, not permission to edit Locked methods.

Locked docs are **not** re-locked here. Methods §2 still applies: `confidence = min(data, method, validation)`. OSM/SUMO at **H** does not lift BEH-1 / BEH-3 while VAL-01 is a published FAIL.

## Immediate (only if CR-018 is not on the demo branch)

| Item | Why it is immediate | Done when |
|------|---------------------|-----------|
| Merge / deploy [CR-018](cr-018-gazetteer-live-network.md) | Without it, Hiligaynon/English place names can hash or fall back; the magenta marker is the wrong corridor | `edge_resolution` is not `busiest-baseline-fallback` for Forbes; overlay sits on the bridge; kernel tests `test_gazetteer.py` + `test_edge_resolution.py` pass |

No other item in this CR is a demo blocker.

## Must not do

These would *hurt* credibility if done to chase High:

- Stamp **H** on BEH-1 / BEH-3 because the network data is H
- Fit demand to Calderon so VAL-01 “passes” ([CR-012](cr-012-validation-calibration.md) circularity guard)
- Invent a newer mode-share ([CR-016](cr-016-open-data-only.md) open-data-only)
- Treat on-disk but unused files (FIES, World Bank JSON, tourism, GVA, HDX poverty) as if they already feed the five modules

Honest zeros stay zeros: **BEH-2** has no mode-choice model; **ECO-3** is 0 on a lane closure. Explain them; do not force a non-zero.

## Later — accuracy or a justified chip

Ordered. Do not start these under hackathon time pressure. None of them is “wire the leftover CSV.”

| # | Change | What gets more accurate | Chip (only if the method/gate actually earns it) |
|---|--------|-------------------------|--------------------------------------------------|
| 1 | Independent demand calibration, then **re-measure** VAL-01 (never fit Calderon maxima) | Corridor volumes | BEH-1 / BEH-3 can leave **L** only if VAL-01 **PASSes** (NRMSE ≤ 0.30). WorldPop Tier-B scaling alone is not enough (CR-014 live NRMSE 4.488 FAIL). |
| 2 | Replace ECO-2 `_PM25_PER_CO2E_PROXY` (0.05) with a coefficient calibrated to OpenAQ/EMB | Air-quality Δ | ECO-2 can leave **L**; likely still **M** (method / S5P-NO2) |
| 3 | Per-barangay WorldPop in SOCI-3 instead of `_GENERIC_POP_DENSITY` (5,843/km²) | Health-exposure | Can leave **L** if the §3.6 provisional constant is retired |
| 4 | Real SUMO VKT + WHO-EMEP table instead of 150 m × 120 g/km | ECO-1 CO₂e | Data tier stays ~**H**; the **number** improves |
| 5 | Read CCHAIN `esa_worldcover` when the scenario actually removes cover | ECO-3 hectares | Only for construction / footprint scenarios. Lane closure remaining 0 is honest. |
| 6 | Live OpenAQ key, NHFR dump, NHCP declared-sites, GLO-30 DEM | Lineage matches the cited ID | Modest; several equations stay **M** on method maturity |

**Optional honesty (not a chip-raiser):** Inspect `input_dataset_ids` that the equation never opens (CCHAIN on ECON-1, EMB/S5P on ECO-2, NHFR on SOC-1, DEM on ECO-4). Fix lineage when touching that module — do not batch-rewire for the pitch.

## What is already good (do not reopen)

On a machine with processed BIR, CCHAIN Iloilo subset, ASPBI 2022, OSM extract, and `iloilo.net.xml`:

- ECON-1 uses BIR median CR × footprint × uplift (not the ₱50 fallback)
- SOC-1/2/3 and ECO-4 flood path read CCHAIN when those files exist
- VAL-01 FAIL is published, not hidden
- Missing files return `None` and cap confidence instead of inventing values

Inventory ☐ / ⏳ / FOI items (POPCEN-CBMS, DOT arrivals, Sentinel-5P rasters, GFM VAL-02, LTFRB ridership) stay **deferred substitutes** per [INVENTORY](../data/INVENTORY.md) and CR-016. They do not block the next demo.

## Docs

- This file is the queue. Canonical equations remain [methods-matrix.md](methods-matrix.md). Data status remains [INVENTORY](../data/INVENTORY.md) + [READINESS](../data/READINESS.md).
- Index change log updated. No Locked-doc edit under this CR.
