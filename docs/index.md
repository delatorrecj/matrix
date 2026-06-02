# Documentation Index — MATRIX

**Project slug:** `matrix`
**Maintained by:** Carlos Jerico Dela Torre (Team ATLAN)
**Last updated:** 2026-06-02

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

**Rule:** a fact lives in its canonical doc; everything else links. This is the anti-poisoning contract.

---

## 1. Document Suite

| Document | File | Version | Status | Last Updated | Last Reconciled |
|----------|------|---------|--------|--------------|-----------------|
| BRD — Business Requirements | — | — | N/A — covered by [MATRIX.md](../MATRIX.md) §1–3, §Appendix B | — | — |
| PRD — Product Requirements | [prd-matrix.md](prd-matrix.md) | 0.1 | Draft | 2026-06-02 | N/A — not yet reconciled with code |
| DSD — Design System | [dsd-matrix.md](dsd-matrix.md) | 0.1 | Draft | 2026-06-02 | N/A — not yet reconciled with code |
| SDD — System Design | [sdd-matrix.md](sdd-matrix.md) | 0.1 | Draft | 2026-06-02 | N/A — not yet reconciled with code |
| Methods & Traceability (glass-box ledger) | [methods-matrix.md](methods-matrix.md) | 0.1 | Draft | 2026-06-02 | N/A — equation/provenance registry; backs PRD-F14 |
| QAD — QA & Test Plan | [qad-matrix.md](qad-matrix.md) | 0.1 | Draft | 2026-06-02 | N/A — not yet reconciled with code |
| SAD — Subagents | [sad-matrix.md](sad-matrix.md) | 0.1 | Draft | 2026-06-02 | N/A — 5-agent build roster |
| BUILD — Build Guide | [build-matrix.md](build-matrix.md) | 0.1 | Draft | 2026-06-02 | N/A — materializes to monorepo AGENTS.md at scaffold |
| CLR — Compliance & Legal | [clr-matrix.md](clr-matrix.md) | 0.1 | Draft | 2026-06-02 | N/A — banner set: PWA needs PIA + counsel |
| GTM — Go-To-Market | [gtm-matrix.md](gtm-matrix.md) | 0.1 | Draft | 2026-06-02 | N/A — AAIH journey + post-hackathon LGU path |
| OPS — Ops & Observability | [ops-matrix.md](ops-matrix.md) | 0.1 | Draft | 2026-06-02 | N/A — SLOs incl. 90 s budget; RA 10173 breach runbook |

### RFCs (one per major feature)

| RFC ID | File | Feature | Status | Last Updated |
|--------|------|---------|--------|--------------|
| matrix-rfc-001 | [rfc-matrix-realtime-pipeline.md](rfc-matrix-realtime-pipeline.md) | Real-time simulation pipeline (90 s budget) | Approved | 2026-06-02 |

---

## 2. Change Log

| CR ID | Date | Summary | Trigger doc | Docs touched | File |
|-------|------|---------|-------------|--------------|------|
| — | — | none yet | — | — | — |

---

## 3. Incident Log (Postmortems)

| PM ID | Incident date | Severity | Summary | Action items closed? | File |
|-------|---------------|----------|---------|----------------------|------|
| — | — | — | none yet | — | — |

---

## 4. Health Check

- [ ] Every Locked doc's **Last Reconciled** date is newer than the last code change to its area.
- [ ] Feature IDs (`PRD-F#`) referenced by SDD/RFC/QAD still exist in the PRD.
- [ ] Data confidence tiers in [../data/READINESS.md](../data/READINESS.md) still match what the modules consume.
- [ ] No doc has been in `Draft` longer than expected without movement.

---

## 5. Notes

- **Source of truth:** [MATRIX.md](../MATRIX.md) supersedes the older PUP-ATLAN roadmap framing (see MATRIX.md Appendix A). When MATRIX.md and a generated doc disagree, MATRIX.md wins until the doc is reconciled.
- **Data backing:** [../data/INVENTORY.md](../data/INVENTORY.md) (manifest) and [../data/READINESS.md](../data/READINESS.md) (per-dimension availability + confidence) are the empirical basis the SDD draws on.
- **Scale:** treated as **Full** (multi-feature, public users, hackathon → production path). Backbone sequence INDEX → PRD → SDD; QAD/CLR/OPS to follow before any production launch.
