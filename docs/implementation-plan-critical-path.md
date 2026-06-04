# Implementation Plan — Critical Path (file-level)

**Project:** MATRIX — Multi-Agent Twin for Routing & Infrastructure eXchange
**Date:** 2026-06-04
**Version:** 0.1
**Status:** Draft
**Mode:** **Solo-dev** — one builder owns everything; no task is assigned to a teammate (see the solo-dev banner in [implementation-plan-matrix.md](implementation-plan-matrix.md)).
**Parent:** [implementation-plan-matrix.md](implementation-plan-matrix.md) owns the phase/gate *structure*. **This doc is the granular, file-by-file walk of the critical path** — what function to write, in which stub, consuming which dataset, done-when which test goes green. It does not restate phase rationale; it executes it.

> **Why this doc exists.** The gated plan says *"the single gating dependency is the baseline trajectory dataset; everything hangs off it."* The repo is currently **all stubs around one live contract** ([`DimensionResult`](../app/packages/kernel/matrix_kernel/results.py)). The fastest way to de-risk the whole product is **one vertical glass-box slice**: a scenario in → a *real* Behavioral number out, with provenance, streamed over the WebSocket. This doc builds exactly that, then stops.

---

## 0. The slice we are building (Milestone A)

**One sentence:** a structured Iloilo scenario produces a real `DimensionResult` for **Behavioral / BEH‑1** (Δ trips/day per corridor) — computed from a SUMO delta-vs-baseline run, carrying `equation_id` + `input_dataset_ids` + a *computed* confidence — and the API streams it as `ACCEPTED → PLAYBACK_FRAME* → DIMENSION_RESULT → SYNTHESIS → DONE`.

**Why this slice and not more:** it exercises every architectural commitment once — unified kernel → one trajectory → a module → the glass-box contract → the progressive WS stream — so every later module and dimension is "more of the same," not "new architecture." It deliberately **excludes** the Gemini orchestrator (accept a structured scenario, not NL), the other four modules, and the real frontend. Those come after the slice proves out (§6).

**Critical path, one line:**

> env up → SUMO network (or synthetic fallback) → nightly baseline cached → `simulate()` delta → `confidence` utils → `behavioral.score()` → API streams a real `DIMENSION_RESULT` → one number resolves under Inspect.

**Slice Definition of Done** (the demoable assertion — see §3 for the checklist):
a `pytest` drives `behavioral.score(simulate(scenario), datasets)` and asserts a `DimensionResult` with `equation_id="BEH-1"`, non-empty `input_dataset_ids`, a computed `confidence`, and a `range` whose width came from the ensemble — **and** the WS endpoint emits that same result over the wire.

---

## 1. Step 0 — Environment & ground truth (do this first)

| | Action | Done-when |
|---|---|---|
| 0.1 | `cd app && uv sync` (kernel + api). The repo venv (`app/.venv`) is a **uv** venv with no `pip`. | `uv run pytest` from `packages/kernel` → **5 passed**. |
| 0.2 | `cd app && docker compose up -d` → Postgres+PostGIS `:5432`, Redis `:6379`, Chroma `:8001`. | `docker compose ps` all healthy; `redis-cli ping` → PONG. |
| 0.3 | `cp app/.env.example app/.env`; fill `GOOGLE_API_KEY` only when §6 needs it (Milestone A needs **no** LLM). | `.env` present, gitignored. |
| 0.4 | Confirm raw data on disk: `data/raw/` has OSM-ILO, OVERTURE, CCHAIN, LPTRP per [INVENTORY.md](../data/INVENTORY.md). Re-fetch gaps with `data/fetch/*.py`. | `data/INVENTORY.md` ✅ rows resolve to files. |

**Guardrail for every step below:** **verify-live-before-coding.** Before writing `netconvert`/`sumolib`/TraCI/`redis`/`chromadb` calls, confirm the current API against official docs — do not emit from training memory. Log any drift to [build-matrix.md §3](build-matrix.md).

---

## 2. The slice, step by step

Each step names the **real file**, the **function to fill**, its **inputs** (INVENTORY dataset IDs), the **verify-live** surface, and a **done-when** you can actually check. Steps are strictly ordered — each unblocks the next.

### S1 — Iloilo SUMO network  *(gated-plan 1.1; produces the thing everything drives)*
- **File / output:** `app/packages/data/` pipeline → `app/packages/kernel/data/iloilo.net.xml` + `iloilo.taz.xml`.
- **Do:** `netconvert` from **OSM-ILO** (12,579 ways) clipped to bbox `10.65,122.50,10.78,122.61`; barangay TAZ from CCHAIN/WorldPop boundaries (180 brgy). Stamp the layer with `input_dataset_id` + confidence ([methods-matrix §2](methods-matrix.md)).
- **Verify-live:** `netconvert` flags + `sumolib.net.readNet` API.
- **Done-when:** opens in `sumo-gui`; core network is connected (no islands); `sumolib` loads it and reports edge count.
- **Fallback (if this overruns — see §5):** skip to a synthetic NetworkX corridor graph; the slice survives.

### S2 — Routes & demand  *(gated-plan 2.1)*
- **File / output:** `iloilo.rou.xml`.
- **Do:** map the **LPTRP 24 published routes** + OSM ways onto the net → SUMO routes; seed demand from trip generators (Overture POIs 11,189 + OSM amenities). Calibrate volumes against **Calderon 2014** for one corridor.
- **Done-when:** a bare `sumo` run completes with vehicles routing end-to-end on ≥1 real corridor (e.g. Diversion Rd).

### S3 — Nightly baseline → Redis  *(gated-plan 2.2, 2.5; the gating dependency)*
- **File:** `app/packages/kernel/matrix_kernel/baseline.py` → fill `run_nightly_baseline()` (and `train_baseline()` for the XGBoost per-corridor prior).
- **Do:** run SUMO on the current state → a per-agent, per-tick trajectory; serialize and cache to Redis key **`baseline:iloilo:latest`**. This is what makes scenario runs cheap deltas (the 90 s budget depends on it being hot).
- **Verify-live:** `redis` client API; TraCI step loop.
- **Done-when:** key exists in Redis; a loader returns a trajectory object; cold-run time is recorded (feeds the §3 budget probe).

### S4 — Persona pool + bias auditor  *(gated-plan 2.3, 2.4; PRD‑F6)*
- **Files:** persona generation (new, in kernel) → Redis **`personas:iloilo:v1`**; `app/packages/kernel/matrix_kernel/bias_auditor.py` → fill `audit_personas(observed, target)`.
- **Do:** generate ~500 commuter archetypes (income / mode / trip-purpose weights). **Milestone A may seed the pool from a static weighted distribution** matched to Iloilo mode share — the **Gemini 3.1 Flash-Lite** generator is a §6 upgrade, not a slice blocker. `audit_personas` compares observed vs. target mode share; deviation beyond `MODE_SHARE_TOLERANCE` (±3%) sets `reweighted=True` and appends a `BiasAuditEntry` to the append-only `bias_audit` log (Postgres).
- **Done-when:** an intentionally skewed batch is **caught and reweighted** (the ±3% rule demonstrated in a test); one audit row is written.

### S5 — TraCI delta runner  *(gated-plan 2.6; PRD‑F1 — the "one kernel" promise)*
- **File:** `app/packages/kernel/matrix_kernel/runner.py` → fill `simulate(scenario: Scenario)`.
- **Do:** apply the scenario edit (e.g. close a lane) to the net, run SUMO via TraCI **as a delta against `baseline:iloilo:latest`**, and return **one** per-agent, per-tick trajectory dataset. Every downstream module scores *this one object* — never fork into five simulators.
- **Decision to lock here:** **freeze the trajectory schema.** All Phase-3 modules consume it; freezing now prevents rework (gated-plan Gate 2).
- **Verify-live:** TraCI `libsumo`/`traci` connection + step API.
- **Done-when:** `simulate(Scenario("s1","close a lane on Diversion Rd"))` returns a trajectory; warm (delta) run reuses the cached baseline and is measurably faster than cold.

### S6 — Confidence utilities  *(gated-plan Phase 3 shared utility; PRD‑F5, PRD‑F15)*
- **File:** `app/packages/kernel/matrix_kernel/confidence.py` → fill both stubs.
- **Do:** `confidence_rubric(input_dataset_ids)` returns H/M/L **computed** from the consumed datasets exactly as **[methods-matrix §2](methods-matrix.md)** defines (it's Locked — implement the ledger's rubric, don't invent one). `earned_confidence_interval(point, sample, n=1000)` runs the Monte-Carlo / sensitivity pass so the **range is computed, not a flat ±%**.
- **Done-when:** `confidence_rubric(["OSM-ILO","OVERTURE"])` returns the tier methods §2 prescribes; the ensemble returns a `(lo, hi)` with `lo ≤ point ≤ hi`.

### S7 — Behavioral module (first real numbers)  *(gated-plan Phase 3, order 1; BEH‑1/2/3)*
- **File:** `app/packages/kernel/matrix_kernel/modules/behavioral.py` → fill `score(trajectory, datasets)`.
- **Do:** implement the three equations from **[methods-matrix §3.1](methods-matrix.md)** over the S5 trajectory, each returning a `DimensionResult`:
  - **BEH‑1** Δ trips/day per corridor — `input_dataset_ids=["OSM-ILO","OVERTURE"]` + persona pool.
  - **BEH‑2** Mode-share shift (±3% anchor) — persona pool, `Calderon2014`, `CCHAIN`.
  - **BEH‑3** Peak saturation V/C — SUMO net, `OSM-ILO`.
  Each result: `value`, computed `range` (from S6 ensemble), `confidence` (from S6 rubric — **not guessed**), `equation_id`, `input_dataset_ids`, `references`. The `DimensionResult.__post_init__` invariants reject anything missing `equation_id`/`input_dataset_ids`, so a black-box result **cannot be constructed**.
- **Done-when:** `behavioral.score(...)` returns 3 well-formed `DimensionResult`s; the **`glass-box-auditor`** agent passes on the module; a low-confidence variant renders `directional=True`.

### S8 — Stream it over the wire  *(gated-plan 4.1; RFC §3)*
- **File:** `app/apps/api/matrix_api/main.py` → replace the Phase-0 placeholder handshake in `simulate(ws, scenario_id)`.
- **Do:** on connect, look up/run the scenario, then emit the real progressive sequence using the already-frozen `EVENT_TYPES`: `ACCEPTED` → a few `PLAYBACK_FRAME` (sampled trajectory ticks for the Deck.gl TripsLayer) → `DIMENSION_RESULT` (the Behavioral result as JSON, provenance intact) → `SYNTHESIS` (a **templated** one-liner for now — Gemini synthesis is §6) → `DONE`. Run the module(s) under `asyncio.gather` so the parallel-streaming shape is real from day one.
- **Done-when:** a WS client (or `pytest` + `httpx`/`websockets`) connects to `/simulate/{id}` and receives the five event types in order, with a `DIMENSION_RESULT` payload that still carries `equation_id` + `input_dataset_ids`.

---

## 3. Definition of Done — Milestone A

- [ ] `uv run pytest` green, **including a new slice test** that asserts `behavioral.score(simulate(scenario), datasets)` yields a `DimensionResult(equation_id="BEH-1", …)` with non-empty `input_dataset_ids`, a computed `confidence`, and an ensemble-derived `range`.
- [ ] **Trajectory schema frozen** (S5) — recorded in [sdd-matrix.md](sdd-matrix.md) so the other four modules build against it without rework.
- [ ] **Bias auditor demonstrated** — a skewed persona batch is caught and reweighted (±3%), one `bias_audit` row written.
- [ ] **Glass box holds** — `glass-box-auditor` passes; there is no path to a number without `equation_id` + `input_dataset_ids` + computed confidence; low confidence renders `directional`.
- [ ] **It streams** — `/simulate/{id}` emits `ACCEPTED → PLAYBACK_FRAME* → DIMENSION_RESULT → SYNTHESIS → DONE` with provenance intact.
- [ ] **Budget probe logged** — cold baseline vs. warm delta timing recorded; the dominant cost named (sets the Phase 6 perf target). Both gating agents (`glass-box-auditor`, `eval-test-runner`) PASS.

When all boxes are checked, the architecture is proven end-to-end on one number. Adding Ecological/Social/Economic/Societal and the NL/visual layers is then **width, not depth.**

---

## 4. Deliberately deferred (solo-dev scope discipline)

Cut now; pick up per the gated plan when the team returns or the slice is solid:

- **Gemini orchestrator (NL → scenario).** Accept a structured `Scenario` directly for Milestone A. (gated-plan 4.2)
- **Gemini synthesis narrative.** Use a templated string; swap to Gemini 3.1 Pro with the citation guard later. (gated-plan 4.3)
- **The other four modules** (Ecological → Social → Economic → Societal), in that confidence order. They reuse S5 trajectory + S6 confidence verbatim. (gated-plan Phase 3)
- **Real frontend** (`apps/web`) — stays unscaffolded; the WS shapes from S8 are the contract it will mock against. (gated-plan Phase 5)
- **PWA companion, multi-district breadth, GraphRAG retrieval, cloud deploy, PDF export.** All additive.

---

## 5. Fast fallback if SUMO import overruns

The gated plan's risk register times-boxes S1–S2 at Gate 2. If OSM→SUMO import eats the budget, **do not stall the slice** — substitute a synthetic trajectory and keep every other step identical:

- Replace S1/S2 with a small **NetworkX** corridor graph of 3–5 real Iloilo arterials (Diversion Rd, Gen. Luna, Iznart…).
- `simulate()` emits a synthetic-but-plausible per-agent trajectory over that graph (same frozen schema).
- S6–S8 are **unchanged** — confidence, Behavioral, and the WS stream don't care how the trajectory was produced.
- Label the affected `DimensionResult.assumptions` with *"synthetic network — directional"* so the glass box stays honest.

This keeps the demoable glass-box story intact even in the worst SUMO case, and the real net drops in later behind the same `simulate()` signature.

---

## 6. After the slice (Milestone B → gated Phases 4–6)

Once Milestone A is green, the work converges back onto the gated plan:

1. **Width:** Ecological → Social → Economic → Societal modules (Phase 3 order), each on the frozen trajectory.
2. **Ask-able:** Gemini 3.1 Pro orchestrator turns a real NL query ("3,000-seat school at Molo") into a `Scenario` (Phase 4.2); Flash-Lite generates the real persona pool (upgrade S4).
3. **Watchable:** scaffold `apps/web` per [SCAFFOLD.md](../app/apps/web/SCAFFOLD.md), wire the live WS, Deck.gl TripsLayer playback, the five-dimension panel, the **confidence layer**, and **Inspect on every number** (Phase 5).
4. **Fast:** profile to the **90 s** warm-delta budget (Phase 6) — persona pool + nightly baseline hot, modules parallel, streaming first paint early.
5. **Honest:** surface the Calderon-2014 / 2024-flood back-test in-product (PRD‑F18).

The rule that gates all of it stays the same: **if a number on screen has no working Inspect, it's not done.**
