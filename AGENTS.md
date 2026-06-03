# AGENTS.md — MATRIX Build Agents

**For the 5-person Team ATLAN, in Claude Code / Cursor / Windsurf.**

These agents help enforce the two non-negotiable guardrails during build (Sprints 2–4): **glass-box traceability** and **test/validation gates** so they cannot be skipped under hackathon time pressure.

**Full specifications:** [docs/sad-matrix.md](docs/sad-matrix.md) (Subagents Document). **Build guide:** [docs/build-matrix.md](docs/build-matrix.md).

---

## The 5 Agents

| Agent | Spawn when | Owner | Done when |
|-------|-----------|-------|-----------|
| **module-kernel-builder** | Building/debugging the SUMO kernel or any of the 5 impact modules | Jerico / Yushin | Module returns scored output with provenance fields + unit tests pass |
| **glass-box-auditor** ⚠️ *guardrail* | Before any result or narrative ships | Jerico | Every number traces to `equation_id` + `input_dataset_ids` + `confidence`, or is flagged |
| **frontend-3d-builder** | Building/fixing a UI surface (3D twin, Inspect drawer, control panels) | Yushin (+ Maria, UX) | Component matches DSD tokens + all states (empty/loading/streaming/error/success) complete |
| **eval-test-runner** ⚠️ *guardrail* | After code changes, before merge | QA (Maria/Rica/Russell) | Clear PASS on pytest/Vitest/Playwright/`run_eval.py`, or actionable FAIL |
| **data-pipeline-runner** | Data refresh or new source integration | Rica / Russell | Files land in `data/raw|processed`, INVENTORY.md status updated, never commit raw data |

---

## The Merge Gate

**Both guardrails must PASS before merging:**
```
your code → glass-box-auditor PASS → eval-test-runner PASS → merge
                          ↓ FAIL                        ↓ FAIL
                      fix & re-audit            fix tests & re-run
```

**glass-box-auditor** (A2) blocks **uncited numbers**. Never invent provenance — only flag missing citations.

**eval-test-runner** (A4) blocks **unvalidated code**. Never skip or delete tests to make them pass.

---

## Before You Scaffold (Sprint 1 setup)

1. **Manually download four economic datasets** (scripts return 403):
   - BIR zonal values RDO 74 → `data/raw/economic/BIR_ZV_RDO74_IloiloCity.pdf`
   - PSA FIES 2023 → `data/raw/economic/PSA_FIES2023_RegionVI.xlsx`
   - PSA ASPBI 2023 → `data/raw/economic/PSA_ASPBI2023_RegionVI.xlsx`
   - DOT visitor arrivals 2024 → `data/raw/economic/DOT_VisitorArrivals_Region_2024.xlsx`
   
   See [data/INVENTORY.md](data/INVENTORY.md) for exact URLs.

2. **At monorepo scaffold:** the SAD will be materialized to `.claude/agents/*.md` in the build repo. Use those agent definitions in Claude Code.

---

## Key Constraints (read before coding)

- **LLMs:** Gemini 3.1 Pro (orchestration) + Gemini 3.1 Flash-Lite (high-volume persona generation). Never Gemini 1.5 or 2.0.
- **Simulation engine:** Eclipse SUMO via TraCI Python API.
- **Stack:** Next.js 14 (App Router) · FastAPI · Supabase · Deck.gl · shadcn/ui. See [docs/build-matrix.md](docs/build-matrix.md) §3 for pinned versions.
- **Equations:** Every number in the modules must map to [docs/methods-matrix.md](docs/methods-matrix.md) §3 (the glass-box ledger). Read this before coding any module.
- **90 s budget:** End-to-end latency from query to playback. Hard constraint. RFC-001 has the pipeline strategy.

---

## Docs You'll Reference

| Read | For |
|------|-----|
| [docs/prd-matrix.md](docs/prd-matrix.md) | What features you're building (PRD-F#) |
| [docs/sdd-matrix.md](docs/sdd-matrix.md) | How the system is architected (schema, APIs, AI safety) |
| [docs/rfc-matrix-realtime-pipeline.md](docs/rfc-matrix-realtime-pipeline.md) | The 90 s pipeline implementation |
| [docs/dsd-matrix.md](docs/dsd-matrix.md) | UI design system, 3D twin, routes & actions |
| [docs/methods-matrix.md](docs/methods-matrix.md) | Every module equation + provenance. **Read before coding any module.** |
| [docs/qad-matrix.md](docs/qad-matrix.md) | Test scenarios (US-##), eval gates, validation rules |
| [MATRIX.md](MATRIX.md) | Vision, why it wins, locked decisions |

---

## Questions?

- **"Is my doc/feature spec the source of truth?"** → Check [docs/index.md](docs/index.md) §0. If it's not listed, ask.
- **"Can I change the architecture?"** → Propose a Change Record (`docs/cr-*.md`). Locked docs need formal approval.
- **"The agent failed — what do I do?"** → If it's escalation-blocking, return to the owning human (Jerico/Maria). Never force-merge.
