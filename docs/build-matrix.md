# Project Build Guide

**Project:** MATRIX
**Date:** 2026-06-02
**Version:** 0.1
**Owner:** Jerico (Team ATLAN)
**Status:** Active
**Last reconciled:** 2026-06-09 — reconciled with Phase 4/5/6 integrations (Vercel/Fly.io, Next.js frontend, Playwright & Vitest testing suites).
**PRD:** [prd-matrix.md](prd-matrix.md) · **SDD:** [sdd-matrix.md](sdd-matrix.md) · **SAD:** [sad-matrix.md](sad-matrix.md)

> The spec→code bridge. Materialized to the app monorepo's root **[`../app/AGENTS.md`](../app/AGENTS.md)** at scaffold — the app is **nested at `app/`** in this repo (one clone), not a separate repo. Owners per [PRD §10](prd-matrix.md).

---

## 1. How to Build From These Docs

Source of truth is the suite. Read order each session:
1. **[index.md](index.md)** — §0 source-of-truth map + what's stale. Start here.
2. **[PRD](prd-matrix.md)** — what + why (features `PRD-F#`, stories `US-##`).
3. **[SDD](sdd-matrix.md)** — architecture, schema, APIs, AI safety.
4. **[RFC](rfc-matrix-realtime-pipeline.md)** — the 90 s pipeline implementation.
5. **[DSD](dsd-matrix.md)** — UI, 3D twin, routes & actions.
6. **[methods-matrix](methods-matrix.md)** — equations + provenance (glass-box). **Read before coding any module.**
7. **This guide** — stack, patterns, guardrails.

**PRD, SDD, and methods-matrix are Locked** (CR-001, 2026-06-03); subsequent changes require a Change Record. The remaining docs are Draft. If reality diverges from a Locked doc, file a Change Record (`docs/cr-*.md`) — don't silently code around it.

### Traceability — "to build X, read Y"
| To implement… | Read | Verify against |
|---|---|---|
| A feature `PRD-F#` | PRD §3/§4 → SDD components → RFC | QAD scenarios tagged `US-##` |
| An impact module | **methods-matrix §3 (its equation)** → SDD §3 | QAD §8 TRACE gates |
| A schema change | SDD §3 | SDD migration strategy |
| The 90 s pipeline / WS | RFC §2/§3 | QAD `PERF-01` |
| An AI behavior | SDD §8/§8.1 → RFC §5 | QAD §7 evals |
| A UI surface | DSD §4/§9–12 + PRD §5 | DSD a11y self-check |
| Phase order / gate criteria | [implementation-plan-matrix.md](implementation-plan-matrix.md) | Gate checklists per phase |
| Which file to open next (critical path) | [implementation-plan-critical-path.md](implementation-plan-critical-path.md) | Milestone A DoD |
| Phase 1 data pipeline (`iloilo.net.xml`) | `app/packages/data/build_network.py` — Stage 1–3 | Gate 1 checklist |

---

## 2. Subagents
Specialist build agents are in the [SAD](sad-matrix.md), materialized to `.claude/agents/` at scaffold. **`glass-box-auditor` + `eval-test-runner` gate every merge** (both must PASS). Spawn per SAD §4.

---

## 3. Stack Currency & Deprecations

> **The rule:** do **not** trust training memory for fast-moving frameworks. Before writing framework code, **verify the current convention against the pinned version's official docs.** If you can't verify, say so — never emit a plausible-but-stale API. This register **overrides** model memory.

### Pinned stack *(versions to confirm + date at monorepo scaffold — do not assume from memory)*
| Layer | Technology | Pin | Verify at scaffold |
|-------|------------|-----|--------------------|
| Language | Python · TypeScript | 3.12 · 5.x | ✔ |
| Sim kernel | Eclipse SUMO (TraCI) + OSMnx | latest stable | eclipse.dev/sumo |
| LLM | **Gemini 3.1 Pro + Flash-Lite** via **`google-genai`** SDK | 3.1 | ai.google.dev |
| Frontend | Next.js (App Router) + Tailwind + shadcn/ui | 14+ / v4 | nextjs.org, tailwindcss.com |
| Map/3D | Mapbox GL JS + Deck.gl (TripsLayer) | current | deck.gl |
| Backend | FastAPI + uvicorn + websockets | current | fastapi.tiangolo.com |
| Data | Supabase (Postgres + PostGIS) · ChromaDB · Redis | current | — |
| ML | XGBoost · sentence-transformers (`bge-small-en`) | current | — |
| Testing | Vitest + Playwright | current | vitest.dev, playwright.dev |

### Deprecations — DO NOT use the stale form (overrides memory)
| ❌ Stale | ✅ Current | Why |
|---------|-----------|-----|
| Gemini **1.5 / 2.0** | **Gemini 3.1** (Pro + Flash-Lite) | 1.5 shut down; 2.0 shuts down 2026-06-01 — before submission (MATRIX.md §6) |
| `google-generativeai` SDK | **`google-genai`** (unified SDK) | verify import shape against current docs |
| **OASIS / MiroFish** as the simulator | **SUMO** | OASIS/MiroFish simulate social media, not urban agents (MATRIX.md §6) |
| Tailwind v3 PostCSS plugin (`tailwindcss`) | **`@tailwindcss/postcss`** (v4) | taste-skill §3.A |
| `framer-motion` import | **`motion/react`** | taste-skill §3.A |
| `<link>` Google Fonts | **`next/font`** (self-host) | taste-skill §3.A; Geist + Geist Mono |
| Five independent simulators | **one unified kernel → 5 modules** | cross-dimension consistency (PRD-F1) |
| A number emitted without provenance | **always `equation_id` + `input_dataset_ids` + confidence** | glass-box (PRD-F14) |

**Verify-live-before-coding:** the Gemini SDK, Next.js, Deck.gl, Tailwind. **Self-anneal:** add a row whenever drift is caught.

---

## 4. Golden-Path Patterns

### Glass-box impact module *(canonical — our convention, version-stable)*
Every module returns a result that carries its own provenance. This is the shape `module-kernel-builder` (SAD-A1) produces:
```python
def score(dim_input, datasets) -> DimensionResult:
    value = sum(vkt[k] * EF[k] for k in modes)          # equation ECO-1 (methods-matrix §3.2)
    lo, hi = ensemble(value, assumptions)               # PRD-F15 earned confidence
    return DimensionResult(
        dimension="ecological", value=value, range=(lo, hi),
        confidence=confidence_rubric(datasets),          # methods §2 — computed, not guessed
        directional=(confidence == "L"),
        equation_id="ECO-1",
        input_dataset_ids=["CCHAIN", "OSM-ILO", "WHO-EMEP"],
        references=["WHO-EMEP", "Calderon2014"],
    )
```
*Why:* no number ships without its equation, inputs, and confidence. The `glass-box-auditor` (SAD-A2) rejects results missing these.

### Gemini call (synthesis) — *shape only; verify `google-genai` API before coding*
Pattern: cached static system prefix (Iloilo context + mode-share anchors) + retrieved GraphRAG chunks; **the narrative must cite `equation_id` + `dataset_ids`** for any number (citation guard, methods §4); on 429 → backoff + cached parse. *Confirm the exact SDK call shape against current `google-genai` docs (§3) — do not copy from memory.*

### WebSocket streaming consumer (frontend) — *verify Deck.gl/Next version*
Pattern: consume `WS /simulate/{id}` events (RFC §3); start TripsLayer playback on first `PLAYBACK_FRAME`; fill each Dimension Card on its `DIMENSION_RESULT`; every rendered number gets an Inspect affordance (DSD §12). *Confirm Deck.gl TripsLayer + Next App Router conventions against pinned versions.*

### Data fetch — *reference implementation exists*
Follow [`data/fetch/fetch_open.py`](../data/fetch/fetch_open.py): stdlib, idempotent skip-if-exists, browser UA, TLS fallback, writes to `data/raw/`. Never commit `data/raw`.

---

## 5. Conventions & Guardrails

**Repo layout (nested monorepo at `app/`, as built):** `apps/web` (Next.js, Phase 5) · `apps/api` (FastAPI+WS, health + WS skeleton) · `packages/kernel` (SUMO/TraCI + 5 glass-box modules) · `packages/data` (processing pipeline → `build_network.py`) · `data/` (this repo's raw data + fetch scripts) · `docs/` (this suite).

**Always:** validate external input at the boundary (Pydantic/Zod); **every emitted number carries `equation_id` + `input_dataset_ids` + confidence**; tag confidence on every dimension; cite sources in narratives.

**Never:** commit secrets or `data/raw`; use **Gemini 1.5/2.0**; use **OASIS/MiroFish**; emit a number the LLM originated; fake precision; use a §3-deprecated API from memory.

**Tests:** every Must-Have ships with QAD happy + sad + abuse coverage; the **glass-box gate (TRACE-01..04)** and **validation gates** must pass. Run the eval suite before "done."

**Definition of Done (one task):**
- [ ] Meets the referenced `PRD-F#` / `US-##` acceptance criteria
- [ ] Framework conventions verified against §3 (no stale APIs)
- [ ] Every number traces (equation + datasets + confidence) — `glass-box-auditor` PASS
- [ ] Tests + evals pass (`eval-test-runner` PASS)
- [ ] No secrets / no `data/raw` committed
- [ ] Touched a Locked doc's assumptions? → Change Record filed

---

## 6. Materialization

| Target | File | Notes |
|--------|------|-------|
| Canonical | `docs/build-matrix.md` | edit here |
| App agents | `app/AGENTS.md` | quick-reference materialized from this doc at scaffold; auto-read by Codex/Cursor/Gemini/Claude Code when in `app/` |
| Claude Code | `CLAUDE.md` (repo root) | full code-orientation guide (Working in `app/`, commands, guardrails) — not a thin pointer |
| Cursor / Gemini | `.cursor/rules/build.mdc` · `GEMINI.md` | pointers |

Materialize `app/AGENTS.md` from this doc on any significant guardrail change; re-check `CLAUDE.md` for drift. Root copies are build artifacts, not sources of truth.
