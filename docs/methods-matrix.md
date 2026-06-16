# MATRIX — Methods & Traceability Registry (Glass-Box Ledger)

**Project:** MATRIX · **Version:** 0.1 · **Date:** 2026-06-02 · **Owner:** Team ATLAN · **Status:** Locked — 2026-06-03 (Phase 0; changes require a Change Record) · **Amended:** 2026-06-17 by CR-007 PR 6 (BEH-4 promotion, dataset-tier ratification, method-cap rule, proxy constants — see §2 addenda, §3.1 BEH-4, §3.6)
**Backs:** [prd-matrix.md](prd-matrix.md) `PRD-F14` · [sdd-matrix.md](sdd-matrix.md) · data IDs from [../data/INVENTORY.md](../data/INVENTORY.md)

> **MATRIX is a glass box, not a black box.** Every number it outputs is **derived by an explicit equation from named data**, carries a **confidence tier computed by a rule**, and is **reproducible and citable**. If a number cannot be traced through this ledger, it does not ship. The LLM (Gemini) *orchestrates and narrates with citations* — it **never originates a number**; all scores come from the deterministic kernel and the equations below.

---

## 1. The Glass-Box Guarantee

Every output element MATRIX renders must be backed as follows. The "Inspect" UI (`PRD-F14`) exposes this on click.

| Output element | Backed by | Mechanism | Lives in |
|---|---|---|---|
| Dimension score (e.g. CO₂e Δ) | explicit equation + input numbers | §3 Equation Registry | `dimension_results.equation_id` |
| Each input value | dataset ID + vintage + license + confidence | data lineage | [INVENTORY](../data/INVENTORY.md) → `datasets` table |
| Range / uncertainty | ensemble over uncertain assumptions | §5 sensitivity (`PRD-F15`) | `dimension_results.range_*` |
| Confidence tag (H/M/L) | derivation rubric | §2 rubric | `dimension_results.confidence` |
| Narrative claim (LLM) | inline citation → number + source | §4 model cards (citation guard) | synthesis output |
| Persona mix | mode-share vs ground-truth anchor | bias auditor | `bias_audit_log` |
| Orchestration decision | retrieved evidence + params + seed | §4 decision trace | `run_trace` |
| The whole run | params + seed + data/model versions | §6 reproducibility | `simulation_runs` |

### Provenance contract (every emitted value carries)

```json
{
  "value": 11.2, "range": [8.4, 14.1], "unit": "ktCO2e/yr",
  "equation_id": "ECO-1", "input_dataset_ids": ["CCHAIN", "OSM-ILO", "WHO-EMEP"],
  "assumptions": ["mode_share=Iloilo-2014", "EF=WHO-EMEP-2023"],
  "confidence": "H", "references": ["Calderon2014", "WHO-EMEP"]
}
```

---

## 2. Confidence Derivation Rubric (H/M/L is computed, not guessed)

`confidence = f(data vintage, spatial coverage, method maturity, validation status)` — worst factor caps the tier.

| Tier | Data vintage | Coverage | Method | Validation |
|---|---|---|---|---|
| **High** | ≤ 2 yr (or live) | full Iloilo (180 brgy / network) | established / physics-based | validated or directly measured |
| **Medium** | ≤ ~10 yr or proxy | partial / regional proxy | literature-calibrated | indirect |
| **Low → "directional only"** | sparse / missing | gaps | heuristic | unvalidated |

A dimension flagged **Low** renders as *directional only* (`PRD-F5`) — never as a precise number.

**Method-maturity cap rule** (`method_capped_confidence`, ratified CR-007 PR 6): where an equation's method maturity is weaker than its input-data tier, confidence is capped at the method tier — not the data tier. `confidence = min(data_tier, method_maturity_tier)`. Applied explicitly to ECO-4 (exposure-redistribution method literature-calibrated → M despite H hazard inputs) and SOC-1 (equity-weighted access method literature-calibrated → M despite H registry inputs).

**Dataset tier ledger** (authoritative: `packages/kernel/matrix_kernel/confidence.py` `DATASET_TIERS`; tiers below ratified CR-007 PR 6 from [data/INVENTORY.md](../data/INVENTORY.md)):

| Dataset | Tier | Rationale |
|---|---|---|
| EMB (DENR-EMB air-quality stations) | H | Current Iloilo ground readings; INVENTORY Conf = H |
| LIPAD (PhilLiDAR/LiPAD DTM + flood extents) | H | Full Iloilo coverage; INVENTORY Conf = H |
| DEM (Copernicus GLO-30) | H | Global sub-30 m; INVENTORY Conf = H |
| NHFR (DOH National Health Facility Registry) | H | Live open-gov, Iloilo-complete; INVENTORY Conf = H |
| S5P-NO2 (Sentinel-5P NO₂ column) | M | Satellite proxy — regional column, not ground PM₂.5; INVENTORY Conf = M |

---

## 3. Equation Registry (per dimension)

Inputs reference [INVENTORY](../data/INVENTORY.md) IDs. Equations are versioned; changing one is a Change Record.

### 3.1 Behavioral
| ID | Metric | Equation | Inputs | Unit | Conf basis |
|---|---|---|---|---|---|
| BEH-1 | Δ trips/day per corridor | `ΔT_c = Σ_a 1[a traverses c]_scenario − _baseline` (counted from SUMO trajectories) | OSM-ILO, OVERTURE, persona pool | trips/day | H (network physics) |
| BEH-2 | Mode-share shift | `Δm_k = (n_k^sc − n_k^base)/N`, constrained to ground-truth anchor ±3% | persona pool, Calderon2014, CCHAIN | %-points | M (literature calibration) |
| BEH-3 | Peak saturation (V/C) | `VC_l = volume_l / capacity_l` per link | SUMO net, OSM-ILO | ratio | H |
| BEH-4 | Facility demand redistribution | Gravity trip deltas: `n_total = capacity × trips_per_capacity`; origins sampled from a distance-decay catchment (Wilson-type: `w(d) ∝ d^-β`); `n_redirected = round(n_total × redirected_fraction)` transferred from baseline demand, remainder induced; mode hints drawn from the Iloilo mode-share anchor | Calderon2014 (mode-share anchor) | trips/AM-window | L (heuristic / uncalibrated gravity model — method caps tier; per-kind and per-scenario constants PROVISIONAL until survey calibration; see §3.6; CR-006 PR #4, promoted CR-007 PR 6) |

### 3.2 Ecological
| ID | Metric | Equation | Inputs | Unit | Conf basis |
|---|---|---|---|---|---|
| ECO-1 | Transport CO₂e Δ | `ΔCO2e = Σ_k (VKT_k · EF_k)_sc − _base` | SUMO VKT per mode k, WHO/EMEP EF | ktCO₂e/yr | H |
| ECO-2 | Air-quality delta | `ΔPM2.5 ∝ Δemissions` dispersed, calibrated to station readings | EMB/OPENAQ, S5P-NO2 | µg/m³ at station | M |
| ECO-3 | Green-cover loss | `Σ area(class_change)` vs land-cover baseline | CCHAIN `esa_worldcover`, WORLDCOVER, Sentinel-2 | hectares | H |
| ECO-4 | Flood-exposure Δ | project footprint × hazard layer → `Δ pop_exposed` | CCHAIN `project_noah_hazards`, LIPAD, DEM | persons | M (`method_capped_confidence`: hazard inputs CCHAIN/LIPAD/DEM are H, but population-exposure redistribution method is literature-calibrated → caps at M; CR-007 PR 6) |

### 3.3 Social
| ID | Metric | Equation | Inputs | Unit | Conf basis |
|---|---|---|---|---|---|
| SOC-1 | Equity-weighted access | `A = Σ_b w_b · Δaccess_b`, `w_b = inverse income decile` | CCHAIN RWI + health isochrones, NHFR | index | M (`method_capped_confidence`: inputs CCHAIN/NHFR are H, but equity-weighted access method is literature-calibrated → caps at M; CR-007 PR 6) |
| SOC-2 | Displacement risk count | informal workers/vendors within impact buffer | CCHAIN `osm_poi_*`, OSM-ILO | count | M |
| SOC-3 | Distributional split (`PRD-F17`) | win/lose by income decile & barangay | CCHAIN RWI, WorldPop | per-decile | M |

### 3.4 Economic
| ID | Metric | Equation | Inputs | Unit | Conf basis |
|---|---|---|---|---|---|
| ECON-1 | Land-value Δ (≤1 km) | `ΔLV = LV_base · uplift(Δaccessibility)` (range) | **BIR-ZV** (✅ manual XLS), CCHAIN RWI | PHP range | M |
| ECON-2 | Footfall Δ per zone | dwell/pass counts from trajectories | persona pool, OVERTURE places | visits/day | M |
| ECON-3 | Employment Δ | `direct + indirect(multiplier) − displaced` | PSA-ASPBI/OpenStat, ADB/NEDA multiplier | jobs | M |

### 3.5 Societal
| ID | Metric | Equation | Inputs | Unit | Conf basis |
|---|---|---|---|---|---|
| SOCI-1 | Societal composite | `Σ w_i · subscore_i` (heritage, health, walk, noise) | below | 0–100 | M |
| SOCI-2 | Heritage proximity | distance decay to nearest declared site | NHCP, OSM heritage (117) | score | M |
| SOCI-3 | Health-exposure proxy | `PM2.5 × population density` | ECO-2, WorldPop | index | M |
| SOCI-4 | Walkability Δ | bike/sidewalk coverage + Macalalag factors | OSM-ILO, TSSP-2019 bike | score | M |

### 3.6 PROVISIONAL Proxy Constants (Milestone A; ratified CR-007 PR 6)

These named constants are the current Milestone-A stand-ins backing the equations above. They are
**PROVISIONAL and uncalibrated** — declared in each result's `assumptions` field (Inspect-resolvable;
PRD-F14) so users see them on click. Replacing them with sourced values is tracked under CR-007 PR 7
(depends on PR 6 ratification) and PR 9 (mode-share calibration). None of these values is backed by
a specific Iloilo measurement; they are order-of-magnitude placeholders declared honestly as such.

| Constant | Location | Current value | Backs | Pending replacement |
|---|---|---|---|---|
| `_PM25_PER_CO2E_PROXY` | `modules/ecological.py` | 0.05 | ECO-2 air-quality delta | Calibrated dispersion-to-station coefficient (EMB readings vs modelled emissions) |
| `_PHP_PER_TRIP_PROXY` | `modules/economic.py` | ₱50.0 / trip | ECON-1 land-value Δ | BIR-ZV zonal schedule uplift curve (`ΔLV = LV_base × uplift(Δaccessibility)`) |
| `_VENDORS_PER_CLOSED_LANE` | `modules/social.py` | 12 vendors | SOC-2 displacement risk | CCHAIN `osm_poi_*` impact-buffer count |
| `_GENERIC_POP_DENSITY` | `modules/societal.py` | 8,500 persons/km² | SOCI-3 health-exposure proxy | Per-zone WorldPop density wired into the kernel |
| `FACILITY_PROFILES` | `demand_delta.py` | per-kind `trips_per_capacity`, `redirected_fraction`, `catchment_radius_m` | BEH-4 (all kinds) | Local travel-survey calibration per facility kind |

---

## 4. Model / Method Cards

Each non-trivial component documents what it does and how its output is made traceable.

| Component | Purpose | Inputs → Output | Grounding | Known limits / failure mode | Traceability hook |
|---|---|---|---|---|---|
| **Orchestrator** (Gemini 3.1 Pro) | NL/map → structured sim plan | query → JSON plan | GraphRAG retrieval | mis-parse → clarification prompt (never guess) | `run_trace`: prompt, retrieved chunks, params |
| **Persona generator** (Flash-Lite) | commuter persona pool | archetypes → agents | mode-share anchor | LLM bias → bias auditor reweights | `bias_audit_log` |
| **Bias auditor** (Python) | enforce mode-share fairness | persona batch → pass/reweight | Iloilo ground truth (Calderon2014) | anchor stale → flagged | public `bias_audit_log` |
| **SUMO kernel** (TraCI) | physical trajectories | net + agents → per-tick dataset | deterministic physics | net gaps → confidence floor | seed + net version in `simulation_runs` |
| **XGBoost baseline** | corridor volume forecast | history → baseline | trained on open series | extrapolation risk | model version stamped |
| **Synthesis** (Gemini 3.1 Pro) | narratives + report | scores → prose | **must cite numbers + sources**; "unknown" allowed | hallucination → citation guard rejects uncited claims | citations resolve to equation_id + dataset_ids |

**Citation guard:** synthesis narrative claims that assert a number must reference an `equation_id` and its `input_dataset_ids`; uncited quantitative claims are blocked from render.

---

## 5. Uncertainty & Sensitivity (earned confidence — `PRD-F15`)

- **Ensemble:** vary the uncertain assumptions (mode share, multipliers, emission factors) over plausible bounds → output **distribution**, not a point. `range_low/high` = e.g. 10th–90th percentile.
- **Sensitivity table** per result: which assumption moves the number most (one-at-a-time elasticity). Surfaced in the Inspect panel so a planner sees *what the answer depends on*.

---

## 6. Validation Ledger (checked against reality)

| Check | Method | Target | Status |
|---|---|---|---|
| Behavioral corridor | RMSE vs **Calderon 2014** BRT model on one Iloilo corridor | report RMSE | planned (QAD) |
| Flood redistribution | back-test vs **2024 Iloilo flood** extent (Sentinel-1 GFM) | spatial overlap (IoU) | planned (QAD) |
| Mode-share anchor | generated vs ground-truth ±3% | within band | enforced (bias auditor) |

---

## 7. Reproducibility

A run is reproducible: `simulation_runs` records the scenario params, **random seed**, **dataset vintages**, and **model versions**. Same inputs → same outputs. Methodology + notebooks published (open methodology — MATRIX.md §7.4).

---

## 8. Why MATRIX is structurally less of a black box

- **The numbers are not the LLM's.** They are computed by §3 equations on §INVENTORY data. The LLM plans and narrates, and even its narration must cite (§4).
- **vs live-IoT simulators:** their sensor coverage gaps are invisible and unstated; MATRIX makes every gap an explicit confidence tier (§2).
- **vs pure-LLM tools:** those generate the answer; MATRIX generates only *behavioral inputs* (personas, audited against ground truth) and computes outputs deterministically.

> Glass-box rule of thumb for the team: *if you put a number on screen, you must be able to click it and see its equation, its data, and its confidence.* If you can't, it isn't ready.
