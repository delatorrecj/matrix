# AAIH 2026 — AI Use & Ethics Report

| | |
| :---- | :---- |
| **Team Name** | ATLAN |
| **Institution** | Polytechnic University of the Philippines (PUP) |
| **Country** | Philippines |
| **Track** | [ ] Climate Change  [ ] Telemedicine  [x] **Smart Cities**  [ ] AI for Education |
| **Project Title** | MATRIX — Multi-Agent Twin for Routing & Infrastructure eXchange |
| **Pilot City** | Iloilo City, Western Visayas, Philippines |

> **File for submission:** `SmartCities_PUP_ATLAN_AI_Report.pdf`

---

### 1. INTRODUCTION

Urban infrastructure in developing ASEAN regions is routinely planned on outdated, static feasibility studies. Municipalities commit multi-billion-peso decisions — siting transport hubs, routing flood-drainage corridors, zoning high-density complexes — without a way to test them against real demand, so new infrastructure often arrives already congested or already displacing the vulnerable. MATRIX is a **pre-construction infrastructure-impact simulator**: a planner asks a what-if in plain language and, within a 90-second budget, sees the change scored across five dimensions — Behavioral, Social, Economic, Ecological, and Societal. AI is necessary because the problem is doubly intractable for hand methods: simulating the non-linear routing choices of thousands of diverse commuters, and translating five streams of physics output into one honest, citation-anchored brief.

### 2. PROBLEM CONTEXT & SOLUTION OVERVIEW

Iloilo City — 2026 ASEAN Clean Tourist City — is expanding fast with no digital planning twin. Stakeholders span the City Planning and Development Office (CPDO), transport franchises, local businesses, residents, and the **vulnerable informal sector**: tricycle drivers and street vendors whose livelihoods turn on routing and footfall. MATRIX integrates open data — OpenStreetMap road topology, the Iloilo CLUP zoning plan, public-transit routes, PSA poverty/population censuses, Project NOAH flood hazards, Sentinel-2 imagery, and WHO/EMEP emission factors. A planner's query (*"What if we build a 3,000-seat school in Molo?"*) is parsed by a Gemini 3.1 Pro orchestrator into structured simulation parameters; these drive **one** headless SUMO multi-agent run populated by economic-demographic personas. The single trajectory dataset is then scored in parallel by five impact modules and narrated by a synthesis agent. One kernel feeding five modules is deliberate: it is the reason the five dimensions can never contradict each other.

### 3. AI TOOLS & METHODS USED

- **Orchestration & Synthesis:** Gemini 3.1 Pro — parses NL queries and writes the final narrative.
- **Persona Generation:** Gemini 3.1 Flash-Lite — builds a 200–500 agent commuter pool matched to Iloilo's mode-share.
- **Traffic Kernel:** Eclipse SUMO (via the TraCI API) — simulates vehicle and pedestrian physics.
- **Predictive Layer:** XGBoost — forecasts baseline corridor volumes.
- **Retrieval (RAG):** a **ChromaDB** vector store embedded with `bge-small-en-v1.5` (Sentence-Transformers). An ingestion step indexes the Hiligaynon gazetteer, place context, and methods-ledger snippets; at query time the top-k chunks (each carrying a `source`) are injected into the orchestrator prompt for disambiguation and into synthesis for grounding. RAG informs prose only — it **never originates a number** (the citation guard enforces this).

To hit the 90-second budget, the persona pool is generated and audited once at startup, scenarios run as delta changes against a pre-warmed nightly baseline, and the five modules score concurrently.

### 4. ASSESSMENT OF AI OUTPUT (CRITICAL EVALUATION)

- **Accuracy & Ground-Truth Comparison.** Every metric is computed by deterministic equations and SUMO physics — the LLM only reads and formats. We back-test against Iloilo history: **VAL-01** compares simulated corridor flows to the Calderon (2014) Ungka–Iloilo counts (target NRMSE ≤ 0.30), and **VAL-02** compares flooded-segment extent to the 2024 floods (IoU). In honest current status, **VAL-01 is withheld** (`NOT_RUN`): our synthetic demand is not yet calibrated to a 2026 travel survey, so a passing RMSE would be a false precision; **VAL-02 is provisional** pending Copernicus Sentinel-1 ground-truth. We publish the withhold and its reason rather than a fabricated pass.
- **Technical Bias — auditor in action.** LLM persona generation skews toward middle-class, private-car behavior. A **Bias Auditor** runs on every simulation, comparing the pool's mode-share to Iloilo's ground-truth anchor; beyond ±3% it **reweights** the pool with per-mode factors `f_k = target_k / observed_k`. *Worked example:* the generator over-produces cars at 0.18 vs the 0.07 anchor (+11 pts); the auditor applies `f_car ≈ 0.39` (down-weight) and up-weights jeepney, resampling the pool back inside ±3%. The factors are published in a public audit log and shown in the UI.
- **Cultural & Regional Sensitivity.** Personas reflect ASEAN suburban behavior — multi-leg tricycle-to-jeepney transfers, tropical walking tolerances. The **informal sector** is modeled explicitly: tricycles as bounded, terminal-anchored feeder trips and street vendors as footfall-dependent revenue with displacement loss under closures. MATRIX also handles **extreme events** — a monsoon-flood or sudden full-closure query closes the affected segments, redistributes demand, and re-scores all five dimensions under capped confidence.
- **Linguistic Nuance.** A curated **Hiligaynon gazetteer** maps colloquial terms to canonical GIS nodes before the LLM step (e.g. *"barahan ang tulay sa Forbes"* → *tulay* = bridge → Forbes Bridge node). The node id comes from the gazetteer, never the model — preserving semantic integrity.

### 5. HUMAN INTERVENTION & JUSTIFICATION

Human developers authored every equation, confidence rubric, and ground-truth anchor; the AI is **structurally barred** from altering a calculation or inventing a figure (the "glass box" — every number resolves to its `equation_id`, input datasets, and a *computed* confidence in the UI's Inspect drawer). We drew a hard line: AI handles only unstructured cognition (parsing language, generating personas, summarizing), while deterministic code owns all numbers. Two human-designed safeguards bound the AI: a **Low-Confidence Protocol** (sparse/missing data, >10-year vintage, uncalibrated method, or an unknown dataset → the dimension is flagged **Low** and rendered as a *direction*, not a point estimate, with the triggering reason surfaced), and a **CPDO feedback loop** (PRD-F20): planners can flag a result as implausible or attach a known value, which becomes a candidate validation fixture — human-in-the-loop refinement, never silent auto-tuning.

### 6. REFLECTION ON AI-HUMAN CO-CREATION

**Advantages:** scale and speed — generating hundreds of nuanced micro-demographic personas and parsing arbitrary scenarios would take planners months; the LLMs do it in minutes. **Risks:** numeric hallucination and middle-class bias. We resolved hallucination with a programmatic **Citation Guard** that strips any number lacking its `equation_id`, and bias with the auditor above. **Key learning:** the AI is best as an intuitive translator and synthesizer; the moment a decision touches a number, a human-coded, auditable algorithm must be the authority.

### 7. CONCLUSION

MATRIX shows that a pre-construction multi-agent twin can evaluate complex infrastructure impacts in a developing region transparently, without an expensive live-sensor network — turning fixed open data into an honest strength. By fusing physical simulation with agentic LLM personas, cities like Iloilo can model flood risk, carbon deltas, and informal-worker displacement *before* breaking ground. The ethical path for AI in ASEAN, we argue, is the **glass box**: systems that stay fully auditable, state their confidence limits (High/Medium/Low), trace every forecast to its data provenance, and withhold a result rather than fake one.

---

### 8. APPENDICES

#### A. Walkthrough Screenshots
- **Landing Page & Input:** [landing_page.png](images/landing_page.png)
- **Live Dashboard & Playback:** [dashboard.png](images/dashboard.png)
- **Inspect Traceability Drawer:** [inspect_drawer.png](images/inspect_drawer.png)

#### B. Prompt Samples

**1. NL Scenario Parser (`orchestrator.py`):**
```python
system_instruction = (
    "You are the MATRIX Orchestrator. Parse natural-language urban-planning "
    "queries into structured simulation parameters for Iloilo City.\n"
    "Only fill numeric parameters the user stated or clearly implied — never invent numbers.\n"
    "If the query lacks a location or an action, flag it as ambiguous and ask for clarification."
)
```

**2. Narrative Synthesis (`synthesis.py`) — the citation contract:**
```python
system_instruction = (
    "You are the MATRIX Synthesis Agent. Write a 2-3 paragraph summary of the results.\n"
    "CRITICAL: every time you state a number you MUST append its Equation ID in brackets, "
    "e.g. 'Trips increased by 450 [BEH-1].' Do not invent any numbers — use only those provided."
)
```

#### C. Data Citations
- **OpenStreetMap (Philippines extract):** © OpenStreetMap contributors, ODbL.
- **PSA Population/Poverty Census (2020/2024 POPCEN-CBMS):** Philippine Statistics Authority — Open Government Data.
- **PAGASA / Project NOAH hazard layers:** DOST, Philippines — public hazard data.
- **BIR Zonal Values (RDO 74), PSA FIES 2023 / ASPBI, DOT Visitor Arrivals 2024:** public government statistics.
- **Project CCHAIN (barangay-level Iloilo climate/air/wealth/health/buildings):** open research dataset.
- **Iloilo CLUP 2021–2029:** City Government of Iloilo — public zoning regulation.
- **Calderon (2014) Iloilo BRT corridor study:** academic literature (VAL-01 ground truth).

#### D. Module → Data-Source Traceability (Judges' Ask #8)

| Module | Primary equations | Key datasets | Confidence |
| :--- | :--- | :--- | :--- |
| Behavioral | BEH-1…4 (Δtrips, V/C, mode-share, facility demand) | OSM/Overture network, persona pool, nightly baseline | Medium (BEH-4 provisional) |
| Ecological | ECO-1…4 (carbon, PM2.5, noise, flood exposure) | WHO/EMEP emission factors, Project NOAH/CCHAIN flood | Medium |
| Social | SOC-1…3 (accessibility, equity, vendor displacement) | CCHAIN RWI/poverty, LPTRP terminals, OSM POI | Medium |
| Economic | ECON-1…3 (land value, business activity, informal income) | BIR zonal values, PSA FIES/ASPBI, DOT arrivals | Medium (ECON-1 = M w/ BIR-ZV) |
| Societal | SOCI-1…4 (well-being, exposure synthesis) | derived from Ecological + accessibility outputs | Low–Medium (directional) |

*(Generated from the `DATASET_TIERS` ledger + methods-matrix §3; see [methods-matrix.md](methods-matrix.md) Appendix A and [../data/INVENTORY.md](../data/INVENTORY.md) for the authoritative, per-equation mapping.)*

#### E. Response to Judges' Feedback (9 Asks)

| # | Judge ask | Where addressed |
| :-- | :--- | :--- |
| 1 | Ground-truth comparison vs Iloilo history | §4 Accuracy (VAL-01/VAL-02, honest withhold) |
| 2 | Vulnerable informal sector (tricycles, vendors) | §4 Cultural Sensitivity |
| 3 | Bias Auditor in action + reweight math | §4 Technical Bias (worked example + factors) |
| 4 | Low-confidence trigger + user alert | §5 (Low-Confidence Protocol) |
| 5 | Extreme events / resilience | §4 Cultural Sensitivity (flood/closure path) |
| 6 | CPDO iterative-feedback mechanism | §5 (PRD-F20 feedback loop) |
| 7 | Hiligaynon colloquial term → GIS node | §4 Linguistic Nuance (gazetteer example) |
| 8 | Module → data-source traceability table | Appendix D |
| 9 | RAG setup & implementation | §3 AI Tools (ChromaDB + bge-small) |

> **Honest scope note (Ethics First).** Several capabilities are implemented and tested but still maturing: VAL-01 is withheld pending mode-share calibration; the Bias Auditor's reweight fires on the LLM-generated pool (the deployed default is a literature-anchored pool already on-anchor); and the gazetteer's GIS node ids are provisional placeholders pending OSM resolution. We disclose these rather than overstate them.
