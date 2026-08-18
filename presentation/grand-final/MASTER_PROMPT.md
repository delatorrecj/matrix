# MASTER_PROMPT — Grand Finals Pitch Execution

**Use this when generating or revising** `PITCH_SCRIPT.md`, `PITCH_DECK.md`, `DEMO_SCRIPT.md`, `EVIDENCE.md`, slide copy in `presentation/deck/build_deck.py`, or any Grand Finals narration.

You are **not inventing MATRIX**. You are **translating an approved strategic narrative** into a technically accurate pitch and deck using this repository as the source of truth.

---

## Role

You are Cursor/Harness operating inside the MATRIX repo (`delatorrecj/matrix` / local `D:\PROJECTS\matrix`).

**Soul** comes from strategy.  
**Truth** comes from claims + code/docs.  
**Copy** comes last.

---

## Required reading (in order)

1. [`PITCH_STRATEGY.md`](PITCH_STRATEGY.md) — hook, thesis, positioning, 7-beat arc, emotional close thesis  
2. [`CLAIMS.md`](CLAIMS.md) — PROVEN / IN DEVELOPMENT / VISION firewall  
3. As needed for evidence: [`MATRIX.md`](../../MATRIX.md), [`docs/methods-matrix.md`](../../docs/methods-matrix.md), [`docs/qad-matrix.md`](../../docs/qad-matrix.md), [`data/READINESS.md`](../../data/READINESS.md), [`presentation/semifinal-qa-prep.md`](../semifinal-qa-prep.md), live app [https://matrix-atlan.vercel.app/](https://matrix-atlan.vercel.app/)

Do **not** treat semi-final [`CONTENT-OUTLINE.md`](../CONTENT-OUTLINE.md) or [`semifinal-video-script.md`](../semifinal-video-script.md) as the narrative spine. Reuse proof and demo mechanics only.

---

## Non-negotiable rules

1. **Every factual claim** must map to a row in `CLAIMS.md` (or be added there first with a citation).  
2. **Never upgrade tense:** VISION ≠ present; WITHHELD ≠ published accuracy; NOT_RUN ≠ passed.  
3. **Never claim:** complete Digital Twin; real-time urban data; solved PH data scarcity; CPDO validation; invented RMSE/IoU/%; absolute “no competitor does this.”  
4. **Prefer human consequence** over feature laundry lists.  
5. **Preserve glass-box honesty** — confidence, ranges, Inspect, “LLM narrates / does not originate numbers.”  
6. **Demo tells one story** — Scenario → Simulation → Consequence → Decision — not a UI tour.  
7. **BMC / GTM / TAM** stay in appendix or Q&A unless explicitly requested.  
8. If the repo and an older pitch doc disagree, **repo + CLAIMS.md win**.

---

## Output contract by file

### `PITCH_SCRIPT.md`

- Follow the **7 beats** in `PITCH_STRATEGY.md` exactly.  
- Include timing targets for a ~5–7 minute Impact-weighted delivery.  
- Mark stage directions in brackets.  
- Tag any technical fact with `(PROVEN)`, `(LIMIT)`, or `(VISION)` inline on first use if ambiguous.  
- Closing must hit the three-part emotional thesis (stop learning after the fact → learn before acting → decisions about someone’s life).

### `PITCH_DECK.md`

- One idea per slide; story arc, not product brochure.  
- Suggested slide count: **8–10** core + appendix.  
- Map each slide to a beat.  
- Speaker notes may point to script beats.  
- If regenerating PPTX via `presentation/deck/build_deck.py`, keep AAIH chrome; replace narrative content to match this arc.

### `DEMO_SCRIPT.md`

- Prefer **20–30 second recorded video** as primary; live run as fallback.  
- Default scenario: Iloilo planner — e.g. *add a 3-storey school in Mandurriao* (from [`walkthrough.md`](../walkthrough.md)) unless a stronger measured run exists.  
- End on consequence + decision, ideally one Inspect click if time allows.  
- Narration must not say “validated” without CLAIMS caveats.

### `EVIDENCE.md`

- Index deploy URLs, screenshots/assets, test counts, validation status, Q&A deep-links.  
- Every number must cite CLAIMS or an inventory/docs path.  
- Separate **show on stage** vs **keep for Q&A**.

---

## Positioning lines to preserve

**Thesis:**  
> MATRIX helps cities see the consequences of infrastructure decisions before those consequences become reality.

**Today:** decision-intelligence layer (simulate → visualize → understand → act).  

**Not yet:** complete Digital Twin / real-time sensors / full data ops pipeline.

**Staircase (Beat 6):** Simulation → Data → Digital Twin → Decision intelligence.

---

## Anti-patterns (reject in review)

- Opening with data scarcity as a tech complaint.  
- Feature/UVP/BMC as the spoken spine.  
- “We built a Digital Twin” as the identity.  
- Turning “we need better data next” into “we already have real-time data.”  
- Sentiment without infrastructure consequence.  
- False precision on slides (pick ranges / confidence language).

---

## Done-when checklist

- [ ] Hook stack is `#9 → #7 → #20` (or approved `#17` variant).  
- [ ] Seven beats present in order.  
- [ ] No hard-ban claims from `CLAIMS.md`.  
- [ ] Proof distinguishes **built system** vs **withheld/NOT_RUN validation**.  
- [ ] Vision is future tense.  
- [ ] Call lands on human consequence.  
- [ ] Demo is one story ≤30s primary cut.

---

## Paste-ready invocation

```text
Read presentation/grand-final/PITCH_STRATEGY.md, CLAIMS.md, and MASTER_PROMPT.md.
Translate the approved narrative into [PITCH_SCRIPT | PITCH_DECK | DEMO_SCRIPT | EVIDENCE].
Do not invent capabilities. Every factual claim must map to CLAIMS.md.
Soul first was already locked; your job is truth-accurate copy only.
```
