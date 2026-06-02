# Documentation Index — MATRIX

**Project slug:** `matrix`
**Maintained by:** Carlos Jerico Dela Torre (Team ATLAN)
**Last updated:** 2026-06-02

---

> Manifest for the MATRIX formal doc suite generated via the FMD framework. The canonical product/technical source is **[../MATRIX.md](../MATRIX.md)**; these docs decompose it into the spec-driven suite (PRD → SDD → …). Read this first to see what exists and what's stale.
>
> **Status lifecycle:** `Draft → Locked → Superseded`. Changing a Locked doc requires a Change Record.

---

## 1. Document Suite

| Document | File | Version | Status | Last Updated | Last Reconciled |
|----------|------|---------|--------|--------------|-----------------|
| BRD — Business Requirements | — | — | N/A — covered by [MATRIX.md](../MATRIX.md) §1–3, §Appendix B | — | — |
| PRD — Product Requirements | [prd-matrix.md](prd-matrix.md) | 0.1 | Draft | 2026-06-02 | N/A — not yet reconciled with code |
| DSD — Design System | — | — | Planned | — | — |
| SDD — System Design | [sdd-matrix.md](sdd-matrix.md) | 0.1 | Draft | 2026-06-02 | N/A — not yet reconciled with code |
| QAD — QA & Test Plan | — | — | Planned | — | — |
| SAD — Subagents | — | — | Planned | — | — |
| BUILD — Build Guide | — | — | Planned (at scaffold) | — | — |
| CLR — Compliance & Legal | — | — | Planned (RA 10173 / data privacy) | — | — |
| GTM — Go-To-Market | — | — | Planned | — | — |
| OPS — Ops & Observability | — | — | Planned (pre-prod) | — | — |

### RFCs (one per major feature)

| RFC ID | File | Feature | Status | Last Updated |
|--------|------|---------|--------|--------------|
| — | — | (candidate: simulation kernel; 90s latency pipeline) | Planned | — |

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
