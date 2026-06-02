# **TECHNICAL ROADMAP** 

# **TEMPLATE**

**Submission Deadline:** **May 17, 2026**  
**Format:** PDF (Strictly maximum 5 pages)  
**Naming Convention:** Smart City\_PUP\_ATLAN\_Roadmap.pdf

---

### **TEAM INFORMATION**

| Team Name | ATLAN |
| :---- | :---- |
| **Institution** | Polytechnic University of the Philippines |
| **Country** | Philippines |
| **Track** | \[/\] Smart Cities |
| **Team Leader Name** | Carlos Jerico Dela Torre, [carlosjericodelatorre@gmail.com](mailto:carlosjericodelatorre@gmail.com), \+639496369705 |

### **SECTION 1: EXECUTIVE SUMMARY (PROBLEM-SOLUTION FIT)**

*Urban infrastructure in ASEAN developing regions consistently fails due to a catastrophic data vacuum. City planners rely on static, outdated feasibility studies and incomplete manual census data to design multibillion-dollar transit systems. Because they cannot accurately predict human behavior, new infrastructure often becomes congested the day it opens.*

*ATLAN solves this by bridging the data gap using Agentic AI. We are an Urban Simulation Engine that creates highly accurate, behavioral Digital Twins of city bottlenecks. Instead of relying purely on flawed historical data, ATLAN ingests baseline open-source mapping and traffic data, then utilizes Large Language Models to run "Agentic Simulations"—simulating thousands of commuter personas reacting to real-time variables like weather, road closures, or policy changes.*

*Our dual-model architecture utilizes time-series forecasting to predict peak saturation and Generative AI to deploy "Behavioral Nudges"—targeted interventions (e.g., transit fare discounts or alternate routing) triggered before the bottleneck occurs. ATLAN transitions Smart City infrastructure from reactive concrete pouring to proactive, AI-driven behavioral routing.*

### **SECTION 2: TECHNICAL ARCHITECTURE**

*The system requires a purely cloud-native, AI-driven architecture to process and simulate commuter behaviors:*

**2.1 System Components:**

* **Inputs (The Data Ingestion Layer):** Real-time API integrations via OpenStreetMap (topology), OpenWeather API (environmental triggers), and public traffic APIs (TomTom/Google Maps) to establish baseline conditions. User inputs define the "What-If" parameters (e.g., closing a lane, changing toll prices).  
* **Processing Core (The Simulation Engine):** A hybrid ML/Agentic cloud backend. A Time-Series ML engine (XGBoost) predicts baseline volume. A Generative AI Orchestration Layer (Gemini 1.5 Pro) powers the Agentic Simulation, calculating how simulated commuter personas deviate from the baseline when exposed to the user's "What-If" variables.  
* **Outputs:** *A web-based Digital Twin Dashboard (Next.js/WebGL) for urban planners detailing simulated congestion severity, environmental impact, and AI-recommended policy interventions.*

**2.2 Architecture Diagram:**  
*(Insert Image/Diagram here: You can use tools like Lucidchart, Draw.io, or Canva).*

### **SECTION 3: AI APPROACH & MODEL SELECTION**

*Identify the specific AI techniques and tools you plan to use.*

* **Primary AI Approach:** \[x\] Machine Learning \[x\] Generative AI \[x\] Other: Agentic Simulation  
* **Model Selection:**   
  * ***Predictive Layer:** XGBoost for lightweight, high-accuracy baseline time-series forecasting.*  
  * ***Simulation & Prescriptive Layer:** Gemini 1.5 Pro (or Claude 3 Opus) via API. Used to simulate complex human behavioral economics (Agentic AI) and generate contextual, human-readable intervention reports based on the numeric predictions.*  
* **Reasoning:** *Pure ML fails when historical data is absent or flawed. By injecting an Agentic LLM layer, we can synthesize realistic behavioral data based on economic and psychological principles, allowing planners to simulate the impact of unbuilt infrastructure or new policies without needing decades of prior data.*

### **SECTION 4: DATA STRATEGY & ETHICS**

*(Based on Workshop 2: Technical Architecture & Data Ethics)*

* **Data Sources:** *Open-source environmental and mapping APIs (OpenStreetMap, OpenWeather), combined with Synthetic Data Generation.*  
* **Data Quality & Cleaning:** *We address the "garbage in, garbage out" problem inherent in government data by heavily utilizing synthetic data generation. The AI engine sanitizes and augments sparse open data sets, ensuring the simulation has enough volume to find statistically significant behavioral patterns.*  
* **Licensing & Legality:** *All APIs used are standard commercial/developer tiers.*  
* **Bias Mitigation & Fairness:** *The Agentic AI prompts are carefully engineered to ensure the "Commuter Personas" represent a diverse economic baseline (e.g., ensuring lower-income demographics dependent on public transit are weighted accurately against private vehicle owners), preventing policies that disproportionately favor high-income commuters.*

### **SECTION 5: DEVELOPMENT MILESTONES (AGILE ROADMAP)**

*(Based on Workshop 3: Agile Prototyping)*

*Outline your development sprints leading up to the Semi-Finals in late June.*

| Phase | Activity / Task | Tools Used | Expected Outcome |
| :---- | :---- | :---- | :---- |
| **Sprint 1  (May 1-15)** | API Aggregation, Data Collection, Data Cleaning, Data Pipeline, & Environment Setup | Python, Postman, Supabase, GitHub, Antigravity, Gemini CLI, Claude Code | Automated ingestion of Map, Weather, and Traffic baselines with clean dataset. |
| **Sprint 2  (May 16-31)** | MVP / Agentic Simulation Engine & ML Training | Python, XGBoost, Gemini API, Antigravity, Gemini CLI, Claude Code, Google Colab | Functional AI core capable of running "What-If" scenarios. |
| **Sprint 3  (June 1-15)** | Interactive Dashboard UI/UX & WebGL rendering | React/Next.js, Tailwind, Deck.gl | Working interactive prototype allowing parameter adjustments. |
| **Sprint 4  (June 16-25)** | System stress testing, prompt refinement, and Pitch recording | Vercel, OBS, GitKraken | Final Demo Video & Codebase ready for submission. |

### **SECTION 6: SCALABILITY & REGIONAL RESILIENCE**

*How can your solution expand beyond your local university or city?*

* **Scaling Potential:**  
  * *Because ATLAN is a purely cloud-native simulation engine, scaling across the ASEAN region requires zero physical infrastructure. Traditional Smart City solutions require millions of dollars in sensor hardware, which prices out developing nations. ATLAN scales via API.*  
  * *To deploy our solution in a new country, we simply shift the geographic bounding box for our Open Data ingestion (OpenStreetMap, TomTom). The true regional scalability lies in our Agentic LLM Architecture. By adjusting the demographic and economic prompts for our commuter personas, the simulation instantly adapts to local contexts—seamlessly shifting the Digital Twin's behavior from Manila’s Jeepney-heavy transit to Ho Chi Minh City’s motorcycle-dominated arteries, or Jakarta's BRT systems. It is a unified urban planning engine that democratizes predictive infrastructure for the entire developing ASEAN region.*  
* **Technical Constraints:**  
  * Compute Cost & Simulation Latency: Running high-fidelity agentic simulations (where thousands of AI commuter personas make independent routing decisions) via LLM APIs is computationally expensive and introduces latency. The current MVP runs asynchronous "What-If" batches rather than real-time, millisecond-level live simulations.  
  * Open-Data Dependency & Hallucination Risk: Because we bypass government data, our baseline accuracy relies heavily on the density of OpenStreetMap and public weather/traffic APIs. In severely underserved rural ASEAN areas where open data is sparse, the Generative AI layer risks "hallucinating" behavioral synthetic data that may drift from ground-truth reality without manual calibration.

### **INSTRUCTIONS FOR SUBMISSION:**

1. **Strictly PDF:** Convert your final document to PDF.  
2. **Visuals Matter:** Use clear diagrams for Section 2\.  
3. **Submission Link:** Team Leaders must upload this file to the **Official Submission Folder** **[SUBMISSION - TECHNICAL ROADMAP](https://drive.google.com/drive/folders/1_0fN0UrJThY9FCYv_7QFloY4kjrAAtTf?usp=drive_link)** by **May 17, 2026** (9:00 PM GMT+7).

