# Grand Finals pitch pack

Narrative architecture and truth-accurate materials for **ASEAN AI Hackathon 2026 Grand Finals**.

## The deck

Two artifacts, one design system. Both are generated from the same nine spoken slides plus six appendix slides, and both carry the same speaker notes.

| Artifact | Use it for |
|----------|------------|
| [`deck/index.html`](deck/index.html) | **Primary.** Open in any browser. Arrow keys or click to navigate, `S` for presenter notes, `F` for fullscreen. Fully offline: fonts and images are local. |
| [`MATRIX_GrandFinals_PitchDeck.pptx`](MATRIX_GrandFinals_PitchDeck.pptx) | **Projector fallback**, for a venue that insists on PowerPoint. Speaker notes land in the notes pane, so presenter view works. |

### Presenting the HTML deck

```bash
python -m http.server 8100 --directory presentation/grand-final/deck
```

Then open `http://localhost:8100` and press `F`. Opening `index.html` straight from the filesystem also works in Chrome, though some browsers block local font loading over `file://`.

| Key | Action |
|-----|--------|
| `→` `←` `Space` `PgDn` `PgUp` | Next / previous slide |
| `Home` `End` | First / last slide |
| `S` | Toggle presenter notes |
| `F` | Fullscreen |
| Click | Right two thirds advances, left third goes back |

Slides deep-link by number (`#7`), so a judge asking to see slide 7 again is one URL away.

### Exporting a PDF

Chrome, `Ctrl+P`, **Save as PDF**, margins **None**, **Background graphics on**. The print stylesheet sets a 13.333in x 7.5in landscape page and puts one slide on each, with no trailing blank page.

### Regenerating the PPTX

```bash
cd presentation/grand-final
python build_deck.py
```

Both artifacts render in **Geist**, the same face the product uses. The HTML deck self-hosts it from `deck/fonts/`; PowerPoint needs it installed as a system font (the TTF release lives at [vercel/geist-font](https://github.com/vercel/geist-font)). Without it PowerPoint substitutes silently, so for a machine you cannot prepare:

```bash
MATRIX_DECK_FONT="Segoe UI" MATRIX_DECK_FONT_MONO="Consolas" python build_deck.py
```

### Adding the demo still

Slide 6 ships as a clean cue card for cutting to the 20 to 30 second video. Save a frame as `deck/assets/demo-still.png` (1600x900 or wider) and both artifacts promote that slide to full bleed automatically. The HTML deck picks it up on reload; the PPTX needs `python build_deck.py` again.

## Design system

Inherited from the shipped product ([`app/apps/web/src/app/globals.css`](../../app/apps/web/src/app/globals.css)), so the deck looks like the thing the judges will click through.

| Token | Value | Where |
|-------|-------|-------|
| Surface | `#0A0E1A`, appendix `#06090F` | Product dark background |
| Ink | `#E9EEF8` / `#94A3B8` / `#7C8CA8` | All three clear WCAG AA on both surfaces |
| Accent | `#4F82EE`, small text `#93B4F7` | Product primary, lifted for dark |
| Limits | `#FBBF24` | Reserved for the honest-limits block. Never decorative. |
| Dimensions | Behavioral `#60A5FA` · Social `#F472B6` · Economic `#FACC15` · Ecological `#4ADE80` · Societal `#C084FC` | Only on slides where the five dimensions are the subject |
| Type | Geist, Geist Mono for data and labels | Product type stack |

Both artifacts are authored against the same **1280 x 720 design canvas**. In CSS that is `calc(N * var(--u))`; in Python it is `u(N)` and `fs(N)`. A measurement means the same thing in both files, which is what keeps them from drifting.

House rules the deck holds to: one idea per slide, no eyebrow labels above headings, no section-number kickers, no gradient text, no glow shadows, no em-dashes anywhere on screen, and no number that is not in [`CLAIMS.md`](CLAIMS.md).

## Source documents

| File | Role |
|------|------|
| [PITCH_STRATEGY.md](PITCH_STRATEGY.md) | Locked hook, thesis, positioning, 7-beat arc |
| [CLAIMS.md](CLAIMS.md) | PROVEN / IN DEVELOPMENT / VISION firewall |
| [MASTER_PROMPT.md](MASTER_PROMPT.md) | Cursor instruction: translate strategy, invent nothing |
| [PITCH_SCRIPT.md](PITCH_SCRIPT.md) | Spoken script by beat |
| [PITCH_DECK.md](PITCH_DECK.md) | Slide-by-slide content source of truth |
| [DEMO_SCRIPT.md](DEMO_SCRIPT.md) | 20 to 30s video plus live fallback |
| [EVIDENCE.md](EVIDENCE.md) | Proof index, Q&A pointers, asset checklist |

**Order:** Strategy → Claims → Script / Deck / Demo. Semi-final materials in the parent `presentation/` folder are reuse-only for assets and Q&A depth, not the spoken spine.
