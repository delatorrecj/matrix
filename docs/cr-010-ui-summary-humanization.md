# CR-010 — Summary-First UI & Plain-Language Humanization

**Change Record ID:** CR-010
**Status:** **Applied** — Phase 1 (`f323e42`) + Phase 2 (`6c3351f`) merged to `main` & deployed to production (2026-06-24)
**Date opened:** 2026-06-24
**Owner:** Carlos (delatorrecj)

> **Implementation status (2026-06-24) — DONE; both phases live in production.**
> **Phase 1** (PR #30, merge `f323e42`): `lib/format.ts` + `lib/metrics.ts` number humanization (no false precision; near-zero → "No meaningful change"), plain-language Summary dock (`SummaryView`/`SummaryCard`) + a dedicated, *interpreted* `AnalyticsView`, nav-rail cleanup (logo→home, disabled-with-reason items, **AU avatar + dead Help removed**), and a minimal real Settings (`SettingsPanel` + `LanguageProvider`: theme + EN/Hiligaynon).
> **Phase 2** (PR #31, merge `6c3351f`): synthesis prompt rewritten to a plain-language **BLUF** brief (HEADLINE → WHAT WE SIMULATED → KEY FINDINGS → RECOMMENDATION → KEY RISK), **delimited bilingual** (`=== HILIGAYNON ===`, kernel `HILIGAYNON_MARKER` + web `lib/bilingual.ts`) consumed via the language toggle, a print-scoped one-page `ScenarioBrief` (with an EVIDENCE appendix), and a tightened citation guard (newline-split — strictly stronger). Local gates: kernel `pytest` 182p/11s, API 64p/4s, `next lint` + `tsc` clean; vitest + Playwright e2e + `next build` verified in CI.
> Both gating agents (`glass-box-auditor`, `eval-test-runner`) **PASS**; all CI green (kernel/api pytest, web vitest+build, Playwright e2e); both Vercel **production deploys succeeded**. The Locked docs `methods-matrix.md` §4/§4.3 + `prd-matrix.md` PRD-F7 were amended and **re-locked** with owner approval (`cc46b78`). Glass box (PRD-F14) preserved throughout: humanization is display-only; every number still resolves to its `equation_id` + datasets + computed confidence in Analytics/Inspect, and the LLM still originates no number.
**Trigger:** Live production QA of [matrix-atlan.vercel.app](https://matrix-atlan.vercel.app/) surfaced (a) dead/stub navigation controls, (b) false-precision raw-float numbers, and (c) a dense, jargon-heavy "brief". The product owner wants a **summary-first** results experience, full statistics moved behind a working **Analytics** tab, plain-language output instead of jargon/stats, and removal/repair of non-functional controls (Settings, the "AU" admin avatar).

> **North star:** a city planner should grasp *"does this intervention help or hurt, and by how much?"* in under 30 seconds — without reading an equation code or a 19-digit float. The glass box (PRD-F14) is **preserved, not deleted**: every humanized number still resolves to its `equation_id` + datasets + computed confidence one click away (Analytics tab / Inspect drawer).

---

## 1. Overview

This CR restructures the **web frontend** (`app/apps/web`) results experience into two progressive-disclosure levels — a plain-language **Summary** (default) and a full-statistics **Analytics** view — plus a presentation-layer number formatter, a plain-language label/confidence layer, a minimal real **Settings** panel (theme + language), and removal of the dead controls. It also revises the **kernel synthesis prompt** (`app/packages/kernel`) into a plain-language BLUF brief and adds a **dedicated brief generator** to replace the current `window.print()` dump.

Scope splits cleanly into **Phase 1 (frontend-only, no gates touched)** and **Phase 2 (kernel + Locked-doc changes, requires re-gating)**. See §8.

---

## 2. QA evidence (live, production — 2026-06-24)

Driven against the live Vercel deployment with the browser MCP; cross-checked against source. A full reference scenario ("School in Molo") was run (`/scenario/df5e6531-…`, completed in 28.7 s).

### 2.1 Dead / stub / inconsistent controls

| Control | Live behavior | Root cause (file:line) | Verdict |
|---|---|---|---|
| **Analytics** nav tab | Highlights as "active" but **no view appears** — on home *and* on the scenario page | `IconNavRail.tsx:16` defines it; click → `onNavigate("analytics")` (`:54`) has **no handler branch** in [page.tsx:153-158](app/apps/web/src/app/page.tsx) or [scenario/[id]/page.tsx:387-391](app/apps/web/src/app/scenario/[id]/page.tsx). No `/analytics` route exists. | **Stub — the owner's "can't click" complaint.** Wire it (WS-4). |
| **Trajectories** nav tab | No-op everywhere; forced active on scenario page yet inert | `IconNavRail.tsx:15`; no handler branch anywhere | **Dead.** Repurpose as the Summary/map view selector (WS-1/WS-4). |
| **Settings** gear | No-op; no settings UI exists at all | `IconNavRail.tsx:18`; no handler branch; no settings component | **Stub.** Build minimal Settings (WS-6). |
| **"AU" avatar** | No `onClick`, hardcoded text, no auth/user state on the web side | `IconNavRail.tsx:98-107` (tooltip "Admin User"); web has zero auth (`lib/api.ts:50` TODO only) | **Dead placeholder. Remove** (WS-6). |
| **Cube logo** | Decorative `<div>`, not clickable | `IconNavRail.tsx:82-86` | Make it link **Home** (WS-1). |
| **Home** nav tab | Works only from scenario page; no-op on home | `scenario/[id]/page.tsx:388-390` handles `home`; `page.tsx:153-158` does not | Inconsistent — centralize (WS-1). |
| **Layers** nav tab | Works on home (toggles legend); no-op on scenario page | `page.tsx:155-157` only | Inconsistent — make uniform (WS-1). |
| **Help** (`?`, top-right) | No `onClick` | `HeaderControls.tsx:25-30` | Stub — repurpose to a "How to read these results" explainer, or remove (WS-6). |
| **Download Brief** | Triggers `window.print()` of the *entire* results panel | `scenario/[id]/page.tsx:419-426` | Not a real brief — replace with a generated one-page brief (WS-5b). |

### 2.2 False-precision numbers (verbatim from the live run)

The `DIMENSION_RESULT` handler stringifies the raw float with **no rounding** — `value: … ? "+"+msg.value : String(msg.value)` ([scenario/[id]/page.tsx:300](app/apps/web/src/app/scenario/[id]/page.tsx)) — and the range is `` `${msg.range[0]}..${msg.range[1]}` `` (`:275-277`). `ResultCard.tsx:42,46` prints both verbatim. **There is no shared number formatter in `src/lib`.** Result:

- `Employment Δ: -0.7000000000000001 jobs`
- `Societal composite: -0.0069731280430000014` (unit `0-100`)
- `Health-exposure proxy: -0.026871957000000002 index`
- `Air-quality delta: -0.000004599 µg/m³`, `Transport CO₂e Δ: -0.00009198 ktCO₂e/yr`
- Ranges: `R: -0.96681056831497..-0.41654314880168575`
- Zeros render awkwardly: `0 %-points`, `R: 0..0` (mode-share, green-cover, flood-exposure)

### 2.3 Jargon dump

- **Equation codes leak into prose.** The synthesis narrative reads *"trips on the corridor decline by -14.00 **BEH-1**"*, *"-0.00 **ECO-1**"*, etc. — codes `BEH-1..3, ECO-1..4, SOC-1..3, ECON-1..3, SOCI-1..4` litter every sentence, and a `-0.00` reads as meaningless. Source: the kernel prompt **requires** `[EQN-ID]` after every number ([synthesis.py:47-49](app/packages/kernel/matrix_kernel/synthesis.py)); the citation guard strips claims that lack one ([synthesis.py:76](app/packages/kernel/matrix_kernel/synthesis.py)).
- **The "brief" *is* this whole panel.** `window.print()` prints the dense narrative, the bilingual persona block (Hiligaynon + parenthetical English, interleaved inline), **plus** the technical Validation panel (`normalized_rmse`, `length_weighted_iou`, `IoU over closed road segments`) and the Bias Audit log (`Reweight Triggered (±3% tol): NO`). None of that belongs in an executive brief.
- **Confidence is a bare letter** (`H`/`M`/`L`) with an icon; `ConfidenceChip.tsx:51` renders `level[0]` in compact mode.

### 2.4 What already works (do not regress)

Theme toggle (home only), reference-scenario presets, the live WebSocket run (`ACCEPTED → PLAYBACK_FRAME → DIMENSION_RESULT×17 → SYNTHESIS → DONE`), the Inspect drawer's two-stage glass-box reveal, the citation-chip → Inspect resolution, the structured scenario `/builder`, map layers (Trajectories/Congestion/Confidence/Flood), and the 90 s latency budget (28.7 s observed, warm baseline).

---

## 3. Decisions (resolved with owner, 2026-06-24)

1. **Brief humanization scope = options 2 + 3:** revise the **kernel synthesis prompt** into a plain-language BLUF brief (with a Hiligaynon **toggle**, not inline interleave) **and** build a **dedicated brief generator** — on top of the baseline display-layer humanization.
2. **Settings = keep a minimal real panel** (Theme + English/Hiligaynon language toggle); **remove the AU avatar.** The language toggle also drives the bilingual brief.
3. **Analytics target = a dedicated, full-screen, *interpreted* Analytics view** (revised 2026-06-24 per owner). The in-panel dock is **summary-only**; clicking the (now functional) Analytics nav icon opens a comprehensive view that shows the full statistics **and explains what they mean** (a plain-language "what this means" interpretation per dimension), not a raw stat dump. Implemented as a full-screen view within the `/scenario/[id]` route (state-driven, reading the already-streamed results — no re-run, no WS/map-pipeline refactor); a separate `/scenario/[id]/analytics` route backed by a shared run-state provider is a documented future enhancement.

---

## 4. Design principles (sourced)

Condensed from a best-practices sweep (Nielsen Norman Group; Shneiderman; GOV.UK / ONS content & numbers style; plainlanguage.gov / USWDS; UK Gov Analysis Function on uncertainty; BLUF/policy-brief literature). These are the rules each task implements.

- **Two disclosure levels, never three** (NN/g). Summary → Analytics/Inspect. The headline must stand alone; the recommendation and direction-of-effect must **not** sit behind a click.
- **"Overview first, zoom and filter, details on demand"** (Shneiderman) → Summary tab / Analytics tab / Inspect drawer.
- **Most important info first; plain words; short active sentences** (GOV.UK, plainlanguage.gov). Replace abstract verbs ("impact", "facilitate"). Address the reader.
- **Every number carries its meaning** ("so what"): `<change> → <what it means for the city/people>`.
- **2–3 significant figures, ≤2 decimals, leading zeros, signed deltas, explicit units, comma grouping** (GOV.UK/ONS, KPI guidance). *"518M beats 517,893,412."* Trailing decimals **reduce** lay trust.
- **Near-zero → language, not a tiny float**: below a per-metric "negligible band", render **"No meaningful change"**.
- **Ranges with "to"**, not hyphen; show the **range as the headline when confidence is Medium/Low**, a point estimate only at High.
- **Confidence spelled out** + plain tooltip; visually de-emphasize Low-confidence values; never color-only.
- **Brief = BLUF**: headline finding → purpose → 3–5 key findings → recommendation → key risk/caveat; one page; no methodology.
- **Bilingual: toggle/parallel, never inline-interleaved** (interleaving doubles density and destroys scannability).

(Full source list in the Appendix.)

---

## 5. Workstreams

Each task gives the concrete anchor and a **done-when**. Phase tags in §8.

### WS-1 — Navigation & dead-control cleanup  *(Phase 1)*

- **T1.1 Centralize nav semantics.** Replace the per-page inline `onNavigate` handlers ([page.tsx:153-158](app/apps/web/src/app/page.tsx), [scenario/[id]/page.tsx:387-391](app/apps/web/src/app/scenario/[id]/page.tsx)) with a single shared handler so behavior is identical across pages. Item → action: `home` → `router.push("/")`; `layers` → toggle legend; `trajectories` → select **Summary** tab; `analytics` → select **Analytics** tab (WS-4); `settings` → open Settings panel (WS-6).
- **T1.2 Disabled-with-reason for scenario-scoped items on Home.** On `/`, `trajectories`/`analytics` have no scenario to act on. Add a `disabled` + tooltip ("Run a scenario first") state to `IconNavRail` items rather than letting a click silently no-op. *(This is the honest fix for "feels unclickable".)* Anchor: `IconNavRail.tsx:47-73` (add `disabled?: boolean` to `NavItem`, render `aria-disabled`).
- **T1.3 Logo → Home.** Make the cube logo a `<button>`/link → `router.push("/")`. Anchor: `IconNavRail.tsx:82-86`.
- **T1.4 Active-state reflects the in-panel tab** on the scenario page (currently hardcoded `activeId="trajectories"`, `scenario/[id]/page.tsx:387`).
- **Done-when:** every rail control either performs a visible action or is visibly disabled with a reason; no silent no-ops; `aria-current`/`aria-disabled` correct.

### WS-2 — Number humanization (`src/lib/format.ts`)  *(Phase 1)*

- **T2.1 New `src/lib/format.ts`** (none exists today — only `cn()` in `lib/utils.ts`). Exports:
  - `formatMetricValue(value: number, metricKey: string): { display: string; isNegligible: boolean }` — applies the metric registry's precision/sig-figs, leading zero, signed delta (`+`/`−`), thousands grouping; returns `"No meaningful change"` when `|value|` is inside the metric's negligible band.
  - `formatRange([lo, hi]: [number, number], metricKey): string` → `"−0.97 to −0.42"` (em-dash minus, "to", same precision).
  - `formatConfidenceLabel(conf): "High" | "Medium" | "Low"` (reuse `toConfidenceLevel`).
- **T2.2 Metric registry** (`src/lib/metrics.ts`): one entry per equation id `{ equationId, humanLabel, unit, decimals|sigFigs, negligibleBand, polarity }`. **Derive labels/units/polarity from [methods-matrix.md](docs/methods-matrix.md) (Locked)** — these are presentation *aliases*, never redefinitions; do **not** invent metric semantics. Proposed labels in §6.
- **T2.3 Wire into the stream handler.** In `scenario/[id]/page.tsx:272-305`, format `value`/`range` through `format.ts` for **display**, but keep the **raw** `String(msg.value)` and raw range in `provData` (`:282-283`) so Inspect/Analytics retain full precision (glass box). `ResultCard.tsx:42,46` consumes the formatted strings on the Summary view.
- **Done-when:** no raw float artifact appears on the Summary view; `−0.7000000000000001 jobs` → `−0.7 jobs`; near-zero metrics read "No meaningful change"; Inspect/Analytics still show the exact raw number.

### WS-3 — Plain-language labels & confidence  *(Phase 1)*

- **T3.1 Human metric labels** on Summary cards via the WS-2 registry (e.g. `Employment Δ` → **"Change in local jobs"**, `Societal composite` → **"Overall wellbeing score"**). The raw metric name + `equation_id` stay visible in Analytics/Inspect.
- **T3.2 Dimension labels:** `behavioral`→"Travel & mobility", `ecological`→"Environment", `social`→"Community & access", `economic`→"Local economy", `societal`→"Equity & wellbeing". Anchor: wherever `DIMENSIONS` titles render (`DimensionResultGroup`).
- **T3.3 "So what" line** per Summary card: a neutral direction phrase keyed to polarity (`falls` / `rises` / `little change`; promote to `improves`/`worsens` only where the registry's polarity is known). Smallest text under the headline number.
- **T3.4 Confidence chip plain-language:** on Summary, render the **full word** + a plain tooltip ("Estimate — treat as directional", etc.), and de-emphasize Low. Keep the compact glyph for Analytics/dense contexts. Anchor: `ConfidenceChip.tsx:48-53` (the `compact` path).
- **Done-when:** Summary cards show a human label, a formatted number, a one-line meaning, and a spelled-out confidence; no equation code on the Summary surface.

### WS-4 — Summary dock + dedicated Analytics view  *(Phase 1)*

- **T4.1 `panelView` state** (`"summary" | "analytics"`) on the scenario page. The nav rail drives it (WS-1): `trajectories` → summary, `analytics` → analytics. The summary dock also carries a "View full analytics →" affordance.
- **T4.2 Summary dock (default, narrow):** a BLUF headline (the synthesis EXECUTIVE SUMMARY's lead, else a client-built one-liner), five **humanized** dimension `SummaryCard`s (human label + formatted headline number / "No meaningful change" + a "so what" line + spelled-out confidence), and the "View full analytics →" button. **No** equation codes, raw floats, ranges, bias log, or validation panel here. New `SummaryCard` + `SummaryView` components.
- **T4.3 Analytics view (full-screen, scrollable, *interpreted*):** per-dimension sections, each opening with a plain-language **"What this means"** interpretation, then the full detail — values + ranges, `equation_id` chips, the `SynthesisNarrative` with inline citations, `ValidationPanel` (`:479`) and `BiasAuditLog` (`:480`). Reuses `DimensionResultGroup`/`ResultCard` (now formatter-backed so even here there are no 19-digit floats; exact raw stays in Inspect). New `AnalyticsView` component; reads the already-streamed `results`/`synthesis` (no re-run).
- **T4.4 Inspect drawer** stays the per-number "details on demand" layer off both views (unchanged glass-box contract; optionally fix the structural oddity where the header `<div>` is never closed before the body, `InspectDrawer.tsx:159-330`).
- **Done-when:** the default scenario view is the plain-language summary dock; the functional Analytics nav icon opens a comprehensive, interpreted full-screen view; no raw floats/codes on the summary; every number still resolves in Inspect.

### WS-5 — Brief: kernel prompt rewrite + dedicated generator  *(Phase 2 — touches Locked docs + gates)*

- **T5.1 Rewrite the synthesis prompt** ([synthesis.py:38-50](app/packages/kernel/matrix_kernel/synthesis.py)) to a **BLUF** structure: `HEADLINE` (1–3 sentences, conclusion + call-to-action first) → `WHAT WE SIMULATED` (1 line) → `KEY FINDINGS` (3–5, plain sentences, lead with the insight then the number) → `RECOMMENDATION` (one paragraph, no hedging) → `KEY RISK / CONFIDENCE CAVEAT`. Enforce short active sentences, human-scaled framing, no methodology.
  - **Glass-box constraint:** **keep the inline `[EQN-ID]` citation contract** — `citation_guard.strip_uncited_claims` ([synthesis.py:76](app/packages/kernel/matrix_kernel/synthesis.py)) strips numeric claims that lack a valid bracket. The Summary renderer **de-emphasizes** codes (subtle superscript/ⓘ link); Analytics shows the full chip. Do **not** remove the bracket requirement from the prompt.
- **T5.2 Bilingual via delimiters, not interleave.** Have the model emit a clearly delimited `=== HILIGAYNON ===` block (not inline parentheticals). The web **language toggle** (WS-6) renders EN or HIL; the brief generator prints the selected language (with the other as an optional appendix).
- **T5.3 Update Locked docs:** [methods-matrix.md](docs/methods-matrix.md) §4 (synthesis) and PRD-F7 own this output — update them under this CR and **re-lock**.
- **T5.4 Dedicated brief generator** to replace `window.print()` of the whole panel (`scenario/[id]/page.tsx:419-426`). Render a **print-scoped** brief DOM (or `/scenario/[id]/brief` print route): headline → purpose → 3–5 findings (one plain sentence + headline number + confidence each) → recommendation → key risk → a compact **Evidence appendix** (equation ids + datasets, preserving traceability). Reuse `window.print()` as the PDF mechanism but scope the printed nodes to the brief only (drop Validation/Bias/map controls from print).
- **Done-when:** the generated brief is one page, plain-language, BLUF-ordered, single-language with an evidence appendix; **`glass-box-auditor` and `eval-test-runner` PASS** (citation guard + AI evals green); methods-matrix re-locked.

### WS-6 — Minimal Settings + theme/language  *(Phase 1; language consumption completes in Phase 2)*

- **T6.1 Settings panel** (drawer or popover) opened by the gear (`IconNavRail.tsx:18` handler). Contents: **Theme** (light/dark/system — reuse `ThemeProvider`, the existing toggle logic in `HeaderControls.tsx:12-22`) and **Language** (English / Hiligaynon).
- **T6.2 `LanguageProvider`/context** controlling narrative + brief language; consumed by `SynthesisNarrative` and the brief generator (T5.2). Until Phase 2 ships the delimited bilingual output, the toggle is wired but the HIL view falls back gracefully.
- **T6.3 Remove the AU avatar** (`IconNavRail.tsx:98-107`).
- **T6.4 Theme everywhere:** ensure a theme control is reachable on the scenario page too (the scenario page does not render `HeaderControls`) — Settings satisfies this.
- **T6.5 Help (`?`) decision:** repurpose `HeaderControls.tsx:25-30` to open a short "How to read these results" explainer (complements humanization), or remove it. Recommend repurpose.
- **Done-when:** Settings opens a working panel; theme + language are changeable on every page; AU avatar gone; no dead controls remain in the rail/header.

---

## 6. Proposed label registry (verify against methods-matrix before coding)

Presentation aliases only. **Polarity** = does a positive Δ read as better (+) or worse (−) for the city, used by the WS-3 "so what" line.

| eq id | raw metric | human label | unit | polarity |
|---|---|---|---|---|
| BEH-1 | Δ trips on affected corridor (AM-peak) | Trips on the affected road (morning rush) | trips/window | context |
| BEH-2 | mode-share shift (jeepney) | Shift to/from jeepney travel | %-points | + |
| BEH-3 | peak saturation V/C | How full the road gets at peak | ratio | − |
| ECO-1 | Transport CO₂e Δ | Change in transport carbon emissions | ktCO₂e/yr | − |
| ECO-2 | Air-quality delta | Change in air pollution | µg/m³ | − |
| ECO-3 | Green-cover loss | Green space lost | hectares | − |
| ECO-4 | Flood-exposure Δ | People exposed to flooding | persons | − |
| SOC-1 | Equity-weighted access | Fair access to services | index | + |
| SOC-2 | Displacement risk count | People at risk of displacement | count | − |
| SOC-3 | Distributional split (low-income) | Impact on low-income residents | per-decile | + |
| ECON-1 | Land-value Δ (≤1 km) | Nearby land-value change | PHP | context |
| ECON-2 | Footfall Δ per zone | Foot traffic for local businesses | visits/day | + |
| ECON-3 | Employment Δ | Local jobs | jobs | + |
| SOCI-1 | Societal composite | Overall wellbeing score | 0–100 | + |
| SOCI-2 | Heritage proximity | Effect on heritage sites | score | context |
| SOCI-3 | Health-exposure proxy | Health-risk exposure | index | − |
| SOCI-4 | Walkability Δ | Walkability | score | + |

> "context" = direction isn't inherently good/bad (e.g. land value up helps owners, hurts renters) → render neutral wording, never "improves/worsens".

---

## 7. Glass-box guardrails (must-not-break — PRD-F14)

1. Every number on the **Summary** view resolves to its exact raw value + `equation_id` + datasets + computed confidence in **Analytics/Inspect** (≤2 clicks). Humanization is **display-only**; the data model keeps full precision.
2. **"No meaningful change" never hides data** — the precise value remains visible in Analytics/Inspect. It is a summary label, not a deletion.
3. The LLM still **never originates a number** and still **cites every numeric claim** ([synthesis.py:47-49,76](app/packages/kernel/matrix_kernel/synthesis.py)). The prompt rewrite changes prose, not the citation contract.
4. Confidence labels stay **computed**, never guessed (`toConfidenceLevel` keeps the honest Low default, `ConfidenceChip.tsx:11-15`).
5. The **bias auditor** and **validation panel** survive in Analytics — moved, not removed.

---

## 8. Phasing & sequencing

**Phase 1 — frontend-only, ships fast, no gate/Locked-doc changes** (WS-1, WS-2, WS-3, WS-4, WS-6 except language consumption). Order: WS-2 (formatter) → WS-3 (labels/confidence) → WS-4 (tab split) → WS-1 (nav) → WS-6 (settings). This alone resolves the false-precision, jargon-on-summary, dead-control, and Analytics-tab complaints.

**Phase 2 — kernel + Locked docs + gates** (WS-5, plus WS-6 language consumption). Requires `methods-matrix.md`/PRD updates, `glass-box-auditor` **PASS**, `eval-test-runner` **PASS** before merge.

---

## 9. Testing & gates

- **Frontend:** `next build` clean + `next lint`; update Playwright e2e ([happy-paths.spec.ts](app/apps/web/tests/e2e/happy-paths.spec.ts)) for the new `Summary|Analytics` toggle, removed Settings/AU/Help controls, the formatter output, and the new brief; add unit tests for `format.ts` (sig-figs, negligible band, signed deltas, ranges) and the metric registry. *(vitest is flaky on Windows/node22 — run `next build` + Playwright as the authoritative gate; see [matrix-ci-playwright-e2e](memory).)*
- **Kernel (Phase 2):** `eval-test-runner` over the AI-eval + citation-guard suites; `glass-box-auditor` must verify every brief number still traces. Re-lock `methods-matrix.md`.
- **Non-regression:** 90 s end-to-end budget; live WS event order; Inspect resolution; bias auditor + validation still render (in Analytics).
- **DSD compliance** pass for new components (tabs, Settings panel, formatter output): density, a11y self-check, motion budget (per the open CR-009 task).

## 10. Definition of Done

- [x] Summary view is the default; plain-language cards (human label + formatted number + "so what" + spelled-out confidence); zero equation codes/raw floats on Summary.
- [x] Summary dock + dedicated Analytics view; Analytics holds full stats + codes + ranges + bias + validation; Analytics rail icon works (no silent no-op anywhere).
- [x] `src/lib/format.ts` + metric registry land with unit tests; near-zero → "No meaningful change"; Inspect/Analytics keep raw precision.
- [x] AU avatar removed; minimal Settings (theme + language) works on every page; no dead rail/header controls remain.
- [x] Phase 2: synthesis prompt is BLUF plain-language with delimited bilingual; dedicated brief generator replaces panel-print; `glass-box-auditor` + `eval-test-runner` PASS; `methods-matrix.md` re-locked.
- [x] Playwright e2e + `next build` green (CI). *(Formal DSD-compliance audit of the new components is recommended as a follow-up — not blocking.)*
- [x] Change Log in [docs/index.md](docs/index.md) entry added and marked **Applied** (CR-010 reconcile, 2026-06-24).

## 11. Risks & open questions

- **Synthesis-prompt change ↔ citation guard.** Keeping the `[EQN-ID]` bracket contract is mandatory; only prose/structure changes. Mitigation: re-gate before merge.
- **Polarity wording could mislead.** Verify each metric's polarity against `methods-matrix.md`; default to neutral direction words when unsure.
- **Negligible-band thresholds** must be justified per metric so real signal isn't summarized away (data still in Analytics). Document each epsilon with rationale.
- **Label aliases vs Locked methods.** Aliases are presentation-only — but confirm they don't contradict the canonical metric definitions.
- **Open (future, not this CR):** the Analytics tab v1 reuses today's stat cards + ranges + bias + validation; richer *charts/timeseries* ("true analytics") are deferred to a follow-up.

---

## Appendix — sources

- Progressive Disclosure; Dashboards — Nielsen Norman Group (nngroup.com)
- Visual Information-Seeking Mantra — Shneiderman (infovis-wiki.net)
- A-to-Z style guide; Content design — GOV.UK; Numbers — ONS service manual
- Plain language guide — digital.gov / plainlanguage.gov; Design principles — USWDS
- Communicating quality, uncertainty and change — UK Government Analysis Function
- Data storytelling — HBS Online; BLUF writing format — Univ. of Illinois; policy-brief elements — Centre College

*(QA performed live against [matrix-atlan.vercel.app](https://matrix-atlan.vercel.app/) and cross-checked against `app/apps/web` + `app/packages/kernel` source on 2026-06-24.)*
