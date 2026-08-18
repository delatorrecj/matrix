# MATRIX — Grand Finals Pitch Deck

**Format:** Story deck, not BMC brochure. **9 core slides + 6 appendix.**
**Built:** [`deck/index.html`](deck/index.html) (primary) and [`MATRIX_GrandFinals_PitchDeck.pptx`](MATRIX_GrandFinals_PitchDeck.pptx) (fallback, regenerate with [`build_deck.py`](build_deck.py)). See [README.md](README.md) for how to present and export.
**Narrative:** [`PITCH_STRATEGY.md`](PITCH_STRATEGY.md) · **Claims:** [`CLAIMS.md`](CLAIMS.md) · **Spoken:** [`PITCH_SCRIPT.md`](PITCH_SCRIPT.md)

This file is the **content** source of truth. If a line changes here, change it in both artifacts.

---

## Design constraints

- One idea per slide. Large type. Low density.
- No false-precision stats. Ranges and confidence language over point estimates.
- Dark instrument surface inherited from the shipped product, not an invented deck brand.
- Human-consequence photography opens and closes; product UI appears only on Demo.
- No eyebrow labels above headings, no section-number kickers, no em-dashes on screen.

---

## Core slides

### 1 — Title
**Beat 1, cold open.** Full-bleed aerial city at dusk.
- Wordmark, AAIH and P2A partner marks
- *See what a decision will do before a city has to live with it.*
- Team ATLAN · Polytechnic University of the Philippines
- ASEAN AI Hackathon 2026, Smart Cities track · Pilot city: Iloilo

**Notes:** deliver the Imagine This question before advancing. Do not open with architecture.

---

### 2 — The question
**Beat 1.**
- *What if a city could see what a decision will do, before it has to live with the result?*
- Sub: *Today it cannot. Cities decide about roads, evacuation routes and transport without seeing what those decisions do to the people living there.*

---

### 3 — The cost of not knowing
**Beat 1.** Two roots on the left, the consequence cascade on the right.
- Heading: *Two problems sit underneath almost every bad urban decision.*
- Root: *Cities decide without seeing what happens next.*
- Root: *The information they rely on is fragmented, inconsistent, or out of date.*
- Cascade: a road is built · traffic shifts · an evacuation route becomes harder to reach · flood risk moves to a barangay that was never in the plan · **the city learns the cost after the concrete is poured**
- Close: *Cities should not have to wait for reality to tell them they made the wrong decision.*

**Do not put:** "Philippines has no data," TAM, competitor logos.

---

### 4 — What if
**Beat 2.**
- *"What happens if we put this here?"*
- Thesis: ***MATRIX** helps cities see the consequences of infrastructure decisions before those consequences become reality.*
- Sub: *Not another static study that ages the day it is filed. A way to explore possible futures, and to understand who pays if we are wrong.*

---

### 5 — How it works
**Beat 3.** Five steps across, then the dimension strip.
- Heading: *Five steps, one simulated reality.*
- **Simulate** plain language, or a pin on the map
- **Visualize** watch the city move once that future exists
- **Compare** five dimensions score the same run
- **Identify** risks, and where our confidence is honestly low
- **Act** a brief a planner can answer
- Strip: *One kernel, one trajectory dataset, five scores that cannot contradict each other:* Behavioral · Social · Economic · Ecological · Societal

**Do not put:** SUMO / Redis / Azure block diagram. That is appendix A1.

---

### 6 — Demo
**Beat 4, hard protected.** Cue card, or full-bleed still if `deck/assets/demo-still.png` exists.
- *Watch one decision.*
- Scenario › Simulation › Consequence › Decision
- matrix-atlan.vercel.app

**Notes:** play the video, do not narrate the controls.

---

### 7 — Proof
**Beat 5.** Evidence ledger, then the honest-limits block in amber.
- Heading: *This is not just an idea.*
- **Runs today** — unified simulation kernel, five impact modules, streaming API and Deck.gl frontend `(PROVEN)`
- **Grounded in Iloilo** — open-data foundation across 180 barangays and 5,680 priced parcels `(PROVEN)`
- **Traceable** — every scored number opens in Inspect: equation, named datasets, computed confidence `(PROVEN)`
- **Gated** — 254 passing automated tests, plus two merge gates that block unprovenanced results `(PROVEN)`
- *And what we will not claim.* Behavioral gate built, headline **withheld** pending calibration · flood back-test **not yet run** · no planner sign-off yet `(LIMIT)`
- Close: *False precision is the real risk. Honest confidence is the feature.*

---

### 8 — The staircase
**Beat 6.** Four ascending flights, "we are here" on the first.
- Heading: *We are not claiming the whole staircase. We are showing the first flight.*
- **Simulation** (we are here) → **Data** → **Digital twin** → **Decision intelligence**

Steps 2 to 4 are vision, future tense only.

---

### 9 — The call
**Beat 7, hard protected.** Full-bleed Iloilo esplanade at sunset.
- *Learn before they act.*
- *Every road, school and flood wall is a decision about someone's life.*
- Team ATLAN · matrix-atlan.vercel.app · Thank you

---

## Appendix (Q&A only, never the spoken spine)

| # | Slide |
|---|-------|
| A1 | Architecture: orchestrator → kernel → one trajectory dataset → synthesis, fanning out to the five modules |
| A2 | Glass box: `equation_id` · `input_dataset_ids` · computed `confidence`, enforced by a merge gate |
| A3 | Validation status: VAL-01 WITHHELD · VAL-02 NOT RUN · VAL-03 ENFORCED |
| A4 | Latency: architected for 90 s, warm vs cold stated honestly |
| A5 | Path: Iloilo → Philippine cities → ASEAN, bbox swap plus persona reweight |
| A6 | Stack: SUMO, Azure OpenAI gpt-5.4, FastAPI, Chroma, Postgres/PostGIS, Redis, Next.js/Deck.gl, Vercel + Hugging Face |

BMC / GTM / revenue is not a slide. If asked: public-good LGU tier, paid later, TBD.

---

## Slide → script mapping

| Slide | Script beat |
|-------|-------------|
| 1–3 | Beat 1 |
| 4 | Beat 2 |
| 5 | Beat 3 |
| 6 | Beat 4 |
| 7 | Beat 5 |
| 8 | Beat 6 |
| 9 | Beat 7 |
