# MATRIX

**Multi-Agent Twin for Routing & Infrastructure eXchange** — a pre-construction infrastructure impact simulator for ASEAN cities, piloting in **Iloilo City**. Built by Team **ATLAN** (Polytechnic University of the Philippines) for the **ASEAN AI Hackathon 2026**, Smart Cities track.

> **Repo status:** this is the **planning, data, and documentation** workspace. There is no app to run yet — application code is scaffolded into a separate monorepo per [MATRIX.md](MATRIX.md) §8. What's here today: the spec, a working Iloilo data pipeline, and (in `docs/`) the formal doc suite.

---

## Quick start (developers)

**Prerequisites:** Python 3.12+, Git, ~200 MB free disk for raw data. Windows/macOS/Linux all fine.

```bash
git clone https://github.com/delatorrecj/matrix.git
cd matrix

# Get the Iloilo data — open & contact-free. Raw data is gitignored but regenerable.
python data/fetch/fetch_open.py      # OSM extract + literature + Project CCHAIN (barangay data)
python data/fetch/subset_iloilo.py   # filter CCHAIN -> data/processed/cchain_iloilo/ (180 barangays)
python data/fetch/scrape_lptrp.py    # published Iloilo jeepney (LPTRP) routes

# Optional richer geo (one extra package)
pip install overturemaps
python data/fetch/fetch_geo.py       # Overture buildings / POIs / transport
```

The Iloilo CCHAIN subset (`data/processed/cchain_iloilo/`, ~7 MB) is **committed**, so you have usable barangay-level data the moment you clone — even before running any fetch.

**API keys (optional, Tier-B live sources):** `cp data/fetch/.env.example data/.env` and fill in what you have (TomTom, OpenWeather, OpenAQ, Gemini, HERE). `data/.env` is gitignored.

---

## Where things are

| Path | What it is |
|---|---|
| **[MATRIX.md](MATRIX.md)** | Canonical product + technical spec — the single source of truth. **Read first.** |
| [data/INVENTORY.md](data/INVENTORY.md) | Live data manifest — every dataset: link, license, vintage, confidence, status. |
| [data/READINESS.md](data/READINESS.md) | Data mapped to the 5 impact dimensions, with confidence + real gaps. |
| [MATRIX_Iloilo_Data_Sources.md](MATRIX_Iloilo_Data_Sources.md) | Source rationale, tiers, OSM bounding boxes. |
| [data/fetch/](data/fetch/) | Re-runnable fetch scripts (Python stdlib; idempotent). |
| [data/processed/](data/processed/) | Analysis-ready, git-tracked outputs (Iloilo CCHAIN subset). |
| [data/outreach/](data/outreach/) | Send-ready contact drafts — only for fidelity upgrades; none block the build. |
| [reference/](reference/) | AAIH admin & deliverables (roadmap, orientation). |
| [CLAUDE.md](CLAUDE.md) | Operating guide for AI coding agents in this repo. |
| `docs/` | Formal doc suite — PRD, SDD, QAD… — generated via the FMD framework. |

## Data layout

```
data/
  raw/        # fetched as-is — GITIGNORED (large / third-party / regenerable)
  interim/    # conversions (OSM->SUMO net, partial GTFS) — GITIGNORED
  processed/  # analysis-ready, git-tracked (Iloilo CCHAIN subset)
  fetch/      # download scripts
  outreach/   # contact drafts (last resort)
  INVENTORY.md   READINESS.md   README.md
```

## Conventions

- **Never commit `data/raw/`, `data/interim/`, or secrets.** They're gitignored; regenerate raw with the fetch scripts.
- **Branch off `main`** and open a PR. Keep history clean — separate commits for data vs docs.
- **Data honesty:** every dataset carries a confidence tier (H/M/L). Don't launder estimates as precision — confidence-bounded output is the product's core differentiator (see [READINESS](data/READINESS.md)).
- **Prefer the newest vintage** (e.g. 2024 POPCEN-CBMS, not 2020).

## Two git repos in one folder

[`FMD/`](FMD/) (the documentation-generation framework) is a **separate git repository** vendored here, with its own remote. It's gitignored by this repo — operate on it with `git -C FMD …`, and never `git add FMD`. Details in [CLAUDE.md](CLAUDE.md).

---

*Team ATLAN — Polytechnic University of the Philippines · ASEAN AI Hackathon 2026 · Smart Cities · Pilot: Iloilo City*
