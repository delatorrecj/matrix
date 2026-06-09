# MATRIX — application monorepo

The build for **MATRIX** (Multi-Agent Twin for Routing & Infrastructure eXchange).
Nested inside the planning repo so the docs and the Iloilo data sit one clone away.

> **Source of truth is the docs suite at [`../docs/`](../docs/index.md).** Read
> [`../docs/index.md`](../docs/index.md) §0 first (the canonical map), then build per
> [`AGENTS.md`](AGENTS.md). The *what / when / done-when* is
> [`../docs/implementation-plan-matrix.md`](../docs/implementation-plan-matrix.md).

## Layout

```
app/
├── apps/
│   ├── web/      Next.js 14 + Deck.gl frontend   (built — InspectDrawer, TripsLayer, e2e)
│   └── api/      FastAPI + WebSocket gateway      (health + /scenario + /simulate stream + Gemini)
├── packages/
│   ├── kernel/   SUMO/TraCI kernel + 5 glass-box impact modules (Phase 2–3)
│   │   └── data/ iloilo.net.xml + iloilo.taz.xml (produced by Phase 1 pipeline)
│   └── data/     processing pipeline → SUMO net + PostGIS + GraphRAG (Phase 1)
│       └── build_network.py  Stage 1–3: OSM JSON → net.xml + TAZ (run from app/)
└── AGENTS.md     build guardrails (materialized from ../docs/build-matrix.md)
```

Build agents live at the **repo root** [`../.claude/agents/`](../.claude/agents) so Claude
Code discovers them when you run from `D:\PROJECTS\matrix`.

## Quickstart

```bash
# Kernel — glass-box contract + 5 impact modules. 23 tests pass with eclipse-sumo + Redis.
# app/.venv is a uv venv (no pip). Use uv run, which syncs the SUMO wheel:
cd packages/kernel
uv run pytest           # full suite — 23 pass with Redis up (syncs eclipse-sumo on first run)
# Bare pytest w/o SUMO is safe: the 6 SUMO-dependent modules skip cleanly.
python -m pytest -q     # → 15 passed, 7 skipped (no collection errors)

# One test:
python -m pytest tests/test_results.py::test_low_confidence_is_directional

# API — health + /scenario + streaming /simulate (Gemini orchestrator/synthesis wired)
cd apps/api && uvicorn matrix_api.main:app --reload
#   GET http://localhost:8000/health  ->  {"status":"ok",...}

# Phase 1 data pipeline — build SUMO network + TAZ
#   (run from app/; needs Docker: docker compose up -d for datastores, SUMO image for Stage 2)
python packages/data/build_network.py --stage 1   # JSON -> iloilo.osm (pure Python)
python packages/data/build_network.py --stage 2   # netconvert via Docker -> net.xml
python packages/data/build_network.py --stage 3   # TAZ from barangay polygons
python packages/data/build_network.py             # all three stages + validation

# Local datastores — Postgres+PostGIS :5432, Redis :6379, Chroma :8001
docker compose up -d    # from app/  (down -v to wipe volumes)

# Frontend — Next.js 14 + Deck.gl (built; see apps/web/SCAFFOLD.md for provenance)
cd apps/web && npm install && npm run dev   # http://localhost:3000 ; npm run test:e2e
```

## Non-negotiables (full text in [AGENTS.md](AGENTS.md))

1. **Glass box** — no number ships without `equation_id` + `input_dataset_ids` + a
   *computed* confidence. `DimensionResult` enforces this at construction.
2. **One kernel → five modules** — never fork into five simulators.
3. **Verify-live-before-coding** the fast-movers (Gemini SDK, Next.js, Tailwind v4,
   Deck.gl). Never Gemini 1.5/2.0.
4. **90-second** end-to-end budget.
