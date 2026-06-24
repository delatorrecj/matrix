# **AI-USE & ETHICS** 

# **REPORT**

**Submission Deadline:** June 20, 2026
**Format:** PDF  
**Naming Convention:** SmartCities_PUP_ATLAN_AI_Report.pdf

---

### **TEAM INFORMATION**

| Team Name | ATLAN |
| :---- | :---- |
| **Institution** | Polytechnic University of the Philippines (PUP) |
| **Country** | Philippines |
| **Track** | [ ] Climate Change [ ] Telemedicine [x] Smart Cities [ ] AI for Education |
| **Project Title** | MATRIX: Multi-Agent Twin for Routing and Infrastructure eXchange |

### **1. INTRODUCTION**

Urban infrastructure in developing ASEAN regions is routinely planned on outdated, static feasibility studies. Municipalities commit multi-billion peso decisions, like siting transport hubs or zoning high-density complexes, without a way to test them against real demand. As a result, new infrastructure often arrives already congested or displacing the vulnerable. MATRIX is a pre-construction infrastructure impact simulator designed to solve this. A city planner asks a what-if question in plain language and within 90 seconds sees the proposed change scored across five dimensions: Behavioral, Social, Economic, Ecological, and Societal. Artificial intelligence was necessary because it is impossible to manually simulate the non-linear routing choices of thousands of diverse commuters and translate five streams of complex physics output into one honest, easy-to-understand brief.

### **2. PROBLEM CONTEXT & SOLUTION OVERVIEW**

Iloilo City, the 2026 ASEAN Clean Tourist City, is expanding fast but lacks a digital planning twin. Stakeholders include the City Planning and Development Office, transport franchises, local businesses, residents, and the vulnerable informal sector. We considered data factors such as road networks, local zoning plans, public transit routes, poverty censuses, flood hazards, and emission factors. Our solution integrates this open data to fuel the simulation. The core functionality allows a planner to ask a question, which is parsed by an orchestrator into structured parameters. These parameters drive a traffic simulation populated by economic and demographic personas. The single trajectory dataset is then scored in parallel by five impact modules and narrated by a synthesis agent. Using one core engine feeding five modules ensures that the dimensions never contradict each other.

### **3. AI TOOLS & METHODS USED**

Our prototype relies on several specific AI tools and frameworks. We use Azure OpenAI GPT-5.4 via the Python SDK as our core orchestrator to parse natural language queries and write the final narrative interpretation. We also use it to build a diverse pool of commuter personas matched to Iloilo's specific transportation mode share. For the underlying simulation, we use Eclipse SUMO, accessed via the TraCI API, to model vehicle and pedestrian physics. To provide localized context to the AI, we implemented a Retrieval-Augmented Generation system. This uses a ChromaDB vector store embedded with Sentence-Transformers. It retrieves relevant chunks from a local Hiligaynon gazetteer and our methods ledger, injecting them into the prompts to ground the AI and prevent hallucination. The entire application is deployed as a self-contained container on Hugging Face Spaces.

### **4. ASSESSMENT OF AI OUTPUT (CRITICAL EVALUATION)**

We critically evaluated our AI system to ensure integrity and fairness.

**Accuracy:** Every metric is computed by deterministic equations and physical simulation. The AI only reads and formats the results. We explicitly test against historical data. However, if our data is uncalibrated, like our current mode share, we withhold the final accuracy score and explain why. We publish the withheld status rather than fabricating a passing grade, proving the model's reliability through transparent boundaries.

**Technical Bias:** Generative AI persona pools naturally skew toward middle-class, private car behavior due to training data bias. To counteract this, we built a live Bias Auditor that runs on every simulation. It compares the generated persona pool to Iloilo's actual ground truth. If the AI over-produces cars, the auditor dynamically applies a mathematical reweighting factor, resampling the pool to accurately reflect the real demographics of the city before the simulation begins. To be precise about what runs in production: the default persona pool is sampled directly from this ground-truth anchor, so it is on-target *by construction* — the audit runs on every simulation and passes without correction. The reweighting is the safety net that activates for the opt-in LLM-generated persona path (`MATRIX_PERSONA_LLM=1`), where the model's bias can surface. A concrete worked example — a private-car-over-indexed batch corrected to within ±3% of ground truth, with the exact per-mode factors — is in [methods-matrix.md §4.1](methods-matrix.md#41-bias-auditor-middle-class-bias-reweight-example) and is pinned by an automated test so the published numbers cannot silently drift.

**Cultural & Regional Sensitivity:** Our personas reflect actual ASEAN suburban behavior. We explicitly model the vulnerable informal sector. Tricycles operate as distinct vehicles with specific feeder routes. Street vendors are modeled via economic displacement and footfall. If a new hub routes foot traffic away, the system flags the potential loss of livelihood.

**Linguistic Nuance:** We curated a local Hiligaynon gazetteer to ensure semantic integrity. When a planner uses a colloquial term like "tulay" for a bridge, the system maps it to the specific geographic node, bypassing AI hallucination entirely.

### **5. HUMAN INTERVENTION & JUSTIFICATION**

Human developers authored every equation, confidence rubric, and ground truth anchor. The AI is structurally barred from altering a calculation or inventing a figure. We call this the glass box principle. Human intervention was required to establish low confidence protocols. When data is sparse or outdated, the system flags the output as low confidence and presents it as a directional trend rather than a precise estimate. Furthermore, we implemented an iterative feedback mechanism. City planners can flag implausible results, correct location mappings, or attach known ground truth values. The AI output was insufficient on its own because urban planning requires local context that general models lack. We rely on AI for translation and synthesis, but we rely on human expertise for the underlying physics and final validation.

### **6. REFLECTION ON AI-HUMAN CO-CREATION**

The main advantage of using AI was the scale and speed. Generating hundreds of nuanced demographic personas and parsing arbitrary scenarios would take planners months, but the AI does it in minutes. This democratizes complex simulation for municipalities with limited resources. The biggest risks were numeric hallucination and middle-class bias. We resolved hallucination with a programmatic guard that strips any number lacking a specific citation, and we resolved bias with our live auditor. We learned that AI is best used as an intuitive translator. The moment a decision touches a number, a human-coded, auditable algorithm must be the authority.

### **7. CONCLUSION**

MATRIX demonstrates that a pre-construction simulator can evaluate complex infrastructure impacts in a developing region transparently, turning fixed open data into an honest strength. By fusing physical simulation with agentic personas, cities can model flood risk, carbon changes, and informal worker displacement before breaking ground. Our solution contributes to a more sustainable ASEAN by enabling data-driven decisions that consider the vulnerable. The ethical path for AI in our region requires systems that stay fully auditable, state their confidence limits clearly, capture local feedback iteratively, and withhold a result rather than fake one.

### **8. APPENDICES**

#### **Screenshots**

* **Landing Page:** [landing_page.png](images/landing_page.png)
* **Live Dashboard:** [dashboard.png](images/dashboard.png)
* **Inspect Traceability Drawer:** [inspect_drawer.png](images/inspect_drawer.png)

#### **Prompt Samples**

**Scenario Parser:**
"You are the MATRIX Orchestrator. Parse natural language urban planning queries into structured simulation parameters for Iloilo City. Only fill numeric parameters the user stated or clearly implied. Never invent numbers. If the query lacks a location or an action, flag it as ambiguous and ask for clarification."

**Narrative Synthesis:**
"You are the MATRIX Synthesis Agent. Write a summary of the results. CRITICAL: every time you state a number you MUST append its Equation ID in brackets. Do not invent any numbers. Use only those provided."

#### **Data Citations**

* **OpenStreetMap:** © OpenStreetMap contributors, ODbL.
* **Population and Poverty Census:** Philippine Statistics Authority, Open Government Data.
* **Project NOAH flood hazards:** Department of Science and Technology, Philippines.
* **Zonal Values and Business Surveys:** Bureau of Internal Revenue and Philippine Statistics Authority.
* **Iloilo Comprehensive Land Use Plan:** City Government of Iloilo.
