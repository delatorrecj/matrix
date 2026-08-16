# MATRIX — AAIH 2026 Semi-Final Pitching Video: Script & Production Plan

> **Deliverable:** 5:00 MP4 recording for Semi-Final Pitching
> **Required topics:** Live Prototype Demonstration, Technical Hurdle Breakdown, Explanation of Model Accuracy/Efficiency
> **Round focus:** Technical Integrity & Prototype Quality
> **Judging weights:** Technical Execution **40%** | Innovation & Originality **25%** | Impact & Scalability **20%** | Presentation & Video **15%**
> **Team:** ATLAN (PUP) | **Pilot city:** Iloilo City
> **Grounded in:** the as-built code, [MATRIX.md](../MATRIX.md), and [walkthrough.md](walkthrough.md). Every number below is real or labeled provisional.

---

## 1. Strategic Read: Where the 300 Seconds Go

Time is allocated to mirror the rubric. The live demo is the anchor because it simultaneously serves Technical Execution (40%) and Innovation (25%). Two-thirds of the runtime is on-screen technical proof. The narrative wrapper exists to make that proof land, not to replace it.

| Segment | Time | Duration | Required Topic | Rubric Served |
|---------|------|----------|----------------|---------------|
| **A. Hook: The Problem** | 0:00 to 0:30 | 30s | (framing) | Innovation, Impact |
| **B. What MATRIX Is** | 0:30 to 0:50 | 20s | (positioning) | Innovation |
| **C. Live Prototype Demo** | 0:50 to 2:35 | 105s | Live Prototype Demonstration | **Technical Execution + Innovation** |
| **D. Technical Hurdles** | 2:35 to 3:45 | 70s | Technical Hurdle Breakdown | **Technical Execution** |
| **E. Model Accuracy & Efficiency** | 3:45 to 4:30 | 45s | Model Accuracy/Efficiency | **Technical Execution** |
| **F. ASEAN Scaling + Close** | 4:30 to 5:00 | 30s | (payoff) | Impact & Scalability |

---

## 2. Recurring On-Screen Assets (build once, reuse across segments)

1. **The live app** (`apps/web`, Next.js + Deck.gl) running locally, persona pool pre-warmed, trajectory cache seeded.
2. **The Inspect drawer** open on a real number. Rehearse clicking a result to reveal its `equation_id`, `input_dataset_ids`, and computed confidence.
3. **The architecture diagram** from [MATRIX.md section 5.1](../MATRIX.md). The kernel fanning out to five modules.
4. **A code window** (VS Code) on two files: `matrix_kernel/results.py` (`DimensionResult`, the glass-box contract) and one module (e.g. `modules/ecological.py`) showing an equation with its `equation_id`. Plus a terminal showing the test run passing.
5. **The validation report** in the app Validation panel and `validation_report.json`.

---

## 3. The Full Script

> Target pace: roughly 145 words per minute (technical narration pace). Total voiceover: approximately 680 words. Bracketed stage directions are not spoken.

---

### SEGMENT A: Hook, the Problem (0:00 to 0:30)

**[0:00 to 0:12] ON SCREEN:** Real-world footage of a busy Iloilo intersection or the Iloilo River Esplanade at golden hour (8 to 12 seconds, phone capture or stock). Lower-third title fades in: "MATRIX, Pre-Construction Infrastructure Impact Simulator, Team ATLAN, PUP."

**NARRATION:**

> "Across ASEAN, we are building more infrastructure, faster, than at any point in our history. And we are still deciding blind."

**[0:12 to 0:30] ON SCREEN:** Hard cut to a split screen. On the left, a static PDF feasibility study. On the right, a congested real terminal or intersection.

**NARRATION:**

> "A road, a terminal, a tower. These are billion-peso decisions made on feasibility studies that age the day they are filed. The cities that learn to simulate a project before pouring concrete will pull ahead. The ones that find out on opening day inherit the congestion, the displaced vendors, the flooded barangay the plan was supposed to protect."

*[Problem established in 30 seconds. Move.]*

---

### SEGMENT B: What MATRIX Is (0:30 to 0:50)

**[0:30 to 0:40] ON SCREEN:** Talking head of the presenter, looking into the camera. Clean background, good lighting.

**NARRATION:**

> "MATRIX changes the question from 'is this allowed?' to 'what will this actually do?' A planner asks in plain language. The answer comes back across five impact dimensions, each with an honest confidence level, in about ninety seconds."

**[0:40 to 0:50] ON SCREEN:** Cut to the MATRIX app in the browser. The Iloilo map is loaded and ready.

**NARRATION:**

> "One simulation kernel. Five modules. Every number traceable. Let me show you a live run."

*[Promise made. Handoff straight into the demo.]*

---

### SEGMENT C: Live Prototype Demonstration (0:50 to 2:35)

This is the anchor of the entire video. 105 seconds of the working system, running a real scenario on a real city simulation.

> **Demo scenario:** A new Rapid Deployment Transit (RDT) station on Diversion Rd. This scenario lights up all five dimensions (trips from commuters, emissions from traffic redistribution, economic shifts for informal vendors around the station, etc.). Validate the night before using this scenario to ensure the cleanest five-way spread on the seeded baseline.

**[0:50 to 1:05] ON SCREEN:** Type the natural-language query into the app and drop the project polygon on the map along Diversion Rd.

**NARRATION:**

> "I am a city planner. No GIS training, no modeling background. I describe the project: 'What if we build a new RDT station on Diversion Rd?' Azure OpenAI parses that into a simulation plan. Watch."

**[1:05 to 1:35] ON SCREEN:** Hit run. The WebSocket stream activates. The Deck.gl TripsLayer animation begins playing agent trajectories across the Iloilo road network. [If using the cached warm run, this is near-instant. If showing a sped-up cold run, display a "playback accelerated" label on screen.]

**NARRATION:**

> "This is not a recording. It is a live SUMO simulation. Hundreds of commuter agents, each a persona with a demographic profile, routing through the real Iloilo road network. Jeepney riders, tricycle passengers, pedestrians, private cars, all rerouting around the new trip generator. The animation starts while the impact modules are still computing. That is the streaming architecture. The motion you see is the actual simulated reality that all five dimensions are about to score."

**[1:35 to 2:10] ON SCREEN:** Dimension cards stream in one by one. Behavioral and Ecological land first (high confidence), then Social, Economic, Societal. Each card shows a value, a range, and a confidence chip (High, Medium, or Low).

**NARRATION:**

> "And here they come. Not one black-box verdict, but five. Behavioral and Ecological land first because they are our highest-confidence dimensions. Then Social, Economic, Societal. Notice: every card carries a range and a confidence level. Behavioral is at Medium. The Economic card shows a peso range, not a fake point estimate. This is the opposite of a tool that tells you '47.3 jobs lost' from data that could never support that precision."

**[2:10 to 2:35] ON SCREEN:** Click on one result number. The Inspect drawer slides open, showing the equation ID, the input dataset IDs, and the computed confidence. Pan the cursor slowly across each field.

**NARRATION:**

> "And here is the part that matters most. Click any number and the glass box opens. The exact equation that produced it. The exact datasets that fed it. A confidence that was computed, not guessed. The language model narrates and cites, but it is architecturally forbidden from inventing a number. If a figure on this screen has no working Inspect trail, it does not ship. That is the contract."

*[Live demo complete. The judges have seen the system run end to end.]*

---

### SEGMENT D: Technical Hurdle Breakdown (2:35 to 3:45)

**[2:35 to 2:55] ON SCREEN:** Cut to the architecture diagram (the kernel fanning out to five modules). Highlight the single trajectory dataset at the center.

**NARRATION:**

> "Three hard engineering problems stood between that demo and a credible result. The first was contradiction. Five separate simulators would disagree with each other. Behavioral says trips increase, Ecological says emissions stay flat, because they ran different physics. So we built one kernel. A single SUMO trajectory dataset that all five modules score. They cannot contradict each other because they are reading the same simulated reality."

**[2:55 to 3:20] ON SCREEN:** Cut to VS Code showing `results.py` with the `DimensionResult` contract, then a module file showing an equation with its `equation_id`. Then show the terminal with the test output (passing count).

**NARRATION:**

> "The second problem was the black box. Every result object is bound by contract to its equation ID, its input datasets, and a computed confidence. An automated auditor blocks a merge if a number ships without provenance. That is not a UI feature added at the end. It is a constraint baked into the kernel. And the test suite enforces it."

**[3:20 to 3:45] ON SCREEN:** Cut to a terminal showing per-stage latency timings or the Redis trajectory cache configuration. Show the warm versus cold timing difference.

**NARRATION:**

> "The third problem was speed. Thousands of agents simulated in ninety seconds is brutal. We attack it four ways: a persona pool pre-warmed at startup, delta simulations against a nightly baseline instead of full reruns, all five modules running in parallel, and a trajectory cache that makes a repeated scenario return in under a second. I will be straight with you: a cold run today is still about 123 seconds, above our 90-second target. But every stage is now measured and visible, so we are optimizing against real numbers, not a guess."

*[The honest over-budget admission signals engineering maturity, not weakness.]*

---

### SEGMENT E: Model Accuracy and Efficiency (3:45 to 4:30)

**[3:45 to 4:05] ON SCREEN:** The in-app Validation panel and the `validation_report.json` output. Show the VAL-01 threshold and its Calderon 2014 literature citation.

**NARRATION:**

> "So the question judges rightfully ask: is it accurate? We do not assert accuracy. We compute it. Our validation harness grades the behavioral model against the published Calderon 2014 Iloilo BRT corridor study, using normalized RMSE against an FHWA threshold. It also back-tests flood redistribution against the 2024 Iloilo flood event. The thresholds carry their literature provenance in code."

**[4:05 to 4:30] ON SCREEN:** Show the confidence chips across all five dimensions. Highlight Behavioral at Medium and the "PROVISIONAL" label on the flood fixture.

**NARRATION:**

> "And here is the line most teams will not say out loud. VAL-01 is a published FAIL. Live NRMSE sits on the validation ledger against a 0.30 threshold, so corridor volumes are directional, not city-calibrated. Publishing a passing accuracy number from uncalibrated demand would violate the glass-box principle this product is built on. For an honesty-first tool, publishing the FAIL is the feature. Not the hedge."

*[Integrity proven. This directly answers the judges' ground-truth question.]*

---

### SEGMENT F: ASEAN Roadmap and Close (4:30 to 5:00)

**[4:30 to 4:50] ON SCREEN:** The map zooms out from Iloilo to show the ASEAN region. Show the `CityConfig` concept or a one-line config swap. Briefly show target cities: Jakarta, Bangkok, Ho Chi Minh City, Kuala Lumpur.

**NARRATION:**

> "Iloilo is the pilot, not the ceiling. Scaling to Jakarta, Bangkok, or Ho Chi Minh City is a configuration change. Swap the OpenStreetMap bounding box, reweight the commuter personas to local transit modes: ojek, angkot, tuk-tuk, xe om. The engine is city-agnostic by design. No hardware. No sensors. The cost is API tokens, not procurement. One simulator for every ASEAN city that is deciding blind today."

**[4:50 to 5:00] ON SCREEN:** Talking head of the presenter, or the app showing the five-dimension result with confidence chips visible. End card fades in: "MATRIX | Team ATLAN | Decide before you build."

**NARRATION:**

> "MATRIX. Five dimensions, one honest simulated reality, before the concrete is poured. Decide before you build."

*[Close on the product, not on a face. The tagline lands.]*

---

## 4. Production Plan

### Recommended Tier: Screen-First with Talking-Head Bookends

| Component | Duration | What to capture |
|-----------|----------|-----------------|
| Real-world cold open | 8 to 12s | Phone clip of the actual Iloilo corridor you simulate (the visual rhyme between the real street and the simulated one is powerful) |
| Talking head intro | 10 to 15s | Presenter on camera for Segment B |
| Screen capture | ~240s | The live app, the code, the architecture, the validation panel |
| Talking head outro | 5 to 10s | Presenter for the closing line, or skip and end on the app |

### Capture Setup

- **Screen recording:** OBS Studio, 1080p60 (60 fps keeps Deck.gl animation smooth). Capture the browser at a fixed 1920x1080. Hide bookmarks and notifications. Use a clean OS profile.
- **Cursor:** Enable click highlighting. Move deliberately and slowly, especially into the Inspect drawer.
- **Audio:** A decent USB mic in a quiet room. Record voiceover separately and lay it over the screen capture. This is far cleaner than narrating live. Do a 3-second room-tone capture for noise removal.
- **Talking head:** Window light in front of the presenter (never behind), phone on a tripod at eye level, plain or lightly-blurred background. 1080p.
- **Editing:** DaVinci Resolve (free) or CapCut. Add lower-thirds for technical terms (`equation_id`, `DimensionResult`, `TripsLayer`) so judges can read what they are hearing.
- **Export:** 1080p H.264 MP4 for maximum compatibility with the submission platform.

### On-Screen Integrity Rules

1. **If the demo is sped up, label it.** A cold run is roughly 123 seconds and cannot play in real time within a 5-minute video. Either run from the warm trajectory cache (genuinely fast) or speed-ramp the wait and put "playback accelerated" on screen. Never fake real-time.
2. **Do not fabricate an accuracy number.** The withheld-RMSE honesty is stronger than a made-up percentage.
3. **Show real test output** (the actual passing count) rather than typing a claim.
4. **Keep narration and visuals in sync.** If you say "equation ID," the equation ID must be visible at that exact moment.

---

## 5. Pre-Recording Checklist

Complete this the day before the recording session. After completing it, do not touch the machine.

- [ ] Docker containers running: `cd app && docker compose up -d` (Postgres + Redis + Chroma)
- [ ] Baseline simulation pre-warmed and persona pool cached
- [ ] One throwaway run of the exact demo scenario completed so the trajectory cache is populated (the recorded run will stream quickly and deterministically)
- [ ] `AZURE_OPENAI_API_KEY` set and a quota check passing (do not get rate-limited on camera)
- [ ] `cd app/packages/kernel && uv run pytest` confirms passing tests. Screen-grab the green output for Segment D.
- [ ] Inspect drawer tested on the demo result number. Confirm `equation_id`, dataset IDs, and confidence all resolve. If any number's Inspect is broken, pick a different result to click.
- [ ] Fallback scenario selected and rehearsed in case the primary misbehaves
- [ ] Browser in clean profile: no extensions, notifications off, zoom 100%, Iloilo basemap pre-loaded
- [ ] OBS Studio configured: 1080p60, click highlighting on, recording to local disk
- [ ] USB mic tested; room tone captured for noise removal
- [ ] Lower-third text labels prepared in the editor for: `equation_id`, `DimensionResult`, `TripsLayer`, `CityConfig`, `PROVISIONAL`
- [ ] Full script printed or on a second screen for the narrator

---

## 6. Risk and Integrity Notes

1. **Bias auditor.** The auditor currently flags mode-share skew but does not yet reweight. On camera, say it "audits and surfaces" the anchor. Do not claim it rebalances the simulation.
2. **GraphRAG.** Describe retrieval at the architecture level. There is no public ingestion script yet, so do not demo a step that does not exist.
3. **Latency.** Always pair the 90-second target with the honest 123-second cold reality and the sub-one-second warm-cache reality. The three numbers together are more credible than the target alone.
4. **Visual-narration sync.** The single most common scoring mistake in technical demos is narration describing something the judge cannot see on screen. If you say "equation ID," the equation ID must be visible at that moment.
5. **Video length.** Exactly 5:00 or just under. Going over may result in disqualification or the judges stopping the video before the close lands.

---

## 7. One-Line Cheat Sheet for the Presenter

> Open with the blind-building problem (30s), promise five honest dimensions in 90 seconds (20s), **run it live and open the glass box** (105s), explain the unified kernel, enforced provenance, and the speed fight (70s), show we grade ourselves and honestly withhold what is not calibrated (45s), scale it to ASEAN and land the line (30s).

**Decide before you build.**
