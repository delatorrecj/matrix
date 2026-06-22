# MATRIX — Pitch presentation

The pitch deck for the **ASEAN AI Hackathon 2026** (Smart Cities track), built from code with
[python-pptx](https://python-pptx.readthedocs.io/) so every slide is reproducible and version-controlled.

> **History:** this folder previously held a self-contained HTML deck (`deck/index.html` +
> `styles.css`, exported to PDF via Playwright). That pipeline was retired in favor of a native
> `.pptx` so the deck opens and edits in PowerPoint/Google Slides like the judges expect. The old
> HTML files are recoverable from git history if ever needed.

```
presentation/
  deck/
    build_deck.py   # the generator (python-pptx) — builds all slides on the AAIH brand chrome
    _assets/        # brand chrome consumed by the build: bg*.png + logo_*.png (tracked)
    Smart Cities_PUP_ATLAN_PitchDeck.pptx   # generated output (tracked deliverable)
    # PPT Template AAIH (student).pptx       # AAIH source template — git-ignored heavy reference
  assets/
    README.md       # legacy screenshot drop-in notes (from the old HTML deck)
  semifinal-video-script.md  # 5-minute semi-final pitching video: full script + production plan
  walkthrough.md    # slide-by-slide narration + the 90-second live-demo run-of-show
  CONTENT-OUTLINE.md  # the scrutinized/debunked/refined content rationale
  DESIGN-NOTES.md     # design discipline (taste-skill dials, DSD palette, no fake precision)
```

## Build the deck
From this folder, regenerate `Smart Cities_PUP_ATLAN_PitchDeck.pptx` from source:

```bash
pip install python-pptx
cd presentation/deck
python build_deck.py        # writes Smart Cities_PUP_ATLAN_PitchDeck.pptx next to the script
```

The canvas is 20in × 12.5in (16:10, matching the AAIH template). All content — text, shapes, the
5-dimension palette, logos — is emitted programmatically from `build_deck.py` reading `_assets/`;
there is no manual slide editing step.

## Editing
Edit slides in `build_deck.py` and re-run it, or open the generated `.pptx` directly in PowerPoint /
Google Slides for last-mile tweaks. If you hand-edit the `.pptx`, fold the change back into
`build_deck.py` so the source of truth stays runnable.

Keep the honesty discipline: every number on a slide is either sourced or explicitly labeled
*directional / target / planned*. See [CONTENT-OUTLINE.md](CONTENT-OUTLINE.md) for the rationale and
[walkthrough.md](walkthrough.md) for the run-of-show.
