# Open data refresh playbook (CR-016)

**Cadence:** monthly, or before any demo / eval gate.  
**Policy:** open sources only — no government FOI ([outreach/FOI_STATUS.md](outreach/FOI_STATUS.md)).

## 1. Force-refresh raw open vintages

```bash
cd data
python fetch/refresh_dynamic.py --all
# If OSM 504s: python -c "from fetch.fetch_open import overpass; overpass()"
# (mirrors in fetch_open.py)
```

Writes [last_refresh.json](last_refresh.json). Stamp **Last refresh** in [INVENTORY.md](INVENTORY.md).

| Source | Script | Notes |
|--------|--------|-------|
| OSM-ILO | `fetch_open.py` (via refresh) | Live; mirrors on 5xx |
| PSA OpenStat + WB | `fetch_economic.py` | FIES/ASPBI/GVA paths fixed 2026-08-05 |
| CCHAIN HDX | refresh + `subset_iloilo.py` | Brgy tables |
| Overture | `fetch_geo.py` | Only if buildings/POIs clearly stale |
| OpenAQ | `fetch_openaq.py` | Needs free `OPENAQ_API_KEY` (not government) |
| LiPAD flood | `fetch_lipad_flood.py` | 10 m hazard WFS GeoJSON (EPSG:4326) |
| GHSL / WorldPop | CCHAIN refresh | Prefer `processed/cchain_iloilo/worldpop_population.csv`; no separate GHSL pull unless that CSV is missing |

## 2. Rebuild kernel artifacts (Redis up)

```bash
cd app
docker compose up -d   # redis at least

# UTF-8 on Windows: set PYTHONIOENCODING=utf-8
uv run --directory packages/kernel python -X utf8 -u ../data/build_network.py
uv run --directory packages/kernel python -X utf8 -u ../data/build_demand.py --calibrate --fringe-factor 1.0
uv run --directory packages/kernel python -c "from matrix_kernel.baseline import run_nightly_baseline; print(run_nightly_baseline())"
uv run --directory packages/kernel python -m matrix_kernel.build_validation_report
```

## 3. After flood hazard update

```bash
uv run --directory packages/kernel python -m matrix_kernel.build_flood_fixture
# Uses MATRIX_FLOOD_EXTENT or data/raw/flood/lipad_iloilo_fh25yr.geojson
# Event VAL-02 stays NOT_RUN; hazard fixture is for ECO-4 / hazard-skill
```

# Optional OpenAQ: set OPENAQ_API_KEY in data/fetch/.env (free key at openaq.org).
# Without it, matrix_kernel/data/openaq_iloilo_fixture.json remains the offline scale check.

- Mode-share: literature — do not invent (`MATRIX_MODE_SHARE` only from open published tables).
- VAL-01: directional vs Calderon; never fit demand to Calderon targets.
- Do not claim agency-calibrated absolute volumes.
