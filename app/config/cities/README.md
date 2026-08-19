# City configuration (Phase 4–5)

MATRIX scales by swapping `CityConfig` — see [`packages/kernel/matrix_kernel/config.py`](../packages/kernel/matrix_kernel/config.py).

| File | Purpose |
|------|---------|
| [`iloilo-full.json`](iloilo-full.json) | Full Iloilo pilot bbox + default net paths (SUMO proof) |
| [`jakarta-demo.json`](jakarta-demo.json) | Second-city demo stub (ASEAN portability) |

Enable from `app/`:

```bash
export MATRIX_CITY_CONFIG=config/cities/iloilo-full.json
```

Reference scenarios for CPDO pilot (Phase 3): school in Molo (`new_facility`), lane closure on Diversion Road, flood-sensitive esplanade corridor — document outcomes in `docs/qad-matrix.md` when locked.
