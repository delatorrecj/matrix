# MATRIX — Definition of Terms

Working glossary for describing bugs/behavior precisely. Grounded in the **as-built code** in `app/`, not just the spec — where docs and code disagree, both are noted. Not part of the Locked FMD suite; update freely as terms drift.

## 1. Core architecture concepts

| Term | Definition |
|---|---|
| **Scenario** | A user-submitted proposed intervention: an NL query or a map-drop location/action. Created via `POST /scenario`; identified by `scenario_id`. |
| **new_facility** | A Scenario intervention type for a school, market, or terminal. Changes travel demand (BEH-4), not road geometry. Distinct from `lane_closure`. |
| **Intervention truth** | A new-facility query (e.g. a 3,000-seat school in Molo) is simulated as `new_facility` / BEH-4 demand, not as a construction lane closure. Map overlay/marker stay off; trips are not yet injected into SUMO (that is SUMO proof / issue #47). |
| **Orchestrator** | The Azure OpenAI (gpt-5.4) step that parses a Scenario into a structured simulation plan. Uses GraphRAG retrieval + gazetteer annotation as grounding. On a mis-parse it asks a clarification question rather than guessing (`AmbiguousScenarioError` on the frontend). |
| **Unified Simulation Kernel** | The SUMO (via TraCI) + persona pool + bias auditor pipeline. Runs **once per scenario**; its single output (`Trajectory`) feeds all five impact modules, so results can't contradict each other across dimensions. |
| **Persona pool** | The set of synthetic commuter archetypes (static literature-anchored by default, or LLM-generated when `MATRIX_PERSONA_LLM=1`) that drive SUMO agents. |
| **Bias auditor** | Reweights the persona pool's mode-share against the Iloilo ground-truth anchor (`ILOILO_MODE_SHARE`, Calderon 2014) when it drifts past `MODE_SHARE_TOLERANCE` (±3%). Produces a public, per-scenario `bias_audit_log` entry with `adjustment_factors` — never a silent correction. See `docs/methods-matrix.md` §4.1 for the worked example.
| **Trajectory** | The per-agent, per-tick dataset SUMO produces (location, mode, action). The one "simulated reality" all five modules score. |
| **Baseline** | The nightly, cached "as-is" simulation run a Scenario's delta is measured against (so a full cold SUMO run isn't needed per request). |
| **Glass box (PRD-F14)** | The rule that no number ships without `equation_id` + `input_dataset_ids` + a *computed* (never guessed) confidence, and it must resolve when clicked in the Inspect drawer. This is the top invariant — most "this number looks wrong / unexplained" bugs are glass-box violations. |
| **DimensionResult** | The concrete glass-box record type (`packages/kernel/matrix_kernel/results.py`). One is emitted per impact module per scenario. Fields: `dimension` (behavioral / social / economic / ecological / societal), `metric`, `equation_id`, `value`, `range` (a `[lo, hi]` earned-confidence interval, not a flat ±%), `unit`, `confidence` (`H`/`M`/`L`), `input_dataset_ids`, `references`, `assumptions`, `focus_geometry`. A `directional` property is `True` when `confidence == "L"` — such values render as directional-only, never false-precision. |
| **Equation ID** | The stable ID (e.g. `ECO-1`, `BEH-4`) tying a `DimensionResult` back to its exact formula in `docs/methods-matrix.md` §3. Use these IDs, not prose, when reporting "this metric is wrong" — it's the only unambiguous pointer to the formula. |
| **Confidence level** | `H` / `M` / `L`, computed (never asserted) per result. `L` results are "directional only." A result can be capped at `M` even when its inputs are `H`, if the *method* (not the data) is only literature-calibrated (`method_capped_confidence` — see ECO-4, SOC-1 in methods-matrix). |
| **Synthesis** | The LLM-generated plain-language brief. Structure (locked, CR-010): `HEADLINE → WHAT WE SIMULATED → KEY FINDINGS → RECOMMENDATION → KEY RISK`, English first, then a `=== HILIGAYNON ===` marker line, then the full Hiligaynon translation. The LLM narrates and cites; it never originates a number. |
| **Citation guard** | Validates that every numeric claim in the Synthesis brief carries a real `[EQUATION_ID]` bracket resolving to actual provenance; splits the brief into claim-sized units so a number can't "ride along" on a cited neighbor. Uncited numeric claims are blocked from rendering. |
| **Gazetteer** | A curated lookup mapping local/Hiligaynon place names (e.g. "tulay sa forbes") and Iloilo district names (e.g. "Molo") to OSM/SUMO ids *before* the LLM sees the query — the LLM never originates a GIS id. **Current entries are PROVISIONAL** (`gazetteer_iloilo.json`, flagged `"provisional": true`) — the ids are placeholders, not yet verified against the real OSM/SUMO net. `coordinates` on an entry may still drive the results-map camera when the `sumo_edge` is missing from the live net. |
| **Location of interest** | Camera/map-marker `[lon, lat]` for a scenario. **Not** `Scenario.geometry` (that is map-drop GeoJSON only) and **not** a TraCI edge id. `GET /scenario/{id}` returns it as `location_of_interest`: map-drop centroid if present, else gazetteer coordinates for the stored location name. The `/simulate` `EDGE_COUNTS` event may supply a SUMO edge midpoint when resolution was geometry/gazetteer-with-real-edge/keyword; fallback resolutions emit `null` (glass box). |
| **GraphRAG corpus** | A ChromaDB vector index of local context, ingested at API startup, that grounds the orchestrator/synthesis retrieval. |
| **Validation gates (VAL-01, VAL-02, …)** | Automated checks comparing simulated output to ground truth. `VAL-01` (corridor flow vs Calderon 2014) is a **published FAIL** (live NRMSE vs threshold ≤ 0.30 in `GET /validation` / `validation_report.json`). Corridor volumes are directional, not city-calibrated. `VAL-02` (flood closures vs Sentinel-1 extents) currently reports `NOT_RUN` — no real satellite extent is wired yet. |

## 2. The five impact modules

One kernel run, five parallel scorers — all in `packages/kernel/matrix_kernel/modules/`. Equation-id prefixes (from `docs/methods-matrix.md` §3):

| Module | Prefix | Computes | Confidence tier (typical) |
|---|---|---|---|
| **Behavioral** | `BEH-#` | Trip-count deltas per corridor (BEH-1), mode-share shift (BEH-2), peak volume/capacity saturation (BEH-3), gravity-model facility-demand redistribution (BEH-4) | L / directional for BEH-1/3 while VAL-01 is FAIL (uncalibrated demand); M for BEH-2; L for BEH-4 |
| **Ecological** | `ECO-#` | Transport CO₂e delta (ECO-1), air-quality/PM2.5 delta (ECO-2), green-cover loss (ECO-3), flood-exposure population delta (ECO-4) | H (ECO-1/3); M (ECO-2/4, method-capped) |
| **Social** | `SOC-#` | Equity-weighted access index (SOC-1), displacement/vendor-risk count (SOC-2), win/lose distributional split by income decile (SOC-3, PRD-F17) | M |
| **Economic** | `ECON-#` | Land-value delta within 1 km (ECON-1), footfall delta per zone (ECON-2), employment delta (ECON-3) | M |
| **Societal** | `SOCI-#` | Composite 0–100 score (SOCI-1) from heritage proximity (SOCI-2), health-exposure proxy (SOCI-3), walkability delta (SOCI-4) | M |

Note the module names in code/API payloads are lowercase (`ecological`, `societal`); MATRIX.md prose says "Ecological Impact" / "Societal Impact" — same concept, casing only.

**PROVISIONAL proxy constants** (methods-matrix §3.6) worth knowing when a number looks "off but not wrong": `_PM25_PER_CO2E_PROXY`, `_PHP_PER_TRIP_PROXY`, `_VENDORS_PER_CLOSED_LANE`, `_GENERIC_POP_DENSITY`, `FACILITY_PROFILES`, `_INJECTION_WEIGHT`, `_OCCUPANCY_BY_MODE` — these are declared, honest placeholders (visible in each result's `assumptions` field), not calibrated Iloilo measurements. A "this number seems arbitrary" bug may just be one of these, expected to be swapped out later.

## 3. WebSocket event sequence

Exact event-type strings (`apps/api/matrix_api/main.py`):

```
ACCEPTED → [QUEUED] → PLAYBACK_FRAME* → EDGE_COUNTS → DIMENSION_RESULT ×5 → SYNTHESIS → DONE
```

`ERROR` can fire at any point instead of/alongside the above (never a silent drop). `PLAYBACK_FRAME` repeats (animates the trip playback); `DIMENSION_RESULT` fires once per module (5 total). When reporting a stuck/broken run, name the **last event actually received** — that pinpoints which stage failed (kernel run, a specific module, or synthesis).

## 4. Frontend user flow (as built)

1. **Landing** (`/`, `app/page.tsx`) — marketing/about page, not part of the simulation flow.
2. **Cockpit** (`/app`, `app/page.tsx` under `app/app/`) — the primary entry point. User either:
   - types an NL query or picks a preset scenario, or
   - right-clicks the map → "Use this location" (`MapContextMenu`), or
   - opens the secondary **`/builder`** route (`ScenarioBuilder` component) for a structured, multi-step scenario composer.
3. **Submit** — `createScenario()` POSTs to `/scenario`. On success, navigates to `/scenario/{scenario_id}`. On failure:
   - `AmbiguousScenarioError` → shows an inline clarification prompt (the orchestrator asking for missing detail).
   - `ApiUnreachableError` → falls back to **Sample mode**, explicitly labeled illustrative-only, never presented as real output.
4. **Results/run view** (`/scenario/[id]`) — opens the WebSocket and drives UI through the event sequence above:
   - `RunStatusBanner` — current run state, including errors.
   - `InitializingState` — shown before the first `DIMENSION_RESULT`.
   - `PlaybackBar` + Deck.gl `TripsLayer` — animates trips from `PLAYBACK_FRAME`.
   - Map layers — congestion (`EDGE_COUNTS`), flood extent, confidence cells.
   - `IconNavRail` toggles the results panel between **`SummaryView`** (default, plain-language BLUF cards) and **`AnalyticsView`** (interpreted numeric detail per dimension).
   - Clicking any metric opens **`InspectDrawer`** — the glass-box provenance view (equation, inputs, confidence, assumptions).
   - **`ScenarioBrief`** — print-scoped, one-page exportable version of the synthesis brief.
   - **`BiasAuditLog`** / **`ValidationPanel`** — surface the audit trail and validation-gate status.

## 5. Known naming gaps to watch for

- The `/builder` structured-scenario flow is described in some docs as central, but in the running app it's a secondary path off the Cockpit — the primary flow is the NL/map-drop query on `/app`.
- `QUEUED` and `ERROR` are additive to whatever event list `docs/rfc-matrix-realtime-pipeline.md` documents — if that RFC only lists the original 6, treat the code's 8-event list above as current.
- Module `equation_id` prefixes are 4 letters for two modules (`ECON-`, `SOCI-`) and 3 for the others (`BEH-`, `ECO-`, `SOC-`) — easy to mistype when citing an ID in a bug report; copy it from the Inspect drawer rather than guessing.
