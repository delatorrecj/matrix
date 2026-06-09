# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This is the **planning and documentation workspace for MATRIX** (Multi-Agent Twin for Routing & Infrastructure eXchange) — a pre-construction infrastructure impact simulator built by **Team ATLAN** (Polytechnic University of the Philippines) for the **ASEAN AI Hackathon 2026**, Smart Cities track, piloting in **Iloilo City**.

**Application code now lives in the nested [`app/`](app/) monorepo** (scaffolded 2026-06-03 per [docs/implementation-plan-matrix.md](docs/implementation-plan-matrix.md) Phase 0) — **nested in this repo** (one clone, data co-located), *not* a separate repo despite the earlier plan. The repo root still holds the spec, the data-source catalog, and the `docs/` suite. The code is **substantially built through Milestone B** (CR-004, 2026-06-07): the glass-box kernel, all five impact modules, the WebSocket API, the Gemini orchestrator + synthesis, and the Next.js + Deck.gl frontend are implemented end-to-end. See **["Working in `app/`" below](#working-in-app-the-code)** for the code's actual state, the commands, and the guardrails.

## Read this first

[MATRIX.md](MATRIX.md) is the **canonical product + technical specification** and the single source of truth for the project's vision, architecture, stack, and roadmap. Read it before doing substantive work. Key companion docs:

- [MATRIX_Iloilo_Data_Sources.md](MATRIX_Iloilo_Data_Sources.md) — tiered catalog of every Iloilo data source, with access method, license, confidence tier, and the **OSM bounding boxes** for the pilot area.
- [`reference/PUP-ATLAN_TECHNICAL ROADMAP TEMPLATE _ AAIH 2026.md`](<reference/PUP-ATLAN_TECHNICAL ROADMAP TEMPLATE _ AAIH 2026.md>) — the **filled** AAIH roadmap deliverable (deadline May 17, 2026).
- [`reference/TECHNICAL ROADMAP TEMPLATE _ AAIH 2026.md`](<reference/TECHNICAL ROADMAP TEMPLATE _ AAIH 2026.md>) — the blank AAIH template it was filled from.
- [`docs/index.md`](docs/index.md) — the **FMD documentation suite** (PRD, SDD, DSD, Methods/glass-box ledger, QAD, SAD, BUILD, CLR, GTM, OPS, plus RFC-001 on the real-time pipeline) and its **§0 source-of-truth map**. For *what / how / test / comply* detail the `docs/` suite is canonical and de-duplicated; **MATRIX.md owns vision + business case (it serves the BRD role)**. Read §0 first to know which doc owns which fact.
- [`data/READINESS.md`](data/READINESS.md) — per-dimension data confidence map (what's in hand vs. scripted vs. outreach-only). The bridge between INVENTORY and the spec: it declares the confidence floor each impact module must advertise.

> **The filled roadmap predates the current vision.** It still describes the older "ATLAN" framing (transit-only simulator, Gemini 1.5 Pro, reactive "behavioral nudges"). MATRIX.md **supersedes** it — see MATRIX.md Appendix A for the full list of pivots. When the two disagree, MATRIX.md wins. Do not reintroduce the older framing.

## Product architecture (the big picture)

MATRIX is **one simulation kernel feeding five impact modules** — this is the central architectural commitment and the reason results stay internally consistent. A single SUMO + LLM-persona run produces one unified per-agent trajectory dataset; all five impact modules score *that same simulated reality*:

```
NL query / map drop → Gemini orchestrator → UNIFIED SIMULATION KERNEL (SUMO + persona pool + bias auditor)
  → one trajectory dataset → [Behavioral | Social | Economic | Ecological | Societal] modules run in parallel
  → synthesis agent → Next.js + Deck.gl real-time visualization
```

Every dimension carries an **explicit confidence level (High/Medium/Low)**. Confidence-anchored, honestly-bounded outputs (ranges, not false-precision point estimates) and the **bias auditor** (mode-share anchoring, public audit log) are first-class product features, not optional polish — preserve them in any doc or code you produce.

## Working in `app/` (the code)

`app/` is a **uv (Python) monorepo** (`apps/api`, `apps/web`, `packages/kernel`, `packages/data`). The build's source of truth is the `docs/` suite; [`app/AGENTS.md`](app/AGENTS.md) is the in-repo quick-reference (materialized from [`docs/build-matrix.md`](docs/build-matrix.md)), and [`docs/implementation-plan-matrix.md`](docs/implementation-plan-matrix.md) is the phase-gated *when / done-when*.

**Current state — Milestone A + B done (CR-004, 2026-06-07).** The kernel's glass-box **contract** (`packages/kernel/matrix_kernel/results.py`, `DimensionResult`) is implemented and tested. Baseline caching, demand generation, persona pool generation, the TraCI delta runner, and the `Trajectory` schema are fully implemented. The five `modules/*.py` (Behavioral, Ecological, Social, Economic, Societal) are implemented with Phase 3 equations and return valid glass-box results. The WebSocket progressive API is wired (`apps/api`: `/health`, `/scenario`, `/simulate/{id}` streaming `ACCEPTED→PLAYBACK_FRAME→DIMENSION_RESULT×5→SYNTHESIS→DONE`), with the Gemini 3.1 Pro orchestrator + synthesis (`google-genai`) and citation guard. The frontend (`app/apps/web`) **is scaffolded and implemented** — Next.js 14 + Deck.gl `TripsLayer` + a real glass-box `InspectDrawer`, bias-audit log, validation panel, and Playwright e2e (see [`app/apps/web/SCAFFOLD.md`](app/apps/web/SCAFFOLD.md) for its generation provenance). Remaining roadmap work: mode-share calibration and the `qad-matrix` validation gates (Calderon-2014 RMSE, 2024 flood back-test) — both *planned, not yet shipped*.

**Tests: 23 pass with `eclipse-sumo` + Redis up** (the project `.venv` bundles SUMO; `uv run pytest` syncs it). The 6 SUMO-dependent test modules guard their import with `pytest.importorskip("sumo")`, so a **bare** `python -m pytest` with no SUMO **skips them cleanly** → **15 passed, 7 skipped** (no collection errors). With SUMO but Docker/Redis down, the integration tests skip (≈20 passed, 3 skipped). See [`docs/qad-matrix.md`](docs/qad-matrix.md).

**Two guardrails govern any code here** (full text in [`app/AGENTS.md`](app/AGENTS.md)):
1. **Glass box (PRD-F14).** No number ships without `equation_id` + `input_dataset_ids` + a *computed* confidence (never a guessed label), and it must resolve under the UI's Inspect drawer. The LLM narrates and cites — it **never originates a number**. Equations live in [`docs/methods-matrix.md`](docs/methods-matrix.md) (**Locked**); read it before coding any module. The `glass-box-auditor` agent blocks violations.
2. **Verify-live-before-coding.** Confirm framework conventions against the **pinned version's** official docs before writing — do **not** emit framework code from training memory. Known traps: `google-genai` (not `google-generativeai`), `motion/react` (not `framer-motion`), Tailwind v4 `@tailwindcss/postcss`, `next/font` (not `<link>`). Never Gemini 1.5/2.0.

**Build agents** live at the repo root [`.claude/agents/`](.claude/agents) so they're discoverable from `D:\PROJECTS\matrix`: `module-kernel-builder`, `glass-box-auditor` (gate), `frontend-3d-builder`, `eval-test-runner` (gate), `data-pipeline-runner`. Both gating agents must PASS before a merge.

### Commands

```bash
# Kernel tests. app/.venv is a uv venv with NO pip; use uv, or any global pytest
# (pyproject sets pythonpath=["."], so it imports matrix_kernel from the source tree).
cd app/packages/kernel
uv run pytest                 # full suite — syncs eclipse-sumo; 23 pass with Redis up
python -m pytest -q           # bare/no-SUMO: SUMO tests skip cleanly → 15 passed, 7 skipped
python -m pytest tests/test_results.py::test_low_confidence_is_directional   # single test

# Kernel Baseline & Demand Generation
uv run python -c "from matrix_kernel.baseline import run_nightly_baseline; print(run_nightly_baseline())"
uv run --directory packages/kernel python -X utf8 -u packages/data/build_demand.py

# API — FastAPI + WS, kernel + Gemini wired
cd app/apps/api && uvicorn matrix_api.main:app --reload      # GET /health -> {"status":"ok",...}

# Local datastores — Postgres+PostGIS :5432, Redis :6379, Chroma :8001
cd app && docker compose up -d          # `down -v` to wipe volumes

# Frontend — Next.js 14 + Deck.gl (scaffolded)
cd app/apps/web && npm install && npm run dev   # http://localhost:3000 ; npm run test:e2e for Playwright
```

No Python linter/formatter is wired yet, and `apps/web` brings its own ESLint — don't introduce tooling without asking.

## Locked technical decisions (do not silently revert)

These were chosen deliberately with documented justification (MATRIX.md §6). Treat them as invariants unless the user explicitly reopens the decision:

- **Simulation engine: Eclipse SUMO** (via TraCI Python API) — *not* OASIS or MiroFish (those simulate social-media dynamics, not physical urban agents).
- **LLMs: Gemini 3.1 Pro** (orchestration/synthesis) + **Gemini 3.1 Flash-Lite** (high-volume persona generation). **Never** Gemini 1.5 (shut down) or 2.0 (shut down June 1, 2026). The PUP-ATLAN roadmap's "Gemini 1.5 Pro" is stale.
- **Unified kernel → five modules**, not five independent simulators (avoids cross-dimension contradictions).
- **Real-time interactive visualization** with a hard **90-second end-to-end latency budget** (Option C). Hit it via pre-warmed persona pool, delta simulations against a nightly baseline, parallel modules, and streaming/progressive UI.
- **Planned stack:** Next.js 14 (App Router) + Tailwind + shadcn/ui frontend; Mapbox GL JS + Deck.gl (TripsLayer) for animated playback; FastAPI + WebSocket backend; Supabase Postgres + ChromaDB (GraphRAG/LightRAG) + Redis; XGBoost baseline forecaster. Deploy targets: Vercel + Fly.io.
- **Pilot city is Iloilo.** Geographic scaling is intended to be API-level (swap OSM bbox) and behavioral scaling prompt-level (reweight persona archetypes) — keep the engine city-agnostic.

## The FMD framework (`FMD/` — a separate, nested repository)

`FMD/` is a **distinct git repository vendored into this folder** (its own remote `github.com/delatorrecj/fmd.git`, its own history; it appears as *untracked* in the parent's `git status` and is **not** a submodule). It is the **Foundational Matrix Documents** system: a suite of documentation templates plus a trigger-phrase routing layer for generating a project's formal doc suite (BRD, PRD, DSD, SDD, RFC, QAD, SAD, BUILD, CLR, GTM, OPS, plus CR/PM/INDEX).

- When the user asks for a formal document ("write a PRD", "architect the system / write an SDD", "compliance review", etc.), **follow [FMD/AGENTS.md](FMD/AGENTS.md)** (its canonical operating guide) and [FMD/CLAUDE.md](FMD/CLAUDE.md) (Claude-Code-specific notes). That guide owns the trigger→template mapping, project-scale rules, sequencing, and living-docs/traceability conventions — do not duplicate them here.
- Generated documents for MATRIX live in the **`docs/`** folder at this repo root (e.g. `docs/prd-matrix.md`), per FMD's naming convention. The full suite (PRD · SDD · DSD · Methods · QAD · SAD · BUILD · CLR · GTM · OPS · RFC-001) was generated 2026-06-02. **PRD, SDD, and methods-matrix are Locked** (CR-001, 2026-06-03); the rest are Draft. See [`docs/index.md`](docs/index.md) for current status.
- The `FMD/*_Template.md` files are **canonical sources** — never hand-edit them as part of MATRIX work, and never delete them (FMD's `exit fmd` cleanup only removes generated `docs/` output, never templates).
- The editor rule files under `FMD/.cursor/` and `FMD/.windsurf/` are thin pointers to FMD/AGENTS.md and apply only when operating inside FMD.

## Git: two independent repositories in one folder

Commands run from the root operate on the **matrix** repo (`github.com/delatorrecj/matrix.git`) and **do not see `FMD/`'s contents** (FMD is ignored as a nested clone). To act on FMD's own files and history, target it explicitly with `git -C FMD …`. Keep changes to the two repos in separate commits to their respective remotes.

## Conventions

- This is a docs-first repo: deliverables are Markdown (and PDF exports for hackathon submission). Match the existing register of [MATRIX.md](MATRIX.md) — precise, sourced, confidence-aware, no false precision.
- Cite sources and tag confidence/data tiers when adding claims to the spec or data catalog, consistent with how MATRIX.md and the data-sources file already do it.
- Honor real-world constraints already documented (FOI timing for LTFRB data, Sentinel-2 cloud gaps, RA 10173 / Philippine Data Privacy Act, OSM ODbL attribution) rather than papering over them.

## Data acquisition (`data/`)

Iloilo pilot data lives under `data/` — an **open-data-first, contact-free** workflow. Orient from [data/INVENTORY.md](data/INVENTORY.md) (what we have) and [data/READINESS.md](data/READINESS.md) (per-dimension confidence). Raw data is **gitignored** (large/third-party/regenerable) — reproduce it with the idempotent scripts in `data/fetch/`:

```
python data/fetch/fetch_open.py       # direct HTTP + OSM Overpass; stdlib only
python data/fetch/fetch_economic.py   # PSA OpenStat + World Bank APIs; stdlib only
python data/fetch/fetch_geo.py        # Overture/rasters; needs: pip install overturemaps
python data/fetch/scrape_lptrp.py     # transit routes (LPTRP)
```

Tier B API keys go in a gitignored `data/.env` (template `data/fetch/.env.example`). **Four economic datasets require manual browser download** (PSA/BIR sites block scripts with 403): BIR zonal values RDO 74, PSA FIES 2023, PSA ASPBI 2023, DOT visitor arrivals 2024 — see INVENTORY.md for exact URLs and save targets under `data/raw/economic/`. Tier C outreach drafts in `data/outreach/` are last-resort fidelity upgrades — each has an open substitute, so none blocks the build. **Prefer newest vintages** (e.g. 2024 POPCEN-CBMS, not 2020). [MATRIX_Iloilo_Data_Sources.md](MATRIX_Iloilo_Data_Sources.md) keeps the source rationale; INVENTORY tracks acquisition. The single richest source is **Project CCHAIN** (barangay-level Iloilo data across climate/air/wealth/health/buildings).
