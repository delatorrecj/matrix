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

**Short answer:** A planner asks in plain language or drops a project on the map. Azure OpenAI GPT-5.4 parses that into a structured simulation plan — it never invents numbers. One SUMO kernel runs hundreds of persona agents through Iloilo's real road network and produces a single trajectory dataset. Five impact modules score that same dataset in parallel — Behavioral, Ecological, Social, Economic, Societal — then a synthesis agent narrates with citations. The frontend streams results over WebSocket while Deck.gl animates the trajectories.

**Backing:** Pipeline in [MATRIX.md §5.1](../MATRIX.md); WebSocket stream `ACCEPTED → PLAYBACK_FRAME → DIMENSION_RESULT×5 → SYNTHESIS → DONE` in `apps/api`; modules in `app/packages/kernel/matrix_kernel/modules/`.

**Guardrail:** Do not say "five separate simulators." Say "one kernel, five modules."

---

### Q1.2 — "Why one kernel instead of five independent models?"

**Short answer:** Independent simulators contradict each other — behavioral says trips up while ecological says emissions flat because they ran different physics. We run one SUMO simulation once; all five modules read the same trajectories. They cannot disagree about what happened on the road network.

**Backing:** Architectural commitment in [MATRIX.md](../MATRIX.md) and [methods-matrix.md §1](../docs/methods-matrix.md); each module consumes `Trajectory` from `runner.py`.

**Guardrail:** Do not claim cross-module consistency without naming the shared trajectory dataset.

---

### Q1.3 — "What is the glass box, and can you show me it working?"

**Short answer:** Every number on screen carries an `equation_id`, the named datasets that fed it, and a confidence tier that was *computed* — not guessed. Click any result and the Inspect drawer opens the full provenance chain. If a number has no working Inspect, it doesn't ship — that's enforced in code, not just in the UI.

**Backing:** `DimensionResult` contract in [`results.py`](../app/packages/kernel/matrix_kernel/results.py) (`equation_id`, `input_dataset_ids`, `confidence` are required fields); Inspect drawer in `apps/web`; PRD-F14 in [methods-matrix.md §1](../docs/methods-matrix.md).

**Guardrail:** Demo the Inspect click live. Never describe glass box without showing it.

---

### Q1.4 — "How is AI used in your system — does it generate the numbers?"

**Short answer:** AI does four jobs, and computing the impact numbers is *not* one of them. A single Azure OpenAI GPT-5.4 deployment handles: (1) **orchestration** — turning a plain-language query into a structured simulation plan; (2) **synthesis** — narrating the finished results in plain language with inline citations; (3) **optional persona generation** — off by default in production, where we use a static, literature-anchored persona pool; and (4) **grounding** — a GraphRAG retrieval step feeds it real Iloilo planning documents so it isn't guessing from generic training data. Every impact *number* is computed by deterministic Python equations on named open datasets. Two rails enforce that boundary: a citation guard rejects any synthesis claim that states a number without a valid `[EQUATION_ID]`, and a bias auditor checks the persona pool against Iloilo ground truth. The cardinal rule: **the LLM narrates and cites — it never originates a number.**

**Backing:** Azure OpenAI `gpt-5.4` via the `openai` SDK ([CLAUDE.md](../CLAUDE.md) locked decision); orchestrator + `citation_guard` in `synthesis.py`; `bias_auditor.py`; `graphrag.py` ingested at API startup; "LLM never originates a number" in [methods-matrix.md §1 + §4](../docs/methods-matrix.md); `DimensionResult.__post_init__` fails fast if provenance is missing. Deeper follow-ups: **Q1.13** (why Azure), **Q1.14** (GraphRAG), **Q1.12** (bias auditor).

**Guardrail:** Never say "AI-powered predictions." Say "AI plans, grounds, and narrates; deterministic equations compute every number." If pushed "so what's the AI actually for?" — orchestration + synthesis, with equations as the source of truth.

---

### Q1.5 — "What equations power each dimension?"

**Short answer:** Each dimension has a versioned equation registry. Behavioral uses BEH-1 through BEH-4 — trip deltas, mode-share shift, volume/capacity, facility redistribution. Ecological uses ECO-1 through ECO-4 — CO₂e, PM₂.₅, green-cover, flood exposure. Social uses SOC-1 through SOC-3 — equity-weighted access, displacement, distributional split. Economic uses ECON-1 through ECON-3 — land value, footfall, employment. Societal uses SOCI-1 through SOCI-4 — composite, heritage, health exposure, walkability.

**Backing:** Full registry in [methods-matrix.md §3](../docs/methods-matrix.md); implementations in `app/packages/kernel/matrix_kernel/modules/*.py`.

**Guardrail:** If asked for one example, pick BEH-1 or ECO-1 — both are High-confidence, physics-based, easy to explain.

---

### Q1.6 — "How is confidence computed — High, Medium, or Low?"

**Short answer:** Confidence is derived from four factors — data vintage, spatial coverage, method maturity, and validation status — and the *worst* factor caps the tier. A heuristic method on good data still caps at Medium or Low. Low confidence renders as "directional only" — the precise value is suppressed and the range is labeled honestly.

**Backing:** Rubric in [methods-matrix.md §2](../docs/methods-matrix.md); `confidence_rubric()` and `DATASET_TIERS` in `confidence.py`; `method_capped_confidence` rule (CR-007 PR 6).

**Guardrail:** Never say "we're confident" generically. Always name the tier and why (e.g., "Medium because Calderon 2014 is literature-calibrated, not a live survey").

---

### Q1.7 — "What are your datasets — how many, and where from?"

**Short answer:** We catalog roughly **40 Iloilo data sources** (Tier A) across all five dimensions plus the engine and the GraphRAG knowledge base — about **16 are fetched and wired into the build today**; the rest are scripted or outreach-only, each with an open substitute already in hand, so none blocks us. The headline sets: **Project CCHAIN** — 25 tables, 180 barangays, a 20-year span; the **SUMO road network** built from OpenStreetMap + Overture — 36,367 edges, 14,465 nodes, 148,630 buildings; **BIR zonal land values** — 5,680 priced parcels; **12 PSA + World Bank** economic series; **NOAH flood hazards** across 180 barangays; and a **peer-reviewed knowledge base** led by Calderon 2014. Every dataset carries an INVENTORY ID, a license, a vintage, and a confidence tier — and all are **open data, no proprietary feeds.**

**Backing:** Full manifest in [data/INVENTORY.md](../data/INVENTORY.md) (Tier A/B/C, ~39 catalogued, 16 ✅ fetched); per-dimension map in [data/READINESS.md](../data/READINESS.md); licenses ODbL (OSM/Overture) · PSA open-gov · ESA & World Bank CC BY 4.0; network stats (36,367 edges / 14,465 nodes) in READINESS.

**Guardrail:** Do not claim "complete coverage." Name the soft spot out loud: mode-share comes from literature (Calderon 2014 + LPTRP), not a live LTFRB origin-destination survey. Say "~40 catalogued, ~16 wired" — don't inflate to "40 integrated datasets."

---

### Q1.8 — "Why SUMO and not a social-dynamics simulator like OASIS or MiroFish?"

**Short answer:** We simulate physical urban mobility — vehicles, pedestrians, road capacity — not social-media dynamics. SUMO via TraCI gives us deterministic, physics-based trajectories on a real network. That's the substrate all five impact modules need.

**Backing:** Locked decision in [MATRIX.md §6](../MATRIX.md) and [CLAUDE.md](../CLAUDE.md); TraCI runner in `runner.py` + `sumo_env.py`.

**Guardrail:** Do not dismiss OASIS/MiroFish as "bad" — say they solve a different problem (information diffusion, not road physics).

---

### Q1.9 — "What's your test coverage — does this actually run?"

**Short answer:** Yes. The kernel suite runs 190 tests passing with 11 skipped cleanly when SUMO isn't installed. The API has its own suite — 64 passed, 4 skipped. Every module has unit tests; the glass-box contract is tested; validation gates have dedicated tests. We also have Playwright e2e for the frontend.

**Backing:** [docs/qad-matrix.md](../docs/qad-matrix.md) (reconciled 2026-06-24); run `python -m pytest -q` in `app/packages/kernel` and `app/apps/api`.

**Guardrail:** Say "190 passed" not "all tests pass" — be precise about skips.

---

### Q1.10 — "Explain your WebSocket streaming architecture."

**Short answer:** When a simulation starts, the API accepts the scenario and immediately begins streaming. First comes trajectory playback frames for the Deck.gl animation — so the user sees motion while modules compute. Then dimension results arrive one by one as each module finishes. Finally synthesis narrative, then DONE. This progressive delivery is how we make a multi-stage pipeline feel real-time.

**Backing:** RFC-001 in [docs/rfc-matrix-realtime-pipeline.md](../docs/rfc-matrix-realtime-pipeline.md); WebSocket handler in `apps/api/matrix_api/`.

**Guardrail:** Do not claim sub-second full runs on cold start — distinguish warm/cached from cold.

---

### Q1.11 — "What happens when data is poor or missing?"

**Short answer:** The Low-Confidence Protocol kicks in. Any sparse dataset, heuristic method, PROVISIONAL constant, or unvalidated gate caps the result at Low — and Low renders as directional only. The Inspect drawer prints the exact capping factor so the planner knows *why* the number is bounded.

**Backing:** Low-Confidence Protocol table in [methods-matrix.md §2](../docs/methods-matrix.md); PROVISIONAL constants in §3.6 (e.g., `_VENDORS_PER_CLOSED_LANE = 12`, `_PHP_PER_TRIP_PROXY = ₱50`).

**Guardrail:** Treat "directional only" as a feature, not an apology.

---

### Q1.12 — "How does your bias auditor work?"

**Short answer:** After persona generation, we compare the observed mode share against the Iloilo ground-truth anchor — jeepney 50%, private car 15%, motorcycle 15%, walk 10%, bicycle 5%, tricycle 5%. If any mode deviates beyond ±3%, the pool is reweighted using per-mode correction factors and the adjustment is logged publicly. Every audit entry is keyed to a scenario and fetchable via the API.

**Backing:** `MODE_SHARE_TOLERANCE = 0.03` in `bias_auditor.py`; anchor in `config.py` `ILOILO_MODE_SHARE`; `GET /audit/{scenario_id}`; worked example in [methods-matrix.md §4.1](../docs/methods-matrix.md).

**Guardrail:** Say "audits and reweights the LLM-generated pool." The deployed default static pool is on-anchor by construction — reweight rarely fires in production today.

---

### Q1.13 — "You use Azure OpenAI — why not Gemini or another model?"

**Short answer:** We use Azure OpenAI GPT-5.4 via the standard `openai` Python SDK pointed at the Azure AI Foundry v1 endpoint — one deployment for orchestration, synthesis, and optional persona generation. We migrated off Gemini in CR-008 because Foundry routing and citation discipline required a single, controlled endpoint.

**Backing:** [docs/cr-008-azure-openai-migration.md](../docs/cr-008-azure-openai-migration.md); [docs/cr-009-azure-foundry-client.md](../docs/cr-009-azure-foundry-client.md) — use `openai.OpenAI(base_url=…)`, not `openai.AzureOpenAI`.

**Guardrail:** Do not mention Gemini as a current option.

---

### Q1.14 — "What is GraphRAG doing in your pipeline?"

**Short answer:** At API startup we ingest a corpus of Iloilo planning documents, literature, and local context into ChromaDB. When a user asks a question, the orchestrator retrieves relevant chunks and injects them into the prompt — so the LLM grounds its scenario parsing in local facts, not generic training data.

**Backing:** `graphrag.py`; CR-008 wired ingestion at API startup (see [CLAUDE.md](../CLAUDE.md)); retrieval example in [methods-matrix.md §4.2](../docs/methods-matrix.md).

**Guardrail:** GraphRAG grounds *orchestration* — it does not originate dimension scores. Do not demo a retrieval step that isn't wired.

---

### Q1.15 — "Can you reproduce a run — same inputs, same outputs?"

**Short answer:** Yes. Every simulation records the scenario parameters, random seed, dataset vintages, and model versions. Same inputs produce the same outputs. That's a first-class reproducibility contract, not an afterthought.

**Backing:** [methods-matrix.md §7](../docs/methods-matrix.md); `simulation_runs` schema in SDD; seed control in `runner.py`.

**Guardrail:** Do not claim bit-identical reproduction across different SUMO versions without noting the version stamp.

---

## Section 2 — Model Accuracy, Validation & Efficiency

### Q2.1 — "Who validated this system — is there an outside expert who checked it?"

**Short answer:** Validation runs on three levels, and we're honest about where each one stands. **One — empirical back-testing against published research:** our behavioral proxy is checked against the peer-reviewed Calderon et al. 2014 Iloilo BRT study using normalized RMSE at the FHWA-documented 0.30 threshold. The gate is built and running, but we deliberately *withhold* the headline number until demand volume is calibrated — publishing a confident figure off uncalibrated demand would break our own glass-box rule. **Two — internal engineering validation:** two automated merge gates, a glass-box auditor and an eval test-runner, block any merge that ships an unprovenanced number or a failing test, across 254 automated tests. **Three — and this is the honest gap: no external CPDO planner or transport engineer has formally signed off yet.** Getting one real Iloilo CPDO planner to validate the demo is our highest-leverage next step, and the product already ships a PRD-F20 feedback loop built to capture exactly that expert input.

**Backing:** `validate_calderon()` in [`validation.py`](../app/packages/kernel/matrix_kernel/validation.py) vs `LIT-CALDERON`; two merge gates in [AGENTS.md](../AGENTS.md) (`glass-box-auditor` + `eval-test-runner`); 254 tests (190 kernel + 64 API) in [docs/qad-matrix.md](../docs/qad-matrix.md); PRD-F20 CPDO feedback loop; status in [methods-matrix.md §6](../docs/methods-matrix.md) + [docs/cr-012-validation-calibration.md](../docs/cr-012-validation-calibration.md).

**Guardrail:** Never imply a domain expert has validated it. Say "validated against peer-reviewed literature and our own glass-box gates today; independent planner validation is the next milestone." Don't conflate automated/empirical validation with human sign-off — name all three levels and which one is still open.

---

### Q2.2 — "How do you validate your behavioral model?"

**Short answer:** VAL-01 back-tests our corridor passenger-flow proxy against the published Calderon et al. 2014 Iloilo BRT study — normalized RMSE against an FHWA-documented threshold of 0.30. The gate is published as an honest **FAIL** (live NRMSE is on screen in the validation panel). Corridor volumes are directional, not city-calibrated. Uncalibrated demand is why it fails — we do not hide the RMSE.

**Backing:** `validate_calderon()` in [`validation.py`](../app/packages/kernel/matrix_kernel/validation.py); `VAL01_THRESHOLD_NRMSE = 0.30` with FHWA provenance; fixture from `LIT-CALDERON`; status in [methods-matrix.md §6](../docs/methods-matrix.md) and [docs/cr-012-validation-calibration.md](../docs/cr-012-validation-calibration.md).

**Guardrail:** Say "published FAIL — directional volumes," not "withheld" and not "validated at 94%."

---

### Q2.3 — "If you can't show RMSE, why should we trust your behavioral numbers?"

**Short answer:** Because we don't hide the uncertainty — Behavioral is rated Medium confidence, ranges are shown instead of false-precision point estimates, and BEH-4 facility redistribution is explicitly Low/directional because its gravity constants are PROVISIONAL. We'd rather show an honest Medium with a working Inspect than a fake "94% accurate" with nothing behind it.

**Backing:** BEH-2 confidence basis "M (literature calibration)" in [methods-matrix.md §3.1](../docs/methods-matrix.md); BEH-4 capped at L; `directional` property on `DimensionResult`.

**Guardrail:** Never invent an accuracy percentage. Point to the confidence tier and the validation roadmap.

---

### Q2.4 — "What about flood validation?"

**Short answer:** VAL-02 compares simulated flood road closures against the 2024 Iloilo flood using length-weighted spatial IoU, threshold ≥ 0.50 per Horritt & Bates 2002. The gate and closure helper are implemented, but the observed fixture is PROVISIONAL until we acquire the Copernicus Sentinel-1 GFM extent — so VAL-02 reports NOT_RUN, not a fake pass.

**Backing:** `validate_flood()` in `validation.py`; `VAL02_THRESHOLD_IOU = 0.50`; `flood2024_closures.json` marked PROVISIONAL; [methods-matrix.md §3.7](../docs/methods-matrix.md).

**Guardrail:** Do not claim flood validation passed. Say "staged, awaiting sourced extent."

---

### Q2.5 — "What's your 90-second latency claim — can you actually hit it?"

**Short answer:** Ninety seconds is our engineered target for a warm baseline, single-user run. We attack latency four ways: pre-warmed persona pool at startup, delta simulations against a nightly baseline instead of full reruns, five modules in parallel, and progressive WebSocket streaming so the user sees motion immediately. A cold first run is still roughly 123 seconds — we measure every stage and optimize against real numbers. A repeated run from the Redis trajectory cache returns in under one second.

**Backing:** RFC-001 strategy; PERF-01 in [docs/qad-matrix.md](../docs/qad-matrix.md) (~48 s warm, <1 s cached repeat); honest cold-run admission in [semifinal-video-script.md](../reference/AAIH-2026-semifinal-video-script.md).

**Guardrail:** Always give the triplet: **90 s target · ~123 s cold · <1 s warm cache.** Never quote only the target.

---

### Q2.6 — "Why is your demand not calibrated — what's the blocker?"

**Short answer:** Our mode-share anchor comes from Calderon 2014 literature plus LPTRP context — not a live LTFRB origin-destination survey. Absolute corridor volumes from synthetic demand run above published Calderon maxima. CR-012 reconciled the proxy definition — removing about 8× of a prior over-count — but residual demand-volume calibration needs LTFRB OD data via FOI or a local household survey.

**Backing:** [docs/cr-012-validation-calibration.md §1](../docs/cr-012-validation-calibration.md); FOI path in `config.py`; READINESS Behavioral gap ("mode-share ground truth is the soft spot").

**Guardrail:** Do not blame "bad code" — frame it as honest data acquisition in progress.

---

### Q2.7 — "What PROVISIONAL constants are still in your equations?"

**Short answer:** Several Milestone-A stand-ins declared openly in methods §3.6: `_PHP_PER_TRIP_PROXY = ₱50` for economic land-value uplift, `_VENDORS_PER_CLOSED_LANE = 12` for vendor displacement, `_PM25_PER_CO2E_PROXY = 0.05` for air-quality delta, and per-kind gravity constants in BEH-4 facility redistribution. Each is flagged PROVISIONAL in the Inspect drawer assumptions field — replacing them with sourced values is tracked under CR-012.

**Backing:** [methods-matrix.md §3.6](../docs/methods-matrix.md) constant table; each caps confidence per the Low-Confidence Protocol.

**Guardrail:** Listing PROVISIONAL constants demonstrates integrity — don't omit them when asked.

---

### Q2.8 — "Do your validation gates ever pass by construction?"

**Short answer:** No. We replaced validation-theater stubs with real computations. A gate with no simulated input reports NOT_RUN with a reason — never fabricated. A FAIL is reported as FAIL. `GateResult.__post_init__` forbids status/value contradictions by construction.

**Backing:** Module docstring in `validation.py` lines 1–23; `PROVISIONAL_MARK` enforcement in `load_fixture()`.

**Guardrail:** If asked about old stubs, acknowledge they existed and were replaced — don't pretend they never happened.

---

## Section 3 — Innovation & Originality (25%)

### Q3.1 — "What's actually novel here — isn't this just SUMO plus ChatGPT?"

**Short answer:** SUMO gives us physics; the LLM gives us orchestration. What's novel is the combination no existing tool ships together: plain-language input, five impact dimensions from one unified simulation, per-dimension computed confidence with glass-box provenance, and a bias auditor anchored to local mode share — deployable on open data with no hardware.

**Backing:** Feature survey gap in [docs/gtm-matrix.md §2.1](../docs/gtm-matrix.md) and [CONTENT-OUTLINE.md §3](CONTENT-OUTLINE.md); locked architecture in [MATRIX.md](../MATRIX.md).

**Guardrail:** Acknowledge SUMO and GPT are components. Own the *integration and honesty layer* as the innovation.

---

### Q3.2 — "How are you different from PTV Vissim or Aimsun?"

**Short answer:** Vissim and Aimsun are excellent traffic microsimulators — but they need a transport modeling specialist, typically cover one or two dimensions, and don't expose per-dimension confidence or plain-language input. MATRIX targets the city planner who can't run Vissim but needs a cross-domain answer in ninety seconds.

**Backing:** Competitor survey in [CONTENT-OUTLINE.md §3](CONTENT-OUTLINE.md) and GTM §2.1; honest caveat "based on our feature survey."

**Guardrail:** Never say Vissim is "bad." Say it solves a different user and scope.

---

### Q3.3 — "What about Replica, UrbanFootprint, or ESRI CityEngine?"

**Short answer:** Replica focuses on mobility analytics from passively collected data — it tells you what *is* happening, not what *would* happen if you build a new tower. UrbanFootprint and CityEngine are strong on land use and 3D visualization but don't run a unified five-dimension impact simulation with explicit confidence. Our gap is the combination: counterfactual simulation plus cross-domain scoring plus provenance.

**Backing:** GTM §2.1 feature matrix; MATRIX counterfactual framing in [MATRIX.md](../MATRIX.md).

**Guardrail:** Do not claim competitors lack AI — claim they lack this specific *combination*.

---

### Q3.4 — "How do you handle the informal economy — jeepneys, tricycles, street vendors?"

**Short answer:** Informal transit is first-class in our persona pool — jeepney at 50% mode share, tricycle at 5% — anchored to Iloilo literature, not a Western-default car-centric mix. Social module SOC-2 models vendor displacement risk when lanes close. Economic and societal modules capture informal livelihood impacts. This is what Western-origin tools typically omit.

**Backing:** `ILOILO_MODE_SHARE` in `config.py`; SOC-2 in [methods-matrix.md §3.3](../docs/methods-matrix.md); ASEAN tailoring in [CONTENT-OUTLINE.md §69–75](CONTENT-OUTLINE.md).

**Guardrail:** Do not claim perfect informal-sector modeling — say it's modeled with Medium confidence and PROVISIONAL vendor constants.

---

### Q3.5 — "You mention Hiligaynon support — how does that work?"

**Short answer:** Users can ask in Hiligaynon or English. A curated gazetteer maps colloquial terms — "merkado," "tulay sa forbes" — to canonical locations *before* the LLM parses the query, so regional language doesn't break scenario extraction. Synthesis output includes a full Hiligaynon brief separated by a `=== HILIGAYNON ===` delimiter, toggled in the UI.

**Backing:** [methods-matrix.md §4.2–§4.3](../docs/methods-matrix.md); `gazetteer_iloilo.json`; CR-010 bilingual BLUF brief; `LanguageProvider` in frontend.

**Guardrail:** Gazetteer OSM/SUMO node IDs are PROVISIONAL placeholders — the mapping logic works; the IDs need GIS verification.

---

### Q3.6 — "What's innovative about your confidence system?"

**Short answer:** Most tools either hide uncertainty or fake precision. We compute confidence from data vintage, coverage, method maturity, and validation status — worst factor wins — and Low confidence suppresses the point estimate entirely. For data-sparse ASEAN cities, stating "we don't know precisely, but directionally it increases flood exposure" is more useful than "47.3 persons affected."

**Backing:** [methods-matrix.md §2](../docs/methods-matrix.md); PRD-F5 directional-only rendering; CR-010 number humanization in `lib/format.ts`.

**Guardrail:** Do not say "AI confidence score." Say "computed confidence tier from a documented rubric."

---

### Q3.7 — "Did you build the bias auditor because LLMs are biased?"

**Short answer:** Yes — LLMs default to WEIRD, middle-class archetypes that over-index private cars. Our persona generator can produce skewed mode shares. The bias auditor detects deviation beyond ±3% from the Iloilo anchor and reweights with logged, Inspect-resolvable correction factors. It's a first-class product feature, not an afterthought.

**Backing:** [methods-matrix.md §4.1](../docs/methods-matrix.md) worked example (observed private_car 0.30 vs target 0.15); CR-008 Item 3; `reweight_pool()` in `bias_auditor.py`.

**Guardrail:** The static default pool is literature-anchored and on-target — reweight demonstrates on LLM-generated pools or test scenarios.

---

### Q3.8 — "What extreme events can you simulate?"

**Short answer:** Users can specify flood hazard extents as GeoJSON. A deterministic helper closes road edges that intersect the hazard layer, SUMO reroutes around them, and ECO-4 calculates population exposure in the footprint. This lets planners ask "what if we build here AND a 2024-scale flood hits?" — a resilience question feasibility studies rarely cover.

**Backing:** [methods-matrix.md §3.7](../docs/methods-matrix.md); `flood_scenario` helper; ECO-4 equation.

**Guardrail:** Flood validation (VAL-02) is NOT_RUN — the simulation works; the back-test against real 2024 extent doesn't yet.

---

## Section 4 — Impact & Scalability (20%)

### Q4.1 — "Who is your actual user?"

**Short answer:** A city planner at Iloilo CPDO or NEDA Region VI — someone who approves capital projects but doesn't have GIS or transport modeling training. They ask in plain language, drop a project on the map, and get five scored dimensions with honest confidence in about ninety seconds.

**Backing:** PRD user stories; beachhead in [CONTENT-OUTLINE.md §2](CONTENT-OUTLINE.md) and [docs/gtm-matrix.md](../docs/gtm-matrix.md).

**Guardrail:** Do not say "everyone." Name the planner persona specifically.

---

### Q4.2 — "Why Iloilo — why not Manila or a bigger city?"

**Short answer:** Iloilo is our pilot, not our ceiling. It won ASEAN Clean Tourist City 2026, has rich open data at 180-baranagay granularity via Project CCHAIN, and represents the ASEAN pattern — rapid growth, informal transit, flood exposure, data that's good but not perfect. If we solve honesty for Iloilo, we solve it for Jakarta, Bangkok, and Ho Chi Minh City.

**Backing:** ASEAN Clean Tourist City 2026 anchor in [MATRIX.md](../MATRIX.md); CCHAIN coverage in [data/READINESS.md](../data/READINESS.md).

**Guardrail:** Iloilo proves the engine — not that we're an Iloilo-only tool.

---

### Q4.3 — "How does it scale to other ASEAN cities?"

**Short answer:** Two configuration changes: swap the OpenStreetMap bounding box for the new city, and reweight the persona pool to local mode shares — ojek in Jakarta, angkot in Bangkok, xe-om in Ho Chi Minh City, songthaew in Chiang Mai. No hardware deployment; cost is API tokens and open-data ingestion, not procurement.

**Backing:** `CityConfig` in [`config.py`](../app/packages/kernel/matrix_kernel/config.py) — `MATRIX_CITY_BBOX`, `MATRIX_MODE_SHARE` env overrides; GTM ASEAN scaling in [docs/gtm-matrix.md](../docs/gtm-matrix.md).

**Guardrail:** Say "configuration change," not "plug and play tomorrow." Each new city needs data ingestion and persona reweighting work.

---

### Q4.4 — "What's your go-to-market after the hackathon?"

**Short answer:** Beachhead is Iloilo LGU plus academic validation — one real CPDO planner validating the demo is the highest-leverage move. Then other Philippine cities, then ASEAN. Revenue model is deliberately TBD: public-good free tier for LGUs and academia now, paid developer/SaaS tier later. At hackathon stage the goal is adoption and credibility, not revenue.

**Backing:** [docs/gtm-matrix.md](../docs/gtm-matrix.md); [CONTENT-OUTLINE.md §9–10](CONTENT-OUTLINE.md).

**Guardrail:** Do not invent TAM/SAM/SOM numbers. Say "directional market frame, assumptions stated."

---

### Q4.5 — "What's the business model — how do you make money?"

**Short answer:** We haven't locked pricing — deliberately. The public-good tier for LGU and academic users stays free to drive adoption. A paid tier for private developers doing site feasibility is the natural monetization path post-hackathon. Right now we're building credibility and a working pilot, not optimizing ARR.

**Backing:** BMC in [CONTENT-OUTLINE.md §8](CONTENT-OUTLINE.md) — revenue labeled TBD/post-hackathon.

**Guardrail:** Never quote a specific price or revenue projection without a sourced model.

---

### Q4.6 — "What's the impact if a city uses MATRIX before approving a project?"

**Short answer:** A planner sees cross-domain impacts — congestion, flood exposure, vendor displacement, land-value effects, heritage proximity — before capital is committed. They can compare scenarios, understand which dimensions are High vs Low confidence, and export a one-page brief for stakeholder review. The value is de-risking billion-peso decisions, not replacing the feasibility study entirely.

**Backing:** PRD-F20 CPDO feedback loop; CR-010 `ScenarioBrief` export; value framing in [CONTENT-OUTLINE.md §7](CONTENT-OUTLINE.md).

**Guardrail:** Do not invent ROI percentages. Say "de-risks capital allocation" with honest confidence bounds.

---

### Q4.7 — "Can this work in data-sparse cities?"

**Short answer:** That's exactly why the confidence layer exists. In cities with sparse data, MATRIX doesn't fake precision — it computes the confidence floor and renders directional results where data can't support a number. For ASEAN cities where IoT coverage is uneven and travel surveys are expensive, honest bounds are more actionable than false precision.

**Backing:** Confidence rubric §2; READINESS per-dimension gaps; [MATRIX.md](../MATRIX.md) honesty principle.

**Guardrail:** Do not claim High confidence where READINESS says Medium or Low.

---

### Q4.8 — "How does MATRIX relate to Iloilo's ASEAN Clean Tourist City 2026 award?"

**Short answer:** Iloilo won ASEAN Clean Tourist City 2026 — recognition that the city invests in sustainable urban planning. MATRIX gives that planning culture a pre-construction impact simulator: before the next esplanade extension, terminal, or commercial development, the city can simulate effects across mobility, ecology, and social equity with transparent confidence.

**Backing:** ASEAN Clean Tourist City 2026 references in [MATRIX.md](../MATRIX.md) and [CONTENT-OUTLINE.md §79](CONTENT-OUTLINE.md).

**Guardrail:** Do not imply MATRIX caused or enabled the award — say it supports the planning culture the award recognizes.

---

## Section 5 — Presentation, Process & Team (15%)

### Q5.1 — "Who built this — what's your team structure?"

**Short answer:** Team ATLAN from Polytechnic University of the Philippines — five members. Carlos Jerico Dela Torre leads product and AI architecture. Yushin Bjorn Matsuda owns frontend and UI/UX. Maria Espina handles QA and UX. Rica Mae Mago and Russell Jay Fajardo cover QA, research, and marketing. We built end-to-end through ten change records with two automated merge gates.

**Backing:** Team roster in [MATRIX.md](../MATRIX.md); build agents in [AGENTS.md](../AGENTS.md).

**Guardrail:** Credit the team, not just the lead. Name specific contributions if asked.

---

### Q5.2 — "How did you manage quality under hackathon time pressure?"

**Short answer:** Two non-negotiable merge gates: a glass-box auditor that blocks any number without provenance, and an eval test runner that blocks any merge without passing tests. Every change goes through a numbered Change Record. We don't skip validation to ship faster — we ship honestly or we don't ship.

**Backing:** [AGENTS.md](../AGENTS.md) merge gate; CR-001 through CR-010 change records in `docs/cr-*.md`; `glass-box-auditor` and `eval-test-runner` agents.

**Guardrail:** Do not claim "no bugs." Claim "no unprovenanced numbers ship."

---

### Q5.3 — "Why a screen-first video instead of a campus shoot?"

**Short answer:** This round weights Technical Execution at 40% and Presentation at 15%. Every second of campus B-roll is a second stolen from the live demo and architecture walkthrough. We use one short Iloilo cold-open for credibility, talking-head bookends, and ~85% screen capture of the working prototype, code, and validation harness.

**Backing:** Production plan in [reference/AAIH-2026-semifinal-video-script.md §5](../reference/AAIH-2026-semifinal-video-script.md).

**Guardrail:** If you accelerated the demo in video, label it on screen — never fake real-time.

---

### Q5.4 — "What would you do with more time or funding?"

**Short answer:** Three priorities: calibrate demand to LTFRB OD data and publish VAL-01 honestly, acquire the Sentinel-1 flood extent for VAL-02, and close the cold-run latency gap from ~123 seconds to the 90-second target via libsumo and headless optimization. Each is scoped in CR-012 with a Tier A (data lands) and Tier B (interim proxy) path.

**Backing:** [docs/cr-012-validation-calibration.md](../docs/cr-012-validation-calibration.md) workstreams WS-1 through WS-4.

**Guardrail:** Frame as a roadmap, not a promise of completion by finals.

---

### Q5.5 — "Is this deployed — can we try it?"

**Short answer:** Yes. The web frontend deploys on Vercel; the API runs on Hugging Face Spaces with Docker. Locally, `docker compose up` for Postgres, Redis, and Chroma, then `uvicorn` for the API and `npm run dev` for the web app. The full pipeline runs end-to-end today.

**Backing:** CR-011 Hugging Face migration in [docs/cr-011-huggingface-migration.md](../docs/cr-011-huggingface-migration.md); commands in [CLAUDE.md](../CLAUDE.md).

**Guardrail:** Have the live URL ready. If the demo environment is down, cut to recorded fallback without apology.

---

## Section 6 — Hardball & Integrity Traps

### Q6.1 — "Show me a number you can't back up."

**Short answer:** BEH-4 facility demand redistribution is Low confidence / directional only — its gravity constants are PROVISIONAL per-kind placeholders, not calibrated to Iloilo survey data. We show the direction and the range, but the Inspect drawer explicitly flags `_TRIPS_PER_CAPACITY` as uncalibrated. We'd rather show that honestly than hide it behind a Medium tag.

**Backing:** BEH-4 in [methods-matrix.md §3.1](../docs/methods-matrix.md); `FACILITY_PROFILES` in §3.6; `directional` property suppresses false precision.

**Guardrail:** This question is a gift — use it to demonstrate integrity, not defensiveness.

---

### Q6.2 — "Your RMSE is hidden — so your model isn't validated at all?"

**Short answer:** The validation *machinery* is built, tested, and running — VAL-01 computes normalized RMSE against Calderon 2014 with an FHWA threshold. We withhold the headline because publishing a number from uncalibrated demand would be dishonest. The gate will publish pass or fail the moment calibration lands. Withholding IS the validation — it proves we hold ourselves to the same glass-box standard we sell.

**Backing:** CR-012 §1; `validation.py`; [methods-matrix.md §6](../docs/methods-matrix.md) status table.

**Guardrail:** Never say "we'll validate later." Say "the harness runs today; the demand calibration is the blocker."

---

### Q6.3 — "You missed your own 90-second budget — why should we believe your engineering?"

**Short answer:** Because we measure every stage and report the honest triplet: 90-second target, roughly 123 seconds cold, under one second on cache repeat. We architected specifically for the budget — pre-warmed personas, delta sims, parallel modules, streaming UI — and we're 30 seconds over on cold start, not 10 minutes. Naming the gap signals senior engineering, not weakness.

**Backing:** RFC-001; PERF-01 in qad-matrix.md; semi-final script §D honest admission.

**Guardrail:** Always pair target with actual. Never quote only "90 seconds."

---

### Q6.4 — "The bias auditor — does it actually reweight or just flag?"

**Short answer:** Both. It flags deviation beyond ±3% and, when triggered, applies per-mode multiplicative correction factors via stratified resampling — logged publicly with exact factors in the audit entry. In production today, the default static persona pool is literature-anchored and on-target, so reweight rarely fires. It demonstrably works on LLM-generated pools where middle-class car bias appears.

**Backing:** `reweight_pool()` in `bias_auditor.py`; worked example in [methods-matrix.md §4.1](../docs/methods-matrix.md); CR-008 Item 3.

**Guardrail:** Do not say "always reweights." Say "audits every batch; reweights when triggered."

---

### Q6.5 — "Your gazetteer IDs are placeholders — doesn't that break the product?"

**Short answer:** The glass-box guarantee for the gazetteer is about *provenance of the ID* — the ID always comes from our curated map, never from the LLM inventing a node. The current OSM and SUMO edge IDs are flagged PROVISIONAL and need GIS verification against the deployed network. Location *names* resolve correctly; edge-level routing precision improves once IDs are verified.

**Backing:** [methods-matrix.md §4.2](../docs/methods-matrix.md) PROVISIONAL note; `gazetteer_iloilo.json` `"provisional": true` flags.

**Guardrail:** Do not claim gazetteer IDs are verified ground truth.

---

### Q6.6 — "Isn't fixed open data a weakness versus live IoT simulators?"

**Short answer:** They answer different questions. IoT tells you what *is* happening right now. MATRIX answers what *would* happen if you build a project that doesn't exist yet — a counterfactual no sensor can observe. Open data is also what makes us deployable to any ASEAN city without installing hardware. The confidence layer states exactly where we're sure and where we're not.

**Backing:** Counterfactual framing in [MATRIX.md](../MATRIX.md); vs IoT comparison in [methods-matrix.md §8](../docs/methods-matrix.md) and [walkthrough.md §Q&A](walkthrough.md).

**Guardrail:** Respect IoT tools — claim complementary scope, not superiority.

---

### Q6.7 — "What about data privacy — RA 10173?"

**Short answer:** The core pipeline uses no personal data — only open datasets under ODbL, PSA, ESA, and similar licenses with attribution. Personas are synthetic archetypes, not real individuals. Any future GPS-trace feature would be gated behind a Privacy Impact Assessment and legal counsel under the Philippine Data Privacy Act.

**Backing:** RA 10173 note in [walkthrough.md §Q&A](walkthrough.md); open-data licenses in [MATRIX_Iloilo_Data_Sources.md](../MATRIX_Iloilo_Data_Sources.md).

**Guardrail:** Do not claim "fully compliant" without counsel review — say "no PII in the current pipeline."

---

### Q6.8 — "You're students — can you maintain this after the hackathon?"

**Short answer:** The codebase is production-architected — monorepo with locked docs, 254 automated tests, change records, and deployment on Vercel plus Hugging Face. CR-006 through CR-010 hardened it beyond a hackathon prototype. We have a post-hackathon roadmap for Iloilo CPDO pilot validation and CR-012 calibration work.

**Backing:** CR history in [CLAUDE.md](../CLAUDE.md); test counts; deployment stack.

**Guardrail:** Be honest about team capacity — don't promise 24/7 enterprise SLA.

---

### Q6.9 — "What if the LLM hallucinates in the synthesis narrative?"

**Short answer:** The citation guard splits the synthesis brief into claim-sized units and blocks any numeric claim lacking a valid `[EQUATION_ID]` that resolves to a kernel result with dataset backing. Uncited quantitative claims are rejected from render. The LLM can still hallucinate qualitative prose — but any number on screen passed the guard.

**Backing:** Citation guard in [methods-matrix.md §4](../docs/methods-matrix.md); `synthesis.py` guard logic; CR-010 BLUF structure.

**Guardrail:** Do not claim "zero hallucination." Claim "zero unprovenanced numbers on screen."

---

### Q6.10 — "Why should we advance you over teams with higher accuracy numbers?"

**Short answer:** Because we'd rather show you an honest Medium with a working Inspect than a fake 94% with nothing behind it — and because the combination we ship — five dimensions, one kernel, glass-box provenance, plain-language input, ASEAN informal-sector modeling — doesn't exist as an integrated product elsewhere. Integrity at semi-finals IS the differentiator the rubric asks for.

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
11. **Validation is three-level** — empirical (Calderon NRMSE published as FAIL vs 0.30), automated (254 tests + 2 merge gates), external planner sign-off = next milestone (none yet — say so openly).

### Three guardrail lines (memorize verbatim)

| Topic | Say this | Never say this |
|---|---|---|
| **Latency** | "90-second target · ~123 seconds cold · under 1 second warm cache" | "Runs in 90 seconds" (without qualifier) |
| **Validation** | "VAL-01 is a published FAIL — live NRMSE vs 0.30; corridor volumes are directional" | "Validated at 94% accuracy" or "RMSE withheld" |
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
