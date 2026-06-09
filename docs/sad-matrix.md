# Subagents Document (SAD)

**Project:** MATRIX
**Date:** 2026-06-02
**Version:** 0.1
**Owner:** Jerico (Team ATLAN)
**Status:** Draft
**Last reconciled:** N/A — not yet reconciled with code
**PRD:** [prd-matrix.md](prd-matrix.md) · **SDD:** [sdd-matrix.md](sdd-matrix.md) · **QAD:** [qad-matrix.md](qad-matrix.md)

> Canonical, platform-agnostic roster of **AI build-subagents** that help the 5-person team ([PRD §10](prd-matrix.md)) build MATRIX. Each agent is owned/operated by a team member. Materialize to Claude Code at monorepo scaffold (§5). These are *build helpers* — they execute within boundaries the PRD/SDD/RFC already set; they do not make product or architecture decisions.

---

## 1. Purpose & Scope

Subagents assist the **build** phase (Sprints 2–4): writing kernel/module code, building UI components, fetching/refreshing data, and — most importantly — **enforcing the two non-negotiable guardrails (glass-box traceability and the test/validation gates) so they cannot be skipped under hackathon time pressure.** Invoked by the owning team member on demand (Claude Code).

**Out of scope:** product/architecture decisions (PRD/SDD/RFC own those).

---

## 2. Roster Design Rationale (anti-sprawl)

| Considered | Decision | Reason |
|------------|----------|--------|
| 5 separate per-dimension agents | **Rejected** | the modules share structure → one `module-kernel-builder` handles all five |
| `doc-writer` agent | **Rejected** | docs are authored by the team/main agent, not delegated |
| `deploy` agent | **Rejected** | CI/CD handles deploys; not spawned often enough to earn a slot |
| `kernel/module builder` | Kept | spawned repeatedly across kernel + 5 modules (criterion 1) |
| `glass-box-auditor` | Kept | enforces the glass-box guardrail (criterion 3) — must never be skipped |
| `eval-test-runner` | Kept | guardrail + repeated (criteria 1+3) |
| `frontend-3d-builder` | Kept | spawned repeatedly across the interfaces (criterion 1) |
| `data-pipeline-runner` | Kept | offloads heavy data fetch/subset from main context (criterion 2) |

Five agents — within the 3–6 norm.

---

## 3. The Roster

| Agent ID | Name | One-line job | Derived from | Spawn trigger | Owner (§10) | Model hint |
|----------|------|--------------|--------------|---------------|-------------|------------|
| SAD-A1 | `module-kernel-builder` | build/debug SUMO kernel + the 5 impact modules from their equations | PRD-F1/F3, SDD §2, RFC RT-03/05, methods §3 | building/fixing a module or the kernel | Jerico/Yushin | balanced |
| SAD-A2 | `glass-box-auditor` | verify every emitted number has equation_id + dataset_ids + confidence; block uncited claims | PRD-F14, methods-matrix, QAD TRACE-01..04 | before any result/narrative ships | Jerico | balanced |
| SAD-A3 | `frontend-3d-builder` | build Next.js/Deck.gl components per the DSD (incl. Inspect drawer, 3D layers) | DSD, PRD-F4/F8/F16 | building/fixing a UI surface | Yushin (+ Maria, UX) | balanced |
| SAD-A4 | `eval-test-runner` | run the QAD suite (AI evals, traceability + validation gates, 90 s perf); gate merges | QAD §3/§7/§8 | after code changes; pre-merge | QA (Maria/Rica/Russell) | fast |
| SAD-A5 | `data-pipeline-runner` | run/refresh `data/fetch/*`, subset to Iloilo, stamp vintages | data/INVENTORY, READINESS | data refresh or new source | Rica/Russell | fast |

---

### Agent Cards

#### SAD-A1 — module-kernel-builder
- **Purpose:** repeated build/debug of the SUMO kernel and the five impact modules (criterion 1).
- **Derived from:** PRD-F1/F3, SDD §2, RFC `matrix-rfc-001` RT-03/RT-05, [methods-matrix](methods-matrix.md) §3.
- **Responsibilities:** wire TraCI runs; implement each module's equation from the registry; emit results with provenance fields.
- **Inputs:** a module/equation ID + the trajectory dataset schema. **Outputs:** a patch + unit tests.
- **Capabilities:** read, edit, run shell/pytest. **Guardrails (never):** never invent a number outside the equation registry; never emit a result without `equation_id` + `input_dataset_ids`. **Done when:** module returns scored output with provenance and passing tests. **Model:** balanced.

#### SAD-A2 — glass-box-auditor *(guardrail)*
- **Purpose:** enforce the non-negotiable glass-box contract (criterion 3).
- **Derived from:** PRD-F14, [methods-matrix](methods-matrix.md) §1/§4, QAD TRACE-01..04.
- **Responsibilities:** scan results for missing provenance; verify Inspect resolves; confirm synthesis narratives cite an `equation_id`+`dataset_ids` (citation guard); recompute confidence vs the rubric.
- **Inputs:** a run's results + narrative. **Outputs:** PASS, or FAIL listing the offending numbers.
- **Capabilities:** read, grep, run checks. **Guardrails (never):** never "fix" by inventing provenance — only flag. **Done when:** every number traces or is flagged. **Model:** balanced.

#### SAD-A3 — frontend-3d-builder
- **Purpose:** repeated build of UI surfaces incl. the 3D simulator + Inspect drawer (criterion 1).
- **Derived from:** [dsd-matrix](dsd-matrix.md) §4/§9–12, PRD-F4/F8/F16.
- **Responsibilities:** build Next.js/shadcn + Deck.gl components to the DSD tokens; implement all states (empty/loading/streaming/error/success); wire the WS event stream (RFC §3).
- **Inputs:** a surface from the DSD interface inventory. **Outputs:** component + states.
- **Capabilities:** read, edit, run dev/build. **Guardrails (never):** never use a hue without its icon/label; never render a number without an Inspect affordance; honor `prefers-reduced-motion`. **Done when:** surface matches DSD + states complete. **Model:** balanced.

#### SAD-A4 — eval-test-runner *(guardrail)*
- **Purpose:** run + triage the test/eval/validation suite; gate merges (criteria 1+3).
- **Derived from:** [qad-matrix](qad-matrix.md) §3 (H/S/AB), §7 (AI evals), §8 (traceability + validation gates).
- **Responsibilities:** run pytest/Vitest/Playwright + `run_eval.py`; on fail, return the minimal failing context.
- **Inputs:** a diff. **Outputs:** PASS, or FAIL with the specific failing cases. **Capabilities:** read, grep, bash. **Guardrails (never):** never edit source to make a test pass; never skip/delete tests or evals. **Done when:** clear PASS or actionable FAIL. **Model:** fast.

#### SAD-A5 — data-pipeline-runner
- **Purpose:** offload heavy data fetch/subset from the main context (criterion 2).
- **Derived from:** [../data/INVENTORY.md](../data/INVENTORY.md), [../data/READINESS.md](../data/READINESS.md).
- **Responsibilities:** run `data/fetch/*` idempotently; subset CCHAIN to Iloilo; record vintages; never commit raw data.
- **Inputs:** a dataset ID or "refresh". **Outputs:** files in `data/raw|processed` + an INVENTORY status update. **Capabilities:** read, edit (data docs), bash. **Guardrails (never):** never commit `data/raw`; never fight a 403 (note manual path instead). **Done when:** files land + INVENTORY reflects status. **Model:** fast.

---

## 4. Orchestration

- **Who spawns:** the owning team member (§10) on demand via Claude Code.
- **Sequencing:** `module-kernel-builder` / `frontend-3d-builder` / `data-pipeline-runner` run in parallel on their verticals → **`glass-box-auditor` and `eval-test-runner` gate every merge** (both must PASS).
- **Hand-off:** builders produce patches; auditor + test-runner verify before merge; shared state = the repo + `run_trace`.
- **Escalation:** any guardrail conflict, ambiguous spec, or repeated failure → stop, hand back to the owning human.

```
builder (A1/A3/A5) ──▶ glass-box-auditor (A2) ──gate──▶ eval-test-runner (A4) ──gate──▶ merge
                            │ FAIL                            │ FAIL
                            └────────── back to builder ──────┘
```

---

## 5. Materialization (Platform Mapping)

**Materialize to: Claude Code** (`.claude/agents/*.md`) **in the build monorepo at scaffold** (Sprint 1) — not in this planning repo, where the agents have no code to act on yet. Re-materialize whenever a card changes; treat the generated files as artifacts.

| Agent ID | Materialized file (monorepo) | Format |
|----------|------------------------------|--------|
| SAD-A1 | `.claude/agents/module-kernel-builder.md` | Claude Code frontmatter |
| SAD-A2 | `.claude/agents/glass-box-auditor.md` | Claude Code frontmatter |
| SAD-A3 | `.claude/agents/frontend-3d-builder.md` | Claude Code frontmatter |
| SAD-A4 | `.claude/agents/eval-test-runner.md` | Claude Code frontmatter |
| SAD-A5 | `.claude/agents/data-pipeline-runner.md` | Claude Code frontmatter |

**Example — Claude Code materialization of SAD-A2:**
```markdown
---
name: glass-box-auditor
description: Use before any result or narrative ships. Verifies every number traces to an equation + datasets + confidence; blocks uncited claims.
tools: Read, Grep, Bash
model: sonnet
---
You enforce MATRIX's glass-box contract (PRD-F14, methods-matrix.md). For every emitted
number, confirm equation_id + input_dataset_ids + confidence exist and Inspect resolves;
confirm synthesis narratives cite equation_id + dataset_ids. Never invent provenance —
only flag. Done when every number traces or is flagged with the offending location.
```
> Map `tools:`/`model:`/body directly from each card. `fast→haiku, balanced→sonnet, deep→opus`.

---

## 6. Maintenance

- The SAD is the source of truth; edit cards here → bump version → re-materialize. Never hand-edit `.claude/agents/`.
- Reconcile orphans/missing on roster drift; re-run the anti-sprawl rule on any new agent proposal (log rejects in §2).
- If a `PRD-F#` an agent derives from is cut, revisit the agent (Change Record).
