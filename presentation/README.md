# MATRIX — Pitch presentation

A self-contained HTML pitch deck for the **ASEAN AI Hackathon 2026** (Smart Cities track) and its
PDF export path. No build step, no CDN, no `node_modules` to run the deck — open the HTML.

```
presentation/
  deck/
    index.html        # the deck (all slides inline; arrow-key / click nav; print-optimized)
    styles.css        # MATRIX design system (dark pitch theme; DSD 5-dimension palette)
  assets/
    README.md         # what screenshots to drop in (deck degrades to styled placeholders if absent)
  scripts/
    export-pdf.mjs    # Playwright (headless Chromium) → matrix-pitch.pdf (one slide per page)
    capture-shots.mjs # optional: capture real-app screenshots from a running apps/web
  walkthrough.md      # slide-by-slide narration + the 90-second live-demo run-of-show
  CONTENT-OUTLINE.md  # the scrutinized/debunked/refined content rationale
```

## View the deck
Open `deck/index.html` in any modern browser. Navigation:
- **→ / Space / click** next · **←** previous · **F** fullscreen · **P** or `Ctrl/Cmd+P` print.
- Slide counter is bottom-right; a thin progress bar runs along the top.

## Export to PDF
The deck's print stylesheet renders **one slide per page** (16:9), so any of these work:

1. **Browser (simplest):** open `deck/index.html`, `Ctrl/Cmd+P`, "Save as PDF", layout **Landscape**, margins **None**, **enable "Background graphics."**
2. **Scripted (deterministic):** from a place where Playwright's Chromium is installed (e.g. `app/apps/web`, which already depends on Playwright):
   ```bash
   node presentation/scripts/export-pdf.mjs            # writes presentation/matrix-pitch.pdf
   # if playwright isn't found: cd app/apps/web && npx playwright install chromium, then re-run
   ```

## Real-app screenshots (recommended for the Proof slide)
The deck shows real UI where possible. To capture from the running app:
```bash
cd app && docker compose up -d            # datastores
cd app/apps/api && uvicorn matrix_api.main:app --reload   # API + WS
cd app/apps/web && npm install && npm run dev             # http://localhost:3000
node presentation/scripts/capture-shots.mjs               # writes into presentation/assets/
```
If a screenshot file is missing, the deck renders a labeled placeholder — nothing breaks.

## Editing
All content lives in `deck/index.html` as `<section class="slide">` blocks; styling in `styles.css`.
Keep the honesty discipline: every number on a slide is either sourced or labeled *directional / target / planned*. See [CONTENT-OUTLINE.md](CONTENT-OUTLINE.md).
