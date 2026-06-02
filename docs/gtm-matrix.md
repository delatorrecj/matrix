# Go-To-Market (GTM) Strategy

**Project:** MATRIX
**Date:** 2026-06-02
**Version:** 0.1
**Owner:** Jerico — lead/pitch · **Research & Marketing:** Rica Mae Mago + Russell Jay Fajardo ([PRD §10](prd-matrix.md))
**Status:** Draft
**Last reconciled:** N/A
**PRD:** [prd-matrix.md](prd-matrix.md)

> "Launch" here = the **ASEAN AI Hackathon 2026** journey (submission → semi-final → final) *and* the post-hackathon path to real LGU users. Not monetized at this stage — open/public-good. Judging-criteria alignment is in [MATRIX.md Appendix B](../MATRIX.md) (the BRD).

---

## 1. Product Summary (GTM View)

**What it does:** drops a proposed project onto a digital twin of a city and returns scored, confidence-anchored impact across five dimensions in ~90 seconds — with every number traceable.

**Who it's for:** LGU planners, developers/master-planners, and civic/academic stakeholders in ASEAN cities that can't afford sensor-based digital twins.

**Core value proposition:** **answers "what *would* happen if we build this?"** — the pre-construction, counterfactual question no live-IoT twin can answer — across five dimensions, honestly bounded, **with no hardware and no black box.**

**Category:** urban-planning decision-support / civic AI (pre-construction impact simulation).

---

## 2. Target Audience

**Primary ICP — the LGU planner.**
- *Who:* a city planning officer (Iloilo CPDO, NEDA VI) evaluating infrastructure proposals; map-literate, not a simulation modeler.
- *Where:* LGU offices; planning networks (League of Cities); the Clean Air Asia / ICLEI / UNESCAP sustainability-mobility circles; UP Visayas SURP.
- *Believes:* static feasibility studies fail, cross-domain impacts are siloed, existing tools need specialists.
- *Trigger to try:* a 90-second, five-dimension, glass-box demo **on their own city's data.**

**Secondary:** developers/master-planners (Megaworld Iloilo Business Park, Ayala Land) — site selection, pre-consultation impact. **Tertiary:** civic/academic (UP Visayas, Clean Air Asia) — independent, simulation-backed verification.

---

## 3. Pricing Model

**Model:** `Free / Open` for the hackathon (MIT-licensed, public demo URL).

| Tier | Price | Included | Gate |
|------|-------|----------|------|
| Open (hackathon) | $0 | full demo, public repo, reference scenarios | single-user demo load |
| *(future)* LGU / academic | free (public-good) | hosted city instance | post-hackathon |
| *(future)* Private developer | paid (TBD) | private scenarios, SLA | post-hackathon |

**Rationale:** at hackathon stage the goal is **adoption + credibility**, not revenue; free/open maximizes judge trust and LGU/academic uptake. Monetization (private-developer tier) is a post-hackathon question.

---

## 4. Positioning & Messaging

**Tagline:** *Real-time twins tell a city what is happening. MATRIX tells it what will happen if it builds.*

**Primary message:** "Multi-billion-peso infrastructure is decided on static studies that age the day they're filed. MATRIX simulates the community impact of a project **before a single peso is spent** — five dimensions, explicit confidence, in 90 seconds, every number traceable to its data and equation. No sensors, no black box, deployable to any ASEAN city."

**Proof points:**
- Five dimensions from **one simulation kernel** — internally consistent, not five contradicting tools.
- **Glass-box:** every output traces to an equation + named open data + confidence ([methods-matrix](methods-matrix.md)).
- **Validated** against the Calderon 2014 BRT model + the 2024 Iloilo flood ([QAD §8](qad-matrix.md)).
- **No hardware** — pure cloud + open data; runs where IoT twins can't afford to.
- Anchored to **Iloilo, ASEAN Clean Tourist City 2026.**

**Objection handling:**
| Objection | Response |
|-----------|----------|
| "Deployed IoT digital twins already exist." | They monitor the *present*; MATRIX simulates the *unbuilt future* — a different, harder question. And it needs zero sensors. |
| "Your data is fixed, not real-time." | Fixed open data is what makes it deployable everywhere; the confidence layer states exactly where it's sure vs estimating — more honest than hidden sensor gaps. |
| "How do we know the numbers are right?" | Every number is clickable to its equation + sources + confidence (glass-box), and the model is back-tested (RMSE vs Calderon; IoU vs the 2024 flood). |
| "Tools like this need specialists." | Plain-language input; a planner gets a calibrated five-dimension answer with no modeling background. |

---

## 5. Launch Channels & Tactics

**Owned:** public GitHub repo + README, the live demo URL, the pitch deck + semi-final video, the 8 reference scenarios.

**Earned / institutional (the real channel for a civic tool):**
| Channel | Tactic | Timing |
|---|---|---|
| AAIH 2026 judges + workshops | the live 90-second five-dimension demo on Iloilo; the glass-box "Inspect" moment | semi-final / final |
| **Iloilo CPDO** | the data-request letter ([data/outreach](../data/outreach/)) → a planner validates the demo | now → semis |
| Clean Air Asia (SMMR), UP Visayas SURP, ICLEI | share the open methodology; invite verification | post-submission |
| ASEAN Clean Tourist City narrative | open pitch with the Iloilo award as the hook | throughout |

**Content assets before final submission:**
- [ ] Demo video (semi-final): the NL query → animated 5-dim playback → Inspect drill-down.
- [ ] Pitch deck (AAIH template) leading with the differentiation thesis.
- [ ] Public repo + README + demo URL + MIT LICENSE.
- [ ] One real Iloilo planner reaction (the highest-leverage proof point).

---

## 6. Launch Phases (mapped to the AAIH timeline)

| Phase | Criteria to enter | Target | Goal |
|-------|-------------------|--------|------|
| **Alpha** (internal) | kernel + 2 dimensions live | Sprint 2 (late May) | end-to-end demo on one scenario |
| **Beta** (Top 20 / semi-final) | all 5 dimensions + UI + 90 s budget | late May–June | live semi-final demo; integrate workshop feedback |
| **Public submission** | all deliverables 48 h early; **CLR cleared** (PWA trace surface gated until PIA done) | ~June 20 | public repo + demo URL; judged submission |
| **Post-hackathon** | — | post-July | **Iloilo CPDO pilot**; ASEAN city #2 scaling demo |

---

## 7. Success Metrics

No `BRD-M#` (MATRIX.md is the BRD); targets align to the AAIH judging weights (MATRIX.md Appendix B) + product proof.

| Metric | Target | How measured |
|--------|--------|--------------|
| AAIH placement | advance Top 20 → Top 8 → final | competition results |
| Real planner validation | ≥ 1 Iloilo CPDO/NEDA planner confirms the workflow is useful | recorded reaction |
| Demo reliability | 90 s budget held; glass-box Inspect works on every number | `PERF-01` + TRACE gates ([QAD §8](qad-matrix.md)) |
| Open-methodology credibility | repo + methods-matrix public; reproducible run | GitHub + a reproduced scenario |
| Scaling proof | one ASEAN city #2 bbox demo | scaling demo (`PRD-F12`) |

---

## Self-Check

- [x] §2 ICP is nameable (Iloilo CPDO / NEDA VI planners; Megaworld/Ayala teams; UP Visayas SURP).
- [x] §3 pricing fits stage (free/open now; monetization deferred, not forced).
- [x] §5 assets listed and tied to the submission deadline.
- [x] §6 phases have binary entry criteria mapped to the AAIH timeline; CLR is the public-launch gate.
- [x] §7 metrics are measurable (competition results, QAD gates, a recorded planner reaction).
- [x] Drafted before launch.
