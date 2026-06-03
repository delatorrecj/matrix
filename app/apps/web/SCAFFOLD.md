# Frontend scaffold — `apps/web`

> **Deliberately not pre-generated.** Next.js, Tailwind, and Deck.gl move fast, and
> [build-matrix.md §3](../../../docs/build-matrix.md) forbids emitting framework code from
> training memory. Scaffold from the live generators (which pull current config), then
> verify against the pinned-version checklist below. This file is the Gate 0 procedure for
> the web app.

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

- [ ] **Next.js** (App Router) — nextjs.org — resolved version: `____`
- [ ] **Tailwind v4** — uses `@tailwindcss/postcss` (NOT the v3 `tailwindcss` PostCSS plugin) — `____`
- [ ] **Deck.gl** `TripsLayer` API — deck.gl — `____`
- [ ] **shadcn/ui** CLI + Radix — ui.shadcn.com — `____`
- [ ] **Fonts** — Geist + Geist Mono via `next/font` (self-hosted, NOT `<link>`) — DSD requires tabular nums
- [ ] **Motion** — import from `motion/react` (NOT `framer-motion`)

## 3. Then build to the DSD

UI surfaces, tokens, the Inspect drawer, and the 3D layers are owned by
[dsd-matrix.md](../../../docs/dsd-matrix.md); the `frontend-3d-builder` agent (SAD-A3)
builds them. Consume the WS event shapes from `apps/api` (`ACCEPTED → PLAYBACK_FRAME →
DIMENSION_RESULT → SYNTHESIS → DONE`). **Every rendered number needs a working Inspect
affordance** (PRD-F14) and **confidence is a separate visual channel** from the 5-dimension
palette (PRD-F5). This is Phase 5 (Gate 5).
