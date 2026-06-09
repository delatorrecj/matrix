# Design System Document (DSD)

**System Name:** MATRIX Foundation
**Date:** 2026-06-02
**Version:** 0.1
**Owner:** Carlos Jerico Dela Torre (Team ATLAN)
**Status:** Active
**Last reconciled:** 2026-06-07 — reconciled with Next.js 14 + Tailwind v4 implementation.
**PRD:** [prd-matrix.md](prd-matrix.md)

> **Design read (taste-skill §0):** *Reading this as a **trust-first, data-dense decision instrument** for government + technical planners — not a marketing site. Dials: VARIANCE 3 (coherent, austere), MOTION 4 (the agent playback is the only motion that matters), DENSITY 7 (a cockpit). Foundation: shadcn/ui + Radix primitives on the locked Next.js 14 / Tailwind stack; Geist + Geist Mono; one cobalt accent; light-first (planners use daylight/projectors). The taste-skill's landing-page rules apply to the **marketing/pitch site**, not this app.*
>
> **Glass-box is a design requirement, not just a backend one** (`PRD-F14`): every number on screen is clickable to its equation, data, and confidence (§12). The taste-skill rule "never fake engineering precision" and MATRIX's glass-box mandate are the same rule.

---

## 1. Design Philosophy & Vision

**Core aesthetic:** Instrument-grade and calm. The **map and the agents are the hero**; chrome recedes. Honest data visualization over decoration — this is a tool a city office stakes a decision on, not a demo that dazzles.

**Emotional intent:** A planner feels **in control and never asked to trust a number they can't interrogate.** Confidence is always visible; uncertainty is shown, not hidden.

**Aesthetic references:** Linear (clean density), Observable / Datawrapper (honest charts), kepler.gl & Mapbox Studio (geospatial), Bloomberg-terminal restraint (density without chaos).

**What this system explicitly avoids:**
- AI-purple gradients / glassmorphism-for-its-own-sake.
- Decorative or looping motion (motion must communicate state — §5).
- **Fake-precise numbers with no provenance** (banned — every figure traces, §12).
- Dark-mode-only (light is the default; planners present in daylight).
- Three-equal-feature-card slop; hue-only encodings that fail color-blind users.

---

## 2. Brand Primitives

### Colors (light-first; dark is a lock-once theme variant)

| Token | Value | Usage |
|-------|-------|-------|
| `--color-bg` | `#FAFAFA` | Page background |
| `--color-surface` | `#FFFFFF` | Cards, panels |
| `--color-border` | `#E4E4E7` | Dividers, input borders |
| `--color-primary` | `#1D4ED8` | CTAs, active (cobalt — the one accent) |
| `--color-primary-hover` | `#1E40AF` | Hover |
| `--color-text` | `#18181B` | Body copy |
| `--color-text-muted` | `#71717A` | Secondary text, labels |
| `--color-success` | `#15803D` | Confirmations |
| `--color-warning` | `#B45309` | Caution |
| `--color-error` | `#B91C1C` | Errors / destructive |

**Five-dimension categorical palette** (stable across map layers + panels; **always paired with a unique icon + label** so it never relies on hue alone):

| Dimension | Hue | Icon |
|---|---|---|
| Behavioral | `#2563EB` blue | route |
| Social | `#DB2777` rose | users |
| Economic | `#CA8A04` amber | coins |
| Ecological | `#16A34A` green | leaf |
| Societal | `#9333EA` violet | landmark |

**Confidence is a separate visual channel** (composes with the hues above — never a hue): **High** = 100% opacity, solid chip; **Medium** = ~70% + hatch; **Low** = ~40% + dashed "directional only" + warning glyph.

### Typography

| Role | Font | Weight | Size | Line Height |
|------|------|--------|------|-------------|
| Heading 1 | Geist | 600 | 30px | 1.15 |
| Heading 2 | Geist | 600 | 22px | 1.2 |
| Heading 3 | Geist | 500 | 17px | 1.3 |
| Body | Geist | 400 | 14px | 1.5 |
| Small / Caption | Geist | 400 | 12px | 1.4 |
| **Numbers / Metrics / Code** | **Geist Mono** | 450 | 13–14px | 1.4 |

**Tabular figures:** every metric, score, range, and coordinate renders in **Geist Mono with `font-variant-numeric: tabular-nums`** so numbers align and read unmistakably as data. **Font loading:** `next/font` (self-hosted, `font-display: swap`).

### Elevation
`--shadow-sm` `0 1px 2px rgb(24 24 27 / 0.06)` (inline) · `--shadow-md` `0 4px 12px rgb(24 24 27 / 0.08)` (panels/drawers) · `--shadow-lg` `0 12px 32px rgb(24 24 27 / 0.12)` (modals). Shadows tinted to the neutral, never pure black.

---

## 3. Layout & Spatial System

**Base unit:** `4px`. Scale: `--space-1..12` = 4/8/12/16/24/32/48px.

**App shell:** **map-dominant.** The 3D simulator fills the viewport; a left **scenario rail**, a right **impact panel** (dockable/collapsible), and a bottom **timeline/playback** bar overlay it. Chrome is ≤ 72px nav. Panels use `--shadow-md` over the map.

**Grid (panels/forms):** 12-col, 24px gutters, content `max-w-[1400px]`. **Breakpoints:** `sm 640 · md 768 · lg 1024 · xl 1280 · 2xl 1536`. **Desktop-first** (planning workstations); fully responsive; the **PWA companion is a separate mobile-first surface**. Full-height uses `min-h-[100dvh]` (never `h-screen`).

---

## 4. Core Component Specs

**Buttons** — radius `6px`, padding `10px 16px`, weight 500/14px. Primary (cobalt/white), Secondary (outline), Ghost, Destructive. `:active` → `translate-y-[1px]`. Every CTA passes WCAG AA contrast; labels ≤ 3 words, one line.

**Inputs/Forms** — label **above**, helper present, error **below**; border `1px --color-border`, radius `6px`, focus ring `2px --color-primary offset 2px`. No placeholder-as-label.

**Surfaces** — `--color-surface`, `1px --color-border`, radius `8px`. One radius scale page-wide (shape lock).

**Signature custom components:**
- **Dimension Card** — hue bar + icon + label, big mono score, range, **confidence chip**, sparkline, **Inspect** affordance (§12).
- **Confidence Chip** — H/M/L per the confidence channel above.
- **Inspect Drawer** — the glass-box panel (§12).
- **Scenario Bar** — NL input + map-draw tools (point/polygon).
- **Layer Legend & Toggles** — per-dimension + confidence + hazard layers.
- **Timeline Scrubber** — playback control for agent trajectories.
- **Comparison/Ranking** — slider (baseline↔scenario) + A/B/C rank table (`PRD-F16`).
- **Equity Chart** — distributional bars by decile/barangay (`PRD-F17`).
- **Audit Log Table** — mode-share vs ground truth (`PRD-F6`).

All interactive components define **empty / loading (skeleton) / streaming / error / success** states — never just the happy path.

---

## 5. Motion & Micro-interactions

**Default transition:** `150ms ease-in-out`. Button `120ms`; drawer/modal open `200ms` ease-out (fade + slight translate), close `150ms`; layer toggle `180ms`.

**The agent playback is the one substantive motion** — it communicates the simulation, so it earns its place. Everything else is restrained. **No looping decorative animation.** All non-essential motion wrapped in `@media (prefers-reduced-motion: reduce)`; the map exposes a static "final-state" frame when reduced motion is set. *Motion claimed = motion shown* (MOTION dial 4: entry fades on panels + the playback; nothing more).

---

## 6. Accessibility (a11y)

- WCAG **AA**: 4.5:1 text, 3:1 UI. Audit every dimension hue against surface.
- **Never hue-alone:** each dimension carries an icon + text label; confidence carries a glyph + pattern. Verified against deuteranopia/protanopia.
- **Map has an accessible fallback:** every map result is also available as a **semantic data table** (keyboard-navigable) — this serves both a11y *and* the glass-box ethos (the numbers are inspectable without the canvas).
- Focus always visible; touch targets ≥ 44×44px; keyboard-operable everything; semantic HTML first, ARIA only where needed.

---

## 7. Taste-Skill Settings

```
DESIGN_VARIANCE:    3   (coherent, instrument-grade; not expressive)
MOTION_INTENSITY:   4   (playback + subtle entry only)
VISUAL_DENSITY:     7   (cockpit — five dimensions + map + controls)
```

**Chosen variant:** `output-skill` / `minimalist-skill` lineage — **not** `taste-skill` (which targets landing pages). **Reason:** MATRIX's core is multi-step, data-dense product UI; the taste-skill's *discipline* (real design system, anti-defaults, a11y, no fake precision) applies, but its landing-page layout rules do not. Use the full `taste-skill` ruleset for the **separate marketing/pitch site** only.

---

## 8. Impeccable Anti-Pattern Register

*Seeded 2026-06-09 (CR-005) with **watch-items** to verify on the first `impeccable detect src/` run against the now-built `apps/web`. Status `to-check` = a candidate pattern derived from a DSD/PRD rule, **not yet a confirmed detection** — do not report as found until the scan or a manual review confirms it. Becomes a running log.*

| Pattern | Status | Location | Fix |
|---|---|---|---|
| Confidence rendered with the same visual weight/channel as the 5-dimension palette (must be a **separate** channel — opacity/pattern, PRD-F5) | to-check | scenario results panel; map overlays | give confidence its own non-color channel; never let it read as a 6th category |
| A rendered number with **no working Inspect** affordance (PRD-F14 / TRACE-02) | to-check | dimension result cards, synthesis narrative | every metric opens `InspectDrawer` to equation + datasets + confidence |
| Metric values not using `next/font` **tabular-nums** (numbers jitter on update) | to-check | dimension cards, timeline scrubber | apply tabular-nums to all numeric displays |
| Motion without a `prefers-reduced-motion` guard | to-check | TripsLayer playback, result enter animations | gate all non-essential motion on the reduced-motion query |
| **False-precision point estimates** shown instead of confidence-anchored ranges | to-check | economic / societal result cards | render ranges (e.g. "−₱8M to −₱14M"), never a single false-precise number |

---

## 9. 3D Simulator & Map Visualization *(the simulator surface)*

**Stack:** Mapbox GL JS basemap (muted "planner" style) + **Deck.gl** overlay (locked in MATRIX.md §5). Layers, bottom→top:

| Layer | Deck.gl type | Source | Notes |
|---|---|---|---|
| Basemap | Mapbox style | Mapbox | low-saturation; map is context, not decoration |
| Terrain | `TerrainLayer` | **DEM** (GLO-30 / PhilLiDAR) | real elevation for gradients + flood realism |
| **3D buildings** | `PolygonLayer` (extruded) | **Overture 148,630 footprints** (height attr) | proposed project highlighted in cobalt; heights are **real** (Overture attr) or flagged "estimated" |
| **Agents (playback)** | `TripsLayer` | trajectory dataset | animated per-tick movement = `PRD-F4` |
| Impact heatmap | `HexagonLayer` / `HeatmapLayer` | per-dimension scores | toggleable per dimension; uses the categorical hue |
| **Confidence layer** | translucent fringe | `dimension_results.confidence` | shows where data is weak (`PRD-F5`) |
| Hazard overlay | `GeoJsonLayer` | NOAH / LiPAD flood | for resilience scenarios (`PRD-F19`) |

**Camera:** default 2.5D pitch (~45°) with a top-down toggle; smooth `flyTo` on scenario load (motivated motion). **Performance:** the 90 s budget governs — tile/aggregate the 148k buildings (LOD), GPU layers, progressive layer reveal as modules stream. **Glass-box in 3D:** clicking any building, agent cohort, or impact cell opens the **Inspect drawer** (§12) with that element's provenance. **Honesty:** 3D is for *legibility*, not spectacle — extrusion height encodes real data or is explicitly marked estimated; no decorative 3D.

---

## 10. Interface Inventory *(all surfaces)*

| Surface | Key components | States |
|---|---|---|
| **Scenario Query** | NL input, map-draw (point/polygon), reference-scenario picker | empty / typing / parsing / error |
| **Map Stage** (§9) | 3D simulator, layer legend+toggles, timeline scrubber, playback controls, camera toggle | loading / streaming / playing / error |
| **Impact Panel** | 5 Dimension Cards (score · range · confidence · sparkline · Inspect) | per-dimension streaming / complete / directional-only |
| **Inspect Drawer** (§12) | equation, inputs→datasets, assumptions, confidence basis, references, sensitivity mini-chart | loading / loaded |
| **Comparison / Ranking** | baseline↔scenario slider; A/B/C alternatives rank table (`PRD-F16`) | one / compare / ranked |
| **Equity View** | distributional bars by income decile & barangay (`PRD-F17`) | empty / populated |
| **Validation Panel** | Calderon RMSE, 2024-flood back-test (`PRD-F18`) | pending / passed / failed |
| **Bias Audit Log** | mode-share vs ground-truth table, reweight events (`PRD-F6`) | empty / populated |
| **Report Export** | PDF preview with all dims + confidence + sources (`PRD-F7`) | idle / generating / ready / error |
| **Scenario Library** | saved + reference scenarios | empty / list |
| **PWA Companion** *(separate, mobile-first)* | trace consent, GPS upload (`PRD-F10`) | consent / collecting / synced |

---

## 11. Route & Action Map *(the consolidated "everything you can do")*

> **Where this lives:** here in the DSD (front-of-system) — it is the canonical map of **frontend routes + user actions**. Backend/API routes live in [sdd-matrix.md](sdd-matrix.md) §4; this table names the API each action calls so the two stay in sync.

### 11.1 Frontend routes (Next.js App Router)

| Route | Surface | Purpose | Calls (SDD §4) |
|---|---|---|---|
| `/` | Scenario Query + Map | define & launch a scenario | `POST /scenario` |
| `/scenario/[id]` | Map Stage + Impact Panel | watch playback, read 5-dim results | `WS /simulate/[id]`, `GET /runs/[id]` |
| `/scenario/[id]/compare` | Comparison / Ranking | baseline↔scenario, rank alternatives | `GET /runs/[id]`, `GET /baseline` |
| `/scenario/[id]/equity` | Equity View | distributional winners/losers | `GET /runs/[id]` |
| `/scenario/[id]/report` | Report Export | generate/download PDF | `POST /report/[id]` |
| `/audit/[runId]` | Bias Audit Log (public) | fairness transparency | `GET /audit/[runId]` |
| `/validation` | Validation Panel | model-vs-reality checks | `GET /validation` |
| `/library` | Scenario Library | reference + saved scenarios | `GET /scenarios` |
| `/contribute` *(PWA)* | trace consent/upload | opt-in behavioral data | `POST /traces` |

*The Inspect drawer (§12) is an overlay on any route, not a separate page; deep-linkable as `?inspect=<metricId>`.*

### 11.2 Action catalog

| Action | Trigger | Effect | API / WS | Glass-box / confirm |
|---|---|---|---|---|
| Submit NL query | Scenario Bar | parse → plan | `POST /scenario` | unparseable → clarification prompt |
| Drop / draw project | map tools | set geometry | (client) → `POST /scenario` | — |
| Run simulation | "Simulate" | stream playback + dims | `WS /simulate/[id]` | progressive; cancellable |
| Play / pause / scrub | timeline | control playback | (client) | — |
| Toggle layer / dimension | legend | show/hide overlay | (client) | confidence layer always available |
| **Inspect a number** | click any metric/element | open provenance drawer | `GET /runs/[id]` (provenance) | **the glass-box action (§12)** |
| Compare baseline↔scenario | slider | sync map + deltas | `GET /baseline` | — |
| Add / rank alternatives | "Add option" | A/B/C ranking | `POST /scenario` ×N | — |
| View equity | tab | distributional chart | `GET /runs/[id]` | — |
| View bias audit | link/footer | open audit log | `GET /audit/[runId]` | public, read-only |
| Export report | "Export" | render PDF | `POST /report/[id]` | includes sources + confidence |
| Pick reference scenario | Library | load canned run | `GET /scenarios` | fast-path for demo |
| Opt-in trace (PWA) | consent | collect/upload GPS | `POST /traces` | explicit consent; anonymized (RA 10173) |

---

## 12. Glass-Box "Inspect" Pattern *(the signature interaction — `PRD-F14`)*

The interaction that makes MATRIX not-a-black-box. **Every number is a button.** Clicking it (or any map element) opens the **Inspect Drawer**, which renders, straight from [methods-matrix.md](methods-matrix.md) + the run's provenance record:

1. **Value + range** (mono, tabular) and the **confidence chip** with *why* (the rubric factors that set H/M/L).
2. **The equation** (e.g. `ECO-1: ΔCO₂e = Σ_k VKT_k·EF_k`) rendered legibly.
3. **Inputs** — each links to its dataset in [INVENTORY](../data/INVENTORY.md) with **vintage · license · confidence**.
4. **Assumptions** used (e.g. "mode-share = Iloilo 2014").
5. **Sensitivity mini-chart** — which assumption moves this number most (`PRD-F15`).
6. **References** — citations backing it.

Visual: right-docked drawer (`--shadow-md`), `420px`, mono for all values, dataset links as chips. **Team rule (print it on the wall):** *if you put a number on screen and it has no working Inspect, it is not done.*

---

## Self-Check

- [x] §2 has exact HEX values (incl. the 5-dimension palette + confidence channel).
- [x] §3 spacing scale consistent (multiples of 4px).
- [x] §4 components define Disabled + Focus + the full state cycle.
- [x] §7 taste dials set (3/4/7) and a variant chosen with reason.
- [x] §6 WCAG AA + color-blind-safe (hue never alone) + accessible map data-table fallback.
- [x] §9–12 cover the 3D simulator, full interface inventory, Route & Action Map, and the glass-box Inspect pattern.
- [x] Materialize as Tailwind config / CSS variables once the frontend scaffold exists (then set Last reconciled).
