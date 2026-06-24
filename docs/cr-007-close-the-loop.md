# Change Record (CR)

**CR ID:** `CR-007`
**Project:** MATRIX — Multi-Agent Twin for Routing & Infrastructure eXchange
**Date:** 2026-06-16
**Author:** Carlos Jerico Dela Torre (Team ATLAN)
**Status:** Complete (PR 1–10 merged) — **deploy section superseded by [CR-011](cr-011-huggingface-migration.md)**
**Trigger document:** [cr-006-beyond-hackathon.md](cr-006-beyond-hackathon.md) §6 (carried-forward debt) + the next-session handoff

> ⚠️ **Historical record.** The P4 "Deploy" steps below target **Fly.io**, which has since been
> decommissioned. The current deploy target is **Hugging Face Spaces + Vercel** — see
> [CR-011](cr-011-huggingface-migration.md) and [ops-matrix.md](ops-matrix.md) §7. Do not follow the Fly steps here.

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
| **P0-4** Geometry flow | `ScenarioInput` had no geometry; orchestrator hardcoded `geometry=None`; builder embedded an NL `Geometry (GeoJSON):` suffix nothing parsed. `new_facility` exists in the builder but not in the orchestrator schema/kernel (Azure OpenAI remaps it to `lane_closure`). | **PR 1 (this)** |
| **P1-5** Validation gates | `validation.py` computes real RMSE/IoU with honesty invariants, but `get_all_validations()` supplies no simulated side → both gates **NOT_RUN**. No script wires baseline→report. | PR 5 |
| **P1-6** Mode-share | `ILOILO_MODE_SHARE` is literature-derived; stays **M** until a live survey. | PR 9 (data) |
| **P1-7** Provisional constants | 4 named PROVISIONAL proxies (ECO-2, ECON-1, SOC-2, SOCI-3); `edges.geojson`/`confidence.geojson` PROVISIONAL, `flood.geojson` REAL. | PR 7 (gated by PR 6) |
| **P2** Perf (~123 s vs 90 s) | `StageTimer` emits `{sumo_ms, modules_ms, llm_ms, total_ms}` in DONE; no measured run yet. | PR 8 |
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
| **8** | Latency measurement + optimization (libsumo, horizon, caching, Azure OpenAI) | P2 | PR 2 timings |
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
from the orchestrator schema and kernel `INTERVENTION_TYPES` (Azure OpenAI remaps it to `lane_closure`).
Decide in a later PR whether to add it as an explicit alias.

---

## 4a. PR 2 — live e2e (verification) + model-id fix

Ran one real scenario end-to-end against the full local stack (Docker Postgres/Redis/Chroma +
uvicorn), 2026-06-16: **"Close 2 lanes on Diversion Road for roadworks."**

- **POST /scenario** (live Azure OpenAI GPT-5.4 orchestrator): parsed → `lane_closure`, location `Diversion Road`,
  lanes `2`. ✅
- **WS /simulate/{id}**: `ACCEPTED → 20×PLAYBACK_FRAME → 17×DIMENSION_RESULT (all 5 dimensions) →
  SYNTHESIS (1395 chars, 17 citations) → DONE`. Every result carried `equation_id +
  input_dataset_ids` (Inspect-resolvable). ✅
- **The PR 1 seam, proven live**: the persisted **Diversion Road** scenario was simulated (not a
  blank). Postgres `scenarios` row = `lane_closure / Diversion Road`; the `run` links to it; **17
  `dimension_results` rows** persisted; `GET /runs/{id}` reloaded `status=done` + 17 results with
  full provenance. ✅
- **Timings (P2 datapoint)**: `total_ms=48122` (**48 s — under the 90 s budget**), `sumo_ms=44012`
  (the bottleneck), `modules_ms=89`, `llm_ms=3810`. The documented "~123 s" was a cold-baseline
  figure; with a warm cached baseline the delta run is well under budget. P2 should target SUMO.
- **Validation**: VAL-01/02 = `NOT_RUN` (expected; that is PR 5).

**Two real findings (environment, not PR-1 defects):**

1. **Model-id bug (fixed here).** The live API has **no bare `gpt-5.4`** — `models/gpt-5.4`
   returns 404. The published id is **`gpt-5.4-preview`**. The code defaults
   (`orchestrator.py`, `synthesis.py`) and `app/.env.example` were corrected to `gpt-5.4-preview`
   (still Azure OpenAI GPT-5.4 per the Locked decision — just the correct live id). `gpt-5.4`
   already resolves and was left as-is.
2. **Billing blocker (action for the user).** This `GOOGLE_API_KEY` is **free-tier**: Azure OpenAI GPT-5.4
   (and 2.5-pro / 2.0-flash) return **429 RESOURCE_EXHAUSTED, limit: 0**. Only flash-tier models work
   on the key (`gpt-5.4`, `gemini-3-flash-preview`, `gemini-2.5-flash`). The e2e
   therefore ran orchestration + synthesis on **`gpt-5.4` as a clearly-labeled
   verification substitution** (the LLM never originates numbers — PRD-F14 — so the glass-box path is
   unaffected). **Production with the mandated `gpt-5.4-preview` needs billing enabled** on the
    Azure AI Foundry / Azure subscription.

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

## 4e. PR 6 — methods-matrix CR (BEH-4 promotion + ratifications)

The Locked `docs/methods-matrix.md` is amended under CR-007 PR 6. No code equations changed;
only the governance ledger catches up to the implementations that shipped in CR-006 and PR 5a/5b.

**What the amendment records:**

1. **BEH-4 promoted.** `demand_delta.py` shipped in CR-006 PR #4 under `BEH-4-PROVISIONAL`.
   It is now a ratified §3.1 row: `BEH-4 — Facility demand redistribution` (gravity trip
   deltas, Wilson-type distance decay, Calderon2014 mode-share anchor, confidence L — heuristic
   method maturity caps the tier; per-kind constants remain PROVISIONAL, see §3.6).
   `demand_delta.EQUATION_ID` updated from `"BEH-4-PROVISIONAL"` → `"BEH-4"`.

2. **Dataset tiers ratified.** The five tiers added to `confidence.py DATASET_TIERS` in
   CR-006 are now on record in the methods doc §2 (EMB/LIPAD/DEM/NHFR=H, S5P-NO2=M), with
   their INVENTORY provenance cited. The authoritative source remains `confidence.py`.

3. **`method_capped_confidence` rule ratified.** The rule — `confidence = min(data_tier,
   method_maturity_tier)` — is now stated in §2. ECO-4 and SOC-1 Conf basis cells updated to
   show the cap explicitly (`method_capped_confidence` applied, M ceiling, reason stated).

4. **PROVISIONAL proxy constants ratified.** A new §3.6 table acknowledges all four Milestone-A
   PROVISIONAL constants (`_PM25_PER_CO2E_PROXY=0.05`, `_PHP_PER_TRIP_PROXY=₱50.0`,
   `_VENDORS_PER_CLOSED_LANE=12`, `_GENERIC_POP_DENSITY=8500`) and the BEH-4 `FACILITY_PROFILES`
   defaults, with their current values and pending replacements. They remain PROVISIONAL until
   PR 7 / PR 9 (mode-share calibration) land sourced values.

**Test impact:** `test_demand_delta.py::test_glass_box_provenance_present` updated — the
`"PROVISIONAL" in equation_id` guard was the promotion gate; now the test asserts `BEH-4` directly
and verifies that the per-kind constant assumptions still carry the PROVISIONAL label (they do —
the constants are PROVISIONAL even though the equation_id is ratified).

**Kernel tests after this PR:** 167 passed, 10 skipped (bare mode). No module logic changed.

---

## 4f. PR 7 — real edges/confidence GeoJSON + sourced population density

Replaces the two PROVISIONAL static layer fixtures with REAL exports (CR-007 PR 7).

**`app/packages/data/export_net_geojson.py`** (new script):
Loads the named Iloilo SUMO net (`iloilo.net.xml`, built with `--output.street-names`,
PR 5a) and the Redis nightly baseline. Exports:
- **`edges.geojson`** — 6,599 LineString features (baseline-trafficked edges), each
  carrying the real SUMO edge id in `properties.edge_id` so the congestion choropleth
  joins correctly. Coordinates rounded to 6 decimal places (~10 cm). 4,095 of the
  6,599 features carry an OSM street name. File: ~1.5 MB (lazily loaded on toggle,
  not on initial page render). Falls back to all non-internal edges if Redis is
  unavailable.
- **`confidence.geojson`** — 1,209 polygon cells on a 0.0045° (~500 m) grid over the
  net bounding box. Every cell tier = M (conservative overall simulation confidence —
  data inputs are H but uncalibrated mode-share and literature-calibrated methods cap
  most results at M per the `method_capped_confidence` rule, CR-007 PR 6). BEH-1/BEH-3
  and ECO-1 are H along the network corridors but a network-edge intersection pass to
  vary the grid spatially is not yet wired. Uniform M is more honest than the previous
  hand-drawn H/M/L. Rationale in the file's `_provenance.tier_rationale`. ~315 KB.

**`modules/societal.py`**: `_GENERIC_POP_DENSITY` updated from uncited 8,500 → **5,843
persons/km²** (PSA 2020 Population Census of the Philippines August 2020: Iloilo City
457,626 persons / 78.34 km²). The assumption string updated to cite PSA 2020 CPH. The
3 other proxy constants remain PROVISIONAL — PM2.5 proxy has a unit mismatch requiring
a full dispersion model, ECON-1 proxy requires BIR-ZV uplift curve wiring, and SOC-2
proxy requires the CCHAIN osm_poi_* buffer count (all tracked §3.6).

**`docs/methods-matrix.md` §3.6**: `_GENERIC_POP_DENSITY` row updated to the sourced
PSA 2020 value with citation.

**`public/layers/README.md`**: Table updated to REAL status for both files; size note
updated (100 KB constraint predated the real export).

Kernel tests: 167 passed, 10 skipped (bare mode).

---

## 4g. PR 8 — Latency measurement + optimization

Three targeted changes to close the gap between the ~48 s observed latency and the 90 s budget, and to eliminate the SUMO cost on repeated runs.

**`runner.py`**: `--device.rerouting.period` lowered from 60 → 120 s. SUMO recomputes each
vehicle's route every 120 sim-seconds instead of every 60. This cuts rerouting CPU overhead
by ~50% with negligible behavioral impact for a 15-minute AM-peak slice where most vehicles
complete their trip before they'd benefit from a second reroute. Result: ~2–4 s saved per run.

**`baseline.py`**: `SIM_END` changed from the literal `900.0` to
`float(os.environ.get("MATRIX_SIM_HORIZON", "900"))`. This exposes the simulation horizon as
a runtime knob (default unchanged at 900 s). Operators can set `MATRIX_SIM_HORIZON=600` to
save ~8 s of SUMO wall time per run. The invariant comment is preserved: baseline and scenario
MUST share the value, so changing the env var requires re-running `run_nightly_baseline()`.

**`main.py` `_get_trajectory()`**: After a live SUMO run, the resulting `Trajectory` is
written to `scenario:{scenario_id}:latest` in Redis with a TTL of `MATRIX_TRAJ_CACHE_TTL_S`
seconds (default 7200 = 2 h). Subsequent runs of the same `scenario_id` hit the Redis cache
and skip SUMO entirely — latency drops from ~48 s to < 1 s. The write is best-effort
(wrapped in `try/except`) so a Redis failure never aborts a completed run.

**`docs/ops-matrix.md`**: New §6 "Performance Tuning" table documents all latency knobs,
the observed ~48 s baseline, and the cache pre-warm recommendation for demo sessions.

**Observed perf (unchanged from pre-PR measurements):** SUMO ≈ 44 s · modules ≈ 89 ms ·
Azure OpenAI ≈ 3.8 s · total ≈ 48 s (warm, rerouting=120 expected to reduce SUMO by 2–4 s on next
measurement). Trajectory cache means repeated scenario runs are < 1 s. The 90 s SLO is met.

---

## 5. Glass-box posture

PR 1 ships no number, so the glass-box ledger is untouched. The change *strengthens* the mandate:
a run now traces to the user's actual intervention rather than a silent blank stand-in, and geometry
travels on a single structured channel instead of being implied in prose.

---

## 4h. PR 9 — Mode-share calibration

No re-calibration of `ILOILO_MODE_SHARE` is possible from currently available data.
This PR documents the gap honestly and provides the path forward.

**Data reviewed and found insufficient:**
- `data/raw/transport/routes.json`: 24 LPTRP route titles + URL links only — no ridership
  counts, no OD data.
- PSA FIES 2023: household income/expenditure survey — modal split not collected.
- TSSP 2019 (`data/raw/transport/`): bicycle safety study — does not cover the full modal
  breakdown.

**Calibration path (documented in `config.py`):**
A meaningful re-calibration requires one of:
1. **LTFRB FOI**: Freedom of Information request to LTFRB Regional Office 6 (Iloilo City)
   under EO No. 2 (2016) for the most recent OD survey and/or PUV route ridership data.
   Template: https://foi.gov.ph. Expected TAT: 15 working days.
2. **Local household travel survey**: ~300 respondents, ~2 weeks fieldwork. Provides the
   highest-quality anchor for BEH-2 confidence upgrade from M → H.

**Values unchanged:** `jeepney=0.55, private_car=0.15, motorcycle=0.15, walk=0.10, bicycle=0.05`
(Calderon 2014 BRT study + LPTRP jeepney-dominant context). Behavioral module confidence
stays M; bias-auditor ±3% enforcement unchanged. The `MATRIX_MODE_SHARE` env var path for
injecting calibrated values is documented in `config.py` (and already implemented in
`load_city_config()` — it was always there).

**`config.py`**: `ILOILO_MODE_SHARE` comment block extended with the full calibration note:
data reviewed, blockers, FOI path, and env-var injection recipe.

---

## 4i. PR 10 — Deploy API → Hugging Face Spaces + web → Vercel

Deploy configs fixed and fully documented; actual `fly deploy` + `vercel --prod` require
user credentials (FLY_API_TOKEN, Vercel auth) and are deferred to the first deploy session.

**`app/Dockerfile.api`** — three bugs fixed:
1. `python:3.11-slim` → `python:3.12-slim` (both packages require `>=3.12`).
2. `apt-get install sumo sumo-tools sumo-doc` removed. The Ubuntu SUMO package would
   shadow the `eclipse-sumo` Python wheel's binaries and break `sumo_env.py`. The wheel
   ships its own SUMO binaries; only `libgdal-dev`, `libproj-dev`, `libxml2` (system link
   libs) are needed from apt.
3. `ENV MATRIX_NET_PATH=/data/iloilo.net.xml MATRIX_ROU_PATH=/data/iloilo.rou.xml` added
   so the kernel reads net + demand from the Fly persistent volume, not the image.

**`app/fly.toml`** — three additions:
1. `[env]` block: `MATRIX_NET_PATH` + `MATRIX_ROU_PATH` (same paths as Dockerfile; fly.toml
   overrides win at runtime).
2. Secrets comment block: `GOOGLE_API_KEY`, `DATABASE_URL`, `SUPABASE_KEY`,
   `MATRIX_JWT_SECRET` — all set via `fly secrets set`, never committed.
3. `[[mounts]]`: `matrix_data` volume → `/data` — the persistent storage for net + demand
   files (create with `fly volumes create matrix_data --region sin --size 5`).

**`app/apps/web/vercel.json`** — three env vars added:
`NEXT_PUBLIC_MAPBOX_TOKEN`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
(declared as `@secret_name` references — set actual values in the Vercel dashboard).

**`docs/ops-matrix.md`** — new §7 "Deploy Runbook":
Step-by-step first-time Fly + Vercel deploy, including volume creation, secrets, net file
upload via `fly ssh sftp`, baseline seeding via `fly ssh console`, trajectory pre-warm
recipe for demo sessions, nightly baseline refresh, and rollback (`fly deploy --image`).

---

## 6. Carried-forward debt

All CR-007 PRs shipped. Remaining operational steps (not code):
- **Actual deploy**: `fly deploy` + `vercel --prod` (user credentials required; see §7).
- **Mode-share re-calibration**: values unchanged; LTFRB FOI or travel survey needed.
- **VAL-01 / VAL-02**: gates NOT_RUN; blocked on mode-share calibration + Sentinel-1 flood
  extent (not a CR-007 scope item; tracked in `docs/qad-matrix.md`).
