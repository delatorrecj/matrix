# CCHAIN — Iloilo City subset

Analysis-ready slice of **Project CCHAIN** filtered to **Iloilo City's 180 barangays**
(PSGC adm4 prefix `PH063022`). This is **committed** (unlike `data/raw/`) so the team
has the data on clone — useful given HDX's intermittent 504s.

**Regenerate:** `python data/fetch/fetch_open.py` (pulls raw CCHAIN) → `python data/fetch/subset_iloilo.py`.

**Vintage:** CCHAIN 2003–2022 · **Source/license:** [HDX, open](https://data.humdata.org/dataset/project-cchain) · attribute Project CCHAIN.

**Coverage by table** (barangay-keyed `adm4_pcode`, 21 yrs unless noted):

| Table | Iloilo rows | Use |
|---|---|---|
| `worldpop_population` | 3,780 | population + density per barangay (Social) |
| `tm_relative_wealth_index` | 1,260 | Meta Relative Wealth Index (Economic/Social) |
| `nighttime_lights` | 1,980 | economic-activity proxy (Economic) |
| `mapbox_health_facility_brgy_isochrones` | 180 | health-access travel time (Social/Societal) |
| `esa_worldcover` | 180 | land cover share (Ecological) |
| `project_noah_hazards` | 180 | flood/landslide/surge exposure (Ecological) |
| `google_open_buildings` / `tm_open_buildings` | 180 / 1,118 | building stock (Base/Economic) |
| `osm_poi_*` (amenity/health/sanitation/water/total) | 1,620 ea | trip generators + services |
| `geoportal_doh_poi_health` | 180 | DOH health POIs (Social) |
| `ookla_internet_speed` | 720 | digital access (Social) |
| `climate_indices` | 43,200 | derived climate metrics (Ecological) |
| `brgy_geography` | 180 | barangay boundaries/geometry (Base) |
| `disease_pidsr_totals` / `disease_psa_totals` | 6,240 / 4,332 | health surveillance (city adm3) |
| `location` (+ `calendar`, `disease` lookups) | 180 / whole | code↔name + dimension keys |

**Note:** `disease_fhsis_totals` and `disease_lgu_disaggregated_totals` returned **0** Iloilo
rows — they key Iloilo under a different geography than `PH063022*`; pull from raw if needed.
