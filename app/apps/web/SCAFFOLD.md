# Frontend scaffold — `apps/web`

> **STATUS (CR-004, 2026-06-07): the frontend is now generated and implemented.** The app
> exists alongside this file — `src/app/` (App Router), `InspectDrawer.tsx`, the Deck.gl
> scenario page (`TripsLayer` + WS client), `BiasAuditLog.tsx`, `ValidationPanel.tsx`, and
> Playwright e2e. The procedure below is retained as the **provenance record** of *how* it
> was scaffolded (live generators, not training memory) and the **resolved pinned versions**
> verified at Gate 0. Re-run the verify-live checklist before any major dependency bump.

> **Why this procedure (kept for the record).** Next.js, Tailwind, and Deck.gl move fast, and
> [build-matrix.md §3](../../../docs/build-matrix.md) forbids emitting framework code from
> training memory. The app was scaffolded from the live generators (which pull current config),
> then verified against the pinned-version checklist below.

## 1. Generate (run from `app/apps/`)

```bash
# Pulls the current App-Router + Tailwind config — do not hand-roll these.
npx create-next-app@latest web --ts --app --tailwind --eslint --src-dir --import-alias "@/*"
cd web
npx shadcn@latest init           # verify the current CLI name at ui.shadcn.com
npm i deck.gl @deck.gl/react @deck.gl/layers mapbox-gl react-map-gl
npm i motion                     # framer-motion's successor; import from "motion/react"
```

## 2. Verify-live-before-coding checklist (Gate 0)

Confirm each against its official docs and record the resolved version in this file:

- [x] **Next.js** (App Router) — nextjs.org — resolved version: `14.2.35`
- [x] **Tailwind v4** — uses `@tailwindcss/postcss` (NOT the v3 `tailwindcss` PostCSS plugin) — `4.x`
- [x] **Deck.gl** `TripsLayer` API — deck.gl — `^9.3.3`
- [x] **shadcn/ui** CLI + Radix — ui.shadcn.com — `^4.10.0`
- [x] **Fonts** — Geist + Geist Mono via `next/font` (self-hosted, NOT `<link>`) — DSD requires tabular nums
- [x] **Motion** — import from `motion/react` (NOT `framer-motion`) - `^12.40.0`

## 3. Then build to the DSD

UI surfaces, tokens, the Inspect drawer, and the 3D layers are owned by
[dsd-matrix.md](../../../docs/dsd-matrix.md); the `frontend-3d-builder` agent (SAD-A3)
builds them. Consume the WS event shapes from `apps/api` (`ACCEPTED → PLAYBACK_FRAME →
DIMENSION_RESULT → SYNTHESIS → DONE`). **Every rendered number needs a working Inspect
affordance** (PRD-F14) and **confidence is a separate visual channel** from the 5-dimension
palette (PRD-F5). This is Phase 5 (Gate 5).
