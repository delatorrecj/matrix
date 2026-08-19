# MATRIX onboarding primer

**Audience:** a teammate who will answer technical questions about how MATRIX is built.  
**Status:** working study guide, not a Locked FMD doc.  
**Written:** 2026-08-16.

Facts here are a cache of [MATRIX.md](../MATRIX.md), [sdd-matrix.md](sdd-matrix.md), [build-matrix.md](build-matrix.md), and the as-built `app/` tree. If this file and a Locked doc disagree, the Locked doc wins. Terms live in [glossary-matrix.md](glossary-matrix.md). Equations live in [methods-matrix.md](methods-matrix.md).

Read this once. Then use the glossary and methods ledger as lookups.

---

## 1. What MATRIX is

MATRIX (Multi-Agent Twin for Routing & Infrastructure eXchange) is a **pre-construction infrastructure impact simulator** for ASEAN cities, piloted in **Iloilo City**. Team **ATLAN** (PUP) built it for the ASEAN AI Hackathon 2026, Smart Cities track.

A planner types a natural-language question or drops a project on the map. The system simulates how people move, scores the *same* simulated day across five impact dimensions, and returns a cited, confidence-bounded brief in under 90 seconds, with animated trip playback.

The acronym says "Twin." The product is **not** a live digital twin. It uses static and historical data, not a real-time city feed.

**Who it is for:** Iloilo CPDO and regional agencies, developers doing site selection, civic and academic reviewers who want inspectable numbers.

---

## 2. The problem it is built to solve

ASEAN suburban cities still approve infrastructure from siloed paper studies: traffic in one office, EIA in another, economics at Treasury. Those documents do not share one physics. Second-order effects (jeepney demand, vendor displacement, flood corridor blockage) never meet in one run.

Existing tools (PTV Vissim, Aimsun, CityEngine) need specialists. MATRIX accepts "what if we put a school here?" from a planner.

The architectural answer is one kernel, five scorers. Not five simulators.

---

## 3. Pipeline mental model

```
NL query or map drop
  → POST /scenario (orchestrator: Azure OpenAI gpt-5.4 + GraphRAG + gazetteer)
  → WS /simulate/{id}
  → unified kernel: SUMO/TraCI + persona pool + bias auditor
  → one Trajectory (per-agent, per-tick)
  → five modules in parallel
  → synthesis brief (LLM narrates and cites; never invents a number)
  → Next.js + Deck.gl playback
```

As-built WebSocket events (use these names in a bug report or a judge Q&A):

```
ACCEPTED → [QUEUED] → PLAYBACK_FRAME* → EDGE_COUNTS → DIMENSION_RESULT ×5 → SYNTHESIS → DONE
```

`ERROR` can fire at any point. Name the **last event received** when something stalls.

**Primary UI path:** `/app` (cockpit: NL, presets, map right-click). `/builder` is a secondary structured composer. Landing `/` is marketing.

---

## 4. Ideas you must not break

**Glass box (PRD-F14).** Every number on screen carries `equation_id`, `input_dataset_ids`, and a *computed* confidence, and must open in Inspect. If Inspect is dead, the feature is not done.

**LLM role.** Orchestrator parses the scenario into a structured plan. Synthesis writes the brief. Personas are a static literature pool by default (`MATRIX_PERSONA_LLM=1` turns on LLM generation). The model never originates a metric.

**Citation guard.** Numeric claims in the brief must cite a real `[EQUATION_ID]`. Uncited numbers are blocked.

**Confidence.** `H` / `M` / `L`. Low is directional only, not a false-precision float. Some equations are *method-capped* at Medium even when the input data is High.

**One trajectory.** Behavioral cannot say "trips up" while Ecological says "emissions flat" because they ran different worlds. They score one SUMO run.

**90-second budget (single-user).** Hit with four levers: pre-warmed personas, nightly baseline + delta, parallel modules, streaming UI. A cold run with no baseline is allowed to miss the budget and must be flagged, not hidden.

**City-agnostic engine.** Iloilo is the pilot. Scaling is swap OSM bbox + reweight personas, not a rewrite.

---

## 5. The five impact modules

One kernel run, five parallel Python scorers in `app/packages/kernel/matrix_kernel/modules/`. Payload names are lowercase.

| Dimension | Asks | Equation prefix | Typical confidence |
|-----------|------|-----------------|--------------------|
| Behavioral | How do trips, modes, and saturation change? | `BEH-` | High for network physics; BEH-4 gravity model is Low / provisional |
| Social | Who gains access, who is displaced? | `SOC-` | Medium |
| Economic | Land value, footfall, jobs | `ECON-` | Medium |
| Ecological | CO₂e, PM2.5, green cover, flood exposure | `ECO-` | High for ECO-1/3; Medium and method-capped for ECO-2/4 |
| Societal | Heritage, health proxy, walkability, composite | `SOCI-` | Medium |

Prefixes are easy to mistype (`ECO-` vs `ECON-`, `SOC-` vs `SOCI-`). Copy the id from Inspect.

Several constants are **named provisional proxies** (vendors per closed lane, PHP per trip, PM2.5-from-CO₂e). A number that "looks arbitrary" is often one of these, declared in `assumptions`, not a silent fudge.

---

## 6. Repo map

| Path | What it is |
|------|------------|
| `MATRIX.md` | Vision, why it wins, locked stack decisions |
| `docs/` | FMD suite: PRD, SDD, methods, QAD, DSD, RFC-001, CRs |
| `app/` | Nested uv monorepo. This is the product code. |
| `app/apps/web` | Next.js 14 client |
| `app/apps/api` | FastAPI + WebSocket + orchestrator/synthesis |
| `app/packages/kernel` | SUMO runner, modules, glass-box types, bias auditor |
| `app/packages/data` | Network/demand build scripts |
| `data/` | Iloilo acquisition. Raw files are gitignored. Reproduce with `data/fetch/` |

The FMD documentation engine is a **sibling clone** at `D:\PROJECTS\FMD` (v1.28.1), not nested under this repo. Use it only when writing or amending formal docs.

---

## 7. Stack (technical Q&A)

This is the section to rehearse. Canonical architecture: [sdd-matrix.md](sdd-matrix.md) §1–8. Pinned conventions: [build-matrix.md](build-matrix.md) §3. Latency: [rfc-matrix-realtime-pipeline.md](rfc-matrix-realtime-pipeline.md). Deploy: [cr-011-huggingface-migration.md](cr-011-huggingface-migration.md). LLM client: [cr-009-azure-foundry-client.md](cr-009-azure-foundry-client.md).

### 7.1 Layers in one picture

```
Browser
  Next.js 14 App Router + React 18 + Tailwind v4 + shadcn/ui
  Mapbox GL / MapLibre + Deck.gl 9 TripsLayer
        │  REST (create scenario) + WebSocket (run stream)
        ▼
FastAPI (uvicorn)  :8000
  Pydantic at the boundary
  openai.OpenAI(base_url=Foundry v1)  →  gpt-5.4  (parse + synthesis)
  citation_guard on the brief
        │
        ▼
matrix_kernel (Python 3.12)
  TraCI ↔ Eclipse SUMO  (physics)
  persona pool + bias_auditor
  five modules → DimensionResult
  XGBoost  (light corridor-volume prior on the nightly baseline, not the live sim)
        │
        ├── Redis     persona pool, nightly baseline, trajectory cache
        ├── ChromaDB  GraphRAG chunks (bge-small-en embeddings)
        └── Postgres+PostGIS  scenarios/runs/audit  OR in-memory fallback
```

Languages: **Python 3.12** on API and kernel, **TypeScript 5** on the web app. Package manager on the Python side is **uv**, not pip-in-venv as the default story.

### 7.2 Why this stack (judge-ready answers)

**Why SUMO, not an LLM "city simulator"?**  
SUMO (Simulation of Urban MObility, DLR) is a microscopic traffic simulator. Agents have routes, modes, and a network. TraCI is the Python control API: we perturb the network (close a lane, inject demand) and read back trajectories. An LLM cannot produce a reproducible per-tick trajectory you can cite. A pure-LLM sim would violate the glass box.

**Why SUMO, not OASIS or MiroFish?**  
Those model social-media / information dynamics. MATRIX needs physical urban agents on a road graph. Locked in MATRIX.md §6.

**Why one kernel feeding five modules?**  
If Behavioral and Ecological each ran their own sim, they could contradict. One `Trajectory` is the contract. Modules are scorers, not worlds.

**Why Azure OpenAI gpt-5.4, and why that client?**  
One deployment does orchestration, synthesis, and optional persona generation. Low call count per run (parse + synthesis) when personas stay static. The project left Gemini in CR-008. The Foundry **v1** endpoint is OpenAI-compatible. `openai.AzureOpenAI` appends `/deployments/...?api-version=` and **404s** on Foundry. Correct shape: `openai.OpenAI(base_url=…)`. That is CR-009. If someone asks "why not AzureOpenAI class?", that is the answer.

**Why FastAPI + WebSocket instead of request/response?**  
A 90 s run that returns one JSON blob at the end feels dead. The client starts `TripsLayer` on the first `PLAYBACK_FRAME` and fills dimension cards as each `DIMENSION_RESULT` arrives. REST is still used for `POST /scenario`, health, audit, feedback.

**Why Redis?**  
The 90 s budget is a cache budget. Personas are warmed once. The nightly baseline is the "as-is" city. Repeated runs hit a trajectory cache (warm ~48 s in the RFC reconciliation vs a 90 s SLO). Without Redis, every request looks like a cold SUMO run.

**Why Postgres + PostGIS, and why an in-memory fallback?**  
Scenarios have geometry. PostGIS is the right type. Hugging Face Spaces should not require a managed database, so `matrix_api/db.py` falls back to in-memory. Local `docker compose` still runs PostGIS 16. Prod persistence is ephemeral across Space restarts.

**Why Chroma + GraphRAG?**  
The orchestrator must ground place names and policy context in Iloilo material, not invent GIS ids. Embeddings are `bge-small-en` via sentence-transformers. Corpus is ingested at API startup so `retrieve()` is not an empty list. The **gazetteer** runs *before* the LLM and maps Hiligaynon / colloquial names to network ids. Current gazetteer ids are flagged provisional.

**Why Next.js 14 App Router, not a SPA glued to Leaflet?**  
App Router for routes (`/app`, `/scenario/[id]`, `/builder`). Deck.gl `TripsLayer` is the playback. Mapbox GL is the basemap; MapLibre is also in the tree. UI kit is shadcn on Tailwind **v4** (`@tailwindcss/postcss`, not the v3 plugin). Motion is `motion/react`, not `framer-motion`. Fonts are `next/font`, not a Google Fonts `<link>`.

**Why XGBoost if SUMO is the kernel?**  
XGBoost is a **light prior** on the nightly baseline: edge length / speed / lanes → expected volume. It is not the five-dimension scorer and not a substitute for TraCI. Say "baseline forecaster," not "the ML model that predicts impact."

**Why Vercel + Hugging Face Spaces?**  
Web is a Next app; Vercel is the natural host. The API image must include SUMO and Redis. That does not fit a typical serverless function, so the backend is one Docker Space (CR-011). Older docs mentioning Fly.io or Supabase are stale.

### 7.3 What each process does at runtime

| Process | Port (local) | Job |
|---------|--------------|-----|
| `apps/web` `next dev` | 3000 | Cockpit, map, Inspect, Summary/Analytics |
| `apps/api` uvicorn | 8000 | Parse scenario, run kernel, stream WS, synthesis |
| Postgres PostGIS | 5432 | Persist scenarios/runs if configured |
| Redis | 6379 | Personas, baseline, trajectory cache |
| Chroma | 8001 (host) → 8000 in container | Vector retrieve for orchestrator |

SUMO is not a Docker service in `app/docker-compose.yml`. Compose is **datastores only**. SUMO comes from the `eclipse-sumo` Python package / local SUMO install when the kernel actually runs.

Two local boots exist on purpose:

- **Dev up:** Docker + API + web, skip SUMO baseline and persona/GraphRAG warm. For UI work.
- **Simulate up:** Docker + nightly baseline in Redis + full API warm + web. For a real `/simulate`.

### 7.4 How a number gets on screen

1. TraCI writes a `Trajectory`.
2. A module applies a formula from methods-matrix (example: ECO-1 transport CO₂e from VKT × emission factors).
3. It returns a `DimensionResult`: `value`, `[lo, hi]` range, `confidence`, `equation_id`, `input_dataset_ids`, `assumptions`.
4. The API streams `DIMENSION_RESULT`.
5. The web formatter (`lib/format.ts`) kills false precision. Near-zero becomes "No meaningful change."
6. Synthesis may *describe* that number only with a citation the guard accepts.
7. Click Inspect: equation, datasets, confidence, assumptions.

If a judge asks "how do we know the AI is not making up the 14%?", walk that chain. The model is downstream of the kernel.

### 7.5 Hitting 90 seconds (what to say)

Budget from RFC-001 / SDD §7:

| Window | Stage |
|--------|--------|
| 0–5 s | Parse |
| 5–15 s | GraphRAG retrieve |
| 15–60 s | SUMO delta vs baseline |
| 60–80 s | Five modules in parallel |
| 80–90 s | Synthesis |

Levers: do not regenerate 200–500 personas per click; reweight the cached pool. Do not resimulate the whole city; perturb agents whose paths hit the project buffer. Stream early frames. Warm repeats are faster because Redis already has the trajectory.

Honest caveats you should volunteer: the SLO is **single-user**; multi-user needs a queue. Cold run without baseline is outside budget. VAL-01 vs Calderon counts is a **published FAIL** (live NRMSE vs threshold ≤ 0.30); corridor volumes are directional, not city-calibrated. VAL-02 flood IoU is `NOT_RUN` until a real Sentinel extent is wired. Gazetteer node ids are provisional.

### 7.6 API surface worth memorizing

| Call | Role |
|------|------|
| `POST /scenario` | NL or map → `scenario_id` + plan. Ambiguous → clarification, not a guess. |
| `WS /simulate/{scenario_id}` | Kernel + stream |
| `GET /health` | Dependency-aware |
| `GET /audit/{scenario_id}` | Public bias audit, including `adjustment_factors` |
| `GET /validation` | Gate status |
| `POST/GET /feedback` | CPDO loop (PRD-F20) |

Auth is env-gated API key, off by default for the public demo. Scenario POST is rate-limited to protect the Azure budget. No PII in the core sim; personas are synthetic; barangay aggregates, not people.

Bias auditor: if simulated mode share drifts more than ±3% from the Iloilo anchor (Calderon 2014, `ILOILO_MODE_SHARE`), it reweights and **logs** the factors. No silent correction. Default static pool is on-anchor by construction, so live reweight is most visible when LLM personas are on.

### 7.7 Frontend stack details

Pinned in `app/apps/web/package.json` as of this writing: Next **14.2.35**, React 18, Deck.gl **9.3.x**, Tailwind **4.3**, Mapbox GL 3, `motion` 12, Vitest + Playwright.

CR-010 UX you should be able to name: Summary-first cards, interpreted Analytics view, Settings (theme + EN/Hiligaynon), BLUF synthesis (`HEADLINE → WHAT WE SIMULATED → KEY FINDINGS → RECOMMENDATION → KEY RISK`), then `=== HILIGAYNON ===` and the translation, plus a print-scoped one-page `ScenarioBrief`.

If the API is down, the UI can enter **Sample mode**, labeled illustrative-only.

### 7.8 Data path (not on the hot path)

Fetch scripts under `data/fetch/` pull OSM, PSA OpenStat, etc. Some economic files are **manual browser downloads** because the sites 403 scripts. Confidence per dimension is [data/READINESS.md](../data/READINESS.md). Inventory is [data/INVENTORY.md](../data/INVENTORY.md). Project CCHAIN is the richest barangay-level bundle.

Runtime simulation reads processed network/demand and Redis caches. It does not scrape the web per scenario.

### 7.9 Stale answers to refuse

| If someone says | You say |
|-----------------|--------|
| Gemini 1.5 Pro / `google-genai` | Migrated off in CR-008. Azure OpenAI gpt-5.4 only. |
| `openai.AzureOpenAI` | 404s on Foundry v1. Use `OpenAI(base_url=…)`. |
| Five independent sims | One kernel, five modules. |
| Live twin / real-time traffic feed on the critical path | Historical + static; OpenWeather/TomTom are optional Tier B, not the kernel. |
| Fly.io / Supabase | Removed. Vercel + HF Spaces. |
| Tailwind v3 plugin, `framer-motion`, Google Fonts `<link>` | v4 `@tailwindcss/postcss`, `motion/react`, `next/font`. |
| LLM writes the 14% | Kernel + equation_id. LLM cites. |
| VAL-01 proves we are calibrated | VAL-01 is a published FAIL (live NRMSE vs 0.30). Volumes are directional. |

### 7.10 Tests (so you do not overclaim)

Kernel, no SUMO: `python -m pytest` from `app/packages/kernel` → SUMO tests skip via `importorskip`. API has its own `apps/api` suite. Web: `next build` is in the eval gate; Playwright e2e; Vitest has been flaky on Windows/node 22. Merge requires glass-box-auditor and eval-test-runner both PASS.

---

## 8. Where to go next

| Need | Open |
|------|------|
| Term lookup | [glossary-matrix.md](glossary-matrix.md) |
| Feature ids `PRD-F#` | [prd-matrix.md](prd-matrix.md) |
| Schema, endpoints, AI safety | [sdd-matrix.md](sdd-matrix.md) |
| Formulas | [methods-matrix.md](methods-matrix.md) §3 |
| UI tokens and routes | [dsd-matrix.md](dsd-matrix.md) |
| 90 s pipeline | [rfc-matrix-realtime-pipeline.md](rfc-matrix-realtime-pipeline.md) |
| Commands | Root [CLAUDE.md](../CLAUDE.md), [app/AGENTS.md](../app/AGENTS.md) |
| Which doc owns a fact | [index.md](index.md) §0 |
