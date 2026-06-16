# Change Record (CR)

**CR ID:** `CR-007`
**Project:** MATRIX — Multi-Agent Twin for Routing & Infrastructure eXchange
**Date:** 2026-06-16
**Author:** Carlos Jerico Dela Torre (Team ATLAN)
**Status:** In progress (PR 1–4 merged = P0 closed; PR 5a net-prereq done; PR 5b–10 in progress/planned)
**Trigger document:** [cr-006-beyond-hackathon.md](cr-006-beyond-hackathon.md) §6 (carried-forward debt) + the next-session handoff

> **What this Record is.** CR-006 shipped a 16-unit product-hardening batch (PRs #1–#17), but
> several of those features were built *self-contained and never connected end-to-end*. This
> Record is the **review + implementation plan** to close that loop, plus the log of the units
> that land against it. It supersedes nothing Locked; methods-matrix follow-ups stay deferred to
> their own CR (see §6).

---

## 1. The central finding (why this CR leads with one fix)

A code-level review of the merged batch surfaced a disconnect the handoff under-weighted:

**The live WebSocket pipeline never simulated the parsed scenario.**

- `POST /scenario` → `parse_scenario()` built a full `Scenario` (intervention_type, location,
  parameters, geometry) and `db.save_scenario()` persisted it — including geometry.
- But the run did **not** read it back. `_get_trajectory(scenario_id)` only checked Redis
  (`scenario:{id}:latest`, never written by `POST /scenario`), then fell back to
  `scenario:demo:latest`, then ran a **blank** `Scenario(scenario_id, "live scenario", corridor="")`.
- Net: every real run simulated the busiest baseline edge with a default lane closure. The user's
  intervention, location, and geometry were discarded; `db.get_scenario` was an unused bridge.

This means the handoff's **P0-4 ("plumb geometry into POST /scenario")** was a symptom of a larger
gap — even *non-geometry* scenario params (type, location) never reached the kernel in a live run.
The kernel was ready (`runner.resolve_edges` already consumes `Scenario.geometry`); only the API
seam was missing. **PR 1 (below) fixes the seam and the geometry flow together, and it must precede
the live e2e** — otherwise the e2e green-lights a blank simulation.

---

## 2. Review: verified state of each gap (P0–P4)

| Item | Verified state | Action |
|---|---|---|
| **P0-1** Live e2e | Pipeline, persistence, timings, typed errors all wired. Real blocker beyond Docker = the §1 seam. | Verify **after** PR 1 |
| **P0-2** Map layers | `src/components/map/` (`useMapLayers` + 3 factories) is pure and **unimported**; scenario page renders only `TripsLayer` and has **no LayerLegend**. Hidden dep: **`edge_counts` is never streamed** over the WS, so congestion can't be driven yet. | PR 3 (needs a backend `edge_counts` event) |
| **P0-3** Builder link | Home has no `/builder` nav. | PR 4 (trivial) |
| **P0-4** Geometry flow | `ScenarioInput` had no geometry; orchestrator hardcoded `geometry=None`; builder embedded an NL `Geometry (GeoJSON):` suffix nothing parsed. `new_facility` exists in the builder but not in the orchestrator schema/kernel (Gemini remaps it to `lane_closure`). | **PR 1 (this)** |
| **P1-5** Validation gates | `validation.py` computes real RMSE/IoU with honesty invariants, but `get_all_validations()` supplies no simulated side → both gates **NOT_RUN**. No script wires baseline→report. | PR 5 |
| **P1-6** Mode-share | `ILOILO_MODE_SHARE` is literature-derived; stays **M** until a live survey. | PR 9 (data) |
| **P1-7** Provisional constants | 4 named PROVISIONAL proxies (ECO-2, ECON-1, SOC-2, SOCI-3); `edges.geojson`/`confidence.geojson` PROVISIONAL, `flood.geojson` REAL. | PR 7 (gated by PR 6) |
| **P2** Perf (~123 s vs 90 s) | `StageTimer` emits `{sumo_ms, modules_ms, gemini_ms, total_ms}` in DONE; no measured run yet. | PR 8 |
| **P3** methods CR | Locked doc; follow-ups await a CR. | PR 6 |
| **P4** Deploy | `fly.toml` + `Dockerfile.api` + `vercel.json` present and consistent; never deployed. | PR 10 |

---

## 3. The plan (PR-sized units)

Recommended order front-loads the seam fix so the e2e validates real behavior.

| PR | Scope | Priority | Depends on |
|----|-------|----------|------------|
| **1** ⭐ | Wire the persisted scenario (incl. geometry) into the live run | P0-4 + seam | — |
| **2** | Live e2e validation (verification gate, not code) | P0-1 | PR 1 |
| **3** | Stream `edge_counts`; wire `useMapLayers` + LayerLegend into the scenario page | P0-2 | (real `edges.geojson` export ideal) |
| **4** | Link `/builder` from home | P0-3 | — |
| **5** | Generate `validation_report.json` (VAL-01 via corridor→edge map + baseline) | P1-5 | seeded baseline |
| **6** | methods-matrix CR (promote BEH-4, ratify tiers + `method_capped_confidence` + proxies) | P3 | — |
| **7** | Replace PROVISIONAL constants + export real `edges`/`confidence` GeoJSON | P1-7 | PR 6 |
| **8** | Latency measurement + optimization (libsumo, horizon, caching, Gemini) | P2 | PR 2 timings |
| **9** | Mode-share calibration (FOI/survey) | P1-6 | data (out-of-band) |
| **10** | Deploy API→Fly + web→Vercel; secrets, staging, monitoring, backup drill | P4 | — |

**Sequence:** PR 1 → PR 2 (verify) → PR 3 + PR 4 → PR 5 → PR 6 → PR 7 → PR 8 → PR 9/10.

---

## 4. PR 1 — what shipped (the seam + geometry wiring)

**Backend**

- `matrix_api.main.ScenarioInput` gains an optional `geometry: dict | None` (a bare GeoJSON
  *geometry*, Point/Polygon). `create_scenario` forwards it to `parse_scenario(query, geometry=…)`
  and surfaces it on the response so the client can confirm the map-drop.
- `matrix_kernel.orchestrator.parse_scenario(query, client=None, geometry=None)` sets
  `Scenario.geometry` verbatim (was hardcoded `None`). The LLM still never originates geometry
  (PRD-F14) — it arrives structurally, out-of-band.
- `matrix_api.main._scenario_from_record(record)` rebuilds a kernel `Scenario` from a persisted
  `db.get_scenario` record (SUMO-free import, so it is unit-testable on a bare venv).
- `matrix_api.main._get_trajectory` now resolves in priority order: id-specific Redis cache → the
  **demo id only** falls back to the demo trajectory → the **persisted scenario** simulated live →
  a blank scenario only when nothing was ever persisted. The demo fallback is now gated to the
  literal demo id (`MATRIX_DEMO_SCENARIO_ID`, default `"demo"`) so a real run is no longer shadowed
  by the cached demo.

**Frontend**

- `lib/api.createScenario(query, geometry?)` posts `geometry` as a structured field, omitting it
  entirely on the plain NL path.
- `ScenarioBuilder` sends `drawnGeometryToGeoJSON(state.geometry)` (a new exported, tested pure
  helper) — a **bare geometry** (so PostGIS `ST_GeomFromGeoJSON` accepts it directly). The
  human-readable NL suffix is retained unchanged (glass box: what the review panel shows is still
  what is sent); geometry is now *additionally* authoritative via the structured field.

**Tests (all green):** kernel `175 passed / 3 skipped`; api `61 passed / 4 skipped` (persistence
`18 passed / 1 skipped`); web `158 passed`. New coverage: orchestrator geometry pass-through;
API geometry forwarding; `_scenario_from_record` (v2 + v1-only); `_get_trajectory` simulates the
persisted scenario and falls back to blank only when nothing is persisted; `createScenario`
geometry include/omit; `drawnGeometryToGeoJSON`; builder posts structured geometry.

**Known follow-up surfaced, not fixed here:** `new_facility` is offered by the builder but absent
from the orchestrator schema and kernel `INTERVENTION_TYPES` (Gemini remaps it to `lane_closure`).
Decide in a later PR whether to add it as an explicit alias.

---

## 4a. PR 2 — live e2e (verification) + model-id fix

Ran one real scenario end-to-end against the full local stack (Docker Postgres/Redis/Chroma +
uvicorn), 2026-06-16: **"Close 2 lanes on Diversion Road for roadworks."**

- **POST /scenario** (live Gemini orchestrator): parsed → `lane_closure`, location `Diversion Road`,
  lanes `2`. ✅
- **WS /simulate/{id}**: `ACCEPTED → 20×PLAYBACK_FRAME → 17×DIMENSION_RESULT (all 5 dimensions) →
  SYNTHESIS (1395 chars, 17 citations) → DONE`. Every result carried `equation_id +
  input_dataset_ids` (Inspect-resolvable). ✅
- **The PR 1 seam, proven live**: the persisted **Diversion Road** scenario was simulated (not a
  blank). Postgres `scenarios` row = `lane_closure / Diversion Road`; the `run` links to it; **17
  `dimension_results` rows** persisted; `GET /runs/{id}` reloaded `status=done` + 17 results with
  full provenance. ✅
- **Timings (P2 datapoint)**: `total_ms=48122` (**48 s — under the 90 s budget**), `sumo_ms=44012`
  (the bottleneck), `modules_ms=89`, `gemini_ms=3810`. The documented "~123 s" was a cold-baseline
  figure; with a warm cached baseline the delta run is well under budget. P2 should target SUMO.
- **Validation**: VAL-01/02 = `NOT_RUN` (expected; that is PR 5).

**Two real findings (environment, not PR-1 defects):**

1. **Model-id bug (fixed here).** The live API has **no bare `gemini-3.1-pro`** — `models/gemini-3.1-pro`
   returns 404. The published id is **`gemini-3.1-pro-preview`**. The code defaults
   (`orchestrator.py`, `synthesis.py`) and `app/.env.example` were corrected to `gemini-3.1-pro-preview`
   (still Gemini 3.1 Pro per the Locked decision — just the correct live id). `gemini-3.1-flash-lite`
   already resolves and was left as-is.
2. **Billing blocker (action for the user).** This `GOOGLE_API_KEY` is **free-tier**: Gemini 3.1 Pro
   (and 2.5-pro / 2.0-flash) return **429 RESOURCE_EXHAUSTED, limit: 0**. Only flash-tier models work
   on the key (`gemini-3.1-flash-lite`, `gemini-3-flash-preview`, `gemini-2.5-flash`). The e2e
   therefore ran orchestration + synthesis on **`gemini-3.1-flash-lite` as a clearly-labeled
   verification substitution** (the LLM never originates numbers — PRD-F14 — so the glass-box path is
   unaffected). **Production with the mandated `gemini-3.1-pro-preview` needs billing enabled** on the
   Google AI Studio / Cloud project.

## 4b. PR 3 — stream `edge_counts` + wire the map data layers

The `src/components/map/` module (congestion/confidence/flood factories + `useMapLayers`) shipped in
CR-006 but was never imported. PR 3 connects it, and adds the backend event it needs.

- **Backend**: the WS pipeline now emits a dedicated **`EDGE_COUNTS`** event (after the
  `PLAYBACK_FRAME`s, before the `DIMENSION_RESULT`s) carrying `Trajectory.edge_counts` — the
  per-edge vehicle counts that drive the congestion choropleth. Added to `EVENT_TYPES`; the run-state
  reducer treats it as a no-op (it is page-owned data, not lifecycle).
- **Frontend** (`scenario/[id]/page.tsx`): added a `LayerLegend` (Agent Trajectories / Congestion /
  Confidence / Flood Zones), `useMapLayers` assembling flood→congestion→confidence under the
  `TripsLayer`, static-layer fetches (`fetchStaticLayer` for edges/flood/confidence, once on mount),
  `edgeCounts` accumulated from the new event and **reset per `runAttempt`** alongside
  `tripsData`/`results`. The `agents` toggle gates the page-owned `TripsLayer`.
- **Verified**: live WS now streams `EDGE_COUNTS` (6,619 real SUMO edge ids, correctly positioned);
  browser preview shows all four legend toggles, no console errors, and the **REAL** `flood.geojson`
  (25 features) loads and toggles. Tests: web `159 passed`; the `EDGE_COUNTS` order/payload assertion
  lives in `test_runtime_hardening` (runs in the ubuntu CI api job).
- **Known caveat (tracked to PR 7)**: `edges.geojson` ships PROVISIONAL placeholder ids that do not
  match the real `edge_counts` keys, so the **congestion layer renders mostly NO_DATA until a real
  edges export** from `build_network.py`. The wiring + join contract are correct; only the static
  sample is provisional. `flood.geojson` is REAL and renders today.

## 4c. PR 5a — street names in the net + honest edge resolution (VAL-01 prerequisite)

Building VAL-01 surfaced a deeper defect: the SUMO net had **0 of 36,354 edges named**, so
`runner.target_edges` never matched a street keyword and **silently fell back to the busiest
baseline edge — while `_resolve_edges` labeled it `"keyword-match"`.** Every NL/keyword scenario
(no map-drop geometry) therefore simulated the busiest edge, not the named location, and the glass
box claimed a corridor match it never made. (This is why PR 2's "Diversion Road" e2e actually ran on
the busiest edge.)

Fix (user-chosen path: regenerate the net with names):

- **`build_network.py`** adds netconvert `--output.street-names true`. Stage 1 already preserved the
  OSM `name` way-tag, so this is the only change needed. Regenerated locally: **10,175 edges now
  named** (was 0); `"Benigno S. Aquino Jr. Avenue"` (Iloilo's "Diversion Road") → 205 edges,
  `"Lopez Jaena Street"` → 138 edges, both via real keyword-match. Edge-id alignment with the cached
  baseline is **100%** (all 6,599 trafficked ids preserved — the +203 edges carry no demand), so no
  re-seed was needed.
- **`runner._resolve_edges`** now separates a real keyword match from the busiest-edge fallback and
  labels the latter honestly, e.g. `busiest-baseline-fallback (no edge named like 'X')` /
  `(no location given)` / `(geometry off-network; …)` — never `"keyword-match"` for a fallback
  (PRD-F14). New `tests/test_edge_resolution.py` (6 tests) locks the labeling.

The net is gitignored, so the committed change is the build flag + the resolver; any environment
that regenerates the net gets named targeting. **VAL-01 (PR 5b) is now unblocked**: the corridor→edge
map is `lopez_jaena → "Lopez Jaena Street"`, `diversion → "Benigno S. Aquino Jr. Avenue"`, resolved
against the named net. VAL-01 will validate only the `passenger_flow_max` quantity (MATRIX has no
transfer model, so the fixture's `passenger_transfer_max` points stay out of scope).

**Reproducibility debt (new, tracked):** the net is built from `ghcr.io/eclipse-sumo/sumo:latest`
(unpinned). The name flag also nudged junction-joining (36,354 → 36,557 edges). Pin the netconvert
image tag before any deploy so the net is reproducible.

## 4d. PR 5b — VAL-01 machinery shipped; the result is honestly WITHHELD

With the net named (PR 5a), the corridor→edge mapping is finally possible. This ships the VAL-01
machinery and records why the *number* is not published.

- **`validation.py`**: `validate_calderon` / `run_validation_gates` gain an optional `quantity`
  filter (default None = unchanged). The live VAL-01 validates **`passenger_flow_max` only** —
  MATRIX produces edge passenger-flow proxies but models **no route transfers**, so the fixture's
  `passenger_transfer_max` points are out of scope, not silently mapped to edge flows (PRD-F14).
  3 new tests; 23 validation tests pass.
- **`matrix_kernel/build_validation_report.py`**: maps `lopez_jaena → "Lopez Jaena Street"`,
  `diversion → "Benigno S. Aquino Jr. Avenue"` against the named net, pulls each corridor's peak
  per-edge flow from the cached baseline, runs the gate, and writes `app/validation_report.json`
  (now **gitignored**).
- **Result (withheld, by the user's call):** against the *uncalibrated* baseline the simulated
  flows are **2744 / 1848 pax** vs Calderon's **90 / 275** → **NRMSE ≈ 11.95, FAIL by ~40×**. That
  is a mode-share calibration gap (P1-6) plus a proxy/unit scale mismatch — **not a model
  validation.** Per the glass-box mandate an *unvalidated* FAIL is not shipped as a validation:
  `GET /validation` keeps **VAL-01 = NOT_RUN** with an honest reason ("computable but withheld
  pending calibration + proxy reconciliation"), and the report stays gitignored — generate it at
  deploy once VAL-01 is meaningful.

VAL-02 stays NOT_RUN (PROVISIONAL flood fixture; no sourced Sentinel-1 extent).

## 5. Glass-box posture

PR 1 ships no number, so the glass-box ledger is untouched. The change *strengthens* the mandate:
a run now traces to the user's actual intervention rather than a silent blank stand-in, and geometry
travels on a single structured channel instead of being implied in prose.

---

## 6. Carried-forward debt (unchanged from CR-006 until its PR lands)

- Mode-share uncalibrated → Behavioral + bias-audit anchor stay **M** (PR 9).
- ~123 s vs the 90 s budget (PR 8).
- `edges.geojson` / `confidence.geojson` map samples PROVISIONAL (PR 7); `flood.geojson` REAL.
- methods-matrix follow-ups (BEH-4 promotion, tier ratification, proxy constants) **deferred to
  PR 6's CR** — methods-matrix stays Locked until then.
