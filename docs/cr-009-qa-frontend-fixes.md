# CR-009 — QA and Frontend Design Fixes

**Change Record ID:** CR-009
**Status:** In progress
**Date opened:** 2026-06-20
**Owner:** Yushin
**Trigger:** Routine QA sweep and frontend design validation for scenario simulation views.

## 1. Overview
This Change Record documents the frontend design fixes, bug resolutions, and ongoing QA tasks performed by Yushin to harden the Matrix simulation interface. It serves as the tracking document for what has been completed and what is yet to be done regarding frontend QA.

## 2. Completed Tasks (Done)
- [x] **Agent Trajectory Animation Bug Fix:** Resolved the issue where agent paths failed to render on the Deck.gl `TripsLayer`. Modified `page.tsx` to properly aggregate `PLAYBACK_FRAME` ticks into full trajectory arrays and implemented a dynamic scrubber to synchronize with backend simulation ticks.
- [x] **Confidence Layer Verification:** Verified that the solid orange grid overlay across the map is the intentional behavior. It correctly enforces the `method_capped_confidence` rule (ratified in CR-007 PR 6) where uncalibrated mode-share forces a conservative "M" (Moderate) baseline.
- [x] **Simulation Verification Guards:** Confirmed that Glass-Box Traceability via the `InspectDrawer` accurately tracks `equation_id`, inputs, and confidence. Validated that Bias and Synthesis narratives execute without hallucinations.

## 3. Remaining Tasks (Yet to be done)
- [ ] Conduct a full DSD compliance pass for any newly introduced UI components (density, a11y self-check, motion budget).
- [ ] Verify frontend behavior gracefully handles `QUEUED` states and edge-case backend errors during high concurrency runs.
- [ ] Address the "uncalibrated mode-share" technical debt to eventually promote the baseline Confidence layer from "M" to an empirical, spatially-varying standard.
- [ ] Cross-check the updated timeline scrubber logic with extreme event scenarios (e.g., massive full-closures) to ensure prolonged delays are rendered accurately.

## 4. Definition of Done
- [ ] All QA and frontend fixes verified and merged to `main`.
- [ ] Frontend end-to-end (e2e) tests updated and passing.
- [ ] Change Log in `index.md` marked as Applied.
