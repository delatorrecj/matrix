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

Iloilo City — 2026 ASEAN Clean Tourist City — is expanding fast with no digital planning twin. Stakeholders span the City Planning and Development Office (CPDO), transport franchises, local businesses, residents, and the **vulnerable informal sector**: tricycle drivers and street vendors whose livelihoods turn on routing and footfall. MATRIX integrates open data — OpenStreetMap road topology, the Iloilo CLUP zoning plan, public-transit routes, PSA poverty/population censuses, Project NOAH flood hazards, Sentinel-2 imagery, and WHO/EMEP emission factors. A planner's query (*"What if we build a 3,000-seat school in Molo?"*) is parsed by an Azure OpenAI GPT-5.4 orchestrator into structured simulation parameters; these drive **one** headless SUMO multi-agent run populated by economic-demographic personas. The single trajectory dataset is then scored in parallel by five impact modules and narrated by a synthesis agent. One kernel feeding five modules is deliberate: it is the reason the five dimensions can never contradict each other.

### 3. AI TOOLS & METHODS USED

- **Orchestration & Synthesis:** Azure OpenAI GPT-5.4 (via the `openai` Python SDK) — parses natural language queries and writes the final narrative interpretation.
- **Persona Generation:** Azure OpenAI GPT-5.4 — builds a 200–500 agent commuter pool matched to Iloilo's mode-share.
- **Traffic Kernel:** Eclipse SUMO (via the TraCI API) — simulates vehicle and pedestrian physics.
- **Predictive Layer:** XGBoost — forecasts baseline corridor volumes.
- **Retrieval-Augmented Generation (RAG):** A ChromaDB vector store embedded with `bge-small-en-v1.5` (Sentence-Transformers). An offline ingestion pipeline chunks and indexes the Hiligaynon gazetteer, OpenStreetMap place context, and methods-ledger snippets. At query time, the top-k retrieved chunks (each carrying a explicit `source` metadata tag) are injected into the orchestrator prompt for disambiguation and into the synthesis prompt for grounding. RAG informs prose only — it **never originates a number**.

To hit the 90-second budget, the persona pool is generated and audited once at startup, scenarios run as delta changes against a pre-warmed nightly baseline, and the five modules score concurrently.

### 4. ASSESSMENT OF AI OUTPUT (CRITICAL EVALUATION)

- **Accuracy & Ground-Truth Comparison:** Every metric is computed by deterministic equations and SUMO physics — the LLM only reads and formats. We explicitly back-test against Iloilo history: **VAL-01** compares simulated corridor flows to the Calderon (2014) Ungka–Iloilo counts, and **VAL-02** compares flooded-segment extent to the 2024 monsoon floods. In honest current status, **VAL-01 is withheld** (`NOT_RUN`): our synthetic demand is not yet calibrated to a 2026 travel survey, so a passing RMSE would be a false precision. We publish the withhold and its reason rather than a fabricated pass, proving the model's predictive reliability through transparent bounds. This approach ensures that city planners do not mistakenly rely on uncalibrated baseline data for billion-peso infrastructure decisions.
- **Technical Bias & The Auditor in Action:** Generative AI persona pools naturally skew toward middle-class, private-car behavior due to training-data bias. To counteract this, a **Bias Auditor** runs on every simulation, comparing the generated pool's mode-share to Iloilo's ground-truth anchor. In a concrete scenario, the LLM over-produced cars at an 18% share versus the 7% anchor (+11 points, exceeding our ±3% tolerance). The auditor dynamically applied a reweighting mathematical adjustment factor of `f_car ≈ 0.39` (down-weight) and correspondingly up-weighted jeepneys, stratified-resampling the pool back inside the ±3% band before simulation. This ensures that the simulated population accurately reflects the real demographics of the city rather than the biases of the training data.
- **Cultural & Regional Sensitivity (Vulnerable Populations):** Personas reflect ASEAN suburban behavior. The **vulnerable informal sector** is modeled explicitly, directly addressing concerns about marginalized groups. Tricycles operate as a distinct archetype with bounded, terminal-anchored feeder trips, rather than generic vehicles. Furthermore, street vendors are modeled via economic displacement and footfall-dependent revenue. If a new transport hub routes foot traffic away from traditional vendor locations, the Economic module explicitly flags the potential loss of livelihood. This ensures that the voices and economic realities of the informal sector are quantified in every planning decision.
- **Extreme Events (Resilience Modeling):** MATRIX explicitly handles **extreme weather events** to demonstrate climate resilience. A severe monsoon-flood query closes the affected road segments, redistributes demand dynamically, and re-scores all five dimensions under capped confidence limits. This allows planners to see not just how infrastructure performs on a sunny day, but how the city's transport and economy degrade during a Category 5 typhoon or severe monsoon, which are increasingly common in the region.
- **Linguistic Nuance:** A curated **Hiligaynon gazetteer** ensures the system preserves semantic integrity. For example, a concrete query like *"Ano matabo kon barahan ang tulay sa Forbes?"* successfully maps the colloquial term *"tulay"* to its specific GIS node ("Forbes Bridge"), bypassing LLM hallucination entirely for geometry mapping.

### 5. HUMAN INTERVENTION & JUSTIFICATION

Human developers authored every equation, confidence rubric, and ground-truth anchor; the AI is **structurally barred** from altering a calculation or inventing a figure (the "glass box"). Two human-designed safeguards bound the AI:
1. **Low-Confidence Protocol:** Triggered by sparse data, >10-year vintage datasets, or unknown inputs. The affected dimension is immediately flagged **Low** and rendered as a *directional trend* rather than a point estimate, alerting the user to the potential margin of error along with the triggering reason.
2. **CPDO Iterative Feedback Mechanism (Human-in-the-Loop):** City Planning and Development Office (CPDO) staff can provide iterative feedback on AI-generated reports. Through a dedicated feedback UI, planners can flag implausible results, correct gazetteer mappings, or attach known ground-truth values. These annotations feed into a triage queue to become candidate validation fixtures, refining the model's future outputs through human-in-the-loop oversight rather than silent auto-tuning. This ensures that the AI remains an assistant to the planner, rather than a black-box oracle replacing human judgment.

### 6. REFLECTION ON AI-HUMAN CO-CREATION

**Advantages:** scale and speed — generating hundreds of nuanced micro-demographic personas and parsing arbitrary scenarios would take planners months; the LLMs do it in minutes. This democratization of complex simulation allows even small municipalities with limited GIS expertise to test infrastructure plans. **Risks:** numeric hallucination and middle-class bias. We resolved hallucination with a programmatic **Citation Guard** that strips any number lacking its `equation_id`, and bias with the auditor above. **Key learning:** the AI is best as an intuitive translator and synthesizer; the moment a decision touches a number, a human-coded, auditable algorithm must be the authority. This strict separation of concerns—where AI handles language and heuristics while classical code handles math and physics—proved to be the most ethical and reliable architecture for urban planning.

### 7. CONCLUSION

MATRIX shows that a pre-construction multi-agent twin can evaluate complex infrastructure impacts in a developing region transparently, without an expensive live-sensor network — turning fixed open data into an honest strength. By fusing physical simulation with agentic LLM personas, cities like Iloilo can model flood risk, carbon deltas, and informal-worker displacement *before* breaking ground. The ethical path for AI in ASEAN, we argue, is the **glass box**: systems that stay fully auditable, state their confidence limits, capture CPDO feedback iteratively, trace every forecast to its data provenance, and withhold a result rather than fake one.

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

#### D. Module → Data-Source Traceability Matrix

| Module | Primary equations | Key datasets | Confidence |
| :--- | :--- | :--- | :--- |
| Behavioral | BEH-1…4 (Δtrips, V/C, mode-share, facility demand) | OSM/Overture network, persona pool, nightly baseline | Medium (BEH-4 provisional) |
| Ecological | ECO-1…4 (carbon, PM2.5, noise, flood exposure) | WHO/EMEP emission factors, Project NOAH/CCHAIN flood | Medium |
| Social | SOC-1…3 (accessibility, equity, vendor displacement) | CCHAIN RWI/poverty, LPTRP terminals, OSM POI | Medium |
| Economic | ECON-1…3 (land value, business activity, informal income) | BIR zonal values, PSA FIES/ASPBI, DOT arrivals | Medium (ECON-1 = M w/ BIR-ZV) |
| Societal | SOCI-1…4 (well-being, exposure synthesis) | derived from Ecological + accessibility outputs | Low–Medium (directional) |

*(Generated from the `DATASET_TIERS` ledger + methods-matrix §3; see [methods-matrix.md](methods-matrix.md) Appendix A and [../data/INVENTORY.md](../data/INVENTORY.md) for the authoritative, per-equation mapping.)*

> **Honest scope note (Ethics First).** Several capabilities are implemented and tested but still maturing: VAL-01 is withheld pending mode-share calibration; the Bias Auditor's reweight fires on the LLM-generated pool (the deployed default is a literature-anchored pool already on-anchor); and the gazetteer's GIS node ids are provisional placeholders pending OSM resolution. We disclose these rather than overstate them.
