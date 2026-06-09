# Documentation Index — MATRIX

**Project slug:** `matrix`
**Maintained by:** Carlos Jerico Dela Torre (Team ATLAN)
**Last updated:** 2026-06-09

---

> Manifest for the MATRIX formal doc suite generated via the FMD framework. The canonical product/technical source is **[../MATRIX.md](../MATRIX.md)**; these docs decompose it into the spec-driven suite (PRD → SDD → …). Read this first to see what exists and what's stale.
>
> **Status lifecycle:** `Draft → Locked → Superseded`. Changing a Locked doc requires a Change Record.

---

## 0. Canonical hierarchy (read this to avoid double-sourcing)

To prevent context poisoning, **each concern has exactly one source of truth.** Other docs *link* to it; they never restate it. When two disagree, the canonical owner wins.

| Concern | Canonical source | Note |
|---|---|---|
| Vision · pitch · why-it-wins | [MATRIX.md](../MATRIX.md) | north-star; **serves the BRD role** |
| What we build (features, flows) | [prd-matrix.md](prd-matrix.md) | stable `PRD-F#` IDs |
| How we build (architecture, schema) | [sdd-matrix.md](sdd-matrix.md) | — |
| Every number's equation + provenance | [methods-matrix.md](methods-matrix.md) | the glass-box ledger |
| UI · 3D twin · routes & actions | [dsd-matrix.md](dsd-matrix.md) | — |
| Tests · validation · AI/traceability gates | [qad-matrix.md](qad-matrix.md) | — |
| Compliance (RA 10173, licenses) | [clr-matrix.md](clr-matrix.md) | — |
| Data: what we have, links, confidence | [../data/INVENTORY.md](../data/INVENTORY.md) + [../data/READINESS.md](../data/READINESS.md) | [MATRIX_Iloilo_Data_Sources.md](../MATRIX_Iloilo_Data_Sources.md) = sourcing *rationale* only |
| Execution order · phase gates · checkpoints | [implementation-plan-matrix.md](implementation-plan-matrix.md) | the *when / in-what-order / done-when*; BUILD owns *how* |

**Rule:** a fact lives in its canonical doc; everything else links. This is the anti-poisoning contract.

---

## 1. Document Suite

| Document | File | Version | Status | Last Updated | Last Reconciled |
|----------|------|---------|--------|--------------|-----------------|
| BRD — Business Requirements | — | — | N/A — covered by [MATRIX.md](../MATRIX.md) §1–3, §Appendix B | — | — |
| PRD — Product Requirements | [prd-matrix.md](prd-matrix.md) | 0.1 | **Locked** | 2026-06-09 | 2026-06-09 (CR-005 — Gemini 2.0 past-tense; verified vs as-built `app/`) |
| DSD — Design System | [dsd-matrix.md](dsd-matrix.md) | 0.1 | Draft | 2026-06-09 | 2026-06-09 (CR-005 — frontend built; anti-pattern register seeded) |
| SDD — System Design | [sdd-matrix.md](sdd-matrix.md) | 0.1 | **Locked** | 2026-06-03 | 2026-06-09 (CR-005 — verified accurate vs as-built `app/`; no content change) |
| Methods & Traceability (glass-box ledger) | [methods-matrix.md](methods-matrix.md) | 0.1 | **Locked** | 2026-06-03 | 2026-06-09 (CR-005 — verified: validations already marked planned, not shipped) |
| QAD — QA & Test Plan | [qad-matrix.md](qad-matrix.md) | 0.1 | Draft | 2026-06-09 | 2026-06-09 (CR-005 — test reality: 23 w/ SUMO, ~15 bare) |
| SAD — Subagents | [sad-matrix.md](sad-matrix.md) | 0.1 | Draft | 2026-06-02 | N/A — 5-agent build roster |
| BUILD — Build Guide | [build-matrix.md](build-matrix.md) | 0.1 | Draft | 2026-06-09 | 2026-06-09 (CR-005 — Gemini 2.0 past-tense; stack as-built) |
| Implementation Plan — phase-gated execution | [implementation-plan-matrix.md](implementation-plan-matrix.md) | 0.2 | Draft | 2026-06-04 | N/A — execution sequence + gates; companion to BUILD |
| Implementation Plan — critical path (file-level) | [implementation-plan-critical-path.md](implementation-plan-critical-path.md) | 0.1 | Draft | 2026-06-04 | N/A — granular vertical-slice walk; companion to the gated plan |
| CLR — Compliance & Legal | [clr-matrix.md](clr-matrix.md) | 0.1 | Draft | 2026-06-02 | N/A — banner set: PWA needs PIA + counsel |
| GTM — Go-To-Market | [gtm-matrix.md](gtm-matrix.md) | 0.1 | Draft | 2026-06-09 | 2026-06-09 (CR-005 — competitor survey + ASEAN-award citation) |
| OPS — Ops & Observability | [ops-matrix.md](ops-matrix.md) | 0.1 | Draft | 2026-06-02 | N/A — SLOs incl. 90 s budget; RA 10173 breach runbook |

### RFCs (one per major feature)

| RFC ID | File | Feature | Status | Last Updated |
|--------|------|---------|--------|--------------|
| matrix-rfc-001 | [rfc-matrix-realtime-pipeline.md](rfc-matrix-realtime-pipeline.md) | Real-time simulation pipeline (90 s budget) | Approved | 2026-06-02 |

---

## 2. Change Log

| CR ID | Date | Summary | Trigger doc | Docs touched | File |
|-------|------|---------|-------------|--------------|------|
| CR-001 | 2026-06-03 | Phase 0: scaffolded `app/` (nested in this repo, not a separate monorepo); acquired BIR DO17-2021 + FIES 2023 + ASPBI 2022 economic data; **Locked PRD + SDD + methods-matrix**. | implementation-plan-matrix.md | prd, sdd, methods, build, README, CLAUDE, INVENTORY, READINESS, this index | (logged here) |
| CR-002 | 2026-06-04 | Refreshed the gated plan for **solo-dev mode** (owners paused, Track B parallelism deferred, code-state + solo-dev capacity risk noted); added the **file-level critical-path plan**; improved root [CLAUDE.md](../CLAUDE.md) (accurate `uv` test commands + a "Working in `app/`" code-orientation section). | implementation-plan-matrix.md | implementation-plan-matrix, implementation-plan-critical-path, CLAUDE, this index | (logged here) |
| CR-003 | 2026-06-04 | **Progress reconciliation:** synced gated plan + INVENTORY to on-disk reality (BIR ZV `.xls` downloaded + parsed → 5,680 entries; Phase 1 ~70% done; SUMO Stage 1 built). **Upgraded `ECON-1` confidence L→M** in [methods-matrix §3.4](methods-matrix.md) now that BIR-ZV is acquired — **Locked-doc edit applied.** | implementation-plan-matrix.md | implementation-plan-matrix, INVENTORY, methods, this index | (logged here) |
| CR-004 | 2026-06-07 | **Milestone B complete (Phases 4-6):** Integrated Gemini orchestrator and synthesis with citation guard. Scaffolded Next.js 14 frontend with DSD compliance, Deck.gl, and glass-box Inspect Drawer. Deployment configs wired for Vercel + Fly.io. | implementation-plan-matrix.md | implementation-plan-matrix, implementation-plan-critical-path, build, qad, dsd, sdd, this index | (logged here) |
| CR-005 | 2026-06-09 | **Truth reconciliation + grounding pass.** Reconciled stale guidance (root `CLAUDE.md`, `apps/web/SCAFFOLD.md`, auto-memory) to the as-built code (Milestone A+B): modules + runner + frontend are built, not stubs. Corrected the test claim (**23 with `eclipse-sumo` / ~15+1 on a bare venv**). Closed truth flags: Gemini 2.0 → past tense (prd/sdd/build); added a **sourced citation** for the ASEAN Clean Tourist City Award 2026 (MATRIX.md/gtm); softened the "no ASEAN platform" absolute to a **competitor feature-survey** (gtm); guarded that the Calderon-2014 + 2024-flood **validations read as planned, not shipped** (qad/methods). Seeded the DSD anti-pattern register. Also corrected the QAD Definition-of-Done (validation ledger + 90 s budget were checked but are not met — now honest). **Locked-doc edit applied under this CR: PRD (Gemini 2.0 → past tense); SDD + methods verified accurate vs as-built, no content change.** | CLAUDE.md / code audit | CLAUDE, app/README, SCAFFOLD, MATRIX.md, prd, dsd, qad, build, gtm, memory, this index | (logged here) |

---

## 3. Incident Log (Postmortems)

| PM ID | Incident date | Severity | Summary | Action items closed? | File |
|-------|---------------|----------|---------|----------------------|------|
| — | — | — | none yet | — | — |

---

## 4. Health Check

- [x] Every Locked doc's **Last Reconciled** date is newer than the last code change to its area. *(CR-005, 2026-06-09 — reconciled with as-built `app/`.)*
- [ ] Feature IDs (`PRD-F#`) referenced by SDD/RFC/QAD still exist in the PRD. *(Spot-checked under CR-005; no full sweep yet.)*
- [x] Data confidence tiers in [../data/READINESS.md](../data/READINESS.md) still match what the modules consume. *(Data audit 2026-06-09 — all five dimensions' floors backed on-disk.)*
- [ ] No doc has been in `Draft` longer than expected without movement.

---

## 5. Notes

- **Source of truth:** [MATRIX.md](../MATRIX.md) supersedes the older PUP-ATLAN roadmap framing (see MATRIX.md Appendix A). When MATRIX.md and a generated doc disagree, MATRIX.md wins until the doc is reconciled.
- **Data backing:** [../data/INVENTORY.md](../data/INVENTORY.md) (manifest) and [../data/READINESS.md](../data/READINESS.md) (per-dimension availability + confidence) are the empirical basis the SDD draws on.
- **Scale:** treated as **Full** (multi-feature, public users, hackathon → production path). Backbone sequence INDEX → PRD → SDD; QAD/CLR/OPS to follow before any production launch.
