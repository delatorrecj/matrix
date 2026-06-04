# Implementation Plan — MATRIX

**Project:** MATRIX — Multi-Agent Twin for Routing & Infrastructure eXchange
**Date:** 2026-06-03
**Version:** 0.1
**Owner:** Carlos Jerico Dela Torre (Team ATLAN)
**Status:** Draft
**Companion to:** [build-matrix.md](build-matrix.md) (the *how*: stack, patterns, guardrails). This doc is the *when / in-what-order / done-when*: the phase-gated execution sequence.

> **Phase-gated, not calendar-gated.** Work proceeds one phase at a time. Each phase has an explicit **Gate** — a checklist of exit criteria. **We stop at every Gate, review, and only then start the next phase.** No phase begins until the prior Gate passes. Dates are deliberately omitted; the gate criteria are the schedule.

---

## 0. How to read this

- **Phase** = a coherent body of work with one goal.
- **Gate** = the Definition of Done for that phase. Every box must be checked before the next phase opens. A Gate is a human checkpoint, not an automated one.
- **Owner** uses Team ATLAN's functional split: **Jerico** + **Yushin** = AI/software build; **Yushin** + **Maria** = UI/UX; **Maria/Rica/Russell** = QA; **Rica/Russell** = research & marketing; **Jerico** = product/lead.
- IDs (`PRD-F#`, `BEH-1`, …) are the real identifiers from [prd-matrix.md](prd-matrix.md) and [methods-matrix.md](methods-matrix.md). "To build X, read Y" lives in [build-matrix.md §1](build-matrix.md).

### Parallel tracks
The phases are sequenced by dependency, but two tracks run in parallel once **Gate 1** passes:
- **Track A (kernel→modules→API):** Phases 2 → 3 → 4. Critical path.
- **Track B (frontend):** Phase 5 can start against **mocked WebSocket events** as soon as the network base map (Gate 1) exists, and converges with Track A at Phase 6.

```
Phase 0 ─ Gate 0 ─ Phase 1 ─ Gate 1 ─┬─ Phase 2 ─ Phase 3 ─ Phase 4 ─┐
                                      │                               ├─ Phase 6 ─ Gate 6 ─ Phase 7 ─ Gate 7
                                      └─ Phase 5 (frontend, mocked) ──┘
```

---

## Phase 0 — Foundation

**Goal:** Remove every downstream blocker. Stand up the repo skeleton, the toolchain, and the build-blocking docs so that no later phase stalls on setup.

| # | Task | Owner | Notes |
|---|------|-------|-------|
| 0.1 | Scaffold the MATRIX application monorepo: `apps/web` (Next.js 14 App Router), `apps/api` (FastAPI), `packages/kernel` (SUMO/TraCI + modules), `packages/data` (processing), `.claude/agents/` (SAD build agents), root `AGENTS.md` (materialized from [build-matrix.md](build-matrix.md)) | Jerico | **Decided: nested at `app/`** inside this repo (one clone, data co-located) — chosen over a separate repo at Gate 0 kickoff. ✅ scaffolded (kernel + API + agents). |
| 0.2 | Toolchain: Python 3.12 (`uv`), Node 20, SUMO 1.x (Docker image), pinned per [build-matrix.md §3](build-matrix.md) | Jerico | **Verify-live-before-coding** the Gemini `google-genai` SDK, Next.js, Deck.gl, Tailwind v4 versions at scaffold — do not trust training memory. |
| 0.3 | Local-first datastores: ChromaDB (local), Postgres+PostGIS (local/Supabase), Redis (local/Upstash). Cloud provisioning deferred to Phase 4 unless trivial. | Jerico | `.env` template; never commit secrets ([clr-matrix.md](clr-matrix.md)). |
| 0.4 | **Manual data downloads** (browser-gated; PSA/BIR return 403 to scripts): BIR ZV RDO 74 → `data/raw/economic/BIR_ZV_RDO74_IloiloCity.pdf`; PSA FIES 2023; PSA ASPBI 2023; DOT visitor arrivals 2024. See [INVENTORY.md](../data/INVENTORY.md) for exact URLs/targets. | Jerico | **Confirmed still pending** as of 2026-06-03. `ECON-1` land-value confidence stays **L** until BIR-ZV lands. Not a hard blocker — substitutes (CCHAIN RWI + nighttime lights) are in hand. |
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

| # | Task | Owner | Produces |
|---|------|-------|----------|
| 1.1 | OSM + Overture → SUMO network (`netconvert`): `iloilo.net.xml` + barangay TAZ file (`iloilo.taz.xml`) for trip zones | Jerico | `packages/kernel/data/iloilo.net.xml`, `…/iloilo.taz.xml` |
| 1.2 | CCHAIN + PSA economic + WorldPop → PostGIS tables keyed by barangay (geometry + social/economic attributes) | Jerico | `barangay_social`, `barangay_economic` tables |
| 1.3 | Fill remaining `⏳` raw items via existing fetch scripts: GLO-30 DEM, GHSL/WorldPop, ESA WorldCover (`fetch_open.py`, `fetch_economic.py`, `fetch_geo.py`) | Jerico | Completed `data/raw/` |
| 1.4 | Build the GraphRAG / ChromaDB index: OSM context + CCHAIN summaries + Calderon 2014 + TSSP-2019 bike + INVENTORY/READINESS, embedded with `bge-small-en` (`PRD-F9`) | Jerico | `packages/data/index/` vector store |
| 1.5 | Static map base export for the frontend (Iloilo bbox `10.65,122.50,10.78,122.61`) so **Track B can start** | Yushin | Mapbox style + bbox config in `apps/web` |

### Gate 1 — Data-ready checkpoint
- [ ] `iloilo.net.xml` opens in `sumo-gui` and is routable (no disconnected core network).
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
- [ ] A scenario (e.g. close a lane on Diversion Rd) runs through TraCI and yields a per-agent, per-tick trajectory dataset.
- [ ] Baseline trajectory is cached and a delta run reuses it (cold vs. warm timing both recorded).
- [ ] Bias auditor runs after persona generation and writes an audit entry; an intentional skew is caught and reweighted (±3% rule demonstrated).
- [ ] Timing probe recorded with the dominant cost identified — this sets the Phase 6 performance budget.
- [ ] **Decision:** is the trajectory schema frozen? All five modules in Phase 3 consume it; freezing it here prevents rework.

---

## Phase 3 — Impact Modules

**Goal:** Five modules score the *same* trajectory dataset (`PRD-F3`). Each returns a glass-box `DimensionResult`. Sequenced by data confidence — highest-confidence dimensions first so the demo's strongest claims are built first.

| Order | Module | Equations ([methods-matrix §3](methods-matrix.md)) | Conf | Owner |
|-------|--------|---------------------------------------------------|------|-------|
| 1 | `behavioral.py` — Δ trips/corridor, mode-share shift, peak V/C | **BEH-1, BEH-2, BEH-3** | H | Jerico |
| 2 | `ecological.py` — CO₂e Δ, air-quality Δ, green-cover loss, flood-exposure Δ | **ECO-1, ECO-2, ECO-3, ECO-4** | H | Jerico |
| 3 | `social.py` — equity access, displacement count, distributional split | **SOC-1, SOC-2, SOC-3** (`PRD-F17`) | M | Jerico |
| 4 | `economic.py` — land-value Δ, footfall Δ, employment Δ | **ECON-1, ECON-2, ECON-3** | M (L for ECON-1 until BIR-ZV) | Jerico |
| 5 | `societal.py` — composite, heritage proximity, health-exposure, walkability | **SOCI-1…4** | M | Jerico |
| — | Earned-confidence ensemble (`PRD-F15`): Monte-Carlo / sensitivity → the range is **computed**, not labeled | shared utility | — | Jerico |

Every module returns the [build-matrix.md](build-matrix.md) golden-path shape: `value`, `range`, `confidence` (computed via the rubric, not guessed), `directional` flag, `equation_id`, `input_dataset_ids`, `references`. **The `glass-box-auditor` build agent rejects any result missing these fields** — wire that agent before merging module 1.

### Gate 3 — Modules checkpoint
- [ ] All five modules consume one trajectory dataset and return well-formed `DimensionResult`s.
- [ ] `glass-box-auditor` passes on every module (no number without `equation_id` + `input_dataset_ids` + confidence).
- [ ] Confidence is **computed** from the rubric; low-confidence outputs render "directional only," never as precision (`PRD-F5`).
- [ ] Ensemble produces a range for at least Behavioral + Ecological (`PRD-F15`).
- [ ] A spot-check trace: pick one on-screen number, confirm its Inspect path resolves to equation + datasets ("if a number has no working Inspect, it's not done").

---

## Phase 4 — API & Orchestration  *(critical path)*

**Goal:** Wire the kernel to the network. NL/map input → sim plan → stream per-dimension results progressively, then synthesize.

| # | Task | Owner | Notes |
|---|------|-------|-------|
| 4.1 | FastAPI gateway + WebSocket `/simulate/{id}`; progressive event stream (`PLAYBACK_FRAME`, `DIMENSION_RESULT`, …) per [rfc-matrix-realtime-pipeline.md §3](rfc-matrix-realtime-pipeline.md) | Jerico | — |
| 4.2 | **Gemini 3.1 Pro orchestrator** (`PRD-F2`): NL/map drop → simulation plan; cached static system prefix (Iloilo context + mode-share anchors) + GraphRAG retrieval | Jerico | Verify `google-genai` call shape live ([build-matrix.md §3](build-matrix.md)). |
| 4.3 | **Gemini 3.1 Pro synthesis** (`PRD-F7`): five `DimensionResult`s → per-dimension narrative; **must cite `equation_id` + `dataset_ids`** (citation guard, [methods-matrix §4](methods-matrix.md)) | Jerico | On 429 → backoff + cached parse. |
| 4.4 | PDF recommendation report export (`PRD-F7`): structured HTML → PDF with assumptions + confidence intervals | Jerico | — |
| 4.5 | Cloud deploy: Fly.io (FastAPI + SUMO Docker + worker), Redis + Supabase wired; SUMO pre-warm on deploy | Jerico | First time the cloud path is exercised end-to-end. |

### Gate 4 — API checkpoint
- [ ] `POST` a scenario → WebSocket streams playback frames then five dimension results then a synthesis narrative.
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
| SUMO cold-start on Fly.io consumes the 90 s budget | **High** | Pre-warm container + hot nightly baseline + delta runs; profile first at Gate 2, attack at Gate 6. |
| BIR zonal-values PDF is scan-only / not machine-readable | Medium | CCHAIN RWI + nighttime lights as spatial proxy; flag `ECON-1` confidence **L** with honest UI label (this is the product's differentiator working as designed). |
| Gemini 3.1 Flash-Lite rate limits on the 500-persona batch | Medium | Generate once, cache to Redis (`personas:iloilo:v1`); reuse the same pool for all demo runs. |
| Phase 2 overruns on SUMO network-import complexity | Medium | Timebox at Gate 2; fallback = NetworkX graph + synthetic trajectory good enough to demo the five modules and the glass-box story. |
| Mode-share calibration is literature-derived, not a live travel survey | Ongoing | Carry Behavioral behavior at **M**; show the H/M/L label honestly. Bias auditor + confidence layer turn this into a trust feature, not a hidden gap. |
| Nested app + docs in one repo blurs concerns (and `FMD/` is a *separate* nested repo) | Low | Resolved the two-repo sync risk by nesting — `app/` shares the clone + `data/`. Keep app changes scoped to `app/`; never `git add FMD`. If the app later needs its own CI/remote, split it out then. |

---

## Critical path, in one line

> Scaffold → SUMO network import → **baseline trajectory (profiled)** → five glass-box modules → streaming API → frontend on live events → end-to-end **< 90 s** → one polished scenario + one real planner.

The single gating dependency is the **baseline trajectory dataset** (Phase 2): every module and the entire latency strategy hang off it. Everything in Track B parallelizes around it.
