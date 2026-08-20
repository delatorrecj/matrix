# Documentation Index - MATRIX

**Project slug:** `matrix`
**Maintained by:** Carlos Jerico Dela Torre (Team ATLAN)
**Last updated:** 2026-08-20
**Built on FMD v1.28.1** (provenance stamp added 2026-08-10)

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
| How we build (architecture, schema) | [sdd-matrix.md](sdd-matrix.md) | - |
| Every number's equation + provenance | [methods-matrix.md](methods-matrix.md) | the glass-box ledger |
| UI · 3D twin · routes & actions | [dsd-matrix.md](dsd-matrix.md) | - |
| Tests · validation · AI/traceability gates | [qad-matrix.md](qad-matrix.md) | - |
| Compliance (RA 10173, licenses) | [clr-matrix.md](clr-matrix.md) | - |
| Data: what we have, links, confidence | [../data/INVENTORY.md](../data/INVENTORY.md) + [../data/READINESS.md](../data/READINESS.md) | [MATRIX_Iloilo_Data_Sources.md](../MATRIX_Iloilo_Data_Sources.md) = sourcing *rationale* only |
| Execution order · phase gates · checkpoints | [implementation-plan-matrix.md](implementation-plan-matrix.md) | the *when / in-what-order / done-when*; BUILD owns *how* |
| Teammate onboarding (reading path) | [onboarding-matrix.md](onboarding-matrix.md) | study guide; **not** canonical. Stack Q&A points at SDD / BUILD / RFC |

**Rule:** a fact lives in its canonical doc; everything else links. This is the anti-poisoning contract.

---

## 1. Document Suite

| Document | File | Version | Status | Last Updated | Last Reconciled |
|----------|------|---------|--------|--------------|-----------------|
| Onboarding primer | [onboarding-matrix.md](onboarding-matrix.md) | 0.1 | Draft | 2026-08-16 | 2026-08-16 (reading path + stack Q&A; not Locked) |
| BRD - Business Requirements | - | - | N/A - covered by [MATRIX.md](../MATRIX.md) §1–3, §Appendix B | - | - |
| PRD - Product Requirements | [prd-matrix.md](prd-matrix.md) | 0.1 | **Locked** | 2026-06-24 | 2026-06-24 (CR-010 - PRD-F7 amended to the BLUF bilingual synthesis brief + re-locked; prior: CR-005 verified vs as-built `app/`) |
| DSD - Design System | [dsd-matrix.md](dsd-matrix.md) | 0.1 | Draft | 2026-06-24 | 2026-06-24 (CR-010 UX updates; verified anti-pattern register status) |
| SDD - System Design | [sdd-matrix.md](sdd-matrix.md) | 0.1 | **Locked** | 2026-06-24 | 2026-06-24 (CR-011 deployment model; RAG and feedback columns) |
| Methods & Traceability (glass-box ledger) | [methods-matrix.md](methods-matrix.md) | 0.1 | **Locked** | 2026-08-20 | 2026-08-20 (CR-020 — §4.2 named corridor spans `keyword-span` / `keyword-span-open`; prior: CR-018 live-net gazetteer; CR-012 PR #37 hash fallback) |
| QAD - QA & Test Plan | [qad-matrix.md](qad-matrix.md) | 0.1 | Draft | 2026-06-24 | 2026-06-24 (CR-012; verified 190 pass kernel / 64 pass api) |
| SAD - Subagents | [sad-matrix.md](sad-matrix.md) | 0.1 | Draft | 2026-06-24 | 2026-06-24 (Materialized build-subagents list) |
| BUILD - Build Guide | [build-matrix.md](build-matrix.md) | 0.1 | Draft | 2026-06-24 | 2026-06-24 (CR-010/CR-012 updates, pointer cleanup) |
| Implementation Plan - phase-gated execution | [implementation-plan-matrix.md](implementation-plan-matrix.md) | 0.3 | Draft | 2026-06-14 | 2026-06-14 (CR-006 - Phase 8 "Beyond the Hackathon" added; PRs #1–#17 merged) |
| Implementation Plan - critical path (file-level) | [implementation-plan-critical-path.md](implementation-plan-critical-path.md) | 0.1 | Draft | 2026-06-04 | N/A - granular vertical-slice walk; companion to the gated plan |
| CLR - Compliance & Legal | [clr-matrix.md](clr-matrix.md) | 0.1 | Draft | 2026-06-24 | 2026-06-24 (Update model provider terms, PWA GPS status) |
| GTM - Go-To-Market | [gtm-matrix.md](gtm-matrix.md) | 0.1 | Draft | 2026-06-24 | 2026-06-24 (ASEAN Clean Tourist City and competitor survey) |
| OPS - Ops & Observability | [ops-matrix.md](ops-matrix.md) | 0.1 | Draft | 2026-06-24 | 2026-06-24 (CR-011 deployment runbook) |

### RFCs (one per major feature)

| RFC ID | File | Feature | Status | Last Updated |
|--------|------|---------|--------|--------------|
| matrix-rfc-001 | [rfc-matrix-realtime-pipeline.md](rfc-matrix-realtime-pipeline.md) | Real-time simulation pipeline (90 s budget) | Approved | 2026-06-24 (Warm runs at ~48 s vs 90 s budget) |

### Change Records (standalone files)

CR-001…CR-005 are logged inline in the [Change Log](#2-change-log) below. CR-006 is the first CR written as a standalone FMD Change Record file:

| CR ID | File | Title | Status | Date |
|-------|------|-------|--------|------|
| CR-006 | [cr-006-beyond-hackathon.md](cr-006-beyond-hackathon.md) | Beyond the Hackathon - product-hardening pivot (PRs #1–#17) | Applied | 2026-06-14 |
| CR-007 | [cr-007-close-the-loop.md](cr-007-close-the-loop.md) | Close the loop - connect the shipped batch end-to-end (all 10 PRs P0–P4 merged) | Applied | 2026-06-17 |
| CR-008 | [cr-008-judges-feedback.md](cr-008-judges-feedback.md) | ASEAN judges' feedback remediation - the 9 asks (ground-truth, informal sector, bias-auditor example, low-confidence, extreme events, CPDO feedback, Hiligaynon gazetteer, traceability table, RAG) | **Applied** | 2026-06-22 |
| CR-009 | [cr-009-azure-foundry-client.md](cr-009-azure-foundry-client.md) | Azure AI Foundry v1 Client Compatibility | **Applied** | 2026-06-22 |
| CR-010 | [cr-010-ui-summary-humanization.md](cr-010-ui-summary-humanization.md) | Summary-first UI & plain-language humanization (Phase 1 web humanization + Phase 2 BLUF synthesis / delimited bilingual / one-page brief) | **Applied** | 2026-06-24 |
| CR-011 | [cr-011-huggingface-migration.md](cr-011-huggingface-migration.md) | Deployment migration - Fly.io → Hugging Face Spaces (self-contained Docker; Vercel frontend unchanged) | **Applied** | 2026-06-22 |
| CR-012 | [cr-012-validation-calibration.md](cr-012-validation-calibration.md) | Validation & calibration — honest VAL-01/VAL-02 + mode-share (un-withhold VAL-01: proxy/unit reconciliation + demand calibration; flood ground-truth; bias-reweight worked example) | Partially Applied (Phase A) | 2026-06-24 |
| CR-018 | [cr-018-gazetteer-live-network.md](cr-018-gazetteer-live-network.md) | Gazetteer aliases verified against the live SUMO net (origId + street alias + coordinate snap; hash fallback unchanged) | **Applied** | 2026-08-20 |
| CR-019 | [cr-019-credibility-next-steps.md](cr-019-credibility-next-steps.md) | Post-gazetteer credibility queue: ship CR-018 only; do not raise chips via unused CSVs; later VAL-01 / provisional-method work | **Proposed** | 2026-08-20 |
| CR-021 | [cr-021-impact-card-honesty.md](cr-021-impact-card-honesty.md) | Impact-card honesty: applicability (Not modeled / Not applicable), VAL-01 on every volume child, type-aware BEH-3, facility-adjacent overlay, flood_hazard for ECO-4 | **Applied** | 2026-08-20 |

> **CR-number note:** `cr-009-qa-frontend-fixes.md` (Yushin's QA pass) self-declares **CR-009** — distinct from the Azure-Foundry CR-009 above (two unrelated CRs share the 009 number; likewise `cr-008-azure-openai-migration.md` shares 008 with the judges-feedback CR-008). These are pre-existing numbering collisions in the as-filed history, surfaced here for the owner; not renumbered (governance call).

---

## 2. Change Log

| CR ID | Date | Summary | Trigger doc | Docs touched | File |
|-------|------|---------|-------------|--------------|------|
| CR-021 | 2026-08-20 | **Impact-card honesty.** `applicability` on `DimensionResult` (Not modeled / Not applicable — no fake 0.0). VAL-01 caps every volume-derived card. ECO-1 uses impacted edges + real lengths. BEH-3 type-aware denominator. Facility-adjacent overlay + orchestrator `flood_hazard`. **Does not stamp High on BEH-1/BEH-3 while VAL-01 FAIL.** No Locked-doc rewrite. | school/flood/road-diet produced a full deck of unearned cards | this index | [cr-021-impact-card-honesty.md](cr-021-impact-card-honesty.md) |
| CR-020 | 2026-08-20 | **Named corridor spans.** Orchestrator emits corridor + `from_cross`/`to_cross`; kernel clips the live named-edge graph (`keyword-span` / `keyword-span-open`). Magenta halo uses closed-edge shapes from the net, not only baseline `edges.geojson`. Gazetteer stays aliases. **methods-matrix §4.2 amended & re-locked.** | stuffed span in `location` hashed / painted the wrong stub | methods, this index | [cr-020-named-span-resolution.md](cr-020-named-span-resolution.md) |
| CR-019 | 2026-08-20 | **Credibility next steps.** Keep honest H/M/L. Immediate: CR-018 gazetteer on the demo branch. Do not stamp High, fit Calderon, or wire unused inventory to chase chips. Later queue: independent VAL-01 re-measure, ECO-2 / SOCI-3 provisional replacements, real VKT, WorldCover on construction only. | post-CR-018 accuracy vs credibility review | this index, READINESS (pointer) | [cr-019-credibility-next-steps.md](cr-019-credibility-next-steps.md) |
| CR-018 | 2026-08-20 | **Gazetteer vs live net.** Replaced placeholder `E_*` ids with live OSM/SUMO membership, origId match, street aliases, and capped coordinate snap. Named-place queries no longer hash onto a busy edge. Hash fallback kept for unmatched strings. **methods-matrix §4.2 amended & re-locked.** | gazetteer placeholders vs OSM-derived edge ids | methods, glossary, this index | [cr-018-gazetteer-live-network.md](cr-018-gazetteer-live-network.md) |
| CR-012 | 2026-06-25 | **Edge-resolution fallback fix (PR #37).** Fixed the "identical -14 trips" defect: `_resolve_edges` now consults the gazetteer before keyword-match and uses a deterministic MD5 hash among the top-50 busiest baseline edges when nothing resolves (instead of always the single busiest edge). Provenance preserved (`gazetteer-match`, `busiest-baseline-fallback (deterministic-hash; …)`). CI green (kernel/api/web/e2e); landing page unaffected. **methods-matrix §4.2 amended & re-locked.** | production QA / teammate fix | cr-012, methods, this index | [cr-012-validation-calibration.md](cr-012-validation-calibration.md) |
| CR-010 | 2026-06-24 | **Summary-first UI & plain-language humanization.** Live production QA found dead nav controls + false-precision floats + a jargon-dense brief. **Phase 1** (PR #30, merge `f323e42`): `lib/format.ts` + `lib/metrics.ts` number humanization (no false precision; near-zero → "No meaningful change"), plain-language Summary dock + a dedicated interpreted Analytics view, nav cleanup (logo→home, disabled-with-reason, **AU avatar + dead Help removed**), real Settings (theme + EN/Hiligaynon). **Phase 2** (PR #31, merge `6c3351f`): synthesis → plain-language **BLUF**, delimited bilingual + language toggle, print-scoped one-page `ScenarioBrief`, tightened citation guard. Both gating agents PASS; **methods-matrix §4/§4.3 + PRD-F7 amended & re-locked** (owner-approved, `cc46b78`). All CI green; both Vercel prod deploys succeeded. | live production QA | cr-010 (new), methods, prd, CLAUDE, this index | [cr-010-ui-summary-humanization.md](cr-010-ui-summary-humanization.md) |
| CR-011 | 2026-06-22 | **Deployment migration + doc de-poisoning (pre-deploy).** Recorded the **Fly.io → Hugging Face Spaces** backend move (self-contained Docker Space: in-container Redis, SUMO net/demand via Git LFS, in-memory persistence, baseline seeded on boot; Vercel frontend unchanged). Purged stale **Supabase / Fly.io / Gemini-"Flash-Lite"** references across the suite (README, MATRIX.md, AGENTS×2, `.env.example`, SECURITY.md, ops §7, sdd/build/prd/clr/qad/methods/rfc/implementation plans, data-sources) so docs match the as-built single Azure OpenAI `gpt-5.4` + Postgres/PostGIS reality. Deleted leftover `replace_gemini_*.py` migration scripts and the garbled orphan `cr-009-huggingface-migration.md`. Fixed dangerous SECURITY.md rotation steps (Azure key → Azure Portal, HF token → HF settings). | deploy readiness review | cr-011 (new), README, MATRIX.md, CLAUDE.md, AGENTS.md, app/AGENTS.md, app/.env.example, SECURITY.md, ops, sdd, build, prd, clr, qad, methods, rfc, implementation plans, data-sources, this index | [cr-011-huggingface-migration.md](cr-011-huggingface-migration.md) |
| CR-009 | 2026-06-22 | **Azure AI Foundry v1 Client Compatibility.** Dropped `openai.AzureOpenAI` class in favor of standard `openai.OpenAI` for compatibility with the Azure AI Foundry v1 endpoint. Solved 404 resource-not-found errors. | user request | cr-009 (new), cr-008, this index | [cr-009-azure-foundry-client.md](cr-009-azure-foundry-client.md) |
| - | 2026-06-22 | **Wire-up + polish pass (pre-deploy).** Connected three implemented-but-disconnected features: (1) the **bias auditor now runs in the live pipeline** - API startup warms the persona pool through the full `generate→audit→reweight` loop (`personas.warm_persona_pool`), and every run logs a public audit entry keyed to `scenario_id` (`adjustment_factors` persisted + rendered), so `GET /audit/{id}` and the BiasAuditLog panel show real data (previously always empty - the auditor lived only in tests); (2) **GraphRAG/Chroma corpus ingested at API startup** so `retrieve()` grounds the orchestrator instead of returning `[]`; (3) `BiasAuditLog.tsx` fetches via `NEXT_PUBLIC_API_URL` (was hardcoded localhost). Also rewrote the **AAIH AI-Use & Ethics report** around the judges' 9 flags (honest validation status, bias worked example, traceability appendix). Tests: kernel bare 182p/11s, API bare 64p/4s, `next build` clean. | code audit (state review) | CLAUDE.md, aaih-ai-use-ethics-report, this index | (logged here) |
| CR-009 (QA) | 2026-06-20 | **QA and Frontend Design Fixes.** Fixed the agent trajectory animation bug in `TripsLayer` (updated `PLAYBACK_FRAME` accumulation and dynamic scrubber bounds). Verified the orange Confidence layer overlay as intentional per the `method_capped_confidence` rule. Confirmed Simulation Verification Guards (Glass-Box Traceability and Bias & Synthesis Audit) are fully functional. Authored by Yushin. *(File self-declares CR-009; shares the 009 number with the Azure-Foundry CR-009 — see CR-number note in §1.5. Was previously mislogged here as "CR-010".)* | QA sweep | cr-009-qa-frontend-fixes (new), this index | [cr-009-qa-frontend-fixes.md](cr-009-qa-frontend-fixes.md) |
| CR-008 | 2026-06-17 | **ASEAN judges' feedback remediation - Milestones 3 & 4 Complete.** Implemented the CPDO Iterative Feedback Loop (Item 6), including `planner_feedback` schema, persistence fallback, and API endpoints (`POST/GET /feedback`); updated `prd-matrix.md` with PRD-F20 and US-09, documented API seam in `sdd-matrix.md`, and added triage runbook in `ops-matrix.md`. Also completed Extreme Events / Resilience (Item 5), Informal Sector Tricycle logic (Item 2), and Ground-Truth Validation (Item 1) from Milestone 3. Test suites for Kernel (197 passing) and API (98 passing) confirmed 100% green and glass-box compliant. | ASEAN judges' feedback | prd, sdd, ops | [cr-008-judges-feedback.md](cr-008-judges-feedback.md) |
| CR-008 | 2026-06-17 | **ASEAN judges' feedback remediation - implementation plan.** Opened the `dev` branch and authored a file-level plan ([cr-008-judges-feedback.md](cr-008-judges-feedback.md)) addressing the 9 judge asks: (1) ground-truth comparison [VAL-01/02], (2) informal-sector modeling [tricycle routing + vendor economics], (3) bias-auditor worked example + **reweight math** (currently flags but does not rebalance - gap), (4) low-confidence trigger + alert protocol, (5) extreme-event resilience [flood/closure], (6) **new PRD-F20** CPDO feedback loop, (7) **Hiligaynon gazetteer** (colloquial→GIS node; none exists today), (8) module⇄data-source traceability appendix, (9) RAG setup/ingestion elaboration (no build script today). Maps 8/9 asks onto existing PRD features; flags Locked-doc edits (methods/prd/sdd) for governance. Branch audit: all 19 remaining remote branches confirmed merged into `main` (stale, undeleted). **No code/doc content shipped yet - plan only.** | ASEAN judges' feedback | cr-008 (new), this index | [cr-008-judges-feedback.md](cr-008-judges-feedback.md) |
| CR-001 | 2026-06-03 | Phase 0: scaffolded `app/` (nested in this repo, not a separate monorepo); acquired BIR DO17-2021 + FIES 2023 + ASPBI 2022 economic data; **Locked PRD + SDD + methods-matrix**. | implementation-plan-matrix.md | prd, sdd, methods, build, README, CLAUDE, INVENTORY, READINESS, this index | (logged here) |
| CR-002 | 2026-06-04 | Refreshed the gated plan for **solo-dev mode** (owners paused, Track B parallelism deferred, code-state + solo-dev capacity risk noted); added the **file-level critical-path plan**; improved root [CLAUDE.md](../CLAUDE.md) (accurate `uv` test commands + a "Working in `app/`" code-orientation section). | implementation-plan-matrix.md | implementation-plan-matrix, implementation-plan-critical-path, CLAUDE, this index | (logged here) |
| CR-003 | 2026-06-04 | **Progress reconciliation:** synced gated plan + INVENTORY to on-disk reality (BIR ZV `.xls` downloaded + parsed → 5,680 entries; Phase 1 ~70% done; SUMO Stage 1 built). **Upgraded `ECON-1` confidence L→M** in [methods-matrix §3.4](methods-matrix.md) now that BIR-ZV is acquired - **Locked-doc edit applied.** | implementation-plan-matrix.md | implementation-plan-matrix, INVENTORY, methods, this index | (logged here) |
| CR-004 | 2026-06-07 | **Milestone B complete (Phases 4-6):** Integrated Azure OpenAI GPT-5.4 orchestrator and synthesis with citation guard. Scaffolded Next.js 14 frontend with DSD compliance, Deck.gl, and glass-box Inspect Drawer. Deployment configs wired for Vercel + Hugging Face Spaces. | implementation-plan-matrix.md | implementation-plan-matrix, implementation-plan-critical-path, build, qad, dsd, sdd, this index | (logged here) |
| CR-005 | 2026-06-09 | **Truth reconciliation + grounding pass.** Reconciled stale guidance (root `CLAUDE.md`, `apps/web/SCAFFOLD.md`, auto-memory) to the as-built code (Milestone A+B): modules + runner + frontend are built, not stubs. Corrected the test claim (**23 with `eclipse-sumo` / ~15+1 on a bare venv**). Closed truth flags: Azure OpenAI GPT-5.4 2.0 → past tense (prd/sdd/build); added a **sourced citation** for the ASEAN Clean Tourist City Award 2026 (MATRIX.md/gtm); softened the "no ASEAN platform" absolute to a **competitor feature-survey** (gtm); guarded that the Calderon-2014 + 2024-flood **validations read as planned, not shipped** (qad/methods). Seeded the DSD anti-pattern register. Also corrected the QAD Definition-of-Done (validation ledger + 90 s budget were checked but are not met - now honest). **Locked-doc edit applied under this CR: PRD (Azure OpenAI 2.0 → past tense); SDD + methods verified accurate vs as-built, no content change.** | CLAUDE.md / code audit | CLAUDE, app/README, SCAFFOLD, MATRIX.md, prd, dsd, qad, build, gtm, memory, this index | (logged here) |
| CR-007 | 2026-06-16 | **Close the loop - connect the shipped batch end-to-end.** Review of the CR-006 batch found its features built but not wired: the live WS run **never simulated the parsed scenario** (`_get_trajectory` read Redis/demo then ran a *blank* Scenario; `db.get_scenario` was unused), so intervention/location/geometry were discarded. CR-007 is the review + 10-PR plan (P0–P4) to connect it. **PR 1 (this) lands the seam + geometry flow:** `ScenarioInput.geometry` → `parse_scenario(geometry=…)` → `Scenario.geometry`; `_get_trajectory` now simulates the **persisted** scenario (demo fallback gated to the demo id); `createScenario(query, geometry?)` + `ScenarioBuilder` post a structured bare GeoJSON geometry (`drawnGeometryToGeoJSON`). No Locked-doc edits; methods follow-ups stay deferred to PR 6. Tests: kernel 175p/3s, api 61p/4s, web 158p. | cr-006 §6 / code review | cr-007 (new), this index | [cr-007-close-the-loop.md](cr-007-close-the-loop.md) |
| CR-006 | 2026-06-14 | **Beyond the Hackathon - product-hardening pivot.** Reframed MATRIX from hackathon submission → **real-world product** (hackathon = milestone/showcase). Documents the merged 16-unit batch (PRs #1–#17 at `2f4e636`): CI + secrets hygiene; **Scenario v2** typed interventions + geometry engine; facility demand-redistribution (`BEH-4-PROVISIONAL`); **computed VAL-01/VAL-02** gates (Calderon RMSE sourced, flood IoU **PROVISIONAL**); city-agnostic `CityConfig`; LLM resilience; **API persistence** (Postgres/PostGIS, `/runs`,`/audit`,`GET /validation`); WS hardening (`QUEUED` event + `DONE.timings`, stage timeouts, semaphore, dependency-aware `/health`); auth+rate-limit+CORS; live cockpit + progressive UX + interactive glass-box provenance; map data layers; structured scenario builder (`/builder`); glass-box debt remediation (SOCI-3 provenance, dataset tiers registered, proxy constants named + PROVISIONAL, citation guard enforces dataset basis). Records PRD/SDD/RFC/methods **amendments** without editing the Locked docs; **methods follow-ups deferred to this CR:** promote `BEH-4-PROVISIONAL`→ methods §3.1; ratify VAL-01/VAL-02 thresholds + dataset-tier additions. Honest debt carried: mode-share uncalibrated; ~123 s vs 90 s budget; flood/edges/confidence-map samples PROVISIONAL. | MATRIX.md §8/Appendix A | cr-006 (new), implementation-plan-matrix, MATRIX.md, this index | [cr-006-beyond-hackathon.md](cr-006-beyond-hackathon.md) |

---

## 3. Incident Log (Postmortems)

| PM ID | Incident date | Severity | Summary | Action items closed? | File |
|-------|---------------|----------|---------|----------------------|------|
| - | - | - | none yet | - | - |

---

## 4. Health Check

- [x] Every Locked doc's **Last Reconciled** date is newer than the last code change to its area. *(Reconciled 2026-06-24.)*
- [x] Feature IDs (`PRD-F#`) referenced by SDD/RFC/QAD still exist in the PRD. *(Sweep complete 2026-06-24 - all IDs validated.)*
- [x] Data confidence tiers in [../data/READINESS.md](../data/READINESS.md) still match what the modules consume. *(Data audit 2026-06-09 - all five dimensions' floors backed on-disk.)*
- [x] No doc has been in `Draft` longer than expected without movement. *(All drafts active and updated under CR-010/CR-012.)*

---

## 5. Notes

- **Source of truth:** [MATRIX.md](../MATRIX.md) supersedes the older PUP-ATLAN roadmap framing (see MATRIX.md Appendix A). When MATRIX.md and a generated doc disagree, MATRIX.md wins until the doc is reconciled.
- **Data backing:** [../data/INVENTORY.md](../data/INVENTORY.md) (manifest) and [../data/READINESS.md](../data/READINESS.md) (per-dimension availability + confidence) are the empirical basis the SDD draws on.
- **Scale:** treated as **Full** (multi-feature, public users, hackathon → production path). Backbone sequence INDEX → PRD → SDD; QAD/CLR/OPS to follow before any production launch.
