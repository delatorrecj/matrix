# Change Record (CR)

**CR ID:** `CR-007`
**Project:** MATRIX — Multi-Agent Twin for Routing & Infrastructure eXchange
**Date:** 2026-06-16
**Author:** Carlos Jerico Dela Torre (Team ATLAN)
**Status:** In progress (PR 1 of the plan merged; PR 2–10 planned)
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
