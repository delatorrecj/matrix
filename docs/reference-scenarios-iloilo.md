# Iloilo reference scenarios (Phase 4)

Multi-district demo set for CPDO pilot and QAD. IDs are assigned at `POST /scenario` time; use these **queries** to reproduce.

| # | Query (NL) | Intervention | District | Map truth |
|---|------------|--------------|----------|-----------|
| 1 | *3-storey school in Molo with 3000 students* | `new_facility` | Molo | `facility-demand` — city default camera; BEH-4 demand injected in SUMO |
| 2 | *Close one lane on Diversion Road* | `lane_closure` | Diversion | Honest corridor overlay + corridor-box fly |
| 3 | *Flood-sensitive development along the esplanade* | corridor / flood context | City Proper | Ecological flood exposure; VAL-02 event gate may be NOT_RUN |

## Full pilot net

```bash
cd app
export MATRIX_CITY_CONFIG=config/cities/iloilo-full.json
```

SUMO proof on the full Iloilo bbox requires the named net at `packages/kernel/data/iloilo.net.xml` (regenerate via `build_network.py` if missing).

## Expected outcomes (honest)

- **School:** Behavioral shows BEH-4 facility demand delta; map does not fake a lane closure.
- **Diversion:** Corridor overlay on `keyword-match` or gazetteer resolution; pin at corridor midpoint when honest.
- **Esplanade:** Ecological dimension uses hazard-skill layers; confidence stays directional where event GT is absent.

Document locked expected ranges in `docs/qad-matrix.md` when CPDO sign-off lands.
