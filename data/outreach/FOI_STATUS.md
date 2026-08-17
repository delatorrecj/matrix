# Outreach status — **WONT-FILE (open-data-only)**

> **Policy (2026-08 / CR-016):** Government FOI, LGU letters, NHCP/CBMS chase, and
> household travel surveys are **not feasible** for Team ATLAN. MATRIX credibility is
> open-data-only: refreshable OSM / OpenStat / CCHAIN / LiPAD / OpenAQ, with honest
> confidence floors where Tier-A agency ground truth is unreachable.

| Item | Value |
|------|--------|
| **Policy** | **WONT-FILE — open-data-only (2026-08)** |
| **Historical draft** | [ltfrb-vi-foi.md](ltfrb-vi-foi.md) (kept for archive; do not submit) |
| **Filed?** | No — and will not be filed under this policy |
| **Tracking number** | n/a |
| **Open substitute** | Literature mode-share (`ILOILO_MODE_SHARE` / Calderon 2014 + LPTRP context) · OSM PT · Tier-B WorldPop demand · LiPAD/NOAH flood hazard |

## What we use instead

| Need | Open path |
|------|-----------|
| Recent network / POIs | `python data/fetch/refresh_dynamic.py --all` → rebuild net/demand/baseline |
| Mode-share | Literature default in `matrix_kernel.config` — confidence **M**; do **not** invent shares |
| Flood | LiPAD 10 m hazard + CCHAIN `project_noah_hazards` (not CDRRMO / GFM event GT) |
| Air scale check | OpenAQ free API key → `fetch_openaq.py` |
| Economics | PSA OpenStat + World Bank + BIR CSV already in hand |

See [OPEN_REFRESH.md](../OPEN_REFRESH.md) and [docs/cr-016-open-data-only.md](../../docs/cr-016-open-data-only.md).

## Inject path (only if an *open* published mode-share later appears)

Do **not** invent shares. If a newer **open-licensed** published table for Iloilo / Region VI lands:

1. Document source + vintage in `INVENTORY.md`.
2. Set `MATRIX_MODE_SHARE={...}` (sum ~1.0) before kernel import.
3. Rebuild demand → baseline → `build_validation_report`.

Until then, Behavioral **behavior** stays **M** (literature). VAL-01 absolute volumes stay **directional** (FAIL expected under open Tier-B demand).
