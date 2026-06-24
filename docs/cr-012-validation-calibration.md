# CR-012 — Validation & Calibration (honest VAL-01 / VAL-02 + mode-share)

**Change Record ID:** CR-012
**Status:** Proposed (implementation plan)
**Date opened:** 2026-06-24
**Owner:** Carlos (delatorrecj)
**Trigger:** Post-CR-010 roadmap review — the headline credibility gap and ASEAN judges' **Ask #1 (ground-truth validation)**. The validation *machinery* is shipped and tested, but **VAL-01 is deliberately withheld** and **VAL-02 is NOT_RUN**: against uncalibrated synthetic demand the Calderon corridor flow proxy runs **~10× the published maxima** (NRMSE ~12 — a FAIL), and no real flood ground-truth is wired. This CR converts *"honesty surfaced"* into *"validated where the data allows, transparently documented where it doesn't."*

> **North star:** publish honest validation numbers (pass **or** documented fail) and lift Behavioral off the conservative capped-**M** only where calibration earns it — **never** massaging a gate to pass. The validation-theater invariants in [`validation.py`](app/packages/kernel/matrix_kernel/validation.py) (`GateResult.__post_init__`, `_check_report`) forbid status↔value contradictions by construction; this CR keeps that contract.

---

## 1. The gap, precisely (grounded in code)

**VAL-01 — Calderon 2014 corridor back-test** ([`validate_calderon`](app/packages/kernel/matrix_kernel/validation.py):180; threshold NRMSE ≤ 0.30). The pipeline is **already complete**: [`build_validation_report.generate()`](app/packages/kernel/matrix_kernel/build_validation_report.py):89 maps the two `scenario1` `passenger_flow_max` corridors to SUMO edges by street name (`CALDERON_CORRIDOR_STREETS` :53 — `lopez_jaena` → "Lopez Jaena Street", `diversion` → "Benigno S. Aquino Jr. Avenue"), pulls each corridor's peak per-edge passenger-flow proxy from the cached baseline (`simulated_corridor_flows_from_baseline` validation.py:444 — *busiest edge × 3600/window × 14 pax/veh*), and runs the NRMSE gate. Today → **NRMSE ~12, withheld** (build_validation_report.py:23-27). Two **distinct** causes:
- **(a) Demand volume uncalibrated (P1-6).** Synthetic demand isn't anchored to real corridor volumes → absolute flows ~10× high.
- **(b) Proxy/unit mismatch.** "busiest single edge × 14 pax/veh" may not be the quantity Calderon's JICA STRADA 3 model published as `passenger_flow_max`.

**VAL-02 — 2024 flood IoU** ([`validate_flood`](app/packages/kernel/matrix_kernel/validation.py):280; threshold IoU ≥ 0.50). The gate + GeoJSON→closures helper (`flood_closures_from_geojson` :252) are ready, but `generate()` only **stages** the helper against a placeholder polygon (build_validation_report.py:96-102) and leaves VAL-02 **NOT_RUN** — there is no sourced flood extent and no flood-scenario kernel run. The observed fixture `flood2024_closures.json` is **PROVISIONAL**.

**Mode share** ([`config.py:68`](app/packages/kernel/matrix_kernel/config.py) `ILOILO_MODE_SHARE`). Literature-derived (Calderon 2014 + LPTRP context), **not** a live survey → Behavioral capped **M** (method-cap rule, methods §2). Re-calibration is blocked on LTFRB OD data (FOI path documented config.py:48-67) or a local household survey; inject via `MATRIX_MODE_SHARE` once sourced. **Note:** modal split ≠ the VAL-01 10× gap — that gap is primarily *absolute demand volume + proxy*, so WS-1 and WS-2 are separate knobs.

**Bias reweight** (`bias_auditor.py`). Fires only on the LLM-generated pool; the deployed **static** pool is on-anchor by construction → no correction. Needs a worked example so the mechanism is demonstrable.

---

## 2. Decision needed (the real-world data fork)

Real calibration/validation data (LTFRB OD survey; Copernicus Sentinel-1 GFM flood extent) needs **FOI / acquisition that may not land soon**. So WS-1/2/3 each have two tiers:
- **Tier A (data lands):** calibrate to sourced data → publish PASS/FAIL honestly.
- **Tier B (data doesn't land in time):** do the proxy/unit reconciliation + a defensible **interim** anchor (CCHAIN / literature) so the gate yields a *meaningful* (not 10×-off) number, and document the residual as a known limitation.

Both are credible; **Tier B is the realistic near-term deliverable.** *(Owner decision: file the LTFRB RO-6 FOI and request the S1-GFM extent now? — recommended in parallel, since TAT ~15 working days.)*

---

## 3. Workstreams

### WS-1 — VAL-01: reconcile the proxy + calibrate demand → publish an honest RMSE *(critical path)*
- **T1.1 Diagnose the 10× gap.** Seed a baseline (`run_nightly_baseline()`), run `uv run python -m matrix_kernel.build_validation_report`, and read `details.pairs` (validation.py:242 — observed vs simulated per corridor). Decompose: how much is demand-volume vs proxy definition?
  > **T1.1 finding (2026-06-24, static — from the fixture + proxy, no live run needed).** The Calderon `scenario1_current` `passenger_flow_max` targets are **90 pax** (`s1_lopez_jaena_flow_max`) and **275 pax** (`s1_diversion_flow_max`) — peak-segment **transit passenger loads** from a calibrated JICA STRADA 3 assignment (paper §4.1; transit frequencies f=22 and f=60 veh/h). MATRIX's proxy (`simulated_corridor_flows_from_baseline`) instead computes **busiest-edge throughput of *all* vehicles × 3600/window × 14 pax/veh** — i.e. mixed road traffic scaled by a jeepney occupancy. These are **different quantities** (all-mode road throughput vs a transit-route segment load), so the ~10× is **not** purely demand-volume — a large part is the **proxy definition**. **Implication:** T1.2 (proxy reconciliation, no new data) is likely the dominant fix, and it must make the proxy measure a comparable quantity — restrict to transit-mode vehicles on the corridor + a mode-appropriate occupancy, *or* reframe the validated quantity — **independently** of the T1.3 demand-volume calibration. (Confirm magnitudes with the live run when Redis + a seeded baseline are available; the conclusion stands on the unit mismatch alone.)
- **T1.2 Reconcile the passenger-flow proxy.** Re-examine `simulated_corridor_flows_from_baseline` (validation.py:444-472): corridor-level vs busiest-single-edge; the 14 pax/veh occupancy (jeepney capacity vs load factor); peak-window vs daily max. Make the proxy measure the *published* quantity; document it in methods §4.
  > **T1.2 implemented (2026-06-24).** `validation.py` now separates the pure, unit-tested `corridor_flow_proxy` from the baseline I/O, and adds `transit_vehicle_share(mode_share)` — a mode's vehicle count is ∝ trip_share / occupancy, so the Iloilo anchor yields a **~13% transit-vehicle share**. `simulated_corridor_flows_from_baseline` now restricts the all-vehicle edge throughput to that transit share before applying the jeepney occupancy (documented `_OCCUPANCY_BY_MODE`, tier M), removing **~8× of the ~10× over-count** by the anchor math — leaving a small residual for demand-volume calibration (T1.3 / WS-2). 6 new unit tests; all 29 `test_validation.py` pass bare. **Live NRMSE confirmation + methods §VAL-01 re-lock are deferred to deploy** (needs the seeded baseline; not runnable bare). `transit_vehicle_fraction=1.0` restores the pre-CR-012 proxy.
- **T1.3 Calibrate demand volume.** Anchor the demand generator ([`packages/data/build_demand.py`](app/packages/data/build_demand.py), `demand_delta.py`) so baseline corridor volumes are in the Calderon ballpark. *Tier A:* scale to LTFRB/observed counts. *Tier B:* an independent volume proxy (e.g. CCHAIN/POPCEN-derived) — **avoid** calibrating to the Calderon target itself (circularity; see §4).
- **T1.4 Publish.** `generate()` already emits the live report when the baseline is present; wire it to run at deploy/startup so `GET /validation` serves it. Un-withhold: report PASS or an honest FAIL with the residual documented; keep the withhold path for genuinely-absent data.
- **Files:** `validation.py`, `build_validation_report.py`, `packages/data/build_demand.py`, `demand_delta.py`, `methods-matrix.md` §4 + §VAL-01, `qad-matrix.md` §8.
- **Done-when:** a non-withheld VAL-01 with a documented proxy; NRMSE is a *real* validation result (pass or fail) within an order of magnitude of threshold; methods updated.

### WS-2 — Mode-share calibration → Behavioral confidence
- **T2.1 Acquire (Tier A):** file the LTFRB RO-6 FOI (config.py:58-67) for Iloilo OD/ridership, or run the ~300-respondent local survey. **T2.2 Interim (Tier B):** derive a defensible empirical anchor from CCHAIN / available transport data; document its tier.
- **T2.3 Inject:** set the calibrated `MATRIX_MODE_SHARE` (config validates the sum); the bias auditor enforces ±3%.
- **T2.4 Confidence:** revisit the method-cap on BEH-2/Behavioral (`confidence.py`, methods §2 `method_capped_confidence`) — promote **M→H only where data + method maturity earn it**; otherwise keep M honestly.
- **Files:** `config.py`, `confidence.py`, `bias_auditor.py`, `methods-matrix.md` §3.1/§2, `data/READINESS.md`, `data/INVENTORY.md`.
- **Done-when:** the anchor's source + tier are documented; Behavioral confidence reflects the calibrated reality (promoted only if earned).

### WS-3 — VAL-02: real flood ground-truth + a flood-scenario run
- **T3.1 Acquire** the Copernicus GFM Sentinel-1 2024 Iloilo flood extent (INVENTORY `S1-GFM` ⏳). **T3.2** intersect with OSM-ILO via `flood_closures_from_geojson` (validation.py:252) → replace the PROVISIONAL `flood2024_closures.json` observed fixture (drop the `PROVISIONAL_MARK` *only* when genuinely sourced). **T3.3** run a flood-closure scenario through the kernel for the simulated side; feed `validate_flood`. **T3.4** wire `generate()` to run VAL-02 live (currently only stages the helper, build_validation_report.py:96-102).
- **Done-when:** VAL-02 computes a real IoU (pass/fail) against a sourced extent, or stays honestly NOT_RUN with the acquisition status.

### WS-4 — Bias reweight: make it demonstrable
- **T4.1** Add a worked example (doc + kernel test) showing the `generate → audit → reweight` loop correcting an off-anchor pool. **T4.2** Either run the LLM-persona path (`MATRIX_PERSONA_LLM=1`) in a controlled demo so the reweight visibly fires, or document why the static pool is on-anchor by construction (no correction needed). Surface `adjustment_factors` in the public audit log (already persisted per `scenario_id`).
- **Files:** `bias_auditor.py`, `personas.py`, `methods-matrix.md` §(bias auditor), the AAIH ethics report.
- **Done-when:** a planner sees, with a concrete example, that the auditor corrects bias (or exactly why none is needed for the deployed pool).
  > **WS-4 done (2026-06-24).** The worked example already lived in methods §4.1 (CR-008); WS-4 closes the loop honestly. (1) `test_methods_4_1_worked_example_matches_doc` is the **executable mirror** of §4.1 — a private-car-over-indexed batch (shares 0.40/0.30/0.15/0.08/0.04/0.03) is flagged (max_delta 0.15 ≫ ±3%), reweighted with the documented per-mode factors (1.25/0.50/1.00/1.25/1.25/1.67), and re-audited within ±3% — so the published numbers can't drift. (2) `test_deployed_static_pool_is_on_anchor_by_construction` asserts the **deployed default pool** passes with no reweight (`adjustment_factors is None`). (3) The AAIH ethics report's Technical-Bias paragraph now states this honestly: the audit runs every sim and passes by construction for the static pool; the reweight is the safety net for the opt-in `MATRIX_PERSONA_LLM=1` path. No new data; no Locked-doc change. 11/11 `test_bias_auditor.py` pass bare.

### WS-5 — Live wiring + UI honesty
- **T5.1** Emit the live `validation_report.json` at deploy/startup so `GET /validation` serves real gates (not NOT_RUN). **T5.2** Verify the UI `ValidationPanel` shows the new live results and still renders NOT_RUN honestly for Tier-B/absent data. **T5.3** Update the AAIH ethics/validation narrative.
- **Done-when:** prod `GET /validation` reflects the computed gates; the panel shows them.

---

## 4. Glass-box guardrails (must-not-break)
- A **FAIL is reported as FAIL**; gates are never massaged (`validation.py` `__post_init__` + `_check_report` enforce status↔value consistency).
- **No circularity:** do **not** calibrate demand to the Calderon target itself and then report a VAL-01 pass — that's validating against the calibration set. Prefer an independent volume anchor; if an interim coarse anchor touches the target, disclose it as *reconciliation*, not an independent back-test.
- A provisional fixture keeps `PROVISIONAL_MARK` until genuinely sourced (`load_fixture` enforces).
- Every calibrated constant (mode share, pax/veh, demand scale) carries its **source + tier** in the methods ledger.

## 5. Testing & gates
- Kernel `pytest` (existing validation tests stay green + new calibration/proxy tests).
- **`glass-box-auditor`** (every published number traces; no massaged gate) + **`eval-test-runner`** before merge.
- Re-lock `methods-matrix.md` §4/§VAL + §3.1 if the proxy/threshold/anchor change; update `qad-matrix.md` §8.

## 6. Phasing
- **Phase A — no new data, shippable now:** WS-1 proxy/unit reconciliation (T1.1–T1.2) + WS-4 worked example + WS-5 live wiring. This alone turns NRMSE ~12 into a *meaningful* number and serves live gates.
- **Phase B — data-dependent:** WS-2 (mode-share), WS-1 T1.3 Tier-A demand calibration, WS-3 (flood). Gated on FOI/acquisition; file requests now.

## 7. Definition of Done
- [ ] VAL-01 emits an honest, non-withheld result (pass or documented fail) with a reconciled, documented proxy.
- [ ] Mode-share anchor source/tier documented; Behavioral confidence reflects reality (promoted only if earned).
- [ ] VAL-02 computes a real IoU against sourced data, or stays honestly NOT_RUN with acquisition status.
- [ ] Bias reweight has a worked example.
- [ ] Live `GET /validation` serves computed gates; `methods-matrix.md` / `qad-matrix.md` updated + re-locked; `glass-box-auditor` + `eval-test-runner` PASS.

## 8. Risks
- **Data never arrives** (FOI delays) → Phase B stalls; mitigate with Tier-B interim anchors + honest documentation.
- **Circularity** (calibrating to the validation target) → disclose; prefer independent anchors.
- **Gap attribution unknown until T1.1** — if the 10× is mostly proxy-definition it's fixable *now* (Phase A); if mostly demand-volume it needs data (Phase B). T1.1 decides the split.
