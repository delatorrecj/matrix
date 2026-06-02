# Compliance & Legal Readiness Register (CLR)

**Project:** MATRIX
**Date:** 2026-06-02
**Version:** 0.1
**Owner:** Carlos Jerico Dela Torre (Team ATLAN)
**Status:** Draft
**Last reconciled:** N/A — not yet reconciled with code
**PRD:** [prd-matrix.md](prd-matrix.md) · **SDD:** [sdd-matrix.md](sdd-matrix.md)

---

> ⚠️ **Structural and regulatory awareness only — NOT legal advice.** This register maps the data MATRIX handles and surfaces obligations. It does not draft a Privacy Policy or Terms of Use and does not replace a licensed Philippine attorney. Every **"counsel needed"** item must be reviewed by a lawyer before any public launch. *(Per project convention: consult a licensed Philippine attorney for RA 10173 matters.)*

---

## 0. Target Markets

| Region | In scope? | Notes |
|--------|-----------|-------|
| EU / UK (GDPR) | No (not targeted) | a public demo URL has no geo-blocking; minimize EU PII exposure |
| California (CCPA) | No (not targeted) | same — incidental only |
| **Philippines (RA 10173, Data Privacy Act 2012)** | **Yes (primary)** | pilot Iloilo; LGU + developer users; **PWA collects GPS traces** |

**Geo-blocking:** none planned for the demo. Primary jurisdiction is the Philippines; the build minimizes personal data so incidental foreign access is low-risk — but a Privacy Policy is required regardless.

---

## 1. Data Inventory / Record of Processing

| Activity | Purpose | Data categories | Subjects | Recipients / sub-processors | Cross-border | Retention | Legal basis |
|----------|---------|-----------------|----------|-----------------------------|--------------|-----------|-------------|
| Simulation | impact scoring | **open/aggregated data only** (OSM, CCHAIN barangay, Overture) — synthetic personas, **no PII** | none (aggregate) | Fly.io, Supabase | US (Supabase/Fly) | run metadata | legitimate interest (no personal data) |
| Scenario NL query | parse → plan + narrative | scenario text (planner-authored; not personal) | user (planner) | **Google (Gemini 3.1 API)** | US/Google | run trace | legitimate interest |
| **PWA GPS traces** (`PRD-F10`) | behavioral calibration | **precise location**, device-anon ID | volunteer contributors | Supabase | US | minimize; aggregate then delete raw | **consent (explicit, opt-in)** |
| Product analytics | usage metrics (PRD §5.5) | event telemetry, no PII | users | Supabase (events table) | US | 30 days | legitimate interest |

**Sensitivity flags:**

| Data type | Collected? | Notes |
|-----------|-----------|-------|
| Basic PII (name, email) | No (v1) | no auth for the demo; add → revisit |
| Special-category | No | — |
| Children's data | No | professional/LGU tool |
| **Precise location** | **Yes** | PWA GPS traces — opt-in, anonymized at device |
| Photos / camera / mic | No | — |
| Device / advertising IDs | Partial | anonymized device ID for trace dedup only; no ad IDs |
| Analytics / telemetry | Yes | aggregate event data |
| Payment / card | No | — |

**Self-check:**

| Item | Done? | Evidence | Counsel? |
|------|-------|----------|----------|
| Every activity has a retention period | Partial | this table | — |
| Every sub-processor named + DPA | No | Google/Supabase/Fly/Mapbox | **Yes** |
| Inventory dated + living | Yes | this doc | — |

---

## 2. Multi-Jurisdiction Obligations Matrix *(Philippines in scope)*

| Dimension | Philippines DPA 2012 (RA 10173) — our obligation |
|-----------|---------------------------------------------------|
| **Consent / legal basis** | PWA location requires **explicit opt-in consent**; aggregate sim data has no personal data |
| **Data subject rights** | access, correct, erase/block, object, portability for trace contributors |
| **Breach notification** | NPC **and** affected subjects within **72 h** of knowledge if real risk of serious harm |
| **DPO / PIA / PMP** | **Mandatory DPO**, a **Privacy Impact Assessment** for the PWA, and a Privacy Management Program |
| **Cross-border transfer** | controller (Team ATLAN) stays accountable for Google/Supabase/Fly (US) processing; ensure comparable protection |
| **Our status / action** | designate a **DPO**; complete a **PIA before enabling PWA traces**; publish a Privacy Policy; sign/confirm DPAs |

**Watch list:** NPC circulars on consent + breach; evolving AI-governance guidance (NPC advisory opinions on AI/automated processing).

**Self-check:**

| Item | Done? | Counsel? |
|------|-------|----------|
| Consent model for PWA location | No (designed, not built) | **Yes** |
| Data-subject-request path (access/delete) | No | **Yes** |
| Breach runbook (72 h NPC + subjects) | No → goes in OPS | **Yes** |
| DPO designated | No | **Yes** |

---

## 3. Escalation Flags — Counsel Required

| Flag | Present? | Why it escalates |
|------|----------|------------------|
| Children's data | No | — |
| Health / medical | No | CCHAIN health data is **aggregate barangay**, not personal |
| Payments | No | — |
| Biometric | No | — |
| **Large-scale / systematic monitoring** | **Yes** | PWA collects movement traces → **PIA/DPIA territory** |
| Automated decisions w/ legal effect **on a person** | No | MATRIX advises on *infrastructure*, not decisions about individuals — but label outputs **decision-support, not determinations** |
| Sale / share / behavioral advertising | No | no ad-tech; data never sold |
| Operating with no local entity | Review | confirm Team ATLAN / PUP standing for a public deployment |

**DPIA / PIA required?** **Yes** — complete a Privacy Impact Assessment for the PWA location processing **before** it is enabled (counsel + NPC guidance). The core simulator (no PII) can proceed; **the PWA is the gated surface.**

> **Banner set** (a Section 3 "Yes" is present): do not enable the PWA trace-collection surface in production without a Philippine attorney + a completed PIA.

---

## 4. Terms of Use / Privacy Policy Readiness *(presence-check; counsel drafts)*

| Clause | Present? | Counsel? |
|--------|----------|----------|
| Privacy Policy (RA 10173-compliant; covers PWA location) | No | **Yes** |
| Consent notice for trace collection | No | **Yes** |
| License grant + acceptable use | No | — |
| Limitation of liability + "decision-support, not legal/engineering determination" disclaimer | No | **Yes** |
| Governing law + jurisdiction (Philippines) | No | **Yes** |
| Data-deletion / contributor-rights mechanism | No | **Yes** |

---

## 5. IP Infringement & Protection Readiness

| Item | Status | Counsel? |
|------|--------|----------|
| **OSM + Overture attribution (ODbL)** | **Required — must display "© OpenStreetMap contributors" + Overture attribution** | — (obligation, not counsel) |
| SUMO (EPL 2.0), OSMnx/FastAPI/Deck.gl (MIT), GraphRAG (MIT), libs | compatible; keep an **SBOM** (SPDX/CycloneDX) | — |
| Data licenses: CCHAIN (open), PSA/WB (open gov / CC BY), Sentinel/Copernicus (free), CC BY 4.0 attributions | attribute each per INVENTORY | — |
| Fonts (Geist — OFL/MIT) | compliant | — |
| **Gemini output ownership / indemnity** (Google AUP + generative-AI terms) | review before commercial use | **Yes** |
| Product/brand name "MATRIX" trademark knockout | not done — "MATRIX" is a common mark; check class | **Yes** |
| IP assignment from all contributors (team) | confirm for the hackathon team | review |

---

## 6. App Store / Platform Compliance

**N/A for v1** — MATRIX ships as a **web app + installable PWA**, not through the Apple App Store or Google Play, so the store privacy-label/data-safety forms do not apply. If a native wrapper is ever published, complete Apple App Privacy + Google Play Data Safety then. A **public Privacy Policy URL is still required** for the PWA regardless.

---

## Self-Check

- [x] §0 declares markets; global-accessibility reality stated honestly.
- [x] §1 one row per processing activity, each with retention + basis.
- [x] §2 filled for the in-scope region (Philippines) only.
- [x] §3 "Yes" (monitoring/PIA) has a counsel action; **banner set**.
- [x] §4 ToU/Privacy presence-checked (drafting left to counsel).
- [x] §5 license obligations listed (ODbL attribution is a hard must); SBOM noted.
- [x] §6 addressed (web/PWA — store forms N/A).
- [x] This register maps + escalates obligations; it is **not legal advice** — consult a licensed Philippine attorney.
