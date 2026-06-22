# Change Record (CR)

**CR ID:** `CR-006`
**Project:** MATRIX — Multi-Agent Twin for Routing & Infrastructure eXchange
**Date:** 2026-06-14
**Author:** Carlos Jerico Dela Torre (Team ATLAN)
**Status:** Applied
**Trigger document:** [MATRIX.md](../MATRIX.md) §8 Development Roadmap + §Appendix A (vision/direction change)

> **Numbering note.** This pivot was scoped as "CR-005" while planning the build batch, but `CR-005` was already taken by the 2026-06-09 truth-reconciliation pass (logged in [index.md §2](index.md) and referenced inline by `prd-/sdd-/dsd-/qad-/methods-/build-/gtm-matrix.md`). Renumbering an applied CR that other docs cite would orphan those references and break the FMD "never reuse or renumber a CR ID" rule, so this Record takes the next free ID, **`CR-006`**, and keeps the descriptive slug (`cr-006-beyond-hackathon.md`). The working branch name (`docs/cr-005-beyond-hackathon`) is retained as-is.

---

## 1. What Changed

**The destination changed.** MATRIX was built to *win* the ASEAN AI Hackathon 2026. As of 2026-06-14 the user redirected it to be built as a **real-world product**, with whatever results from that work presented at the hackathon. The hackathon becomes a **milestone and showcase, not the destination.**

A 16-unit parallel→sequential build batch implemented that redirection end-to-end. All 16 code units are merged into `main` (commit `2f4e636`). This Record documents the change that already shipped.

**Before** — a hackathon demo with honest scaffolding but demo-grade edges:

- **Scenario engine** limited to corridor lane-closures: a 4-field `Scenario` dataclass + a single TraCI edit.
- **Glass-box UX** half-wired: a mock cockpit, non-clickable provenance, a hardcoded `ValidationPanel`.
- **Zero persistence**: empty `schema.sql`, stub `/runs` and `/audit`.
- **Validation gates** returned **hardcoded PASS** values — `PRD-F18` honesty claim not actually computed.
- **No auth / rate-limit / CORS.**
- **Iloilo hardcoded** against the city-agnostic pitch (MATRIX.md §10).
- **~123 s** end-to-end vs the **90 s** budget ([rfc-matrix-realtime-pipeline.md](rfc-matrix-realtime-pipeline.md)), with no per-stage visibility to attack it.
- **Pre-existing glass-box debt:** unregistered dataset tiers silently demoting confidence; unsourced proxy constants.

**After** — a product whose *honesty is the differentiator*, shipped across PRs #1–#17:

| PR | Change |
|----|--------|
| #1 | CI for kernel/api/web + secrets hygiene (`SECURITY.md`, `.gitignore`, `.env.example`) |
| #2 | **Scenario v2** — typed interventions (`lane_closure` / `full_closure` / `speed_change` / `capacity_change`), orchestrator parsing, TraCI dispatch, geometry-carrying `Scenario` |
| #3 | **Geometry engine** — GeoJSON (Point / Polygon) → SUMO edge ids |
| #4 | **Facility demand-redistribution module** (gravity trip deltas; method `BEH-4-PROVISIONAL`) |
| #5 | **Real VAL-01 / VAL-02 validation gates** — computed Calderon-2014 RMSE + 2024 flood IoU + `validation_report.json` (Calderon fixture genuinely sourced; flood fixture flagged **PROVISIONAL**) |
| #6 | **City-agnostic `CityConfig` layer** (Iloilo = zero-change default) |
| #7 | **LLM resilience** — retry/backoff, hard timeout, typed `LLMUnavailable` for Azure OpenAI GPT-5.4 |
| #8 | **API persistence** — Postgres/PostGIS schema, db layer with in-memory fallback, wired `/scenario`, `/runs`, `/audit` + `GET /validation` |
| #9 | **WS runtime hardening** — per-stage timings in `DONE`, stage timeouts, typed `ERROR` + `QUEUED` events, concurrency semaphore, dependency-aware `/health` |
| #10 | **Auth + rate limit + CORS** (env-gated, default off; WS honors the key) |
| #11 | **Live cockpit** — real `POST /scenario`, no unlabeled mock data, sample-mode labeled |
| #12 | **Progressive simulation UX** — skeletons, n/5·m/17 progress, cancel, reconnect, stage-timing summary |
| #13 | **Interactive glass-box provenance** — citation chips → Inspect, clickable dataset metadata, a11y, `ValidationPanel` wired to `GET /validation` |
| #14 | **Map data layers** — congestion choropleth, confidence heatmap, flood overlay (flood sample REAL from CCHAIN/NOAH; others **PROVISIONAL**) |
| #15 | **Structured scenario builder** — intervention picker + map placement + parameter form → NL serialization, `/builder` route |
| #16 + #17 | **Glass-box debt remediation** — SOCI-3 `8500` constant given honest provenance (#16); dataset tiers registered (EMB / LIPAD / DEM / NHFR = H, S5P-NO2 = M, sourced from [INVENTORY.md](../data/INVENTORY.md)), `method_capped_confidence` for ECO-4 / SOC-1, proxy constants (`0.05` / `50` / `12`) named + **PROVISIONAL**-labeled, citation guard strengthened to enforce dataset basis (#17) |
| *(this)* | **CR-006** — direction-change record + living-doc propagation |

Net: the gaps that read as "demo-grade" before are closed or **labeled honestly as provisional** — which, for a glass-box product, is the feature, not a hedge.

---

## 2. Why

The hackathon is a deadline, not a market. Building strictly to win it optimizes for a 5-minute demo: a mock cockpit reads fine on stage, a hardcoded `PASS` looks like validation, a single hardcoded corridor covers the one scripted scenario. Building for the **real world** inverts every one of those — a planner who actually uses MATRIX will drop a *polygon* (not a corridor), expect the validation number to be *computed* from a back-test, expect their run to *persist*, and expect the tool to work in *their* city, not only Iloilo.

The motivating gaps (§1 "Before") were precisely the seams where demo-grade and product-grade diverge. Each was a place where the product would have asserted more confidence than it had earned — the opposite of the glass-box mandate ([methods-matrix.md](methods-matrix.md), `PRD-F14`). The redirection forces the build to **earn** every claim it shows: computed validation instead of a literal, clickable provenance instead of a static panel, registered dataset tiers instead of a silent confidence demotion.

This is also the cheapest moment to do it. The kernel, the five modules, the WS API, and the frontend were already built through Milestone B ([CR-004](index.md)); the batch hardens what exists rather than designing from scratch. The hackathon still benefits — an honest, persistent, city-agnostic product is a *stronger* showcase than a scripted demo (MATRIX.md Appendix B leads with exactly this honesty claim).

---

## 3. Decision

**Reframe MATRIX from "hackathon submission" to "real-world product, with the hackathon as one showcase milestone."** Ship the 16-unit batch (PRs #1–#17) that closes or honestly labels every demo-grade gap, and record the implied amendments to the **Locked** PRD / SDD / methods-matrix here rather than editing those frozen docs (the CR is the amendment mechanism, per [CR-001](index.md)).

**Alternatives rejected:** (a) *Keep building only to the demo* — rejected; it banks confidence the product hasn't earned and leaves no path past June. (b) *Re-open and edit the Locked PRD/SDD/methods directly* — rejected; that silently invalidates downstream docs and breaks the change-propagation contract. The CR is the correct instrument. (c) *Defer hardening to "post-submission"* (MATRIX.md §8 Post-Submission) — rejected; the gaps were cheapest to close while the code was warm, and the honesty they buy is itself the pitch.

This **does not reverse** any locked technical decision (SUMO, Azure OpenAI GPT-5.4, unified-kernel-five-modules, 90 s budget, Iloilo pilot all stand). It changes the *intent and finish quality* of the build, not its architecture.

---

## 4. Propagation Checklist

Trigger doc is **MATRIX.md** (the BRD-role vision doc). Walking downstream: PRD → SDD → RFC, plus DSD / QAD / methods / implementation-plan / index. The PRD, SDD, and methods-matrix are **Locked** — this CR records the deltas as **amendments the Locked docs should absorb at their next revision**; it does **not** edit them.

| Doc | Affected? | Action needed | New version | Done |
|-----|-----------|---------------|-------------|------|
| BRD ([MATRIX.md](../MATRIX.md)) | Yes | Roadmap (§8): add the post-Milestone-B product-hardening batch as a milestone with the hackathon reframed as a showcase. Appendix A: append the direction pivot consistently. | n/a (living) | [x] |
| PRD ([prd-matrix.md](prd-matrix.md)) | Yes — **Locked; amendment only** | `PRD-F2` map-drop is now delivered via the **structured scenario builder** (`/builder`, PR #15) + geometry engine (PR #3). New shipped requirements implied: **persistence** (`/runs`, `/audit`, GET `/validation`; PR #8), **auth/rate-limit/CORS** (PR #10), **validation-as-computed** (`PRD-F18` no longer a hardcoded PASS; PR #5). Record here; do **not** edit the Locked PRD. | 0.1 (unchanged; amendment pending) | [x] |
| DSD ([dsd-matrix.md](dsd-matrix.md)) | Yes | New surfaces shipped: live cockpit (PR #11), progressive UX with skeletons/cancel/reconnect (PR #12), interactive provenance chips → Inspect + wired `ValidationPanel` (PR #13), map data layers (PR #14), scenario-builder route (PR #15). Reconcile at next DSD pass; no edit required under this CR. | 0.1 (reconcile next pass) | [x] |
| SDD ([sdd-matrix.md](sdd-matrix.md)) | Yes — **Locked; amendment only** | §3 schema is now **implemented** (Postgres/PostGIS, db layer with in-memory fallback; PR #8). New components: `CityConfig` layer (PR #6), LLM-resilience wrapper (PR #7), geometry engine (PR #3), WS concurrency semaphore + dependency-aware `/health` (PR #9). Record here; do **not** edit the Locked SDD. | 0.1 (unchanged; amendment pending) | [x] |
| RFC ([rfc-matrix-realtime-pipeline.md](rfc-matrix-realtime-pipeline.md)) | Yes | WS contract gained a **`QUEUED`** event and **`DONE.timings`** (per-stage), plus stage timeouts and a typed `ERROR` path now exercised (PR #9). `ERROR` already existed in the contract; `QUEUED` + `DONE.timings` are additive. Reconcile RFC-001 at next pass; recorded here. | Approved (reconcile next pass) | [x] |
| methods-matrix ([methods-matrix.md](methods-matrix.md)) | Yes — **Locked; amendment only** | Two deliberate follow-ups deferred to this CR (see §4.1). Record as **CR-006-approved** changes the Locked ledger should absorb at its next revision; do **not** edit it now. | 0.1 (unchanged; amendment pending) | [x] |
| QAD ([qad-matrix.md](qad-matrix.md)) | Yes | VAL-01 / VAL-02 are now **computed gates** (Calderon-2014 RMSE + 2024 flood IoU → `validation_report.json`; PR #5), not hardcoded. CI added (PR #1). Reconcile the validation-gate section at next QAD pass; recorded here. | 0.1 (reconcile next pass) | [x] |
| Implementation Plan ([implementation-plan-matrix.md](implementation-plan-matrix.md)) | Yes | Add **Phase 8 — Beyond the Hackathon (Product Hardening)** capturing the batch + its gate; carry forward the honest-debt items. | 0.3 | [x] |
| CLR ([clr-matrix.md](clr-matrix.md)) | No | No new personal-data flow or obligation. Auth/CORS (PR #10) is access-control, not a new data subject; secrets hygiene (PR #1) *strengthens* the existing RA 10173 posture. Re-check if production launch adds user accounts with PII. | — | [x] |
| SAD ([sad-matrix.md](sad-matrix.md)) | No | Build-agent roster unchanged; no agent derives from a cut feature. | — | [x] |
| GTM ([gtm-matrix.md](gtm-matrix.md)) | No (this CR) | Positioning is unchanged in substance — the honesty angle GTM already leads with is now *more* true (computed validation, labeled provisional data). No edit required under this CR. | — | [x] |
| OPS ([ops-matrix.md](ops-matrix.md)) | No (this CR) | Per-stage timings (PR #9) and dependency-aware `/health` strengthen the OPS SLO story; reconcile opportunistically, not blocking. | — | [x] |
| index.md ([index.md](index.md)) | Yes | Bump touched rows; add CR-006 to the Change Log; list the new CR file. | — | [x] |

### 4.1 methods-matrix follow-ups CR-006 records (for the next Locked-doc revision)

The code **deliberately deferred** two methods-ledger changes to this CR so the Locked doc absorbs them in one ratified pass:

1. **Promote `BEH-4-PROVISIONAL` → a real methods §3.1 row.** The facility demand-redistribution module (gravity trip deltas, `packages/kernel/.../demand_delta.py`, PR #4) ships under the provisional method id `BEH-4-PROVISIONAL`. CR-006 approves promoting it to a numbered `BEH-4` row in [methods-matrix.md §3.1](methods-matrix.md) with its gravity-model equation, inputs, and confidence cap stated.
2. **Ratify the VAL-01 / VAL-02 thresholds + the dataset-tier additions.** PR #5 computes VAL-01 (Calderon-2014 RMSE) and VAL-02 (2024 flood IoU); PR #17 registers dataset tiers (EMB / LIPAD / DEM / NHFR = **H**, S5P-NO2 = **M**, sourced from [INVENTORY.md](../data/INVENTORY.md)) and adds `method_capped_confidence` for ECO-4 / SOC-1 plus named, PROVISIONAL-labeled proxy constants (`0.05`, `50`, `12`). CR-006 approves these as the values the Locked methods ledger should record — with the **flood fixture and proxy constants carried as PROVISIONAL** until real fixtures replace them.

These are **recorded, not yet written into** the Locked methods-matrix; its next revision should fold them in citing CR-006.

---

## 5. Impact Summary

- **Scope:** Net **added**. No feature cut. The product gained persistence, computed validation, auth/rate-limit/CORS, a typed scenario engine + geometry, a city-agnostic config layer, LLM resilience, a structured scenario builder, interactive glass-box provenance, map data layers, and progressive UX. The *intent* shifted from "win the demo" to "ship a product, demo what shipped."
- **Stack:** No new locked tech. Adds the implemented Postgres/PostGIS schema (already planned in SDD §3), env-gated auth/CORS/rate-limit, and CI — all within the existing stack envelope.
- **Timeline:** The hackathon is reframed from *destination* to *milestone/showcase*. The batch shipped pre-submission; remaining honest-debt items (§ below) are post-showcase work, not submission blockers.
- **Risk / cost:** **Retired** — silent-confidence-demotion debt, hardcoded validation, zero persistence, single-city hardcoding, missing access control. **Carried forward (honest debt):** mode-share is still **uncalibrated** (literature-derived; Behavioral stays at **M**); end-to-end is still **~123 s vs the 90 s budget** — but per-stage timings are now visible to attack it; **flood / edges / confidence-map samples are PROVISIONAL**; the **live VAL gate numbers need the corridor→edge map + a kernel run** to move from fixture to live. None of these is hidden — each is labeled in-product or in the ledger.
- **Code already written:** This CR *documents* merged code (PRs #1–#17 at `2f4e636`); it invalidates nothing. It records the PRD/SDD/methods amendments the Locked docs must absorb at their next revision.

---

## 6. Rollback

This is a documentation Record over already-merged code; "rollback" means reverting the *documentation*, not the product.

- **Docs:** revert this file, the `implementation-plan-matrix.md` Phase 8 addition, the MATRIX.md §8/Appendix A edits, and the `index.md` Change-Log row. The four touched living docs return to their prior commit; no Locked doc was edited, so none reverts.
- **Code:** out of scope here. The merged batch (PRs #1–#17) would roll back through its own reverts on `main` — independent of this Record.
- **Reversibility:** fully reversible as documentation. The *direction change* it records is a strategic decision, not a code artifact; reversing it would itself warrant a new CR.
