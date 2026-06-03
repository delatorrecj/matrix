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
│   ├── web/      Next.js 14 + Deck.gl frontend   (scaffold via SCAFFOLD.md — Phase 5)
│   └── api/      FastAPI + WebSocket gateway      (health + WS skeleton — Phase 4)
├── packages/
│   ├── kernel/   SUMO/TraCI kernel + 5 glass-box impact modules (Phase 2–3)
│   └── data/     processing pipeline → SUMO net + PostGIS + GraphRAG (Phase 1)
└── AGENTS.md     build guardrails (materialized from ../docs/build-matrix.md)
```

Build agents live at the **repo root** [`../.claude/agents/`](../.claude/agents) so Claude
Code discovers them when you run from `D:\PROJECTS\matrix`.

## Quickstart (Gate 0)

```bash
# Kernel — the glass-box contract + module stubs (tests pass today)
cd packages/kernel && pip install -e ".[dev]" && pytest      # 5 passing contract tests

# API — health + WS skeleton
cd ../../apps/api && pip install -e . && uvicorn matrix_api.main:app --reload
#   GET http://localhost:8000/health  ->  {"status":"ok",...}

# Frontend — generate from the live tooling, then verify versions
#   see apps/web/SCAFFOLD.md
```

## Non-negotiables (full text in [AGENTS.md](AGENTS.md))

1. **Glass box** — no number ships without `equation_id` + `input_dataset_ids` + a
   *computed* confidence. `DimensionResult` enforces this at construction.
2. **One kernel → five modules** — never fork into five simulators.
3. **Verify-live-before-coding** the fast-movers (Gemini SDK, Next.js, Tailwind v4,
   Deck.gl). Never Gemini 1.5/2.0.
4. **90-second** end-to-end budget.
