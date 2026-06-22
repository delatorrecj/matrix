# MATRIX — AAIH 2026 Semi-Final Video Script & Production Plan

> **Deliverable:** 5:00 deep-dive recording — Live Prototype Demo · Technical Hurdle Breakdown · Model Accuracy/Efficiency.
> **Round focus:** *Technical Integrity & Prototype Quality.*
> **Judging weights:** Technical Execution **40%** · Innovation & Originality **25%** · Impact & Scalability **20%** · Presentation & Video **15%**.
> **Team:** ATLAN (PUP) · **Pilot:** Iloilo City. Grounded in the as-built code (through CR-007) and [MATRIX.md](../MATRIX.md). Every number below is real or labeled provisional — keep it that way; honesty *is* our pitch.

---

## TL;DR — your two questions answered first

**Q1. Do we film with real-world scenery (campus / Iloilo streets)?**
**Mostly no — the screen IS the product.** With 40% of the score on Technical Execution and only 15% on Presentation, every second of campus B-roll is a second stolen from the demo and the architecture. **Recommendation: a "screen-first" cut** — ~85–90% screen capture of the live prototype + code + architecture, with **one 8–12 s real-world cold open** (a real Iloilo street/the Esplanade or river corridor you're about to simulate) and **a short talking-head intro + outro** (10–15 s each) so a human voice frames the engineering. **Do not stage a full campus shoot.** A drone-over-PUP sequence wins you nothing here and burns your scarcest asset: 300 seconds. See [§5](#5-scenery--production-plan) for the three production tiers and exactly what to capture.

**Q2. Do we apply "The 5 Elements of a Brilliant Sales Narrative"?**
**Yes — as the *spine*, not the *whole skeleton*.** Use the 5 Elements to frame the open and the close (the 0:00–0:50 setup and the 4:30–5:00 payoff). But the **middle three minutes must be genuine technical substance** — judges weighting execution 40% with a "Technical Integrity" lens will *punish* a pure sales pitch that hides thin engineering. Raskin's deck sells vision; this round grades the machine. So: **Element 1–3 open it, Element 4 (features as "magic gifts") is woven *through* the live demo, and Element 5 (evidence) is the demo + the validation harness + the passing tests.** Mapping in [§3](#3-the-5-elements--mapped-to-our-technical-story).

---

## 1. Strategic read — where the 300 seconds go

Time is allocated to *mirror the rubric*, with the live demo as the anchor (it serves both Technical Execution and Innovation at once):

| Segment | Time | Δ | Primarily serves | Required topic |
|---|---|---|---|---|
| **A. Cold open + the change** | 0:00–0:30 | 30 s | Innovation, Impact | (hook) |
| **B. The promise + what MATRIX is** | 0:30–0:50 | 20 s | Innovation | (positioning) |
| **C. Live prototype demo** | 0:50–2:35 | 105 s | **Technical Execution + Innovation** | ✅ Live Prototype |
| **D. Technical hurdle breakdown** | 2:35–3:45 | 70 s | **Technical Execution** | ✅ Technical Hurdles |
| **E. Model accuracy & efficiency** | 3:45–4:30 | 45 s | **Technical Execution (Integrity)** | ✅ Accuracy/Efficiency |
| **F. ASEAN roadmap + close** | 4:30–5:00 | 30 s | Impact & Scalability | (payoff) |

**The demo is the spine of the score.** Two-thirds of the runtime (C+D+E = 220 s) is on-screen technical proof. The narrative wrapper (A, B, F = 80 s) exists to make that proof *land*, not to replace it.

---

## 2. The recurring on-screen assets (build these once, reuse across segments)

1. **The live app** (`apps/web` — Next.js + Deck.gl) running locally, persona pool pre-warmed, trajectory cache seeded (see [§6](#6-pre-record-technical-prep--so-the-demo-runs-clean)).
2. **The Inspect drawer** open on a real number — this single UI element is your strongest Technical-Integrity proof. Rehearse clicking a result → equation_id → input_dataset_ids → computed confidence.
3. **The architecture diagram** — reuse the kernel→five-modules diagram from [MATRIX.md §5.1](../MATRIX.md). Animate the trajectory dataset fanning out to 5 modules.
4. **A code window** (VS Code) on two files: `matrix_kernel/results.py` (`DimensionResult` — the glass-box contract) and one module, e.g. `modules/ecological.py`, showing an equation with its `equation_id`. Plus a terminal showing `186 passed`.
5. **The validation report** — `validation_report.json` and the in-app Validation panel.

---

## 3. The 5 Elements — mapped to our technical story

| Raskin element | MATRIX framing | Where it lives |
|---|---|---|
| **1. Name a big, relevant change** | ASEAN is in the largest urban-infrastructure build-out in its history — and cities still decide *blind*, on feasibility studies that age the day they're filed. | A (0:00–0:30) |
| **2. Winners & losers** | The cities that can *simulate impact before pouring concrete* will leapfrog; the ones that find out after opening day inherit congested terminals, displaced vendors, flooded barangays. | A (0:20–0:30) |
| **3. Tease the promised land** | A planner asks, in plain language, "what happens if we build this here?" — and sees the answer across five dimensions, with honest confidence, in 90 seconds. | B (0:30–0:50) |
| **4. Features as "magic gifts"** | Each capability is introduced as the tool that *overcomes a specific obstacle* to that promised land — the unified kernel (no contradictions), glass-box provenance (no black box), confidence bands (no false precision), the bias auditor (no hidden skew). | C + D (woven through the demo) |
| **5. Evidence you can deliver it** | It's not a mockup — it runs. 186 passing tests, a real SUMO simulation, every number traceable, a validation harness that grades *itself* against published literature. | C, E (0:50–2:35, 3:45–4:30) |

> **Discipline note:** keep Elements 1–2 to **30 seconds total.** The temptation is to luxuriate in the problem. Don't. Technical judges already believe the problem; they're here to see if you *built the thing*.

---

## 4. The Script (shot-by-shot, timecoded)

Format: **`[TIME] ON SCREEN` → narration.** Narration is written to ~145 wpm (technical pace). Total VO ≈ 660 words. Bracketed *(stage directions)* are not spoken.

---

### SEGMENT A — Cold open + the change · 0:00–0:30

**`[0:00–0:12] ON SCREEN:`** *Real-world B-roll — a busy Iloilo intersection or the Iloilo River Esplanade at golden hour (8–12 s, phone or stock). Lower-third title fades in: "MATRIX — Pre-Construction Infrastructure Impact Simulator · Team ATLAN."*

> "Across ASEAN, we are building more infrastructure, faster, than at any point in our history. And we are still deciding *blind*."

**`[0:12–0:30] ON SCREEN:`** *Hard cut to a split screen — a static PDF "feasibility study" on the left, a congested real terminal on the right.*

> "A road, a terminal, a tower — billion-peso decisions made on feasibility studies that age the day they're filed. The cities that learn to *simulate* a project before they pour the concrete will pull ahead. The ones that find out on opening day inherit the congestion, the displaced vendors, the flooded barangay the plan was supposed to protect."

*(Elements 1 + 2 delivered. 30 seconds. Move.)*

---

### SEGMENT B — The promise + what MATRIX is · 0:30–0:50

**`[0:30–0:50] ON SCREEN:`** *Talking head (presenter, 10 s) → cut to the MATRIX app landing state, Iloilo map loaded.*

> "MATRIX changes the question from *'is this allowed?'* to *'what will this actually do?'* — asked in plain language, answered across five impact dimensions, each with an honest confidence level, in ninety seconds. One simulation kernel. Five modules. Every number traceable. Let me show you a live run."

*(Element 3. Hand off straight into the demo — no breath wasted.)*

---

### SEGMENT C — Live prototype demo · 0:50–2:35 *(the anchor — 105 s)*

> **Demo scenario (recommended):** a new mid-rise commercial development beside a **flood-sensitive corridor near the Iloilo River**, in a zone with **informal vendors** and a **heritage edge** (Esplanade / Calle Real). This single scenario lights up all five dimensions. *Use whichever of your 8 QAD reference scenarios renders the cleanest five-way spread on your seeded baseline — validate the night before.*

**`[0:50–1:05] ON SCREEN:`** *Type the natural-language query into the app and/or drop the project polygon on the map.*

> "I'm a city planner. No GIS training, no modeling background. I just describe the project —" *(type)* "— *'an eight-storey mixed-use building here, beside the Esplanade.'* Azure OpenAI GPT-5.4 parses that into a simulation plan. Watch."

**`[1:05–1:35] ON SCREEN:`** *Hit run. The WebSocket stream kicks in: ACCEPTED → the Deck.gl `TripsLayer` animation starts playing agent trajectories over the Iloilo network.*

> "This isn't a video — it's a live SUMO simulation. Hundreds of commuter agents, each a persona generated by Azure OpenAI GPT-5.4, routing through the real road network. The animation starts *while the impact modules are still computing* — that's the streaming architecture. The motion you're seeing is the actual simulated reality all five dimensions are about to score."

**`[1:35–2:10] ON SCREEN:`** *Dimension cards stream in one by one — Behavioral, Ecological first (High confidence), then Social, Economic, Societal — each with a value, a range, and a confidence chip.*

> "And here they come — not as one black-box verdict, but five. Behavioral and Ecological land first; they're our highest-confidence dimensions. Then Social, Economic, Societal. Notice every card carries a **range and a confidence level** — Behavioral: *Medium*. Economic: a peso *range*, not a fake point estimate. This is the opposite of a tool that tells you '47.3 jobs lost' from data that could never support it."

**`[2:10–2:35] ON SCREEN:`** *Click a result → the **Inspect drawer** slides open, showing equation_id, input dataset IDs, and the computed confidence. Pan slowly.*

> "Here's the part that matters. Click any number — and the glass box opens. The exact equation that produced it. The exact datasets that fed it. A confidence that was *computed*, not guessed. The language model narrates and cites; it is *architecturally forbidden* from inventing a number. If a figure on this screen has no working Inspect, it doesn't ship."

*(Element 4 delivered live — each feature shown as the answer to an obstacle. Element 5 begun: it runs.)*

---

### SEGMENT D — Technical hurdle breakdown · 2:35–3:45 *(70 s)*

**`[2:35–2:55] ON SCREEN:`** *Cut to the architecture diagram — kernel fanning out to five modules. Highlight the single trajectory dataset.*

> "Three hard problems stood between that demo and a credible result. **One: contradiction.** Five separate simulators would disagree with each other — behavioral says trips up, ecological says emissions flat, because they ran different physics. So we built *one* kernel: a single SUMO trajectory dataset that all five modules score. They cannot contradict each other, because they're reading the same reality."

**`[2:55–3:20] ON SCREEN:`** *Cut to code — `results.py` `DimensionResult`, then a module equation with its `equation_id`; then the citation-guard. Terminal shows the test run.*

> "**Two: the black-box problem.** Every result object is bound by contract to its equation ID, its input datasets, and a computed confidence — enforced by a citation guard and an automated auditor that *blocks a merge* if a number ships unprovenanced. That's not a UI feature bolted on at the end; it's a constraint compiled into the kernel."

**`[3:20–3:45] ON SCREEN:`** *Cut to the latency stage-timing view / a terminal with per-stage timings; show the Redis trajectory cache.*

> "**Three: speed.** Thousands of agents in ninety seconds is brutal. We attack it four ways — a persona pool pre-warmed at startup, *delta* simulations against a nightly baseline instead of full reruns, all five modules in parallel, and a trajectory cache that makes a repeated run return in under a second. I'll be straight with you: a *cold* run is still about 123 seconds, over our 90-second target. But every stage is now *measured and visible* — so we're optimizing against real numbers, not a guess."

*(That honest over-budget admission is a feature for this round — it signals senior engineering, not weakness.)*

---

### SEGMENT E — Model accuracy & efficiency · 3:45–4:30 *(45 s)*

**`[3:45–4:05] ON SCREEN:`** *The in-app Validation panel + `validation_report.json`. Show the VAL-01 threshold and its literature citation.*

> "So — is it *accurate*? Here's where Technical Integrity gets real. We don't assert accuracy; we *compute* it. Our validation harness grades the behavioral model against the published Calderon 2014 Iloilo BRT corridor study — normalized RMSE, against an FHWA threshold — and back-tests flood redistribution against the 2024 Iloilo flood. The thresholds carry their literature provenance, in code."

**`[4:05–4:30] ON SCREEN:`** *Show the confidence chips across the five dimensions; highlight Behavioral = Medium and the "PROVISIONAL" label on the flood fixture.*

> "And here's the line most teams won't say out loud: our headline RMSE is *withheld*. Mode-share isn't calibrated yet, so Behavioral stays at *Medium* and the flood fixture is labeled *provisional*. Publishing a confident accuracy number from uncalibrated demand would violate the exact glass-box principle this product is built on. The harness is built, it runs, and it will publish the moment the calibration data lands. **For an honesty-first tool, labeling provisional data is the feature — not the hedge.**"

*(Element 5 completed: evidence + the integrity to bound it. This directly answers the judges' ground-truth ask.)*

---

### SEGMENT F — ASEAN roadmap + close · 4:30–5:00 *(30 s)*

**`[4:30–4:50] ON SCREEN:`** *Map zooms out from Iloilo → ASEAN. Show the OSM-bbox swap concept; one line of `CityConfig`.*

> "Iloilo is the pilot, not the ceiling. Scaling to Jakarta, Bangkok, or Ho Chi Minh City is a *configuration* change — swap the OpenStreetMap bounding box, reweight the commuter personas. The engine is city-agnostic by design. One simulator, every ASEAN city that's deciding blind today."

**`[4:50–5:00] ON SCREEN:`** *Talking head, or app on the five-dimension result. End card: MATRIX / Team ATLAN / "Decide before you build."*

> "MATRIX. Five dimensions, one honest simulated reality, before the concrete is poured. Decide *before* you build."

*(Promised land paid off. End on the product, not on a face.)*

---

## 5. Scenery & Production Plan

### The campus question, answered in full

Filming on campus or around Iloilo is **not required and mostly counter-productive** for *this* round, because:

- **The rubric pays for the screen, not the setting.** 40% Technical Execution + 25% Innovation reward what's *in the app and the code*. Scenery contributes only via the 15% Presentation slice — and even there, a clean screen-capture with crisp VO scores higher than shaky campus footage.
- **5 minutes is brutally short.** A 30-second campus establishing sequence is 10% of your runtime spent on zero technical information.
- **Risk vs. reward.** Location shoots add weather, audio, scheduling, and editing risk for marginal gain.

**But a *little* real-world footage earns credibility cheaply** — it proves Iloilo is a real place with a real problem, not an abstraction. So:

### Three production tiers — pick by your team's capacity

| Tier | What you shoot | Real-world footage | Effort | Use when |
|---|---|---|---|---|
| **Minimal (safe)** | 100% screen capture + voiceover. No camera. | None (or 1 stock clip) | Lowest | Time-poor; demo is strong; presenter prefers VO-only |
| **Recommended ✅** | Screen capture + **talking-head intro/outro** + **one 8–12 s Iloilo cold-open clip** | ~20–25 s total | Moderate | **Default.** Humanizes without stealing demo time |
| **Ambitious** | Above + 2–3 short B-roll cutaways (the actual simulated street, the Esplanade) under Segments A/F | ~35–45 s | Higher | You have a good camera, daylight, and edit time to spare |

> **Recommendation: Recommended tier.** One phone clip of the real corridor you simulate (ideally the *same* location as your demo scenario — that visual rhyme is powerful), plus a talking-head intro and outro. Skip the campus tour entirely.

### Capture setup (technical quality is itself "Technical Execution" signaling)

- **Screen capture:** OBS Studio, **1080p60** (60 fps so the Deck.gl animation is smooth — judges notice jank). Capture the browser at a fixed 1920×1080; hide bookmarks/notifications; use a clean OS profile.
- **Cursor:** enable click-highlighting; move deliberately and slowly, especially into the Inspect drawer.
- **Audio:** a decent USB mic (even a Blue Snowball / headset boom) in a soft-furnished room beats a laptop mic. **Record VO separately** and lay it over the screen capture — far cleaner than narrating live. Do a 3-second room-tone capture for noise removal.
- **Talking head:** window light *in front* of the presenter (never behind), phone on a tripod at eye level, plain or lightly-blurred background. 1080p.
- **Editing:** DaVinci Resolve (free) or CapCut. Add lower-thirds for technical terms (`equation_id`, `DimensionResult`, `TripsLayer`) so judges can read what they're hearing.

### On-screen integrity rules (this round is literally judged on integrity)

- **If you accelerate the demo, label it.** A cold run is ~123 s; you cannot show that real-time inside a 5-minute video. Either run from the **warm trajectory cache** (genuinely fast — see §6) *or* speed-ramp the wait and put **"playback accelerated ~4×"** on screen. **Never fake real-time.** If a judge asks and you faked it, the integrity story dies.
- **Don't fabricate an accuracy number** to fill Segment E. The withheld-RMSE honesty is *stronger* than a made-up "94%." Hold the line.
- **Show real test output** (`186 passed`) rather than a typed claim — proof beats assertion.

---

## 6. Pre-record technical prep — so the demo runs clean

Run this checklist the day before, then *don't touch the machine*:

1. `cd app && docker compose up -d` — Postgres + Redis + Chroma up (Redis is what makes the cache fast).
2. Seed the baseline + **pre-warm the persona pool**, then do **one throwaway run of your exact demo scenario** so the **trajectory cache is populated** — the recorded run then streams quickly and deterministically.
3. Confirm `AZURE_OPENAI_API_KEY` is set and a quota check passes (don't get rate-limited on camera).
4. `cd app/packages/kernel && uv run pytest` → confirm **186 passed, 1 skipped**. Screen-grab the green output for Segment D.
5. Open the Inspect drawer once on your demo number and confirm `equation_id` + datasets + confidence all resolve. If any number's Inspect is broken, pick a different result to click — never click a broken one on camera.
6. Pick a **fallback scenario** in case the primary misbehaves; rehearse both.
7. Browser: clean profile, no extensions, notifications off, zoom 100%, the Iloilo basemap pre-loaded.

---

## 7. Risk & integrity notes

- **The bias auditor currently *flags* mode-share skew; it does not yet *reweight*.** If you mention it on camera, say it "audits and surfaces" the anchor — do **not** claim it rebalances the simulation (that's CR-008 work, not shipped). Overclaiming here is exactly what the integrity rubric catches.
- **GraphRAG / RAG ingestion:** describe retrieval at the architecture level; there's no public ingestion script yet — don't demo a step that doesn't exist.
- **Latency:** always pair the 90 s *target* with the honest ~123 s *cold* reality and the <1 s *warm* reality. The triplet is more credible than the target alone.
- **Keep VO and visuals in sync.** The single most common scoring leak in technical demos is narration describing something the judge can't see on screen. If you say "equation ID," the equation ID must be visible *at that moment*.

---

## 8. One-line cheat sheet for the presenter

> *Open with the blind-building problem (30 s) → promise five honest dimensions in 90 s (20 s) → **run it live and open the glass box** (105 s) → explain the unified kernel, enforced provenance, and the speed fight (70 s) → show we grade ourselves and honestly withhold what isn't calibrated (45 s) → scale it to ASEAN and land the line (30 s).*

**Decide before you build.**
