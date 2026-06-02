# MATRIX — Planning & Documentation Workspace

**MATRIX** (Multi-Agent Twin for Routing & Infrastructure eXchange) is a pre-construction infrastructure impact simulator for ASEAN cities, piloting in **Iloilo City**. Built by **Team ATLAN** (Polytechnic University of the Philippines) for the **ASEAN AI Hackathon 2026** — Smart Cities track.

> This repo holds the **planning, data, and documentation** for MATRIX. Application code is scaffolded into a separate monorepo per the roadmap in [MATRIX.md](MATRIX.md) §8.

## Start here

| Doc | What it is |
|---|---|
| **[MATRIX.md](MATRIX.md)** | Canonical product + technical spec — the single source of truth. **Read first.** |
| [MATRIX_Iloilo_Data_Sources.md](MATRIX_Iloilo_Data_Sources.md) | Iloilo data-source catalog — rationale, tiers, OSM bounding boxes. |
| [data/INVENTORY.md](data/INVENTORY.md) | Live data manifest — what's acquired, links, licenses, vintages, status. |
| [CLAUDE.md](CLAUDE.md) | Operating guide for AI agents working in this repo. |

## Repository map

```
MATRIX.md                       canonical product + technical spec
MATRIX_Iloilo_Data_Sources.md   data-source rationale & catalog
CLAUDE.md                       AI-agent operating guide
data/                           Iloilo data — fetch scripts, INVENTORY, processed subset, outreach drafts
reference/                      AAIH admin & deliverables (technical roadmap, orientation)
FMD/                            Foundational Matrix Documents — doc-generation framework (separate git repo)
docs/                           (reserved) FMD-generated suite: PRD, SDD, QAD… — created when FMD runs
```

## Data — quick start

Open-data-first and contact-free. Raw data is gitignored; reproduce it from the manifest:

```bash
python data/fetch/fetch_open.py      # OSM extract + literature + Project CCHAIN (barangay data)
python data/fetch/subset_iloilo.py   # filter CCHAIN to Iloilo's 180 barangays -> data/processed/
python data/fetch/fetch_geo.py       # Overture buildings/POIs/transport  (pip install overturemaps)
python data/fetch/scrape_lptrp.py    # published Iloilo jeepney (LPTRP) routes
```

Full picture, licenses, and confidence tiers: [data/INVENTORY.md](data/INVENTORY.md).

## Two git repos in one folder

This repo (`matrix`) and **[FMD/](FMD/)** (`fmd`, the documentation-generation framework) are **separate repositories**. `FMD/` is untracked here — target it explicitly with `git -C FMD …`. Generated docs for MATRIX land in `docs/` (per FMD convention) and are part of the `matrix` repo. See [CLAUDE.md](CLAUDE.md) for details.
