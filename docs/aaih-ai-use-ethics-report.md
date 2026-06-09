# **AAIH 2026 AI Use & Ethics Report**

**Team Name:** ATLAN  
**Institution:** Polytechnic University of the Philippines  
**Track:** Smart Cities  
**Project:** MATRIX (Multi-Agent Twin for Routing & Infrastructure eXchange)  
**Pilot City:** Iloilo City, Western Visayas, Philippines  

---

### 1. INTRODUCTION
Urban infrastructure in developing ASEAN regions consistently suffers from a lack of reliable planning data. Municipalities frequently make multi-billion-peso decisions—such as locating transport hubs, routing flood-drainage corridors, or zoning high-density complexes—based on outdated, static feasibility studies or sparse, manual census counts. Consequently, new infrastructure is often misaligned with real public demand, resulting in immediate congestion or displacement. The primary objective of the MATRIX simulator is to model pre-construction urban changes dynamically across five critical dimensions—Behavioral, Social, Economic, Ecological, and Societal—within 90 seconds. AI is necessary to simulate the complex, non-linear routing choices of thousands of diverse commuter personas and to synthesize multi-dimensional results into plain-language, citation-anchored reports.

### 2. PROBLEM CONTEXT & SOLUTION OVERVIEW
Developing ASEAN suburban centers like Iloilo City (Philippines)—recent winner of the 2026 ASEAN Clean Tourist City Award—are expanding rapidly without adequate digital planning twins. Primary stakeholders include local government planning offices (CPDO), transport franchises, local businesses, residents, and vulnerable informal sectors (tricycle drivers and street vendors). MATRIX integrates road topology (OpenStreetMap), zoning layouts, public transit schedules, household poverty censuses, flood hazard layers (Project NOAH), satellite imagery (Sentinel-2), weather APIs, and vehicle emission factors (WHO). 

 planners input natural-language queries like *"What if we build a 3,000-seat school in Molo?"* The AI orchestration layer (Gemini 3.1 Pro) parses the query into specific spatial and transport variables, triggering a headless SUMO multi-agent traffic simulation populated by economic-demographic personas. The trajectory outputs are evaluated by five parallel impact modules and compiled by an LLM synthesis agent into an audit-ready summary.

### 3. AI TOOLS & METHODS USED
The prototype uses a hybrid architecture of simulation packages, machine learning models, and large language models:
* **Orchestration & Synthesis:** Gemini 3.1 Pro parses natural-language inputs and synthesizes multi-dimensional results into a report.
* **Persona Generation:** Gemini 3.1 Flash-Lite constructs a localized commuter persona pool (200–500 distinct agents).
* **Traffic Simulation Kernel:** Eclipse SUMO (Simulation of Urban MObility) simulates physical vehicle trajectories and pedestrian flows.
* **Predictive Layer:** XGBoost forecasts baseline corridor volumes using historical traffic datasets.
* **Semantic Search:** ChromaDB vector store coupled with Sentence Transformers (`bge-small-en`) enables local zoning searches.
* **Knowledge Retrieval:** Microsoft GraphRAG resolves dependencies between zoning policies and local infrastructure constraints.

To achieve a 90-second response latency, commuter personas are generated and cached once at startup; scenarios are simulated as delta changes against pre-warmed baselines; and the five scoring modules process trajectories concurrently.

### 4. ASSESSMENT OF AI OUTPUT (CRITICAL EVALUATION)
* **Accuracy:** Technical metrics (e.g., carbon emissions, delays, mode splits) are calculated using deterministic math formulas (e.g., WHO emission factors) and transport physics within the SUMO simulation kernel. The LLM does not generate numbers; it only reads, formats, and synthesizes the simulator's output.
* **Technical Bias:** Persona generation tends to favor middle-class, private-vehicle behaviors due to biases in online LLM training data. To mitigate this, a custom *Bias Auditor* continuously checks generated mode shares against Iloilo's ground-truth surveys (LTFRB/PSA data) and reweights personas if discrepancy limits (±3%) are exceeded.
* **Cultural & Regional Sensitivity:** LLM personas were prompted to reflect ASEAN suburban travel behaviors (e.g., multi-leg commuting using tricycle-to-jeepney transfers and regional walking tolerances in tropical temperatures).
* **Linguistic Nuance:** System prompts utilize Hiligaynon, Filipino, and English datasets. Local terms (e.g., *"sarakyan"* for vehicles, and barangay-specific colloquial paths) are resolved to their structured route names in the GIS database, preventing the model from mischaracterizing routing choices or informal nodes.

### 5. HUMAN INTERVENTION & JUSTIFICATION
Human developers designed and implemented the mathematical equations, confidence rubrics, and ground-truth mode-share anchors. The AI is structurally prevented from altering calculations or introducing speculative figures.

Generative AI alone is insufficient for this task because LLMs lack spatial awareness, cannot compute physical traffic dynamics, and are prone to numeric hallucinations. Consequently, we drew a strict line: AI is used exclusively for unstructured cognitive tasks (parsing natural language inputs, generating diverse persona profiles, and summarizing multi-dimensional reports). Conversely, deterministic code, the SUMO transport physics engine, and hard-coded mathematical formulas (e.g., economic multipliers, Gini accessibility coefficients) own all numeric evaluations, ensuring strict data integrity.

### 6. REFLECTION ON AI-HUMAN CO-CREATION
* **Advantages:** Unprecedented scale and speed. Generating hundreds of nuanced, micro-demographic personas and parsing arbitrary planning scenarios would have taken human planners months; the LLM completed it in minutes.
* **Risks & Challenges:** The primary risk was LLM numeric hallucination in reports. We resolved this by implementing a programmatic *Citation Guard* that scans generated narratives and strips out any number that does not include its exact simulation `equation_id` in brackets.
* **Key Learning:** AI should serve as an intuitive translator and synthesizer, while human-coded algorithms and deterministic rules must serve as the absolute computational validator.

### 7. CONCLUSION
MATRIX demonstrates that pre-construction multi-agent twins can evaluate complex infrastructure impacts in developing regions with high transparency, bypassing expensive sensor networks. By integrating physical simulation with agentic LLM personas, we enable cities like Iloilo to model flood risks, carbon deltas, and informal worker displacement, resulting in more resilient and equitable smart city layouts. Ultimately, the ethical development of AI in ASEAN requires "glass-box" architectures: systems must remain fully auditable, explicitly state their confidence limits (High/Medium/Low), and trace every forecast back to its data provenance.

---

### 8. APPENDICES

#### A. Walkthrough Screenshots
* **Landing Page & Input:** [landing_page.png](file:///d:/PROJECTS/matrix/docs/images/landing_page.png)
* **Live Dashboard & Playback:** [dashboard.png](file:///d:/PROJECTS/matrix/docs/images/dashboard.png)
* **Inspect Traceability Drawer:** [inspect_drawer.png](file:///d:/PROJECTS/matrix/docs/images/inspect_drawer.png)

#### B. Prompt Samples

**1. Natural Language Scenario Parser Prompt (orchestrator.py):**
```python
system_instruction = (
    "You are the MATRIX Orchestrator. Your job is to parse natural language urban planning "
    "queries into structured simulation parameters for the city of Iloilo.\n"
    "If the query lacks a location or an action (e.g., 'what if we build a school?' - where?), "
    "flag it as ambiguous and ask for clarification."
)
```

**2. Narrative Synthesis Prompt (synthesis.py):**
```python
system_instruction = (
    "You are the MATRIX Synthesis Agent. Your job is to write a cohesive, 2-3 paragraph "
    "summary of the urban planning simulation results for Iloilo City. "
    "CRITICAL RULE: Every time you state a number, you MUST include its Equation ID "
    "in brackets immediately after, for example: 'Trips increased by 450 [BEH-1].' "
    "Do not invent any numbers. Only use the numbers provided."
)
```

#### C. Data Citations
* **OpenStreetMap (Philippines Extract):** Map data © OpenStreetMap contributors, licensed under Open Data Commons Open Database License (ODbL).
* **PSA Barangay Population Census (2020/2024):** Philippine Statistics Authority. Open Government Data policy.
* **PAGASA & Project NOAH Hazard Map Layers:** Department of Science and Technology (DOST), Philippines. Public hazard data.
* **Iloilo Comprehensive Land Use Plan (CLUP 2021–2029):** City Government of Iloilo. Public zoning regulation.
