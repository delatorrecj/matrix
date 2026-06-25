# Handoff — 2026-06-25 frontend session

Frontend batch in `app/apps/web` (parts A–H below; A–D were the first pass, E–H followed same day). **All changes are uncommitted on `main`** (your convention: you commit, not the agent). Verified green: `next lint` clean · `next build` clean · Playwright e2e 2/2 (run in CI mode — see "How to verify"). Touches a couple of `docs/` files too (DSD reconciliation, part G).

## What changed & why

### A. Console hygiene (the warnings you saw)
The scary console lines — `Grabbit: Linkify…`, `content.js:687 NotFoundError: removeChild`, `A listener indicated an asynchronous response… message channel closed` — are from the **Grabbit browser extension, not MATRIX**. Confirm by opening the site in an incognito window with extensions off. The genuinely-ours warnings are fixed:
- **deck.gl `rounded` deprecation** → `TripsLayer` now uses `jointRounded: true, capRounded: true`. — `src/app/scenario/[id]/page.tsx`
- **`Expected value to be of type number, but found null` (×3)** → the 3D building extrusion now coalesces null heights: `["coalesce", ["get", "render_min_height"], 0]` / `render_height`. — `src/lib/mapStyles.ts`
- **`Image "wood-pattern" could not be loaded`** (OpenFreeMap basemap referencing a sprite missing from its own sheet) → new `registerMissingImageFallback(map)` registers a 1×1 transparent pixel for any missing image. Wired into the map effect on both map pages. — `src/lib/mapStyles.ts`, both pages.

### B. "Initializing" gating (scenario page)
While the first run is still computing, the **Scenario summary** body and the **play/pause control** show an "Initializing" state; the real scrubber + results appear only once the run reaches `DONE`.
- New `src/components/InitializingState.tsx` — `variant="pill"` (control slot) + `"panel"` (summary body); reduced-motion safe.
- Gate in `src/app/scenario/[id]/page.tsx`: `const resultsReady = runState.phase === "done";`
  - Summary body: `isRunActive ? <InitializingState panel/> : <SummaryView/>` (analytics tab unchanged).
  - Bottom bar: `resultsReady ? <scrubber/> : isRunActive ? <InitializingState pill/> : null`.
- Edge cases: on error/cancelled/disconnected the existing banners handle messaging and the scrubber stays hidden.

### C. Brand + SVG logo + favicon
- Mark = a **pentad** ("one simulation kernel → five impact dimensions"): center rounded-square + 5 satellite nodes + spokes, brand blue `#1D4ED8`. Hand-authored SVG for 16px crispness.
- **Three synced copies — keep in sync if the mark ever changes:**
  - `src/app/icon.svg` — favicon (Next App Router auto-detects it; the old `favicon.ico` stays as a legacy fallback).
  - `public/logo.svg` — static asset.
  - `src/components/Logo.tsx` — `LogoMark` (currentColor) + `Logo` lockup.
- Used in: cockpit header (replaced the text-only wordmark) and the `IconNavRail` home button (replaced the generic `Box` icon).
- Palette + Geist type are unchanged — this was a *refine*, not a reinvent.

### D. Landing page
- New **server-component landing at `/`**: hero, "one simulation / five dimensions" (with the five dimension hues), a glass-box trust section, footer. Anti-slop, content-true copy. — `src/app/page.tsx`
- **The cockpit moved from `/` to `/app`** — `src/app/page.tsx` → `src/app/app/page.tsx`.
- Updated the only two `/` references → `/app`: scenario-page home-nav and the ScenarioBuilder back button. Deep links `/scenario/[id]` and `/builder` are unaffected.

## Session 2 additions (2026-06-25, same day) — verified `next build` clean + e2e 2/2 (CI mode)

### E. Builder double-back-button fix
The Scenario Builder had two `←` affordances that looked identical but did different things: the header arrow (exit → `/app`) and the footer arrow ("Back" = previous wizard step). Header is now a **`LogoMark` → `/app`** affordance ("click the logo = home", brand-consistent); the footer `←` is the sole step-back. — `src/components/ScenarioBuilder.tsx`

### F. Brand sheet (re-ran `/brandkit`)
Re-rendered the brand as an adaptive SVG **brand sheet** (mark + "one kernel → five dimensions" construction with real dimension hues + palette hex + type/confidence rules) via the visualize tool. brandkit is image-gen-oriented; the shippable SVG identity from session 1 is the real deliverable. No code change.

### G. DSD reconciliation + dark-default decision — `docs/dsd-matrix.md`
- **Decision (yours, 2026-06-25): dark is the default, light is a first-class variant** (never dark-only). The DSD previously said "light-first"; reconciled §1, §2, and the §0 design-read to record dark-default. **No code change** — the app already defaults dark ([layout.tsx](app/apps/web/src/app/layout.tsx) `className="dark"`); the spec now matches the product.
- Updated the **§11.1 route map** to the new topology (`/`=landing, `/app`=cockpit, `/builder`) + bumped "Last reconciled".

### H. Impeccable §8 pass (DSD §8 anti-pattern register) over `apps/web`
Audited the live surfaces against the register. **Result: mostly compliant.** Confirmed PASS: confidence is a multi-channel encoding (color + icon + dashed border + opacity + label, never hue-alone — `ConfidenceChip.tsx`); every metric is a `<button onClick={onInspect}>` (`SummaryCard.tsx`); `font-mono tabular-nums` on values; `format.ts` ranges (no false precision); `.wizard-step` / `.card-reveal` correctly gated behind `prefers-reduced-motion: no-preference`. Two fixes applied:
- **Motion (the one unguarded path):** the scenario agent-playback loop auto-ran even under reduced-motion. Now starts **paused** when `prefers-reduced-motion: reduce` (user can still press play). — `src/app/scenario/[id]/page.tsx`
- **Low-confidence trigger reason:** the capping factor was emitted by the kernel into `assumptions` (e.g. ecological "confidence capped at M: …") but buried. Now surfaced as a **"Capped by:"** line right under the confidence chip in the Inspect drawer. — `src/components/InspectDrawer.tsx`

## How to verify
```bash
cd app/apps/web
npm run lint          # clean
npm run build         # clean — routes: / (landing), /app (cockpit), /icon.svg, /scenario/[id]

# e2e — IMPORTANT on Windows: `next dev` cold-compile of the heavy WebGL scenario
# page intermittently blows the 60s Playwright timeout (pure timeout, not an
# assertion failure). Run it the way CI does, against the production build:
npm run build; $env:CI="1"; npm run test:e2e   # 2 passed (hermetic, mocked backend)
# (plain `npm run test:e2e` uses `next dev` + reuseExistingServer and is flaky here.)
```
Visual check of the landing (no WebGL, screenshots fine): preview server `web` → `/`.

## Deploy notes (Vercel)
- Pure frontend change, no API/kernel/env changes. A normal Vercel deploy of `apps/web` ships it.
- **Routing change to flag:** production `/` is now the landing; the simulator is at `/app`. If anything external (docs, QR codes, the deck, judges' links) points at `/` expecting the cockpit, update it to `/app`.

## Open / not done
- No new automated test for the *intermediate* Initializing state, the reduced-motion pause, or the "Capped by:" line (the e2e covers the post-DONE happy path). Optional to add assertions.
- `/brandkit` is image-gen-oriented; delivered an adaptive SVG brand sheet + the shippable SVG identity instead of a raster board. A formal brand-guidelines doc/board can be generated later if wanted.
- **Impeccable §8** pass done over the surfaces touched; a deeper sweep of the map overlays (confidence layer uses the success/warning/error ramp — acceptable as its own toggleable layer, but worth a look against the "confidence ≠ 6th hue" rule) is a possible follow-up.
- DSD §1/§2/§7 light-vs-dark wording reconciled to dark-default; the token table in §2 still lists light-theme values (noted inline) — fine, just flagged.
- Nothing committed or deployed yet.
