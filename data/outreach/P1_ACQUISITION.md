# P1 open polish (CR-016 — no government chase)

| Dataset | Status | Action |
|---------|--------|--------|
| **OpenAQ** | Free API key (not gov) | Set `OPENAQ_API_KEY` in `data/fetch/.env` → `python data/fetch/fetch_openaq.py`. Offline fixture remains if unset. |
| **GHSL / WorldPop** | CCHAIN WorldPop already wired for Tier-B demand | Optional direct GHSL pull only if CCHAIN vintage is insufficient — see `fetch_ghsl_note` in OPEN_REFRESH. Prefer CCHAIN refresh. |
| **BIR-ZV** | Processed CSV in hand (DO17-2021) | Skip browser chase unless open portal shows a newer DO; ECON-1 already reads CSV. |
| **NHCP** | WONT-FILE | Keep OSM `historic=*` for SOCI-2. |

See [OPEN_REFRESH.md](../OPEN_REFRESH.md) and [docs/cr-016-open-data-only.md](../../docs/cr-016-open-data-only.md).
