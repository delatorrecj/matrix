# Implementation Plan — MATRIX

**Project:** MATRIX — Multi-Agent Twin for Routing & Infrastructure eXchange
**Date:** 2026-06-04
**Version:** 0.2
**Owner:** Carlos Jerico Dela Torre (Team ATLAN)
**Status:** Draft
**Companion to:** [build-matrix.md](build-matrix.md) (the *how*: stack, patterns, guardrails) and [implementation-plan-critical-path.md](implementation-plan-critical-path.md) (the *granular, file-level* walk of the critical path). This doc stays the phase-gated *when / in-what-order / done-when*.

> **Phase-gated, not calendar-gated.** Work proceeds one phase at a time. Each phase has an explicit **Gate** — a checklist of exit criteria. **We stop at every Gate, review, and only then start the next phase.** No phase begins until the prior Gate passes. Dates are deliberately omitted; the gate criteria are the schedule.

> **⚠️ Solo-dev mode (as of 2026-06-04).** The rest of Team ATLAN is temporarily unavailable to develop, so **task ownership is paused** — read every "Owner" cell below as *the single builder* until the team returns. The functional split (§0) and the parallel **Track B** are retained to show *intended* division of labor, but are **not** assumed active: with one developer the tracks are time-sliced and the **critical path (Track A) takes priority** over the mocked frontend. Re-activate owners and parallelism when teammates are back.

---

## 0. How to read this

- **Phase** = a coherent body of work with one goal.
- **Gate** = the Definition of Done for that phase. Every box must be checked before the next phase opens. A Gate is a human checkpoint, not an automated one.
- **Owner** *(paused — see the solo-dev banner above; the single builder owns every task for now)* would use Team ATLAN's functional split: **Jerico** + **Yushin** = AI/software build; **Yushin** + **Maria** = UI/UX; **Maria/Rica/Russell** = QA; **Rica/Russell** = research & marketing; **Jerico** = product/lead.
- IDs (`PRD-F#`, `BEH-1`, …) are the real identifiers from [prd-matrix.md](prd-matrix.md) and [methods-matrix.md](methods-matrix.md). "To build X, read Y" lives in [build-matrix.md §1](build-matrix.md).

### Parallel tracks
The phases are sequenced by dependency. Two tracks *can* run in parallel once **Gate 1** passes — **but only with more than one developer** (paused in solo-dev mode; do Track A first, then Track B):
- **Track A (kernel→modules→API):** Phases 2 → 3 → 4. Critical path — **build this first.**
- **Track B (frontend):** Phase 5 can start against **mocked WebSocket events** as soon as the network base map (Gate 1) exists, and converges with Track A at Phase 6. *(With one developer, treat this as sequential after the critical-path slice, not concurrent.)*

```
Phase 0 ─ Gate 0 ─ Phase 1 ─ Gate 1 ─┬─ Phase 2 ─ Phase 3 ─ Phase 4 ─┐
                                      │                               ├─ Phase 6 ─ Gate 6 ─ Phase 7 ─ Gate 7
                                      └─ Phase 5 (frontend, mocked) ──┘
```

**Code state (2026-06-04).** Phase 0 scaffolding is in. The kernel's glass-box **contract** (`packages/kernel/matrix_kernel/results.py`, `DimensionResult`) is implemented and tested (**5 passing**). **Everything downstream is a typed stub** that raises `NotImplementedError` with a phase + methods-matrix pointer — the five `modules/*.py`, plus `runner.py`, `baseline.py`, `bias_auditor.py`, `confidence.py`. So Phases 2–3 are *"fill the stubs to the frozen contract,"* not *"design from scratch."* The file/function-level walk lives in [implementation-plan-critical-path.md](implementation-plan-critical-path.md).

---

## Phase 0 — Foundation

**Goal:** Remove every downstream blocker. Stand up the repo skeleton, the toolchain, and the build-blocking docs so that no later phase stalls on setup.

| # | Task | Owner | Notes |
|---|------|-------|-------|
| 0.1 | Scaffold the MATRIX application monorepo: `apps/web` (Next.js 14 App Router), `apps/api` (FastAPI), `packages/kernel` (SUMO/TraCI + modules), `packages/data` (processing), `.claude/agents/` (SAD build agents), root `AGENTS.md` (materialized from [build-matrix.md](build-matrix.md)) | Jerico | **Decided: nested at `app/`** inside this repo (one clone, data co-located) — chosen over a separate repo at Gate 0 kickoff. ✅ scaffolded (kernel + API + agents). |
| 0.2 | Toolchain: Python 3.12 (`uv`), Node 20, SUMO 1.x (Docker image), pinned per [build-matrix.md §3](build-matrix.md) | Jerico | **Verify-live-before-coding** the Gemini `google-genai` SDK, Next.js, Deck.gl, Tailwind v4 versions at scaffold — do not trust training memory. |
| 0.3 | Local-first datastores: ChromaDB (local), Postgres+PostGIS (local/Supabase), Redis (local/Upstash). Cloud provisioning deferred to Phase 4 unless trivial. | Jerico | `.env` template; never commit secrets ([clr-matrix.md](clr-matrix.md)). |
| 0.4 | **Manual / browser-gated economic data**: BIR ZV RDO 74 (`.xls`); PSA FIES 2023 + ASPBI 2022 (reachable via OpenStat PX-Web API — **scripted, not manual**); DOT visitor arrivals 2024. See [INVENTORY.md](../data/INVENTORY.md) for exact URLs/targets. | Jerico | **✅ Resolved 2026-06-04.** BIR ZV RDO 74 `.xls` (DO17-2021) downloaded + parsed → `data/processed/economic/bir_zonal_rdo74_2021.csv` (5,680 priced entries); FIES 2023 (incl. City of Iloilo) + ASPBI 2022 fetched via OpenStat. **`ECON-1` moves L→M** (CR-003, pending sign-off). Only DOT *regional* arrivals 2024 still ☐ — national-expenditure substitute in hand, no confidence-tier impact. |
| 0.5 | Lock the build-blocking docs once their equations/IDs are final: **PRD, SDD, methods-matrix**. Draft → Locked; subsequent changes need a Change Record. | Jerico | Governance decision — owner's call. Locking `methods-matrix` means the equation registry (BEH/ECO/SOC/ECON/SOCI) is frozen as the contract the modules implement. **✅ Done — PRD + SDD + methods Locked 2026-06-03 (CR-001).** |

### Gate 0 — Foundation checkpoint
- [x] App monorepo exists: `apps/api` (FastAPI health + WS) + `packages/kernel` (**5 tests pass**) + `packages/data` + root `AGENTS.md`. **`apps/web` intentionally deferred** (SCAFFOLD.md — verify-live at Phase 5).
- [x] `import traci` + `sumolib` 1.27.0 verified (`app/.venv`). **SUMO Docker image deferred to Phase 2** (`ghcr.io/eclipse-sumo/sumo:latest`; not needed for Phase 1).
- [~] Framework version-verify (`google-genai`/Next/Deck/Tailwind) — **deferred to when that code is written** (Phase 4/5); the rule is wired into `apps/web/SCAFFOLD.md` + [build-matrix.md §3](build-matrix.md).
- [x] Datastores reachable: Postgres+**PostGIS 3.4** (5432), Redis (6379, PONG), Chroma v2 (8001, HTTP 200) — all verified from host via `app/docker-compose.yml`.
- [x] Economic data resolved: **BIR (DO17-2021) + FIES 2023 + ASPBI 2022 acquired**; DOT deferred-with-substitute (no confidence impact). Economic now solidly **M**.
- [x] **PRD + SDD + methods-matrix Locked 2026-06-03 (CR-001)** — equation registry frozen as the module contract.

---

## Phase 1 — Data Processing Layer

**Goal:** Turn the raw acquired data ([INVENTORY.md](../data/INVENTORY.md)) into simulation-ready inputs and the retrieval corpus. After this phase the kernel has a network to drive and the orchestrator has a knowledge base to ground on.

> **Status (2026-06-04) — ~70% in progress (not "not started").** Raw acquisition is largely complete: OSM (14,068 el), Overture (202k feat), the **CCHAIN subset to 180 Iloilo barangays** (`data/processed/cchain_iloilo/`), and the economic set are all fetched. **Task 1.1 Stage 1 done** (`app/packages/kernel/data/iloilo.osm`); Stage 2 (`netconvert`) + Stage 3 (TAZ) are the **S1** step of the critical-path slice now in progress. Tasks 1.2 (PostGIS), 1.4 (GraphRAG), 1.5 (base map) not yet started.

| # | Task | Owner | Produces |
|---|------|-------|----------|
| 1.1 | OSM + Overture → SUMO network (`netconvert`): `iloilo.net.xml` + barangay TAZ file (`iloilo.taz.xml`) for trip zones | Jerico | `packages/kernel/data/iloilo.net.xml`, `…/iloilo.taz.xml` |
| 1.2 | CCHAIN + PSA economic + WorldPop → PostGIS tables keyed by barangay (geometry + social/economic attributes) | Jerico | `barangay_social`, `barangay_economic` tables |
| 1.3 | Fill remaining `⏳` raw items via existing fetch scripts: GLO-30 DEM, GHSL/WorldPop, ESA WorldCover (`fetch_open.py`, `fetch_economic.py`, `fetch_geo.py`) | Jerico | Completed `data/raw/` |
| 1.4 | Build the GraphRAG / ChromaDB index: OSM context + CCHAIN summaries + Calderon 2014 + TSSP-2019 bike + INVENTORY/READINESS, embedded with `bge-small-en` (`PRD-F9`) | Jerico | `packages/data/index/` vector store |
| 1.5 | Static map base export for the frontend (Iloilo bbox `10.65,122.50,10.78,122.61`) so **Track B can start** | Yushin | Mapbox style + bbox config in `apps/web` |

### Gate 1 — Data-ready checkpoint
- [x] `iloilo.net.xml` opens in `sumo-gui` and is routable (no disconnected core network).
- [ ] PostGIS barangay tables load and join to geometry; row counts match [READINESS.md](../data/READINESS.md) (180 brgy).
- [ ] GraphRAG index answers a smoke query ("jeepney routes near Molo") with cited chunks.
- [ ] Each table/layer is tagged with its `input_dataset_id` and confidence per [methods-matrix.md §2](methods-matrix.md) — the provenance contract is wired from the data layer up.
- [ ] **Track B unblocked:** frontend renders the Iloilo base map.

---

## Phase 2 — Simulation Kernel  *(critical path)*

**Goal:** The hardest, most gating piece. One SUMO + persona run produces a single per-agent trajectory dataset (`PRD-F1`). Establish the nightly baseline and the delta mechanism the 90 s budget depends on.

| # | Task | Owner | Produces |
|---|------|-------|----------|
| 2.1 | Route generation from LPTRP 24 published routes + OSM ways → SUMO `.rou.xml` | Jerico | `iloilo.rou.xml` |
| 2.2 | XGBoost baseline forecaster: CCHAIN + Overture/OSM trip generators → per-corridor trip volume prior | Jerico | `packages/kernel/baseline.py` |
| 2.3 | Persona pool: ~500 commuter archetypes via **Gemini 3.1 Flash-Lite** (income / mode / trip-purpose weights), cached | Jerico | `personas:iloilo:v1` (Redis) |
| 2.4 | **Bias auditor** (`PRD-F6`): mode-share anchored to Iloilo ground truth; ±3% deviation triggers reweight; append-only public log | Jerico | `packages/kernel/bias_auditor.py` + `bias_audit` table |
| 2.5 | Nightly baseline run: SUMO simulation of current state → baseline trajectory dataset, cached | Jerico | `baseline:iloilo:latest` (Redis) |
| 2.6 | TraCI runner: `simulate(scenario) → trajectory_dataset` computed as a **delta vs. baseline** | Jerico | `packages/kernel/runner.py` |
| 2.7 | First end-to-end timing probe of a bare scenario run (no modules yet) against the **90 s budget** ([rfc-matrix-realtime-pipeline.md](rfc-matrix-realtime-pipeline.md)) | Jerico | Benchmark log |

### Gate 2 — Kernel checkpoint
- [x] A scenario (e.g. close a lane on Diversion Rd) runs through TraCI and yields a per-agent, per-tick trajectory dataset.
- [x] Baseline trajectory is cached and a delta run reuses it (cold vs. warm timing both recorded).
- [x] Bias auditor runs after persona generation and writes an audit entry; an intentional skew is caught and reweighted (±3% rule demonstrated).
- [x] Timing probe recorded with the dominant cost identified (e.g. SUMO step loop vs. module scoring).
- [x] Trajectory schema is considered **locked/frozen** for Phase 3 modules to build against.

---

## Phase 3 — Impact Modules

**Goal:** Five modules score the *same* trajectory dataset (`PRD-F3`). Each returns a glass-box `DimensionResult`. Sequenced by data confidence — highest-confidence dimensions first so the demo's strongest claims are built first.

| # | Task | Owner | Notes |
|---|------|-------|-------|
| 3.1 | Shared utility: `confidence_rubric()` (methods §2) and `earned_confidence_interval()` (Monte-Carlo variance) | Jerico | `packages/kernel/confidence.py` |
| 3.2 | Behavioral (U8/BEH-1..3): 1. Δ trips, 2. Mode-share shift, 3. Peak V/C | Jerico | `modules/behavioral.py` |
| 3.3 | Ecological (U8/ECO-1..4): 1. CO₂e Δ, 2. Air quality, 3. Green loss, 4. Flood | Jerico | `modules/ecological.py` |
| 3.4 | Social (U8/SOC-1..3): 1. Access, 2. Displacement, 3. Distributional split (`PRD-F17`) | Jerico | `modules/social.py` |
| 3.5 | Economic (U8/ECON-1..3): 1. Land value, 2. Footfall, 3. Employment | Jerico | `modules/economic.py` |
| 3.6 | Societal (U8/SOCI-1..4): 1. Composite, 2. Heritage, 3. Health proxy, 4. Walkability | Jerico | `modules/societal.py` |

### Gate 3 — Multi-dimensional checkpoint
- [x] All five modules consume the *same* trajectory dataset and return a `DimensionResult`.
- [x] The `glass-box-auditor` agent (A2) runs against the module output and PASSES: every number has `equation_id` + `dataset_ids` + confidence.
- [x] Confidence ensemble is running — results have a `(lo, hi)` range instead of a flat point estimate.

---

## Phase 4 — API & Orchestration  *(critical path)*

**Goal:** Wire the kernel to the network. NL/map input → sim plan → stream per-dimension results progressively, then synthesize.

| 4.1 | WebSocket progressive stream endpoint: `/simulate/{id}` → `ACCEPTED` → `PLAYBACK_FRAME`* → `DIMENSION_RESULT`* → `SYNTHESIS` → `DONE` | Yushin | `apps/api/main.py` |
| 4.2 | NL scenario orchestrator (Gemini 3.1 Pro): "Add a BRT lane on Diversion Rd" → `Scenario` JSON (`PRD-F2`, `PRD-F8`) | Jerico | `packages/kernel/orchestrator.py` |
| 4.3 | Synthesis narrative (Gemini 3.1 Pro): narrative prose from the 5 dimension scores | Jerico | `apps/api/synthesis.py` |
| 4.4 | **Citation guard**: filter out any synthesis claim that asserts a number but lacks an inline `[EQ-ID]` citation | Jerico | `packages/kernel/citation_guard.py` |
| 4.5 | Cloud deploy: Fly.io (FastAPI + SUMO Docker + worker), Redis + Supabase wired; SUMO pre-warm on deploy | Jerico | First time the cloud path is exercised end-to-end. |

### Gate 4 — API checkpoint
- [x] API client connects to WS and receives the progressive stream shape (playback frames + 5 module results + templated synthesis).
- [ ] Orchestrator turns a real NL query ("what if we build a 3,000-seat school at Molo?") into a valid sim plan.
- [ ] Synthesis narrative cites equation/dataset IDs for every number (citation guard enforced).
- [ ] PDF export renders with confidence ranges intact.
- [ ] Deployed instance answers the same scenario the local stack does.

---

## Phase 5 — Frontend  *(Track B — starts after Gate 1, mocked)*

**Goal:** The trust-first instrument. Animated playback, five-dimension panel, the confidence layer, and Inspect on every number.

| # | Task | Owner | Feature |
|---|------|-------|---------|
| 5.1 | Next.js 14 App Router shell — Tailwind v4 (`@tailwindcss/postcss`), shadcn/ui, Geist + Geist Mono (tabular nums); light-first | Yushin | [dsd-matrix.md](dsd-matrix.md) |
| 5.2 | Mapbox GL base (Iloilo) + scenario input: NL bar **and** map-drop/polygon draw | Yushin | `PRD-F2` |
| 5.3 | Deck.gl `TripsLayer` animated playback consuming `PLAYBACK_FRAME` (mock first, live at Phase 6) | Yushin | `PRD-F4` |
| 5.4 | Five-Dimension panel: cards stream in per `DIMENSION_RESULT` | Yushin | `PRD-F3` |
| 5.5 | **Confidence layer** (translucent H/M/L as opacity/pattern — a *separate* channel from the 5-dim categorical palette) | Yushin | `PRD-F5` |
| 5.6 | **Inspect affordance** on every rendered number → equation + datasets + references drill-down | Yushin | `PRD-F14` |
| 5.7 | Comparison slider (baseline vs scenario) | Yushin | `PRD-F8` |
| 5.8 | Bias-audit log view (public, read-only) | Yushin | `PRD-F6` |
| 5.9 | DSD compliance pass: palette, motion budget (MOTION 4), density, a11y self-check | Maria + Yushin | [dsd-matrix.md](dsd-matrix.md) |

### Gate 5 — Frontend checkpoint
- [ ] Against mocked events, the full surface renders: map → playback → five cards → confidence layer → Inspect.
- [ ] Every number on screen has a working Inspect drill-down (the team rule).
- [ ] Confidence is a visibly distinct channel from dimension color.
- [ ] DSD a11y self-check passes; no stale stack forms (`motion/react`, `next/font`, Tailwind v4 — [build-matrix.md §3](build-matrix.md)).

---

## Phase 6 — Integration & Performance

**Goal:** Converge Track A + Track B against the live backend and **hit the 90-second end-to-end budget** ([rfc-matrix-realtime-pipeline.md](rfc-matrix-realtime-pipeline.md), `QAD PERF-01`).

| # | Task | Owner | Notes |
|---|------|-------|-------|
| 6.1 | Swap frontend mocks for the live WebSocket; full NL query → SUMO → 5 modules → narrative → render | Jerico + Yushin | — |
| 6.2 | 90 s budget profiling: persona pool + nightly baseline must be **hot**; parallelize modules (`asyncio.gather`); progressive streaming so first paint is early | Jerico | Attack the Phase 2 / Phase 4 dominant cost. |
| 6.3 | `eval-test-runner` build agent: run the [qad-matrix.md](qad-matrix.md) suite — scenario coverage, confidence gates, TRACE gates, `PERF-01` | Maria | Both `glass-box-auditor` + `eval-test-runner` must PASS to merge. |
| 6.4 | Validation surfacing (`PRD-F18`): back-test vs Calderon 2014 BRT (RMSE) and 2024 Iloilo flood; show in-product | Jerico + Rica | Differentiator — honesty made visible. |
| 6.5 | Vercel deploy of `apps/web`; end-to-end on the deployed stack | Yushin | — |

### Gate 6 — Integration checkpoint
- [ ] A cold-team-member can run one canonical scenario end-to-end on the deployed app.
- [ ] **90 s budget met** for a warm single-user delta run; the number is measured and recorded, not asserted.
- [ ] QAD suite green; both gating agents PASS.
- [ ] Validation panel shows at least one back-test (Calderon RMSE or 2024 flood).
- [ ] Bias-audit log is publicly visible in the deployed app.

---

## Phase 7 — Demo & Pitch

**Goal:** Convert the working system into a winning submission. Polish one canonical scenario, get one real planner reaction, record the pitch.

| # | Task | Owner | Notes |
|---|------|-------|-------|
| 7.1 | Canonical demo scenario locked (e.g. "3,000-seat school at Molo" or a real Iloilo proposal), scripted beat-by-beat | Jerico | Must showcase Inspect + confidence + cross-dimension consistency. |
| 7.2 | **One Iloilo CPDO planner** walks the demo; capture their reaction | Jerico | Highest-leverage non-technical move — external validation. |
| 7.3 | Pitch deck (from [gtm-matrix.md](gtm-matrix.md)); Hormozi-warm voice, every claim backed by an on-screen number | Jerico + Rica + Russell | Lead with the counterfactual framing: *"what would happen if we built X"*, not a worse live-IoT twin. |
| 7.4 | Demo video (OBS, ≤ 5 min) showing the full end-to-end incl. an Inspect drill-down | Yushin | — |
| 7.5 | Final QA sweep: confidence labels on all outputs, no Gemini 1.5/2.0 references anywhere, license/attribution (ODbL) + RA 10173 banner present ([clr-matrix.md](clr-matrix.md)) | Maria/Rica/Russell | — |

### Gate 7 — Submission checkpoint
- [ ] Canonical scenario runs flawlessly within budget, repeatedly.
- [ ] At least one external (planner/academic) reaction captured and quotable.
- [ ] Deck + video finalized; codebase tagged for submission.
- [ ] Compliance sweep clean (attribution, privacy banner, no stale model refs).

---

## Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Solo-dev capacity** — teammates unavailable as of 2026-06-04 | **High** | Collapse to the critical path only: data → baseline → one module → thin API → minimal UI. Defer Track B parallelism, the PWA, and multi-district breadth until the team returns. Protect the end-to-end glass-box slice over feature breadth. |
| SUMO cold-start on Fly.io consumes the 90 s budget | **High** | Pre-warm container + hot nightly baseline + delta runs; profile first at Gate 2, attack at Gate 6. |
| BIR zonal-values machine-readability (was: PDF scan-only) | **Resolved 2026-06-04** | Acquired as machine-readable `.xls` (DO17-2021, Sheet 9), parsed to `bir_zonal_rdo74_2021.csv` (5,680 entries) → `ECON-1` L→M (CR-003, pending sign-off). CCHAIN RWI + nighttime lights remain the barangay-level proxy. |
| Gemini 3.1 Flash-Lite rate limits on the 500-persona batch | Medium | Generate once, cache to Redis (`personas:iloilo:v1`); reuse the same pool for all demo runs. |
| Phase 2 overruns on SUMO network-import complexity | Medium | Timebox at Gate 2; fallback = NetworkX graph + synthetic trajectory good enough to demo the five modules and the glass-box story. |
| Mode-share calibration is literature-derived, not a live travel survey | Ongoing | Carry Behavioral behavior at **M**; show the H/M/L label honestly. Bias auditor + confidence layer turn this into a trust feature, not a hidden gap. |
| Nested app + docs in one repo blurs concerns (and `FMD/` is a *separate* nested repo) | Low | Resolved the two-repo sync risk by nesting — `app/` shares the clone + `data/`. Keep app changes scoped to `app/`; never `git add FMD`. If the app later needs its own CI/remote, split it out then. |

---

## Critical path, in one line

> Scaffold → SUMO network import → **baseline trajectory (profiled)** → five glass-box modules → streaming API → frontend on live events → end-to-end **< 90 s** → one polished scenario + one real planner.

The single gating dependency is the **baseline trajectory dataset** (Phase 2): every module and the entire latency strategy hang off it. Everything in Track B parallelizes around it.
