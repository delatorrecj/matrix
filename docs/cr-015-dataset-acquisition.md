# CR-015 — Dataset acquisition (credibility blockers only)

**Date:** 2026-08-05  
**Status:** Applied (partial — human FOI still pending)

## Why

Ponytail acquisition: only datasets that unblock credible magnitudes (mode-share FOI path, S1 flood GT, open vintage refresh). No catalog bloat.

## What landed

| Lane | Outcome |
|------|---------|
| Transport FOI | `FOI_STATUS.md` ready-to-file + save/inject path; draft asks ridership/OD. **Not filed by automation.** |
| S1-GFM | STAC fetch script + attempt log. **BLOCKED:** City Proper windows mostly exclusion (`255`); best flood_px=1. VAL-02 stays **NOT_RUN**. |
| Open refresh | `refresh_dynamic.py --all` + Overpass mirror retry; OpenStat PX ids updated (FIES/ASPBI/GVA). Net + demand (`--fringe-factor 1.0`) + Redis baseline + `validation_report.json` rebuilt. |
| P1 | Checklist in `data/outreach/P1_ACQUISITION.md` (OpenAQ key unset; BIR DO17-2021 still current; NHCP still OSM interim). |

## VAL stamp (post-rebuild)

- **VAL-01:** FAIL NRMSE ≈ **4.85** (threshold 0.30) — still uncalibrated vs Calderon; FOI/survey required for Tier A mode-share.
- **VAL-02:** NOT_RUN (no usable S1 GeoJSON).

## Do not

- Invent `MATRIX_MODE_SHARE` or fit demand to Calderon targets (CR-012).
- Publish VAL-02 against the provisional street-name fixture.
