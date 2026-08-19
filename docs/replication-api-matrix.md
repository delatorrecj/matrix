# Public read-only API (Phase 5 — replication)

Academic replication uses existing **GET** endpoints; no write surface beyond scenario creation and simulation WS.

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Dependency status |
| `GET /scenario/{id}` | Parsed scenario metadata (no map-truth camera fields) |
| `GET /scenarios/{id}/latest-run` | Latest completed run + glass-box results |
| `GET /scenarios/compare?a=&b=` | Side-by-side latest runs |
| `GET /validation` | Published VAL-01/02 gate status |
| `GET /audit/{scenario_id}` | Public bias-audit log |

City swap: set `MATRIX_CITY_CONFIG` to a file under [`app/config/cities/`](../app/config/cities/) before API start. Second-city stub: [`jakarta-demo.json`](../app/config/cities/jakarta-demo.json).

Web compare UI: **Full analytics** → **Compare scenarios** panel.
