# MATRIX — Grand Finals Demo Script

**Primary:** 20–30 second recorded video  
**Fallback:** Live app ([https://matrix-atlan.vercel.app/](https://matrix-atlan.vercel.app/) or local pre-warmed stack)  
**Story shape:** Scenario → Simulation → Consequence → Decision  
**Claims:** [`CLAIMS.md`](CLAIMS.md) · Spoken wrapper: [`PITCH_SCRIPT.md`](PITCH_SCRIPT.md) Beat 4

---

## One story (default)

**Role:** Iloilo city planner  
**Question:** *Add a 3-storey school in Mandurriao — what happens to the city around it?*  
**Why this story:** Proven demo path from [`../walkthrough.md`](../walkthrough.md); trip-generator impact is visible on playback; five dimensions have something real to say.

Do **not** turn this into a feature tour (settings, layers menu, every dimension card).

---

## 20–30 second video cut

| Time | Picture | Voice (sparse) |
|------|---------|----------------|
| 0:00–0:05 | Map / scenario entry — pin or NL for Mandurriao school | “One decision.” |
| 0:05–0:18 | Playback — TripsLayer agents re-routing | “A future that doesn’t exist yet — simulated.” |
| 0:18–0:25 | Summary / dimension results streaming — ranges + confidence tags visible | “Who moves. Who is exposed. What changes.” |
| 0:25–0:30 | Inspect open on one number (equation + datasets + confidence) **or** BLUF brief | “Not a guess — a traceable answer.” |

**Total VO:** ≤ ~40 words. Silence is fine while the map moves.

### Alternate last frame (if Inspect is hard to film cleanly)

Hold on Summary card + confidence tags with lower-third: *Glass-box · computed confidence · LLM narrates only*

---

## Live fallback (if video fails)

**Pre-flight (before walking on stage):**

- [ ] Baseline warm; persona pool cached  
- [ ] Web + API healthy; network checked  
- [ ] Scenario screen open; cursor ready  
- [ ] Recorded video still one keypress away  
- [ ] One Inspect target rehearsed (dimension with High/Medium confidence preferred)

**Live cadence (~60–90s max if replacing video — compress if finals clock is tight):**

1. **10s — Scenario.** “I’m an Iloilo planner. Three-storey school in Mandurriao.” Submit.  
2. **30–45s — Simulation.** Point at agents: “Commuters re-routing — jeepney, tricycle, car, walk. We’re not replaying sensors; we’re simulating a future.” `(PROVEN)` / counterfactual framing  
3. **15–20s — Consequence.** Dimensions land; point at ranges + confidence. If “directional only,” name it as honesty.  
4. **10s — Decision / Inspect.** Open Inspect: equation, datasets, computed confidence. “AI narrates. It does not invent the number.” `(PROVEN)`

If the run stalls: cut to recorded video without apology — “same run, recorded this morning.”

---

## Truth guardrails (demo narration)

| Say | Don’t say |
|-----|-----------|
| “Simulated future / counterfactual” | “Real-time city twin feed” |
| “Architected for a fast answer / ~90 s target” `(LIMIT)` | “Always under 90 seconds” (unless measured live today) |
| “Validation gates are built; Behavioral headline withheld pending calibration” | “Validated” / published RMSE |
| “Directional only” as a feature when it appears | Apologize for confidence tags |
| Feature-survey combo if asked | “No tool in ASEAN does this” |

---

## Audio / picture notes for editors

- Prefer map motion over talking-head for the 20–30s cut.  
- Burn in lower-thirds sparingly: scenario question; then “Inspect” on the final beat.  
- No stock “AI brain” B-roll. Real product UI only.  
- Export 1080p; keep a silent cut in case stage VO covers it live.

---

## Done-when

- [ ] A stranger understands MATRIX from the clip without a feature list.  
- [ ] Story is one decision, not five modules explained.  
- [ ] Final frame is consequence or provenance — not a logo splash.  
- [ ] Narration passes `CLAIMS.md` hard bans.
