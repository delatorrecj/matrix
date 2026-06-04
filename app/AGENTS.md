# AGENTS.md — MATRIX build

> Materialized from [`../docs/build-matrix.md`](../docs/build-matrix.md) at scaffold.
> The docs suite is canonical; this is the in-repo quick-reference. When this and the
> docs disagree, **the docs win** — update this file, don't fork the rules.

## Read order each session
1. [`../docs/index.md`](../docs/index.md) §0 — canonical source-of-truth map.
2. [`../docs/implementation-plan-matrix.md`](../docs/implementation-plan-matrix.md) — current phase + its Gate.
3. [`../docs/implementation-plan-critical-path.md`](../docs/implementation-plan-critical-path.md) — file-level walk of the critical path (S1–S8); which stub to open next.
4. [`../docs/prd-matrix.md`](../docs/prd-matrix.md) → [`../docs/sdd-matrix.md`](../docs/sdd-matrix.md) → [`../docs/rfc-matrix-realtime-pipeline.md`](../docs/rfc-matrix-realtime-pipeline.md).
5. [`../docs/methods-matrix.md`](../docs/methods-matrix.md) — **read before coding any module** (the equation registry).
6. [`../docs/dsd-matrix.md`](../docs/dsd-matrix.md) — before any UI surface.

## The two non-negotiable guardrails
- **Glass box (PRD-F14).** Every emitted number carries `equation_id` +
  `input_dataset_ids` + a *computed* confidence, and resolves under Inspect. The LLM
  narrates and cites; it **never originates a number.** `glass-box-auditor` (SAD-A2)
  blocks any violation. *"If a number on screen has no working Inspect, it's not done."*
- **Test/validation gates (QAD).** `eval-test-runner` (SAD-A4) must PASS pre-merge.
  Both gating agents PASS or it does not merge.

## Locked decisions (do not silently revert — MATRIX.md §6)
- Simulation engine **Eclipse SUMO** (TraCI) — not OASIS/MiroFish.
- **One unified kernel → five impact modules** (Behavioral/Social/Economic/Ecological/Societal).
- LLMs **Gemini 3.1 Pro** (orchestration/synthesis) + **Flash-Lite** (personas) via
  **`google-genai`**. **Never Gemini 1.5 (dead) or 2.0 (dead 2026-06-01).**
- **90-second** end-to-end budget (pre-warmed personas + nightly baseline + delta + parallel modules + streaming UI).
- Stack: Next.js 14 + Tailwind v4 (`@tailwindcss/postcss`) + shadcn/ui; Mapbox GL + Deck.gl (TripsLayer); FastAPI + WebSocket; Supabase (Postgres+PostGIS) + ChromaDB + Redis; XGBoost.

## Verify-live-before-coding (overrides training memory)
Before writing framework code, confirm the convention against the **pinned version's**
official docs: **google-genai** (ai.google.dev), **Next.js** (nextjs.org), **Tailwind v4**
(tailwindcss.com), **Deck.gl** (deck.gl). Stale forms to avoid: `google-generativeai`
(→ `google-genai`), `framer-motion` (→ `motion/react`), `<link>` fonts (→ `next/font`),
Tailwind v3 PostCSS plugin (→ `@tailwindcss/postcss`). Self-anneal: add a row to
[`../docs/build-matrix.md`](../docs/build-matrix.md) §3 whenever drift is caught.

## Build agents ([`../.claude/agents/`](../.claude/agents))
`module-kernel-builder` (A1) · `glass-box-auditor` (A2, gate) · `frontend-3d-builder`
(A3) · `eval-test-runner` (A4, gate) · `data-pipeline-runner` (A5). Roster +
cards: [`../docs/sad-matrix.md`](../docs/sad-matrix.md). Builders run on their verticals →
auditor + test-runner gate every merge.
