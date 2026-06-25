# MATRIX — Semi-Final Mock Q&A Prep

**Round:** AAIH 2026 Semi-Finals · Smart Cities track · Team ATLAN (PUP)  
**Round lens:** *Technical Integrity & Prototype Quality*  
**Judging weights:** Technical Execution **40%** · Innovation & Originality **25%** · Impact & Scalability **20%** · Presentation & Video **15%**  
**Format:** ~5-minute pitch/video + ~3-minute Q&A (see [walkthrough.md](walkthrough.md))  
**As-built through:** CR-010 (2026-06-24) — kernel, API, frontend, validation machinery, summary-first UX  
**Golden rule:** honesty *is* the pitch. Every answer cites a real file/number or labels something provisional/target.

---

## How to use this doc

Each entry follows the same shape so you can rehearse out loud:

| Field | Purpose |
|---|---|
| **Q** | Judge voice — the question as they'd ask it |
| **Short answer** | 1–3 sentences, ~145 wpm, spoken-ready |
| **Backing** | The file, equation, test count, or dataset that proves it |
| **Guardrail** | The do/don't line — what never to overclaim |

**Rehearsal tip:** answer the Short answer first, then offer Backing only if they push. Never lead with jargon.

---

## Section 1 — Technical Execution & Integrity (40%)

### Q1.1 — "Walk me through your architecture in one minute."

**Short answer:** A planner types a simple question or drops a project on a map. Azure OpenAI GPT-5.4 translates that into a plan without guessing any numbers. A single SUMO engine then runs hundreds of simulated people through Iloilo's actual roads, creating one shared set of movements. Five different modules (Behavioral, Ecological, Social, Economic, and Societal) look at those same movements at the same time to calculate scores. Finally, an AI writes a summary with exact sources, and the results appear live on the screen with 3D animations using Deck.gl.

**Backing:** Pipeline in [MATRIX.md §5.1](../MATRIX.md); WebSocket stream `ACCEPTED → PLAYBACK_FRAME → DIMENSION_RESULT×5 → SYNTHESIS → DONE` in `apps/api`; modules in `app/packages/kernel/matrix_kernel/modules/`.

**Guardrail:** Do not say "five separate simulators." Say "one kernel, five modules."

---

### Q1.2 — "Why one kernel instead of five independent models?"

**Short answer:** If we used separate simulators, they might give conflicting results—like saying traffic went up but emissions stayed the same, because they use different rules. Instead, we run one SUMO simulation, and all five modules look at that exact same set of movements. This ensures they all agree on what actually happened on the roads.

**Backing:** Architectural commitment in [MATRIX.md](../MATRIX.md) and [methods-matrix.md §1](../docs/methods-matrix.md); each module consumes `Trajectory` from `runner.py`.

**Guardrail:** Do not claim cross-module consistency without naming the shared trajectory dataset.

---

### Q1.3 — "What is the glass box, and can you show me it working?"

**Short answer:** We don't hide how we get our numbers. Every result on the screen comes with a specific equation, the exact data used, and a confidence level that is calculated, not guessed. You can click any number to open an "Inspect" panel and see exactly where it came from. If a number can't prove its source, the system won't display it.

**Backing:** `DimensionResult` contract in [`results.py`](../app/packages/kernel/matrix_kernel/results.py) (`equation_id`, `input_dataset_ids`, `confidence` are required fields); Inspect drawer in `apps/web`; PRD-F14 in [methods-matrix.md §1](../docs/methods-matrix.md).

**Guardrail:** Demo the Inspect click live. Never describe glass box without showing it.

---

### Q1.4 — "How is AI used in your system — does it generate the numbers?"

**Short answer:** The AI does four specific things, but it never calculates the final numbers. We use Azure OpenAI GPT-5.4 to: (1) turn simple questions into a plan, (2) write clear summaries with sources, (3) create simulated people (though we usually use a pre-made set), and (4) read real Iloilo planning documents using GraphRAG so it doesn't guess. The actual numbers are always calculated by strict math formulas using real data. We have built-in checks to make sure the AI only reports and explains the numbers, but never invents them.

**Backing:** Azure OpenAI `gpt-5.4` via the `openai` SDK ([CLAUDE.md](../CLAUDE.md) locked decision); orchestrator + `citation_guard` in `synthesis.py`; `bias_auditor.py`; `graphrag.py` ingested at API startup; "LLM never originates a number" in [methods-matrix.md §1 + §4](../docs/methods-matrix.md); `DimensionResult.__post_init__` fails fast if provenance is missing. Deeper follow-ups: **Q1.13** (why Azure), **Q1.14** (GraphRAG), **Q1.12** (bias auditor).

**Guardrail:** Never say "AI-powered predictions." Say "AI plans, grounds, and narrates; deterministic equations compute every number." If pushed "so what's the AI actually for?" — orchestration + synthesis, with equations as the source of truth.

---

### Q1.5 — "What equations power each dimension?"

**Short answer:** Each area has its own set of specific formulas. For example, Behavioral uses formulas (like BEH-1 to BEH-4) to measure traffic changes and how people travel. Ecological uses formulas (ECO-1 to ECO-4) to check emissions and flood risks. Social, Economic, and Societal also have their own exact formulas to measure things like job impacts, walkability, and how different communities are affected.

**Backing:** Full registry in [methods-matrix.md §3](../docs/methods-matrix.md); implementations in `app/packages/kernel/matrix_kernel/modules/*.py`.

**Guardrail:** If asked for one example, pick BEH-1 or ECO-1 — both are High-confidence, physics-based, easy to explain.

---

### Q1.6 — "How is confidence computed — High, Medium, or Low?"

**Short answer:** We figure out our confidence level based on four things: how recent the data is, how much area it covers, how proven the math is, and whether it's been tested. The weakest of these four determines the final confidence score. If our confidence is "Low," we don't show an exact number because that would be misleading. Instead, we just show the general direction of the impact.

**Backing:** Rubric in [methods-matrix.md §2](../docs/methods-matrix.md); `confidence_rubric()` and `DATASET_TIERS` in `confidence.py`; `method_capped_confidence` rule (CR-007 PR 6).

**Guardrail:** Never say "we're confident" generically. Always name the tier and why (e.g., "Medium because Calderon 2014 is literature-calibrated, not a live survey").

---

### Q1.7 — "What are your datasets — how many, and where from?"

**Short answer:** We use about 40 different public data sources for Iloilo, with 16 already connected directly to the system. This includes things like the SUMO road network (built from OpenStreetMap), flood hazard maps from NOAH, and property values from the BIR. We only use open, public data—no locked or private databases. Every piece of data is tagged with where it came from, its age, and its reliability.

**Backing:** Full manifest in [data/INVENTORY.md](../data/INVENTORY.md) (Tier A/B/C, ~39 catalogued, 16 ✅ fetched); per-dimension map in [data/READINESS.md](../data/READINESS.md); licenses ODbL (OSM/Overture) · PSA open-gov · ESA & World Bank CC BY 4.0; network stats (36,367 edges / 14,465 nodes) in READINESS.

**Guardrail:** Do not claim "complete coverage." Name the soft spot out loud: mode-share comes from literature (Calderon 2014 + LPTRP), not a live LTFRB origin-destination survey. Say "~40 catalogued, ~16 wired" — don't inflate to "40 integrated datasets."

---

### Q1.8 — "Why SUMO and not a social-dynamics simulator like OASIS or MiroFish?"

**Short answer:** We simulate real-world movement—like vehicles, pedestrians, and road capacity—not social media trends or online interactions. We use SUMO because it accurately models the physical movement of people and cars on real roads, which is exactly what our five impact modules need to make calculations.

**Backing:** Locked decision in [MATRIX.md §6](../MATRIX.md) and [CLAUDE.md](../CLAUDE.md); TraCI runner in `runner.py` + `sumo_env.py`.

**Guardrail:** Do not dismiss OASIS/MiroFish as "bad" — say they solve a different problem (information diffusion, not road physics).

---

### Q1.9 — "What's your test coverage — does this actually run?"

**Short answer:** Yes. The core engine passes 190 automated tests, and the API passes another 64. Every module is tested individually, and we have built-in checks to ensure our transparency rules are followed. We also have tests that simulate a user clicking through the web interface to make sure everything works smoothly.

**Backing:** [docs/qad-matrix.md](../docs/qad-matrix.md) (reconciled 2026-06-24); run `python -m pytest -q` in `app/packages/kernel` and `app/apps/api`.

**Guardrail:** Say "190 passed" not "all tests pass" — be precise about skips.

---

### Q1.10 — "Explain your WebSocket streaming architecture."

**Short answer:** When you start a simulation, the system sends data back continuously. First, it sends the animation frames so you can watch the simulation on the Deck.gl map right away. As the five modules finish their calculations, their scores pop up on the screen one by one. Finally, the AI summary arrives. This step-by-step delivery is how we make a complex process feel instant.

**Backing:** RFC-001 in [docs/rfc-matrix-realtime-pipeline.md](../docs/rfc-matrix-realtime-pipeline.md); WebSocket handler in `apps/api/matrix_api/`.

**Guardrail:** Do not claim sub-second full runs on cold start — distinguish warm/cached from cold.

---

### Q1.11 — "What happens when data is poor or missing?"

**Short answer:** Our system shifts to "Low Confidence" mode. If we're using sparse data or unverified assumptions, we cap the confidence at "Low," and the system will only show the general direction of the impact instead of a precise number. You can open the Inspect panel to see exactly what missing or weak data caused this cap.

**Backing:** Low-Confidence Protocol table in [methods-matrix.md §2](../docs/methods-matrix.md); PROVISIONAL constants in §3.6 (e.g., `_VENDORS_PER_CLOSED_LANE = 12`, `_PHP_PER_TRIP_PROXY = ₱50`).

**Guardrail:** Treat "directional only" as a feature, not an apology.

---

### Q1.12 — "How does your bias auditor work?"

**Short answer:** After creating the simulated people, we check if their travel choices match Iloilo's real-world habits (like 50% taking a jeepney). If the simulation drifts more than 3% off these real-world numbers, the system automatically corrects it. This adjustment is recorded in a public log so anyone can see exactly how the balance was restored.

**Backing:** `MODE_SHARE_TOLERANCE = 0.03` in `bias_auditor.py`; anchor in `config.py` `ILOILO_MODE_SHARE`; `GET /audit/{scenario_id}`; worked example in [methods-matrix.md §4.1](../docs/methods-matrix.md).

**Guardrail:** Say "audits and reweights the LLM-generated pool." The deployed default static pool is on-anchor by construction — reweight rarely fires in production today.

---

### Q1.13 — "You use Azure OpenAI — why not Gemini or another model?"

**Short answer:** We use Azure OpenAI GPT-5.4 because it allows us to control the AI from a single, secure endpoint. This single setup handles turning questions into plans, writing the final reports, and generating simulated people if needed. We moved away from Gemini to keep all these tasks under one strict system that ensures sources are properly cited.

**Backing:** [docs/cr-008-azure-openai-migration.md](../docs/cr-008-azure-openai-migration.md); [docs/cr-009-azure-foundry-client.md](../docs/cr-009-azure-foundry-client.md) — use `openai.OpenAI(base_url=…)`, not `openai.AzureOpenAI`.

**Guardrail:** Do not mention Gemini as a current option.

---

### Q1.14 — "What is GraphRAG doing in your pipeline?"

**Short answer:** When our system starts, it loads a library of actual Iloilo planning documents and local research using GraphRAG and ChromaDB. When you ask a question, the AI searches this library and uses those local facts to understand your request. This ensures the AI relies on real local documents instead of generic information from the internet.

**Backing:** `graphrag.py`; CR-008 wired ingestion at API startup (see [CLAUDE.md](../CLAUDE.md)); retrieval example in [methods-matrix.md §4.2](../docs/methods-matrix.md).

**Guardrail:** GraphRAG grounds *orchestration* — it does not originate dimension scores. Do not demo a retrieval step that isn't wired.

---

### Q1.15 — "Can you reproduce a run — same inputs, same outputs?"

**Short answer:** Yes. Every time a simulation runs, it records the exact settings, random numbers used, data versions, and model versions. This guarantees that if you put the exact same inputs in again, you will get the exact same results every time.

**Backing:** [methods-matrix.md §7](../docs/methods-matrix.md); `simulation_runs` schema in SDD; seed control in `runner.py`.

**Guardrail:** Do not claim bit-identical reproduction across different SUMO versions without noting the version stamp.

---

## Section 2 — Model Accuracy, Validation & Efficiency

### Q2.1 — "Who validated this system — is there an outside expert who checked it?"

**Short answer:** We test our system on three levels. First, we test it against real-world research (like the Calderon 2014 study), specifically aiming for an FHWA-standard error rate (RMSE) below 0.30. However, we're holding back from publishing that final accuracy score until we fully adjust our passenger demand numbers, to ensure we stay completely honest. Second, our built-in automated checks block any code updates that fail a test or hide where a number came from. Third, the one thing we're still waiting on is a formal sign-off from an actual city planner, which is our very next priority.

**Backing:** `validate_calderon()` in [`validation.py`](../app/packages/kernel/matrix_kernel/validation.py) vs `LIT-CALDERON`; two merge gates in [AGENTS.md](../AGENTS.md) (`glass-box-auditor` + `eval-test-runner`); 254 tests (190 kernel + 64 API) in [docs/qad-matrix.md](../docs/qad-matrix.md); PRD-F20 CPDO feedback loop; status in [methods-matrix.md §6](../docs/methods-matrix.md) + [docs/cr-012-validation-calibration.md](../docs/cr-012-validation-calibration.md).

**Guardrail:** Never imply a domain expert has validated it. Say "validated against peer-reviewed literature and our own glass-box gates today; independent planner validation is the next milestone." Don't conflate automated/empirical validation with human sign-off — name all three levels and which one is still open.

---

### Q2.2 — "How do you validate your behavioral model?"

**Short answer:** Our VAL-01 test checks our passenger flow estimates against the Calderon 2014 Iloilo BRT study to ensure our error rate (RMSE) is strictly below the 0.30 threshold set by the FHWA. The testing system is fully built and working. However, we're intentionally not sharing the final score just yet because we are still adjusting our baseline passenger numbers, and sharing a score before then would be misleading.

**Backing:** `validate_calderon()` in [`validation.py`](../app/packages/kernel/matrix_kernel/validation.py); `VAL01_THRESHOLD_NRMSE = 0.30` with FHWA provenance; fixture from `LIT-CALDERON`; status in [methods-matrix.md §6](../docs/methods-matrix.md) and [docs/cr-012-validation-calibration.md](../docs/cr-012-validation-calibration.md).

**Guardrail:** Say "withheld pending calibration," not "not validated." The harness validates; the demand isn't calibrated enough to publish.

---

### Q2.3 — "If you can't show RMSE, why should we trust your behavioral numbers?"

**Short answer:** You can trust them because we don't hide when we are uncertain. We openly rate our Behavioral data as "Medium" confidence, and we give you a range of possibilities rather than a fake, overly-exact number. We prefer to show an honest "Medium" rating with fully transparent sources, rather than making up a fake "94% accuracy" claim.

**Backing:** BEH-2 confidence basis "M (literature calibration)" in [methods-matrix.md §3.1](../docs/methods-matrix.md); BEH-4 capped at L; `directional` property on `DimensionResult`.

**Guardrail:** Never invent an accuracy percentage. Point to the confidence tier and the validation roadmap.

---

### Q2.4 — "What about flood validation?"

**Short answer:** Our VAL-02 test compares our simulated flood closures against actual data from the 2024 Iloilo flood, requiring an accuracy overlap (IoU) of at least 0.50 based on Horritt & Bates 2002. While the system to run this test is fully built, we are still waiting to get the official satellite data from Copernicus Sentinel-1 to run it against. Because of this, the system honestly reports that the test has "Not Run" yet, rather than faking a pass.

**Backing:** `validate_flood()` in `validation.py`; `VAL02_THRESHOLD_IOU = 0.50`; `flood2024_closures.json` marked PROVISIONAL; [methods-matrix.md §3.7](../docs/methods-matrix.md).

**Guardrail:** Do not claim flood validation passed. Say "staged, awaiting sourced extent."

---

### Q2.5 — "What's your 90-second latency claim — can you actually hit it?"

**Short answer:** Ninety seconds is our target time for a standard run. We achieve this by prepping the simulated people in advance, calculating only the changes instead of running everything from scratch, running all five modules at once, and streaming the results live. A completely fresh run currently takes about 123 seconds, but if you re-run the same scenario, our cache memory returns it in under one second.

**Backing:** RFC-001 strategy; PERF-01 in [docs/qad-matrix.md](../docs/qad-matrix.md) (~48 s warm, <1 s cached repeat); honest cold-run admission in [semifinal-video-script.md](../reference/AAIH-2026-semifinal-video-script.md).

**Guardrail:** Always give the triplet: **90 s target · ~123 s cold · <1 s warm cache.** Never quote only the target.

---

### Q2.6 — "Why is your demand not calibrated — what's the blocker?"

**Short answer:** Right now, we rely on historical studies (like Calderon 2014) to estimate how people travel, rather than a fresh real-world survey. Because of this, our overall passenger counts are still slightly higher than they should be. We've already fixed a large part of this over-count, but to get it perfectly tuned, we still need the latest official travel data or a local household survey.

**Backing:** [docs/cr-012-validation-calibration.md §1](../docs/cr-012-validation-calibration.md); FOI path in `config.py`; READINESS Behavioral gap ("mode-share ground truth is the soft spot").

**Guardrail:** Do not blame "bad code" — frame it as honest data acquisition in progress.

---

### Q2.7 — "What PROVISIONAL constants are still in your equations?"

**Short answer:** We have a few temporary placeholders while we wait for exact data, such as assuming ₱50 for trip costs, 12 street vendors per closed lane, or a 0.05 ratio for air-quality PM2.5 estimation. We openly label all of these as "PROVISIONAL" in our Inspect panel so users know they are placeholders. We already have a specific plan to replace them with official data soon.

**Backing:** [methods-matrix.md §3.6](../docs/methods-matrix.md) constant table; each caps confidence per the Low-Confidence Protocol.

**Guardrail:** Listing PROVISIONAL constants demonstrates integrity — don't omit them when asked.

---

### Q2.8 — "Do your validation gates ever pass by construction?"

**Short answer:** No. We removed any fake or guaranteed-to-pass tests and replaced them with real math. If a test doesn't have the data it needs, it clearly says "Not Run" and gives a reason. If a test fails, it says "Fail." The code is strictly written to make it impossible to fake a passing score.

**Backing:** Module docstring in `validation.py` lines 1–23; `PROVISIONAL_MARK` enforcement in `load_fixture()`.

**Guardrail:** If asked about old stubs, acknowledge they existed and were replaced — don't pretend they never happened.

---

## Section 3 — Innovation & Originality (25%)

### Q3.1 — "What's actually novel here — isn't this just SUMO plus ChatGPT?"

**Short answer:** SUMO handles the physical traffic rules, and the AI handles understanding the user's questions. What makes this new is combining everything into one package: you can type plain English questions, get results across five different areas from a single simulation, see the confidence level and exact source for every number, and know it has been checked for bias—all without needing to install any expensive hardware.

**Backing:** Feature survey gap in [docs/gtm-matrix.md §2.1](../docs/gtm-matrix.md) and [CONTENT-OUTLINE.md §3](CONTENT-OUTLINE.md); locked architecture in [MATRIX.md](../MATRIX.md).

**Guardrail:** Acknowledge SUMO and GPT are components. Own the *integration and honesty layer* as the innovation.

---

### Q3.2 — "How are you different from PTV Vissim or Aimsun?"

**Short answer:** Vissim and Aimsun are excellent tools for traffic experts, but they are hard to use, usually only measure traffic, and don't clearly show how confident they are in their numbers. MATRIX is built for regular city planners who need quick, easy-to-understand answers across multiple areas (like traffic, economy, and environment) in just ninety seconds.

**Backing:** Competitor survey in [CONTENT-OUTLINE.md §3](CONTENT-OUTLINE.md) and GTM §2.1; honest caveat "based on our feature survey."

**Guardrail:** Never say Vissim is "bad." Say it solves a different user and scope.

---

### Q3.3 — "What about Replica, UrbanFootprint, or ESRI CityEngine?"

**Short answer:** Tools like Replica tell you what is currently happening using collected data, but they don't predict what *would* happen if you built something new. Others like UrbanFootprint or CityEngine are great for 3D maps and land planning, but they don't run a full five-area impact test. We fill the gap by combining all of this: we simulate "what-if" scenarios, score them across five areas, and show exactly where our numbers come from.

**Backing:** GTM §2.1 feature matrix; MATRIX counterfactual framing in [MATRIX.md](../MATRIX.md).

**Guardrail:** Do not claim competitors lack AI — claim they lack this specific *combination*.

---

### Q3.4 — "How do you handle the informal economy — jeepneys, tricycles, street vendors?"

**Short answer:** We built informal transport—like jeepneys and tricycles—directly into our simulated people, based on real local data (where jeepneys make up 50% of travel), rather than assuming everyone drives a car like Western tools often do. Our system also specifically calculates how street vendors might lose their livelihood if a road is closed or changed.

**Backing:** `ILOILO_MODE_SHARE` in `config.py`; SOC-2 in [methods-matrix.md §3.3](../docs/methods-matrix.md); ASEAN tailoring in [CONTENT-OUTLINE.md §69–75](CONTENT-OUTLINE.md).

**Guardrail:** Do not claim perfect informal-sector modeling — say it's modeled with Medium confidence and PROVISIONAL vendor constants.

---

### Q3.5 — "You mention Hiligaynon support — how does that work?"

**Short answer:** Users can ask questions in either Hiligaynon or English. We built a local dictionary that translates common local terms (like "merkado" for market) into exact map locations before the AI even reads the question, preventing misunderstandings. The final report is also available fully translated into Hiligaynon, which you can easily switch to on the screen.

**Backing:** [methods-matrix.md §4.2–§4.3](../docs/methods-matrix.md); `gazetteer_iloilo.json`; CR-010 bilingual BLUF brief; `LanguageProvider` in frontend.

**Guardrail:** Gazetteer OSM/SUMO node IDs are PROVISIONAL placeholders — the mapping logic works; the IDs need GIS verification.

---

### Q3.6 — "What's innovative about your confidence system?"

**Short answer:** Many tools hide when they aren't sure, making their numbers look perfectly precise. We openly calculate our confidence based on how old or reliable the data is. If our confidence is Low, we completely remove the exact number and just say "we know this increases flood risk, but we don't have enough data to say by exactly how much." This honesty is much more useful than a fake number.

**Backing:** [methods-matrix.md §2](../docs/methods-matrix.md); PRD-F5 directional-only rendering; CR-010 number humanization in `lib/format.ts`.

**Guardrail:** Do not say "AI confidence score." Say "computed confidence tier from a documented rubric."

---

### Q3.7 — "Did you build the bias auditor because LLMs are biased?"

**Short answer:** Yes—AI naturally tends to assume everyone is middle-class and drives a car, which doesn't fit our local reality. Because of this, our AI-generated people can sometimes have skewed travel habits. Our bias auditor catches this by comparing the AI's results to real Iloilo data, and if it's off by more than 3%, it automatically corrects it. This correction isn't hidden; it's a core feature that we record for anyone to see.

**Backing:** [methods-matrix.md §4.1](../docs/methods-matrix.md) worked example (observed private_car 0.30 vs target 0.15); CR-008 Item 3; `reweight_pool()` in `bias_auditor.py`.

**Guardrail:** The static default pool is literature-anchored and on-target — reweight demonstrates on LLM-generated pools or test scenarios.

---

### Q3.8 — "What extreme events can you simulate?"

**Short answer:** Users can upload a map showing a flood area. The system automatically closes the flooded roads, forces the simulated traffic to find new routes using SUMO, and calculates how many people are exposed to the flood. This lets planners ask questions like, "What happens if we build this project AND a major flood hits at the same time?"—something standard studies rarely explore.

**Backing:** [methods-matrix.md §3.7](../docs/methods-matrix.md); `flood_scenario` helper; ECO-4 equation.

**Guardrail:** Flood validation (VAL-02) is NOT_RUN — the simulation works; the back-test against real 2024 extent doesn't yet.

---

## Section 4 — Impact & Scalability (20%)

### Q4.1 — "Who is your actual user?"

**Short answer:** A city planner (like someone at Iloilo CPDO or NEDA Region VI) who approves major building projects but doesn't have training in complex mapping or transport modeling. They can simply type a question or drop a project on the map, and get results across five different areas with clear confidence ratings in about ninety seconds.

**Backing:** PRD user stories; beachhead in [CONTENT-OUTLINE.md §2](CONTENT-OUTLINE.md) and [docs/gtm-matrix.md](../docs/gtm-matrix.md).

**Guardrail:** Do not say "everyone." Name the planner persona specifically.

---

### Q4.2 — "Why Iloilo — why not Manila or a bigger city?"

**Short answer:** Iloilo is just our starting point, not our limit. It recently won the ASEAN Clean Tourist City 2026 award and has great public data available through Project CCHAIN. Most importantly, it shares common challenges with many ASEAN cities—rapid growth, informal transport, flood risks, and data that is good but not perfect. By making the system work honestly for Iloilo, we prove it can work for Jakarta, Bangkok, and Ho Chi Minh City too.

**Backing:** ASEAN Clean Tourist City 2026 anchor in [MATRIX.md](../MATRIX.md); CCHAIN coverage in [data/READINESS.md](../data/READINESS.md).

**Guardrail:** Iloilo proves the engine — not that we're an Iloilo-only tool.

---

### Q4.3 — "How does it scale to other ASEAN cities?"

**Short answer:** It takes two main setup steps: swapping out the OpenStreetMap area for the new city, and adjusting the AI's travel habits to match local transport (like ojek in Jakarta or songthaew in Chiang Mai). Because everything runs in the cloud using public data, there is no need to install any expensive physical hardware.

**Backing:** `CityConfig` in [`config.py`](../app/packages/kernel/matrix_kernel/config.py) — `MATRIX_CITY_BBOX`, `MATRIX_MODE_SHARE` env overrides; GTM ASEAN scaling in [docs/gtm-matrix.md](../docs/gtm-matrix.md).

**Guardrail:** Say "configuration change," not "plug and play tomorrow." Each new city needs data ingestion and persona reweighting work.

---

### Q4.4 — "What's your go-to-market after the hackathon?"

**Short answer:** Our first target is getting Iloilo's local government and academics to use and validate it—getting one real city planner to sign off is our biggest priority. From there, we'll expand to other Philippine cities, then across ASEAN. Right now, we are offering it for free to governments and schools to build trust and adoption. Later, we plan to introduce a paid version for private developers.

**Backing:** [docs/gtm-matrix.md](../docs/gtm-matrix.md); [CONTENT-OUTLINE.md §9–10](CONTENT-OUTLINE.md).

**Guardrail:** Do not invent TAM/SAM/SOM numbers. Say "directional market frame, assumptions stated."

---

### Q4.5 — "What's the business model — how do you make money?"

**Short answer:** We haven't set fixed prices yet on purpose. We want to keep the tool free for local governments and academics to encourage them to use it. After the competition, our plan to make money is by charging private developers who want to use the tool to test their own building projects. Right now, our focus is entirely on proving that the system works.

**Backing:** BMC in [CONTENT-OUTLINE.md §8](CONTENT-OUTLINE.md) — revenue labeled TBD/post-hackathon.

**Guardrail:** Never quote a specific price or revenue projection without a sourced model.

---

### Q4.6 — "What's the impact if a city uses MATRIX before approving a project?"

**Short answer:** A planner can see how a project will affect many different areas—like traffic, floods, displaced vendors, land values, and nearby historical sites—before any money is spent. They can compare different options, clearly see what the system is confident about versus what it isn't, and print a one-page summary to share with decision-makers. The goal is to help them avoid billion-peso mistakes, not to completely replace traditional studies.

**Backing:** PRD-F20 CPDO feedback loop; CR-010 `ScenarioBrief` export; value framing in [CONTENT-OUTLINE.md §7](CONTENT-OUTLINE.md).

**Guardrail:** Do not invent ROI percentages. Say "de-risks capital allocation" with honest confidence bounds.

---

### Q4.7 — "Can this work in data-sparse cities?"

**Short answer:** That's exactly why we built the confidence tracking system. In cities with less data, our system doesn't pretend to be perfectly precise. Instead, it openly says "we don't have enough data" and only shows general trends. In many cities where good data is hard or expensive to get, knowing the honest limits of the system is much more useful than getting a fake, hyper-precise number.

**Backing:** Confidence rubric §2; READINESS per-dimension gaps; [MATRIX.md](../MATRIX.md) honesty principle.

**Guardrail:** Do not claim High confidence where READINESS says Medium or Low.

---

### Q4.8 — "How does MATRIX relate to Iloilo's ASEAN Clean Tourist City 2026 award?"

**Short answer:** Iloilo's recent win for the ASEAN Clean Tourist City 2026 award shows they really care about sustainable planning. Our system gives that forward-thinking culture the perfect tool: before they build their next park, terminal, or mall, they can simulate how it will affect traffic, the environment, and the community, all with complete transparency.

**Backing:** ASEAN Clean Tourist City 2026 references in [MATRIX.md](../MATRIX.md) and [CONTENT-OUTLINE.md §79](CONTENT-OUTLINE.md).

**Guardrail:** Do not imply MATRIX caused or enabled the award — say it supports the planning culture the award recognizes.

---

## Section 5 — Presentation, Process & Team (15%)

### Q5.1 — "Who built this — what's your team structure?"

**Short answer:** We are Team ATLAN from the Polytechnic University of the Philippines, a team of five. Carlos Jerico Dela Torre leads the product and AI. Yushin Bjorn Matsuda handles the web design and user interface. Maria Espina manages quality testing and user experience. Rica Mae Mago and Russell Jay Fajardo handle testing, research, and marketing. We built the entire system ourselves, carefully tracking every change and using automated tests to ensure quality.

**Backing:** Team roster in [MATRIX.md](../MATRIX.md); build agents in [AGENTS.md](../AGENTS.md).

**Guardrail:** Credit the team, not just the lead. Name specific contributions if asked.

---

### Q5.2 — "How did you manage quality under hackathon time pressure?"

**Short answer:** We have two strict automated rules before any code is approved: one checks that every number has a valid source, and the other ensures all tests pass. Every single change is documented in a formal record. We refuse to skip these quality checks just to work faster—we either ship an honest product, or we don't ship at all.

**Backing:** [AGENTS.md](../AGENTS.md) merge gate; CR-001 through CR-010 change records in `docs/cr-*.md`; `glass-box-auditor` and `eval-test-runner` agents.

**Guardrail:** Do not claim "no bugs." Claim "no unprovenanced numbers ship."

---

### Q5.3 — "Why a screen-first video instead of a campus shoot?"

**Short answer:** Because this round places a huge 40% focus on technical execution and only 15% on presentation, we decided not to waste time on scenic video shots. Instead, after a quick opening to show our focus on Iloilo, we dedicate 85% of our video to showing the actual working software, the code, and how we test it.

**Backing:** Production plan in [reference/AAIH-2026-semifinal-video-script.md §5](../reference/AAIH-2026-semifinal-video-script.md).

**Guardrail:** If you accelerated the demo in video, label it on screen — never fake real-time.

---

### Q5.4 — "What would you do with more time or funding?"

**Short answer:** Our top three priorities would be: getting official travel data to finalize our passenger estimates, getting the official satellite flood map to complete our flood testing, and speeding up the completely fresh runs from 123 seconds down to our 90-second target. We already have detailed plans written out for how to achieve all three.

**Backing:** [docs/cr-012-validation-calibration.md](../docs/cr-012-validation-calibration.md) workstreams WS-1 through WS-4.

**Guardrail:** Frame as a roadmap, not a promise of completion by finals.

---

### Q5.5 — "Is this deployed — can we try it?"

**Short answer:** Yes. The website is live on Vercel, and the background engine runs on Hugging Face Spaces. It's fully functional today, and we can also easily run the entire system locally on our own computers with just a few standard commands.

**Backing:** CR-011 Hugging Face migration in [docs/cr-011-huggingface-migration.md](../docs/cr-011-huggingface-migration.md); commands in [CLAUDE.md](../CLAUDE.md).

**Guardrail:** Have the live URL ready. If the demo environment is down, cut to recorded fallback without apology.

---

## Section 6 — Hardball & Integrity Traps

### Q6.1 — "Show me a number you can't back up."

**Short answer:** Our estimates for how people change their destinations based on new buildings (our BEH-4 formula) are rated "Low Confidence" because we are using temporary placeholder numbers instead of exact local survey data. We show the general trend, but our system clearly flags these numbers as uncalibrated. We'd rather be honest about this than pretend we have exact data.

**Backing:** BEH-4 in [methods-matrix.md §3.1](../docs/methods-matrix.md); `FACILITY_PROFILES` in §3.6; `directional` property suppresses false precision.

**Guardrail:** This question is a gift — use it to demonstrate integrity, not defensiveness.

---

### Q6.2 — "Your RMSE is hidden — so your model isn't validated at all?"

**Short answer:** The testing system itself is completely built and working. We are only withholding the final score because our passenger numbers are still being adjusted, and publishing a score based on unfinished data would be dishonest. The fact that we are holding the score back actually proves our commitment to transparency—we hold ourselves to the exact same strict standards that our software promotes.

**Backing:** CR-012 §1; `validation.py`; [methods-matrix.md §6](../docs/methods-matrix.md) status table.

**Guardrail:** Never say "we'll validate later." Say "the harness runs today; the demand calibration is the blocker."

---

### Q6.3 — "You missed your own 90-second budget — why should we believe your engineering?"

**Short answer:** We are completely open about our times: our target is 90 seconds, a fresh run currently takes 123 seconds, and a repeat run takes under one second. We built the system specifically to hit that 90-second goal by taking several shortcuts. Being 30 seconds over on a fresh start isn't a failure, and being honest about that gap shows mature engineering rather than weakness.

**Backing:** RFC-001; PERF-01 in qad-matrix.md; semi-final script §D honest admission.

**Guardrail:** Always pair target with actual. Never quote only "90 seconds."

---

### Q6.4 — "The bias auditor — does it actually reweight or just flag?"

**Short answer:** It does both. It flags when travel habits drift more than 3% off target, and then it automatically corrects the numbers to bring them back in line, which is recorded in a public log. Right now, because our default setup is already highly accurate, it rarely needs to fire, but we've proven it works perfectly when the AI accidentally creates too many car-driving, middle-class people.

**Backing:** `reweight_pool()` in `bias_auditor.py`; worked example in [methods-matrix.md §4.1](../docs/methods-matrix.md); CR-008 Item 3.

**Guardrail:** Do not say "always reweights." Say "audits every batch; reweights when triggered."

---

### Q6.5 — "Your gazetteer IDs are placeholders — doesn't that break the product?"

**Short answer:** The guarantee is that our system never lets the AI invent map locations out of thin air. While we currently use some placeholder IDs for exact road segments (which we clearly label as provisional until we verify them fully), the system correctly understands the names of places. The exact routing will get even more precise once those map IDs are fully verified.

**Backing:** [methods-matrix.md §4.2](../docs/methods-matrix.md) PROVISIONAL note; `gazetteer_iloilo.json` `"provisional": true` flags.

**Guardrail:** Do not claim gazetteer IDs are verified ground truth.

---

### Q6.6 — "Isn't fixed open data a weakness versus live IoT simulators?"

**Short answer:** Live sensors only tell you what is happening *right now*. MATRIX answers what *would* happen if you built something new—a future scenario that no sensor can measure yet. Also, relying on public data means we can set this up in any ASEAN city without having to install physical hardware. Our confidence ratings make sure you always know exactly how reliable our predictions are.

**Backing:** Counterfactual framing in [MATRIX.md](../MATRIX.md); vs IoT comparison in [methods-matrix.md §8](../docs/methods-matrix.md) and [walkthrough.md §Q&A](walkthrough.md).

**Guardrail:** Respect IoT tools — claim complementary scope, not superiority.

---

### Q6.7 — "What about data privacy — RA 10173?"

**Short answer:** Our system doesn't use any personal data at all—only public, open data. The simulated people are just generic examples, not real individuals. If we ever add features that collect real location data in the future, we will undergo strict legal and privacy reviews to ensure we fully comply with the Philippine Data Privacy Act.

**Backing:** RA 10173 note in [walkthrough.md §Q&A](walkthrough.md); open-data licenses in [MATRIX_Iloilo_Data_Sources.md](../MATRIX_Iloilo_Data_Sources.md).

**Guardrail:** Do not claim "fully compliant" without counsel review — say "no PII in the current pipeline."

---

### Q6.8 — "You're students — can you maintain this after the hackathon?"

**Short answer:** Our system is built to professional standards, not just as a quick hackathon project. We use strict documentation, 254 automated tests, formal change tracking, and professional cloud hosting. We've spent significant time making the code tough and reliable, and we already have a clear roadmap for how to maintain and improve it after the competition.

**Backing:** CR history in [CLAUDE.md](../CLAUDE.md); test counts; deployment stack.

**Guardrail:** Be honest about team capacity — don't promise 24/7 enterprise SLA.

---

### Q6.9 — "What if the LLM hallucinates in the synthesis narrative?"

**Short answer:** We built a "citation guard" that checks the AI's summary line by line. If the AI tries to state a number without linking it to a verified equation and real data, the system blocks it from showing on the screen. While the AI might still use slightly weird phrasing in its writing, we guarantee that every single number you see is real and verified.

**Backing:** Citation guard in [methods-matrix.md §4](../docs/methods-matrix.md); `synthesis.py` guard logic; CR-010 BLUF structure.

**Guardrail:** Do not claim "zero hallucination." Claim "zero unprovenanced numbers on screen."

---

### Q6.10 — "Why should we advance you over teams with higher accuracy numbers?"

**Short answer:** Because we believe it's better to show an honest "Medium" confidence rating with fully transparent sources than to invent a fake "94% accuracy" score. Also, no other tool combines all of these features—plain English questions, five different impact areas from one simulation, complete transparency, and local informal transport modeling. We believe this level of honesty and completeness is exactly what sets us apart.

**Backing:** Semi-final rubric lens "Technical Integrity & Prototype Quality"; feature gap in GTM §2.1.

**Guardrail:** Never disparage other teams. Lead with what you built and how honestly you report it.

---

## Section 7 — One-Page Cheat Sheet

### Must-not-miss facts (say these even if not asked)

1. **One kernel → five modules** — one SUMO trajectory dataset; modules cannot contradict.
2. **Glass box** — every number → `equation_id` + `input_dataset_ids` + computed confidence; Inspect drawer resolves it live.
3. **AI does four jobs — never computes a number** — orchestrate (NL→plan), ground (GraphRAG), narrate (synthesis), optional persona gen; citation guard + bias auditor enforce the line.
4. **190 kernel tests + 64 API tests pass** — 11 + 4 skip cleanly without SUMO (254 total).
5. **Iloilo data is real & all open** — ~40 sources catalogued (Tier A), ~16 wired today: 180 barangays (CCHAIN, 25 tables), 36,367 edges + 148,630 buildings, 5,680 BIR parcels.
6. **Mode-share anchor** — jeepney 50%, private car 15%, motorcycle 15%, walk 10%, bicycle 5%, tricycle 5%.
7. **Validation harness is built** — VAL-01 (Calderon NRMSE ≤ 0.30), VAL-02 (flood IoU ≥ 0.50), VAL-03 (mode share ±3%).
8. **ASEAN scaling** — OSM bbox swap + persona reweight; no hardware.
9. **Deployed today** — Vercel (web) + Hugging Face Spaces (API).
10. **Team ATLAN, PUP** — built through CR-010 with two merge gates.
11. **Validation is three-level** — empirical (Calderon RMSE, withheld until calibration), automated (254 tests + 2 merge gates), external planner sign-off = next milestone (none yet — say so openly).

### Three guardrail lines (memorize verbatim)

| Topic | Say this | Never say this |
|---|---|---|
| **Latency** | "90-second target · ~123 seconds cold · under 1 second warm cache" | "Runs in 90 seconds" (without qualifier) |
| **Validation** | "VAL-01 withheld pending demand calibration — the harness runs, we won't publish a fake RMSE" | "Validated at 94% accuracy" or "Not validated" |
| **Bias auditor** | "Audits every batch; reweights when LLM pool exceeds ±3% — logged publicly" | "Always rebalances the simulation" |
| **Who validated** | "Against peer-reviewed literature + our own glass-box gates today; external CPDO planner validation is the next milestone" | "An expert validated it" / "It's been independently verified" |
| **AI's role** | "AI plans, grounds, and narrates; deterministic equations compute every number" | "AI-powered predictions" / "the AI calculates the impact" |

### Demo closer (10 seconds)

> "Click any number — equation, datasets, computed confidence. Nothing here is the LLM guessing. The kernel and equations own every number."

### If you freeze — reset phrase

> "Let me show you in the product." → Open Inspect drawer or Validation panel.

---

## Appendix — Quick reference tables

### Equation IDs at a glance

| Module | IDs | Highest-confidence metric |
|---|---|---|
| Behavioral | BEH-1 – BEH-4 | BEH-1 Δ trips (H), BEH-3 V/C (H) |
| Ecological | ECO-1 – ECO-4 | ECO-1 CO₂e (H), ECO-3 green-cover (H) |
| Social | SOC-1 – SOC-3 | All M (method-capped or PROVISIONAL proxies) |
| Economic | ECON-1 – ECON-3 | All M |
| Societal | SOCI-1 – SOCI-4 | All M |

### Validation gates

| Gate | Metric | Threshold | Status |
|---|---|---|---|
| VAL-01 | Normalized RMSE vs Calderon 2014 | ≤ 0.30 (FHWA) | **WITHHELD** — demand calibration pending |
| VAL-02 | Length-weighted IoU vs 2024 flood | ≥ 0.50 (Horritt & Bates 2002) | **NOT_RUN** — Sentinel-1 extent not acquired |
| VAL-03 | Mode-share vs anchor | ± 3% | **Enforced** — bias auditor |

> **Human validation (Q2.1):** no external domain expert (CPDO planner / transport engineer) has formally signed off yet. The empirical gates above test against *published literature* (Calderon 2014, the 2024 flood), and the build is guarded by two automated merge gates across 254 tests. Securing a real Iloilo CPDO planner to validate the demo is the highest-priority next step — the PRD-F20 feedback loop is built for it.

### Latency triplet

| Run type | Time | Mechanism |
|---|---|---|
| Target (warm, single user) | **90 s** | RFC-001 design budget |
| Cold first run | **~123 s** | Measured; optimization in progress |
| Cached repeat | **< 1 s** | Redis trajectory cache |

---

*Last updated: 2026-06-25 · Grounded in as-built CR-010 + CR-012 validation plan · Rehearse with [walkthrough.md](walkthrough.md) and [semifinal-video-script.md](semifinal-video-script.md)*
