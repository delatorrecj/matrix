# MATRIX — Data

Acquisition workspace for the **Iloilo City** pilot. Everything here is open / contact-free unless explicitly flagged. The master manifest is **[INVENTORY.md](INVENTORY.md)** — read it first.

## Layout

```
data/
  raw/         # fetched as-is — GITIGNORED (large / third-party / regenerable)
  interim/     # conversions (OSM→SUMO net, partial GTFS) — GITIGNORED
  processed/   # analysis-ready outputs — tracked if small
  fetch/       # re-runnable download scripts
  outreach/    # send-ready contact drafts (only-if-needed, Tier C)
  INVENTORY.md # master manifest: every dataset, link, license, vintage, status
  README.md    # this file
```

## Reproduce the data

Nothing in `raw/` is committed — it is regenerated from the manifest + scripts:

```bash
# direct-HTTP open data + OSM Overpass extract (Python stdlib, no deps)
python fetch/fetch_open.py
# filter CCHAIN → Iloilo barangay subset
python fetch/subset_iloilo.py
# PSA OpenStat + World Bank economic APIs (Python stdlib)
python fetch/fetch_economic.py
# parse BIR zonal-values XLS → CSV (requires the manually downloaded .xls)
python fetch/parse_bir_zonal.py
# Windows-native equivalent of fetch_open
pwsh fetch/fetch_open.ps1
# heavy geo (Overture, raster COGs) — needs extra packages, run on demand
python fetch/fetch_geo.py        # pip install overturemaps (+ rasterio for rasters)
# published LPTRP jeepney routes → raw/transport/
python fetch/scrape_lptrp.py
```

Scripts are **idempotent** — they skip files already present. Re-run any time to refresh live sources (OSM, Overture, air, traffic, Sentinel); record the refresh date in INVENTORY.

## API keys (Tier B only)

Some sources need a free key. Copy `.env.example` → `.env` (gitignored) and fill in:
`TOMTOM_API_KEY`, `OPENWEATHER_API_KEY`, `OPENAQ_API_KEY`, `GEMINI_API_KEY`, `HERE_API_KEY`.

## Principles

- **Confidence over completeness.** Every dataset carries a confidence tier; OSM/Overture-derived transit is *Medium*, not authoritative. This feeds the product's confidence layer — don't launder estimates as precision.
- **Vintage matters.** Prefer the newest release (e.g. **2024 POPCEN-CBMS**, not 2020 Census). Live sources get a per-run refresh date.
- **No raw third-party files in git.** We commit links + fetch logic, not copyrighted PDFs/imagery.
- **Contact is a last resort.** See `outreach/` — every Tier C item already has an open substitute in hand; nothing there blocks the build.
