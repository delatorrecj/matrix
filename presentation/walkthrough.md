# MATRIX — Pitch Walkthrough & Live-Demo Run-of-Show

**Format:** AAIH semi-final ≈ **5-minute pitch + 3-minute Q&A** (final: longer, more weight on Impact + Presentation).
**Golden rule:** the live 90-second demo is the moment judges remember — protect time for it, and always have a recorded fallback.
**Tone:** confident but honest. We say "target," "planned," and "directional" out loud — that discipline is the brand.

---

## 5-minute run-of-show (timed)

| Time | Slide(s) | Say (compressed) |
|---|---|---|
| 0:00–0:25 | **1 Title** | "Across ASEAN, cities make billion-peso infrastructure decisions on studies that age the day they're filed. Iloilo — this year's ASEAN Clean Tourist City — is our pilot. MATRIX lets a city see a project's impact *before* it builds." |
| 0:25–0:55 | **2 Problem** | Three failures, fast: studies age; impacts judged in silos; the tools that could help need specialists. "No planner can ask a plain question and get a cross-domain answer." |
| 0:55–1:20 | **4 Landscape** *(skip 3 if tight)* | "Vissim, Replica, CityEngine, UrbanFootprint — each excellent, each one or two dimensions, each needs a specialist. Based on our survey, none does the *combination*: plain language + five dimensions in one run + per-dimension confidence." |
| 1:20–1:55 | **5 Solution + 6 Five dimensions** | "Drop a project on your city's simulator; in ~90 seconds, five scored dimensions, each with an explicit confidence interval — Behavioral, Social, Economic, Ecological, Societal — all from *one* simulated reality, so they never contradict each other." |
| 1:55–2:25 | **7 UVP** | "Three things only MATRIX does together: one kernel → five dimensions; a glass box where every number traces to its equation, data, and a computed confidence; and plain language to a 90-second answer." |
| 2:25–4:05 | **8 How it works → LIVE DEMO** | Show the pipeline, then **run the live demo** (script below). Narrate while it computes. |
| 4:05–4:30 | **9 Proof** | "This isn't a mockup — the kernel, all five modules, the streaming API, and this Deck.gl frontend run today, on 180 Iloilo barangays and 5,680 priced parcels. Our empirical validation gates are the *next* milestone — and we'll say so." |
| 4:30–5:00 | **14 Close / Ask** | "MATRIX lets ASEAN cities see the future before they build it — no hardware, deployable region-wide. We're asking to advance, and for a path to a real Iloilo pilot." |

> Slides **3 (Target Market), 10 (Value), 11 (BMC), 12 (GTM), 13 (Why us)** are spoken only if time allows or pulled up in Q&A. Slide **15 (Appendix)** is your Q&A defense — keep it one keypress away.

---

## The live-demo run-of-show (the 90-second moment)

**Before you present:** baseline pre-warmed, persona pool cached, app + API + datastores up, one tab on the scenario screen, network checked. Have the **recorded demo video** open in a second tab as fallback.

1. **Set up the question (≈10s).** "I'm an Iloilo planner. I'll ask: *add a 3-storey school in Mandurriao* — and watch five dimensions resolve." Type / drop the pin.
2. **Narrate the wait (≈45s).** As SUMO runs and the map animates: "Those are simulated commuters — jeepney, tricycle, private car, pedestrian — re-routing around the new trip generator. We're not replaying sensors; we're simulating a future that doesn't exist yet." Point at the animated TripsLayer.
3. **Results stream in (≈25s).** "Behavioral and Ecological land first — highest confidence. Now Social, Economic, Societal. Notice the ranges, and the confidence tag on each."
4. **The glass-box click (≈10s) — the closer.** Open **Inspect** on one number: "Here's the equation, the named open datasets, and the *computed* confidence. Nothing here is the LLM guessing — it narrates and cites; the kernel and equations own every number."
5. **If anything stalls:** cut to the recorded video without apology — "here's that same run from this morning" — and keep the cadence.

**Truth guardrails for the demo (do not overclaim):**
- The 90 s is a **warm-baseline, single-user target**; the current probe is ~123 s. If asked, say so and name the Phase-6 fix (libsumo / headless / lighter rerouting).
- Do **not** say "validated." Say the validation gates (Calderon RMSE, 2024 flood) are *planned for semi-final*.
- If a dimension shows "directional only," that's a feature — point to it as honesty, not weakness.

---

## Q&A prep (3 minutes) — anticipated questions

| Likely question | Crisp answer (pull up Appendix slide 15) |
|---|---|
| "How do you know the numbers are right?" | Glass box: every number → equation + datasets + computed confidence, resolvable in Inspect. Empirical back-tests (RMSE vs Calderon 2014; IoU vs the 2024 flood) are the next milestone — *not yet run*. |
| "Isn't fixed open data a weakness vs live IoT simulators?" | They answer "what *is* happening"; we answer "what *would* happen if you build X" — a counterfactual no sensor can answer. Fixed open data is what makes us deployable to any ASEAN city, and the confidence layer states exactly where we're sure. |
| "Can it really run in 90 seconds?" | That's the engineered target (warm baseline, single user) via pre-warmed personas + delta sims + parallel modules. Current warm run ~123 s; Phase-6 optimization closes it. We architected specifically for the budget. |
| "How does it scale beyond Iloilo?" | API-level (new OSM bbox) + prompt-level (reweight personas to local modes — ojek, angkot, tuk-tuk, xe-om). No hardware → cost is API tokens, not procurement. |
| "What about bias / the informal economy?" | The bias auditor anchors generated mode-share to ground truth (±3% or it reweights, logged publicly), and Social/Economic explicitly model informal vendor & driver displacement. |
| "Business model?" | Public-good free for LGUs/academia now; a paid private-developer/SaaS tier later — deliberately TBD. At hackathon stage the goal is adoption + credibility. |
| "Privacy / legal?" | No PII in the pipeline; open data under ODbL/PSA/ESA licenses with attribution; the optional PWA GPS-trace feature is gated behind a Privacy Impact Assessment + counsel (RA 10173). |

---

## Pre-flight checklist
- [ ] Baseline warm; persona pool cached; API + datastores + web all up.
- [ ] `scenario-playback.png` (+ optional `inspect-drawer.png`) in `assets/` (or placeholders accepted).
- [ ] Recorded demo video open in a backup tab.
- [ ] Deck exported to PDF (`scripts/export-pdf.mjs`) as a projector fallback.
- [ ] One sentence rehearsed for each honesty caveat (90 s target, validation planned).
