# CR-008 — ASEAN Judges' Feedback Remediation (Implementation Plan)

**Change Record ID:** CR-008
**Status:** Applied (merged to `main`; all 9 asks implemented — 2026-06-22)
**Date opened:** 2026-06-17
**Branch:** `dev` (cut from `main` @ `2dac893`; per-item feature branches below)
**Trigger:** ASEAN AI Hackathon 2026 judges' written feedback (9 items, verbatim in §1)
**Owner:** Carlos Jerico Dela Torre (Team ATLAN — solo-dev mode)
**Supersedes/extends:** follows [CR-007](cr-007-close-the-loop.md) (close-the-loop, complete). No conflict — CR-008 is additive elaboration + traceability hardening.

> **What this document is.** A detailed, file-level implementation plan that turns each of the nine judge asks into concrete code + documentation tasks with acceptance criteria, doc homes, and a phased execution order. It is the single coordination surface for the feedback round. As each item lands, this CR's checklist (§6) and the [index](index.md) change log are updated — *docs are updated along the way, not at the end*.

---

## 0. Framing — the good news

Eight of the nine asks map **1:1 onto features the PRD already commits to and the kernel already implements** — the work is mostly to *operationalize, surface, and document* what exists, not to invent. Only the **CPDO feedback loop (#6)** is a genuinely new capability. The table below is the executive map; §2 is the per-item detail.

| # | Judge ask (short) | PRD feature | Primary code today | Doc home (canonical) | State | Type |
|---|---|---|---|---|---|---|
| 1 | Ground-truth comparison (SUMO vs Iloilo history) | PRD-F18 | [`validation.py`](../app/packages/kernel/matrix_kernel/validation.py), `validation_fixtures/calderon2014_corridor.json` | [qad-matrix §8](qad-matrix.md) + [methods §6](methods-matrix.md) | VAL-01 computed but **NOT_RUN/withheld** (uncalibrated demand) | doc + code |
| 2 | Informal sector (tricycle drivers, street vendors) | PRD-F17, SOC-2 | [`personas.py`](../app/packages/kernel/matrix_kernel/personas.py), [`modules/social.py`](../app/packages/kernel/matrix_kernel/modules/social.py), [`modules/economic.py`](../app/packages/kernel/matrix_kernel/modules/economic.py) | [methods §3.3/§3.4](methods-matrix.md) | mode-share has no tricycle archetype; vendors only via `_VENDORS_PER_CLOSED_LANE` proxy | doc + code |
| 3 | Bias Auditor worked example + reweight math | PRD-F6 | [`bias_auditor.py`](../app/packages/kernel/matrix_kernel/bias_auditor.py), [`personas.py`](../app/packages/kernel/matrix_kernel/personas.py) | [methods §4](methods-matrix.md) | flags `reweighted: bool` but **does not perform** the reweight | doc + code |
| 4 | Low-confidence trigger + user alert | PRD-F5, F15 | [`confidence.py`](../app/packages/kernel/matrix_kernel/confidence.py), [`results.py`](../app/packages/kernel/matrix_kernel/results.py), `InspectDrawer.tsx` | [methods §2](methods-matrix.md) + [dsd-matrix](dsd-matrix.md) | rubric computes H/M/L; "what triggers L" + UI alert not consolidated | doc (+ small UI) |
| 5 | Extreme events (monsoon flood, sudden closure) | PRD-F19, ECO-4 | `full_closure` in [`scenario.py`](../app/packages/kernel/matrix_kernel/scenario.py)/[`orchestrator.py`](../app/packages/kernel/matrix_kernel/orchestrator.py), `floodLayer.ts`, `flood2024_closures.json` | [methods §3.2](methods-matrix.md) + [prd-matrix](prd-matrix.md) | mechanism exists; no consolidated "resilience" narrative/test | doc + code |
| 6 | CPDO iterative-feedback mechanism | **none → new PRD-F20** | — (no endpoint, no schema) | [prd-matrix §3](prd-matrix.md) + [ops-matrix](ops-matrix.md) + [sdd-matrix](sdd-matrix.md) | **does not exist** | new feature |
| 7 | Hiligaynon colloquial term → GIS node | PRD-F11 | [`orchestrator.py`](../app/packages/kernel/matrix_kernel/orchestrator.py), [`graphrag.py`](../app/packages/kernel/matrix_kernel/graphrag.py), [`geometry.py`](../app/packages/kernel/matrix_kernel/geometry.py) | [sdd-matrix](sdd-matrix.md) + [methods §4](methods-matrix.md) | **no gazetteer / alias map** anywhere | doc + code |
| 8 | Module → data-source traceability table | PRD-F14 | inputs already in [methods §3](methods-matrix.md) per-equation | [methods Appendix](methods-matrix.md) (new) | consolidated appendix not yet present | doc only |
| 9 | RAG setup/implementation elaboration | PRD-F9 | [`graphrag.py`](../app/packages/kernel/matrix_kernel/graphrag.py) | [sdd-matrix](sdd-matrix.md) + [methods §4](methods-matrix.md) | thin Chroma wrapper; **no ingestion/build script**; retrieve returns [] until built | doc + code |

**Glass-box discipline applies to every item.** No new number ships without `equation_id` + `input_dataset_ids` + a *computed* confidence that resolves under the Inspect drawer (PRD-F14). The `glass-box-auditor` and `eval-test-runner` agents must both PASS before any item merges to `main`.

---

## 1. Judges' feedback (verbatim)

> 1. Include a **"Ground-Truth Comparison"** section showing how the SUMO simulation results align with historical traffic data from Iloilo City to prove the model's predictive reliability.
> 2. Elaborate on the **"vulnerable informal sector"** modeling; explain how the agent-based simulation specifically accounts for the unique routing and economic behaviors of tricycle drivers and street vendors.
> 3. Provide a specific example of the **Bias Auditor in action** — describe a scenario where it detected a middle-class bias and explain the mathematical adjustment made to rebalance the persona pool.
> 4. Add a section on how the system handles **"Low Confidence"** scenarios; define what triggers a low-confidence flag and how the user is alerted to the potential margin of error.
> 5. Explicitly detail how MATRIX handles **extreme events** (e.g., severe monsoon flooding or sudden road closures) to demonstrate the system's resilience beyond standard planning queries.
> 6. Propose a clear mechanism for how **City Planning and Development Office (CPDO) staff can provide iterative feedback** on the AI-generated reports to refine the model's future outputs.
> 7. Provide a concrete example of a **Hiligaynon query** and show how the system successfully maps a colloquial term to a specific GIS node without losing semantic integrity.
> 8. In your Appendices, include a **table mapping each simulation module** (Behavioral, Social, Economic, etc.) **to its specific data source** to further reinforce your commitment to data traceability.
> 9. Elaborating on how **RAG (setup, implementation)** supports the LLM's answer would strengthen the project.

---

## 2. Per-item plan

Each item: **Ask → Current state (file-accurate) → Gap → Tasks → Acceptance criteria.**

### Item 8 — Module → data-source traceability table *(do first: pure-doc, zero risk, highest traceability signal)*

- **Current state.** [methods §3](methods-matrix.md) already carries the `Inputs` column per equation (BEH-1 → OSM-ILO/OVERTURE/persona pool, etc.) and a `DATASET_TIERS` ledger in [`confidence.py`](../app/packages/kernel/matrix_kernel/confidence.py). The data exists but is *scattered across equations*; judges want one consolidated module→source matrix.
- **Gap.** No single appendix that a reader (or judge) can scan to see Module → datasets → INVENTORY id → confidence tier.
- **Tasks.**
  1. Add **methods-matrix Appendix A — "Module ⇄ Data-Source Traceability Matrix"**: rows = the 5 modules (+ kernel/persona layer); columns = equations consumed, INVENTORY dataset ids, dataset tier (from `DATASET_TIERS`), and the live link to [data/INVENTORY.md](../data/INVENTORY.md).
  2. Cross-link from [MATRIX.md](../MATRIX.md) appendices and [prd-matrix.md](prd-matrix.md) PRD-F14.
  3. Generate the table *from* `DATASET_TIERS` + §3 so it cannot drift (note the source of truth inline).
- **Acceptance.** Every dataset cited in any §3 equation appears in the appendix with a tier and an INVENTORY link; no dataset id appears that is not in `DATASET_TIERS`.
- **Locked-doc edit:** methods-matrix (Locked) — additive appendix, logged under CR-008.

### Item 1 — Ground-Truth Comparison

- **Current state.** [`validation.py`](../app/packages/kernel/matrix_kernel/validation.py) implements VAL-01 (RMSE/NRMSE vs Calderon 2014 Ungka–Iloilo corridors, threshold NRMSE ≤ 0.30, FHWA-sourced) and VAL-02 (2024 flood IoU). **VAL-01 currently reports `NOT_RUN` (WITHHELD)** because uncalibrated synthetic demand puts the corridor passenger-flow proxy ~an order of magnitude above the Calderon maxima — an honest withhold, not a pass.
- **Gap.** (a) No reader-facing "Ground-Truth Comparison" narrative tying the method to *Iloilo* history; (b) VAL-01 is withheld pending mode-share calibration (P1-6 / CR-007 PR 9 documented the FOI path). Judges want to *see the comparison*, even if bounded.
- **Tasks.**
  1. **qad-matrix §8** — add a "Ground-Truth Comparison" subsection: the two back-tests, their fixtures + provenance, thresholds + provenance, and the **honest current status** (VAL-02 PROVISIONAL until Sentinel-1 GFM; VAL-01 withheld until demand calibration — show *why*, with the proxy/unit reconciliation gap named).
  2. Wire `build_validation_report.py` to emit the corridor pair (observed vs simulated vs Δ) into a small **comparison table artifact** the UI/report can render even while the gate is `NOT_RUN` (a transparent "directional alignment" view, clearly labelled not-yet-validated).
  3. **methods §6** — promote the Validation Ledger row statuses to point at the computed gate + the withhold reason (replace "planned (QAD)" with the real state).
  4. Stretch (only if mode-share calibration lands via Item 2/CR-007 FOI): re-run VAL-01 and record the RMSE.
- **Acceptance.** A judge can read qad §8 and see, per corridor, observed (Calderon) vs MATRIX value, the metric, the threshold + its citation, and a truthful PASS/FAIL/WITHHELD with the reason. No fabricated pass.
- **Locked-doc edit:** methods-matrix (§6 status) — logged under CR-008.

### Item 2 — Vulnerable informal sector (tricycle drivers + street vendors)

- **Current state.** [`personas.py`](../app/packages/kernel/matrix_kernel/personas.py) samples `mode`/`income_decile`/`trip_purpose` from the Iloilo mode-share anchor; **`tricycle` is not a distinct archetype** today (jeepney-dominant anchor). Vendors enter only through **SOC-2** displacement (`_VENDORS_PER_CLOSED_LANE = 12`, PROVISIONAL) in [`modules/social.py`](../app/packages/kernel/matrix_kernel/modules/social.py).
- **Gap.** No explicit account of (i) tricycle **routing** behavior (short-haul, feeder/last-mile, barangay-bounded, terminal-anchored) or (ii) street-vendor **economic** behavior (footfall-dependent revenue, fixed pitch, displacement loss).
- **Tasks.**
  1. **methods §3.3/§3.4 elaboration** — document the informal-sector model: tricycle as a feeder archetype with bounded catchment + terminal anchoring; vendor revenue as a footfall function (ECON-2 dwell/pass) and displacement as SOC-2 buffer count tied to RWI (PRD-F17 equity weighting).
  2. **Code:** add a `tricycle` mode/archetype path in persona generation gated behind the city config's mode-share anchor (only activates when the anchor includes a tricycle share — keep city-agnostic), and a vendor-exposure helper that ties SOC-2 to ECON-2 footfall instead of the flat constant. Keep both **PROVISIONAL** + Inspect-resolvable until survey-calibrated.
  3. **READINESS / INVENTORY note** — record the informal-sector data confidence floor (Medium; CCHAIN `osm_poi_*` + LPTRP terminals) honestly.
- **Acceptance.** methods §3.3/§3.4 explain tricycle routing + vendor economics with equation ids and inputs; any new number is glass-box (equation + datasets + computed confidence) and declares its PROVISIONAL constants.
- **Locked-doc edit:** methods-matrix (§3.3/§3.4) — logged under CR-008.

### Item 3 — Bias Auditor in action (worked example + reweight math)

- **Current state.** [`bias_auditor.py`](../app/packages/kernel/matrix_kernel/bias_auditor.py) `audit_personas()` computes `max_delta` and sets `reweighted: bool` at the ±3% tolerance, and `persist_audit()` appends to the public `bias_audit_log`. **It flags but does not actually rebalance** — there is no reweight function.
- **Gap.** Judges want (a) a concrete *middle-class bias* scenario and (b) the *mathematical adjustment*. We need to both **implement the reweight** and **document the worked example**.
- **Tasks.**
  1. **Code:** add `reweight_pool(observed, target)` → per-mode multiplicative correction factor `f_k = target_k / observed_k`, applied as importance weights / stratified resampling so the corrected pool's `observed_mode_share` lands within ±3%. Emit the factors into the audit entry (extend `BiasAuditEntry` with `adjustment_factors`) so the math is in the public log, Inspect-resolvable.
  2. **methods §4 (bias auditor card) + new worked example** — the canonical scenario: Flash-Lite over-generates higher-income car/private personas (e.g. car share observed 0.18 vs anchor 0.07 → +11pts, beyond ±3%) → reweight factors per mode → resampled pool back within band → audit-log row. Show the before/after table and the factor formula.
  3. **Test:** unit test asserting a deliberately skewed pool is reweighted back inside MODE_SHARE_TOLERANCE.
- **Acceptance.** Given a skewed pool, `reweight_pool` returns a pool within ±3% of the anchor; the audit entry records the per-mode factors; methods §4 shows the worked middle-class-bias example with numbers that match the code.
- **Locked-doc edit:** methods-matrix (§4 card + example) — logged under CR-008.

### Item 4 — Low-confidence handling (trigger + user alert)

- **Current state.** [`confidence.py`](../app/packages/kernel/matrix_kernel/confidence.py) computes H/M/L via the worst-factor rule + `method_capped_confidence`; [methods §2](methods-matrix.md) says a **Low** dimension renders *directional only* (PRD-F5). `earned_confidence_interval` yields the 10th–90th range (PRD-F15). UI surfaces confidence in `InspectDrawer.tsx`.
- **Gap.** No single "Low-Confidence Protocol" that *defines the triggers* (sparse/missing data, >10yr vintage, heuristic/uncalibrated method, unvalidated, unknown dataset id → L) and *specifies the alert* (directional-only rendering, range banners, the Inspect "why this is Low" line).
- **Tasks.**
  1. **methods §2 subsection "Low-Confidence Protocol"** — enumerate the exact triggers (map each to the rubric row + the `DATASET_TIERS` default-to-L rule for unprovenanced ids) and the consequence (directional-only, range not point, explicit margin).
  2. **dsd-matrix** — specify the UI alert: a Low badge + "directional only" label + a one-line *trigger reason* surfaced from the result's provenance (which factor capped it). Small `InspectDrawer` enhancement to print the capping factor.
  3. **Test:** confirm a result built on an unknown/Low dataset id is flagged Low and carries a human-readable trigger reason.
- **Acceptance.** A reader can name, from methods §2, every condition that yields Low and exactly what the user sees; the UI shows a Low result as directional-only with its trigger reason.
- **Locked-doc edit:** methods-matrix (§2) — logged under CR-008.

### Item 5 — Extreme events / resilience (monsoon flood, sudden closure)

- **Current state.** `full_closure` intervention exists end-to-end ([`scenario.py`](../app/packages/kernel/matrix_kernel/scenario.py) + [`orchestrator.py`](../app/packages/kernel/matrix_kernel/orchestrator.py)); ECO-4 flood-exposure equation + `flood2024_closures.json` fixture + `floodLayer.ts` map layer exist; PRD-F19 commits "Project + 25-year flood" compound shocks.
- **Gap.** No consolidated "resilience / extreme-events" narrative showing the path: flood hazard layer → road-segment closures → demand redistribution → five-module re-score → confidence treatment under shock.
- **Tasks.**
  1. **New prd/methods cross-section "Extreme-Event Resilience"** — document (a) sudden road closure via `full_closure` + drawn geometry; (b) monsoon flooding via CCHAIN `project_noah_hazards`/LIPAD hazard → closed segments → ECO-4 exposure + BEH demand redistribution; (c) compound shock (project + N-year flood, PRD-F19); (d) how confidence behaves under extrapolation (caps to M/L, directional).
  2. **Code:** a thin `flood_scenario` helper that converts a hazard extent (GeoJSON) into the `simulated_closed` segment set already consumed by `validate_flood` (closes the loop between Item 1 VAL-02 and Item 5).
  3. Add a QAD scenario row exercising a full-closure / flood run end-to-end.
- **Acceptance.** A judge can trace a monsoon-flood query from NL → hazard layer → closures → re-scored five dimensions with confidence, and a road-closure query likewise; VAL-02 can be fed by the helper.
- **Locked-doc edit:** prd (Locked) — additive resilience subsection under PRD-F19; methods §3.2 link. Logged under CR-008.

### Item 6 — CPDO iterative-feedback mechanism *(new capability — PRD-F20)*

- **Current state.** **Nothing exists.** No feedback endpoint, schema, or UI affordance. Reports are one-way (synthesis → PDF).
- **Gap.** Judges want a *clear mechanism* for CPDO staff to give iterative feedback that *refines future outputs*.
- **Tasks.**
  1. **PRD — add PRD-F20 "Planner feedback loop"** (Should-Have): on any AI report, CPDO staff can (i) rate/flag a dimension result as plausible/implausible, (ii) attach a correction or a known ground-truth value, (iii) annotate assumptions. Captured against `run_id` + `equation_id`.
  2. **SDD + API:** `POST /feedback` (run_id, equation_id, verdict, note, optional observed_value) → new `planner_feedback` table (Postgres, alongside `bias_audit_log`/`simulation_runs`). Read-back `GET /feedback?run_id=`.
  3. **Refinement path (design, not full ML):** document how captured feedback feeds back — (a) observed_value submissions become **candidate validation fixtures** (feed Item 1 gates); (b) flagged assumptions raise a methods-ledger review; (c) repeated implausibility on a dimension lowers its advertised confidence floor. Keep human-in-the-loop; no silent auto-tuning (glass-box).
  4. **ops-matrix** — the feedback triage runbook (who reviews, cadence, how a fixture is promoted).
  5. **UI (frontend-3d-builder):** a lightweight feedback affordance in the Inspect drawer / report.
- **Acceptance.** A documented, end-to-end mechanism (UI → API → table → triage → fixture/confidence refinement) with PRD-F20, an SDD sequence, and an OPS runbook. MVP endpoint + table implemented and tested; full ML refinement explicitly scoped as future.
- **Locked-doc edit:** prd (Locked) — new PRD-F20; sdd (Locked) — feedback seam. Logged under CR-008.

### Item 7 — Hiligaynon query → GIS node (colloquial term mapping)

- **Current state.** [`orchestrator.py`](../app/packages/kernel/matrix_kernel/orchestrator.py) extracts a free-text `location`; [`geometry.py`](../app/packages/kernel/matrix_kernel/geometry.py) resolves geometry→edges; [`graphrag.py`](../app/packages/kernel/matrix_kernel/graphrag.py) can ground retrieval. **No gazetteer / alias map exists** (confirmed: zero hits for gazetteer/colloquial/hiligaynon/alias in `app/`). PRD-F11 commits Hiligaynon prompting.
- **Gap.** No mechanism to map a colloquial Hiligaynon term (e.g. *"tulay"* = bridge, *"banwa"*, *"merkado"* = Iloilo Central Market, *"plasa"*, *"liko sa…"*) to a specific OSM/GIS node, and no worked example.
- **Tasks.**
  1. **Code:** a small curated **gazetteer** (`gazetteer.py` + JSON: colloquial term/alias → canonical place → OSM/GIS node id / coordinates / SUMO edge), resolved *before* or *alongside* the LLM location step; the LLM may normalize, but the **node id comes from the gazetteer, never invented** (glass-box: the LLM never originates geometry — consistent with the existing orchestrator contract).
  2. **GraphRAG:** index the gazetteer + OSM place context so retrieval disambiguates (semantic integrity = retrieved canonical entry, not a guess).
  3. **methods §4 / sdd worked example** — a concrete Hiligaynon query (e.g. *"Ano matabo kung barahan ang tulay sa Forbes?"* / *"…kon i-sira ang merkado?"*) → colloquial term → gazetteer hit → canonical place → GIS node/edge → scenario, with the retrieval trace shown.
  4. **Test:** assert the example colloquial term resolves to the expected node id deterministically.
- **Acceptance.** A documented Hiligaynon query resolves a colloquial term to a specific GIS node id via the gazetteer (not an LLM guess), with the trace visible; test passes.
- **Locked-doc edit:** none required (sdd is Locked — add via the SDD feedback/seam note already opened for Item 6, or keep the worked example in methods §4 which is Locked → log under CR-008).

### Item 9 — RAG setup + implementation elaboration

- **Current state.** [`graphrag.py`](../app/packages/kernel/matrix_kernel/graphrag.py) is a thin ChromaDB wrapper (`get_collection`, `retrieve`, bge-small-en-v1.5 embeddings, `matrix_knowledge_base` collection). **There is no ingestion/build script** — `retrieve()` returns `[]` until the collection is populated, and nothing populates it.
- **Gap.** No documented RAG architecture (what's indexed, chunking, embedding, retrieval, how it grounds orchestrator + synthesis) and **no build pipeline**.
- **Tasks.**
  1. **Code:** `build_graphrag.py` ingestion script — chunk + embed the corpus (OSM/Overture place context, CCHAIN barangay summaries, Calderon 2014 + TSSP literature, the gazetteer from Item 7, methods-ledger snippets) into Chroma with `source` metadata for citation.
  2. **sdd-matrix "RAG / GraphRAG" subsection** — architecture diagram + the flow: query → `retrieve(top_k)` → chunks (with `source`) injected into orchestrator system prompt (disambiguation) and synthesis (grounding + citation guard). Document embedding model, store, top_k, and the **citation contract** (synthesis claims cite `source` → and numbers still cite `equation_id`, not the RAG text).
  3. **methods §4** — extend the Orchestrator + Synthesis cards to name the retrieval grounding explicitly (the `run_trace.retrieved_chunks` hook already referenced in §4).
  4. **Test:** ingestion smoke test (build a tiny collection, retrieve, assert non-empty + source metadata present).
- **Acceptance.** SDD explains RAG end-to-end; the build script populates Chroma and `retrieve()` returns sourced chunks; synthesis grounding + citation guard documented as the safety boundary (RAG informs prose, never originates a number).
- **Locked-doc edit:** sdd (Locked) — additive RAG subsection; methods §4 cards. Logged under CR-008.

---

## 3. Cross-cutting decisions

- **Glass-box is non-negotiable.** Items 2, 3, 5, 7, 9 introduce code that touches numbers/geometry. Every one keeps the existing contract: the LLM narrates/normalizes but **never originates a number or a node id**; provenance (`equation_id` + `input_dataset_ids` + computed confidence) is attached and Inspect-resolvable. `glass-box-auditor` gate blocks violations.
- **City-agnostic.** The tricycle archetype (Item 2) and gazetteer (Item 7) hang off `CityConfig` / per-city data — Iloilo by default, no hard-coding that breaks the swap-OSM-bbox scaling promise.
- **Honest withholds stay honest.** Item 1 must not "make VAL-01 pass" by massaging demand. A withheld gate stays withheld with its reason until calibration earns the pass.
- **PROVISIONAL labelling.** Any new constant (vendor footfall coefficient, tricycle catchment) ships declared PROVISIONAL in `assumptions`, mirroring methods §3.6.

---

## 4. Locked-doc edit register (governance)

CR-008 touches Locked docs; per [index §0](index.md) every such edit is recorded here and in the change log.

| Locked doc | Edit | Item(s) | Nature |
|---|---|---|---|
| methods-matrix | Appendix A (module⇄source); §2 Low-Confidence Protocol; §3.2/§3.3/§3.4 elaboration; §4 bias example + RAG/orchestrator card; §6 status update | 1,2,3,4,8,9 | additive + status truth |
| prd-matrix | PRD-F20 (planner feedback); PRD-F19 resilience subsection | 5,6 | additive feature + elaboration |
| sdd-matrix | `/feedback` seam + `planner_feedback` table; RAG/GraphRAG subsection | 6,9 | additive seam |

No equation **changes** value under CR-008 (that would be a separate, heavier CR). Edits are elaboration, new appendices, new features, and honest status updates.

---

## 5. Execution sequencing

Per-item feature branches off `dev`; both gating agents (`glass-box-auditor`, `eval-test-runner`) PASS before each merges; `dev` → `main` PR when the phase is green. Solo-dev mode: serial, critical-path first.

| Phase | Items | Branch(es) | Rationale | Gate |
|---|---|---|---|---|
| **A — doc wins (zero/low risk)** | 8, then 4, 5(doc), 2(doc) | `docs/cr008-traceability`, `docs/cr008-confidence-resilience` | Pure-doc + traceability; immediate judge-visible value; no code risk | glass-box-auditor (doc claims cite) |
| **B — code + doc** | 3 (bias reweight), 9 (RAG build), 7 (gazetteer) | `feat/cr008-bias-reweight`, `feat/cr008-rag-ingest`, `feat/cr008-hiligaynon-gazetteer` | Each adds a tested capability + its worked example | both gates |
| **C — new feature** | 6 (CPDO feedback), 1 (ground-truth wiring), 5 (flood helper) | `feat/cr008-planner-feedback`, `feat/cr008-groundtruth` | New API surface + validation wiring; largest blast radius last | both gates |

Recommended start: **Item 8** (appendix) — highest signal-to-effort, unblocks nothing but reinforces the traceability thesis judges rewarded.

---

## 6. Definition of Done (CR-008 checklist)

- [x] **#8** methods Appendix A module⇄source matrix; cross-linked from MATRIX.md + PRD-F14.
- [x] **#1** qad §8 Ground-Truth Comparison subsection + comparison-table artifact; methods §6 statuses truthful.
- [x] **#2** methods §3.3/§3.4 informal-sector model; tricycle archetype + vendor-footfall code (PROVISIONAL, glass-box); READINESS note.
- [x] **#3** `reweight_pool` implemented + tested; audit entry carries factors; methods §4 worked middle-class-bias example matches code.
- [x] **#4** methods §2 Low-Confidence Protocol; DSD alert spec + InspectDrawer trigger-reason; test.
- [x] **#5** Extreme-event resilience section (prd/methods); `flood_scenario` helper feeding VAL-02; QAD scenario row.
- [x] **#6** PRD-F20; `POST/GET /feedback` + `planner_feedback` table + test; SDD seam; OPS triage runbook; UI affordance.
- [x] **#7** `gazetteer.py` + JSON; orchestrator/GraphRAG integration; worked Hiligaynon example; deterministic resolution test.
- [x] **#9** `build_graphrag.py` ingestion + smoke test; SDD RAG subsection; methods §4 cards extended.
- [x] Both gating agents PASS on every merge; kernel/api/web test suites green.
- [x] [index.md](index.md) change log + this CR's status updated; auto-memory updated.

> **Post-merge note (2026-06-22).** Item 3's reweight + Item 9's RAG shipped as *capabilities* but were not on the live run path until the 2026-06-22 wire-up pass: the bias auditor now runs per simulation (`personas.warm_persona_pool` at API startup + a per-run `GET /audit/{scenario_id}` entry carrying `adjustment_factors`), and the GraphRAG corpus is ingested at API startup so `retrieve()` actually grounds the orchestrator. See the [index.md](index.md) change log (2026-06-22 row).

---

## 7. Risks & honest constraints

- **Mode-share calibration is still the long pole.** Item 1's VAL-01 pass and Item 2's tricycle realism both ultimately want the FOI'd LTFRB/LPTRP survey (CR-007 PR 9 path). Until then they ship **directional + PROVISIONAL**, clearly labelled — not faked.
- **VAL-02 fixture is PROVISIONAL** until Copernicus Sentinel-1 GFM extent is acquired (INVENTORY `S1-GFM`, ⏳). Item 5's helper is built and tested against the placeholder, but the back-test result is not publishable until the real extent lands.
- **Gazetteer coverage** (Item 7) starts curated/small (top Iloilo colloquial landmarks); completeness is iterative, not v1-complete. Honest scope.
- **CPDO refinement (Item 6)** ships as capture + human triage + fixture promotion, **not** automated model retraining — deliberately, to preserve the glass box.
- **90 s budget.** RAG retrieval (Item 9) and gazetteer lookup sit on the orchestration path; keep them cached/cheap so they don't erode the latency budget (already ~123 s over the 90 s target — do not regress it).

---

*CR-008 opened 2026-06-17. Update §6 + [index.md](index.md) as items land.*
