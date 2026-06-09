# Design notes — taste-skill applied

Reference: [Leon's taste-skill](https://github.com/Leonxlnx/taste-skill) — an "anti-slop" frontend
discipline with three dials: **DESIGN_VARIANCE**, **MOTION_INTENSITY**, **VISUAL_DENSITY**.
We apply its *discipline* (real system, anti-defaults, a11y, no fake precision) — not its
landing-page layout rules — consistent with [DSD §7](../docs/dsd-matrix.md).

## A. The deck (this folder)
Dials chosen for a projector pitch: **VARIANCE 6 · MOTION (low — slide transitions only) · DENSITY low** (one idea per slide).
- **System, not defaults:** a single token set (`deck/styles.css`), the DSD 5-dimension palette kept brand-true (Behavioral blue / Social rose / Economic amber / Ecological green / Societal violet), one cobalt accent, one radius scale.
- **Type & numbers:** large type scale; **all numbers use `tabular-nums`** in a mono face so figures never jitter and read as instrument output.
- **Dark "instrument" theme:** projector-legible; backgrounds print correctly (`print-color-adjust: exact`).
- **Motion:** transitions only, and gated by `prefers-reduced-motion`. No decorative animation.
- **Honesty as design:** ranges over point estimates; every factual slide carries a source/`note` line; "target / planned / directional" are visible, not buried.

## B. Recommendations for the existing `apps/web` (suggestions — not in scope to rebuild now)
The app is built (InspectDrawer, Deck.gl scenario page, bias-audit log, validation panel). To elevate it with taste-skill discipline — recommended dials **VARIANCE 3 · MOTION 4 · DENSITY 7** (it's a trust-first instrument, not a landing page):

1. **Make the Inspect drawer the visual hero.** It *is* the differentiator. Strengthen the equation → datasets → confidence hierarchy (clear sections, mono values, dataset chips with vintage + confidence). The wall rule: *a number with no working Inspect is not done.*
2. **Confidence as its own channel.** Keep confidence visually distinct from the 5-dimension hue palette (opacity/pattern/fringe), on both map overlays and panels, so it never reads as a 6th category (PRD-F5). *(Tracked as a DSD anti-pattern watch-item.)*
3. **Tabular numbers everywhere.** Apply `next/font` tabular-nums to all metric displays and the timeline scrubber so values don't shift width as they stream/update.
4. **Tasteful streaming motion.** As each dimension result arrives over the WebSocket, animate it in (short, eased) — and gate on `prefers-reduced-motion`. Reinforces the "constant motion within 90 s" feel without noise.
5. **A real progressive/loading state for the 90 s run.** Show the pipeline stage (parse → retrieve → simulate → score → synthesize) so the wait feels like progress, not a spinner.
6. **Ranges, never false precision.** Economic/Societal cards should render confidence-anchored ranges (e.g. "−₱8M to −₱14M"), never a single false-precise number.

> Optional next step: install the taste-skill audit directly — `npx skills add https://github.com/Leonxlnx/taste-skill` — and run its redesign/detect pass over `apps/web`. **Flag before installing** (adds a skill + deps).
