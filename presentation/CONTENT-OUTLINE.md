# MATRIX Pitch — Content Outline (scrutinized, debunked, refined)

**Audience:** ASEAN AI Hackathon 2026 judges (Smart Cities track) — VC-grade business slides kept credible.
**Format:** self-contained HTML deck → PDF (`deck/index.html`, `scripts/export-pdf.mjs`).
**Through-line:** *honest confidence is the brand.* Every claim is sourced or explicitly labeled directional. We never trade trust for a bigger number.
**Status of the build it pitches:** Milestone A+B done (kernel + 5 modules + WS/Gemini API + Next.js/Deck.gl frontend). Validation gates (Calderon RMSE, 2024 flood) are *planned, not shipped* — the deck says so.

> This file is the rationale behind the slides. Your 10 requested sections are all covered; refinements and debunks are called out. **One addition is recommended:** a *Proof / What's-built* slide — the strongest judge asset now that the code genuinely runs.

---

## How each requested section was scrutinized

### 1. Problem
- **Keep:** three documented failures — static feasibility studies age on filing; cross-domain impacts evaluated in silos; existing tools need specialists.
- **Debunk / refine:** drop hard, unsourced figures ("multi-billion-peso," "25–35% first-mile fare") as *precise* claims. The Montalbo / JICA / TRID / ICLEI references are real but not page-linkable, so present them as *illustrative of a documented pattern*, not as cited statistics. This protects us in Q&A.

### 2. Target Market
- **Refine:** present as **beachhead → region**, not a flat list. Beachhead = Iloilo LGU (CPDO, NEDA VI, DOTr/LTFRB VI); then developers (Megaworld, Ayala); then civic/academic (UP Visayas SURP, Clean Air Asia, ICLEI); then ASEAN cities. A beachhead story reads as strategy; a list reads as a wish.

### 3. Current Solutions & Gaps
- **Debunk:** the absolute "no ASEAN platform does this" is unfalsifiable. Replace with a **feature survey** (PTV Vissim, Aimsun, ESRI CityEngine, Replica, UrbanFootprint, AnyLogic) showing the *combination* gap: NL input **+** 5 dimensions in one run **+** per-dimension confidence. Honest caveat on the slide: "based on our feature survey." (Mirrors [GTM §2.1](../docs/gtm-matrix.md).)

### 4. Solution
- **Keep, tighten:** drop a project on a city's digital twin → 90 s → 5 scored dimensions with confidence intervals + animated playback + cited Gemini narrative + exportable report.

### 5. Three Features = UVP (exactly three, all verified built)
1. **One unified kernel → five dimensions in one run.** All five score the *same* simulated reality, so they never contradict each other.
2. **Glass box, confidence-anchored.** Every number → `equation_id` + named open datasets + a *computed* H/M/L confidence, resolvable in an Inspect drawer. Bias auditor + mode-share anchor. Honest ranges, not false precision.
3. **Plain language → 90-second real-time simulation.** A planner asks in words / drops a pin; no specialist, no modeling background.

### 6. How it Works
- **Keep:** pipeline diagram (NL/map → Gemini orchestrator → unified SUMO + persona + bias-auditor kernel → one trajectory dataset → 5 parallel modules → synthesis → Deck.gl) + the 90 s mechanics (pre-warmed persona pool, delta-vs-nightly-baseline, parallel modules, streaming/progressive UI).
- **Honesty note:** the 90 s budget is the **target** and holds with a *warm baseline, single user*; the current warm-run probe is ~123 s and Phase-6 optimization is the named next step. Say "target," show the architecture that earns it.

### 7. Value of the Solution
- **Refine, debunk:** per-segment value (LGU de-risks capital projects; developer de-risks site/entrance/parking; civic gets independent verification). **No invented ROI.** ASEAN value = no hardware; deploys via OSM-bbox swap + persona reweight → cost is API tokens, not procurement. The honesty layer is itself the value in data-sparse cities.

### 8. Business Model Canvas
- **Refine:** full 9-block BMC. Revenue = public-good free tier (LGU/academic) + paid developer/SaaS tier, **labeled TBD/post-hackathon**. Add a **clearly-labeled directional** market frame (count of ASEAN cities × order-of-magnitude planning budgets, assumptions stated) — never a false-precise TAM/SAM/SOM.

### 9. Go-To-Market
- **Keep:** Iloilo beachhead (Clean Air Asia is *already building* the open mobility-data infrastructure MATRIX consumes; ASEAN-award anchor) → other PH cities → ASEAN (Jakarta ojek/angkot, Bangkok songthaew/tuk-tuk, HCMC xe-om, KL Rapid). Land via LGU + academic-validation partnerships; the highest-leverage move is one real Iloilo CPDO planner validating the demo.

### 10. Why Us
- **Keep, strengthen:** Team ATLAN (PUP); glass-box engineering discipline that is *actually built and tested*; Iloilo local knowledge; the honest-confidence philosophy; an ASEAN/Filipino team building for ASEAN cities, with multilingual personas (Filipino + Hiligaynon).

### ➕ Recommended addition — Proof / What's Built
- A "it runs today" slice: the live 90 s demo, the glass-box test contract, the 180-barangay data foundation, real Deck.gl playback + Inspect drawer screenshots. Maps directly to AAIH **Technical Execution** (40% at semi-final). This is the slide that converts "ambitious idea" into "working system."

---

## Slide order (final)
1. Title + hook (ASEAN Clean Tourist City 2026 anchor)
2. Problem
3. Target Market (beachhead → region)
4. Current Solutions & Gaps (feature survey)
5. Solution
6. 3 Features = UVP
7. How it Works (+ the live-demo moment)
8. Proof / What's Built  ← added
9. Value of the Solution
10. Business Model Canvas
11. Go-To-Market (ASEAN scaling)
12. Why Us
13. Close / vision / ask
14. Appendix (glass-box methodology, confidence rubric, validation roadmap, honest constraints) — Q&A defense

## How the ASEAN tailoring is built in
1. Open on the verified regional anchor (ASEAN Clean Tourist City 2026, ATF Cebu).
2. Frame the failure pattern as ASEAN-wide (informal transit, flood, rapid suburban growth, data scarcity) — Iloilo is representative, not a special case.
3. Position the confidence-floor honesty as a *feature for data-sparse ASEAN cities*.
4. Foreground the informal economy (jeepney/ojek/angkot/tuk-tuk/xe-om + vendor displacement) — what Western tools omit.
5. Zero-hardware scaling = ASEAN cost is tokens, not procurement; name the next cities + their transit modes.
6. ASEAN/Filipino team, multilingual personas.
7. Map slides to the AAIH rubric: Innovation, Technical Execution, Impact & Feasibility, Presentation/Q&A.

## Sources used on factual slides
- ASEAN Clean Tourist City Award 2026 — PIA, Panay News, VisMin (ATF Cebu, Jan 30 2026; Iloilo's 2nd, prior cycle 2020–22). See [MATRIX.md References](../MATRIX.md).
- Gemini 3.1 Pro released Feb 19 2026 — Google blog.
- Competitor feature survey — [GTM §2.1](../docs/gtm-matrix.md).
- Equations + provenance — [methods-matrix.md](../docs/methods-matrix.md). Data backing — [data/READINESS.md](../data/READINESS.md).
