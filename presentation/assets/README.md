# Deck assets

Drop real screenshots here so the deck shows the working product instead of placeholders.
The deck (`../deck/index.html`) auto-swaps these in if present; if a file is missing it renders
a labeled placeholder — nothing breaks.

| File | Used on | What it should show |
|---|---|---|
| `scenario-playback.png` | Proof slide | Deck.gl TripsLayer playback on the Iloilo twin + a dimension result panel |
| `inspect-drawer.png` *(optional)* | Proof slide (swap-in) | the glass-box Inspect drawer: equation_id + datasets + confidence |
| `home.png` *(optional)* | — | scenario entry / NL query screen |

Capture them with `node ../scripts/capture-shots.mjs` while the app runs locally
(see [../README.md](../README.md)). Prefer PNG, ~2× device scale, 16:9-ish crops.
