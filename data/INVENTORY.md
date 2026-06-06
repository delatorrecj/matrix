# MATRIX — Data Inventory (Iloilo pilot)

Master manifest of every dataset. Single source of truth for *what we have, where it came from, and how fresh it is*.

**Status:** ☐ pending · ⏳ scripted (needs key/account/tooling) · ✅ fetched to `raw/`
**Confidence:** H/M/L (propagates to the product's per-dimension confidence layer)
**Dim:** Behav · Soc · Econ · Eco · Societal · KB (knowledge base for GraphRAG) · Base (engine)
**Bbox (Iloilo City Proper):** `10.65,122.50,10.78,122.61` · **Metro Iloilo–Guimaras:** `10.55,122.40,10.85,122.80`
**Last refresh:** 2026-06-03 (OSM, CCHAIN + Iloilo subset, Overture, literature, LPTRP, economic: PSA OpenStat poverty/trade/tourism/GVA + **FIES 2023 (incl. City of Iloilo) + ASPBI 2022** by region, World Bank indicators, HDX poverty XLSX, **BIR zonal values RDO 74 — DO17-2021 .xls**)

---

## Tier A — high-value, contact-free

### Engine / geospatial base
| ID | Dataset | Dim | Vintage | License | Access | Conf | Status |
|---|---|---|---|---|---|---|---|
| OSM-ILO | [OSM Iloilo extract (Overpass)](https://overpass-api.de/api/interpreter) — roads, transit, POIs, heritage | Base | live | ODbL | API (bbox) | H | ✅ 14,068 el |
| OVERTURE | [Overture Maps](https://docs.overturemaps.org/download/) — buildings + places (POIs) + transportation | Base/Econ | 2026-05 | ODbL/CDLA | S3/Explorer (`pip overturemaps`) | H | ✅ 202k feat |
| HOTOSM | [HOTOSM PH roads](https://data.humdata.org/dataset/hotosm_phl_roads) + [buildings](https://data.humdata.org/dataset/hotosm_phl_buildings) | Base | rolling | ODbL | direct (HDX) | H | ☐ |
| DEM-GLO30 | [Copernicus GLO-30 DEM](https://copernicus-dem-30m.s3.amazonaws.com/) | Base/Eco | 2021 | open | AWS COG | H | ⏳ |
| LIPAD | [PhilLiDAR/LiPAD Iloilo flood 5yr/25yr 10m](https://lipad-fmc.dream.upd.edu.ph/layers/geonode:ph063022000_fh25yr_10m) + DTM | Eco/Behav | 2015-17 | open | direct (no reg.) | H | ☐ |
| HAZHUNTER | [HazardHunterPH](https://hazardhunter.georisk.gov.ph/map) multi-hazard report | Eco | live | open | web report | H | ☐ |
| WORLDCOVER | [ESA WorldCover 10m](https://esa-worldcover.org/en/data-access) + [Dynamic World](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1) | Eco/Soc | 2021 / live | CC BY 4.0 | AWS / GEE | H | ⏳ |

### Demographics / Social
| ID | Dataset | Dim | Vintage | License | Access | Conf | Status |
|---|---|---|---|---|---|---|---|
| POPCEN24 | [2024 POPCEN-CBMS](https://psa.gov.ph/content/2024-census-population-popcen-population-counts-declared-official-president) barangay pop + [CBMS](https://cbms.psa.gov.ph/) household profile | Soc | 2024 | open gov | direct (public tables) | H | ☐ |
| CENSUS20 | [PSA 2020 Census Region VI](https://psa.gov.ph/system/files/phcd/2022-12/%281%29%20Region%206_final.xlsx) (time-trend) | Soc | 2020 | open gov | XLSX | H | ☐ (manual; PSA 403 to scripts) |
| CCHAIN | [Project CCHAIN](https://data.humdata.org/dataset/project-cchain) — 20-yr barangay climate/socioeco/health, Iloilo | Soc/Eco/Societal | 2003-22 | open | direct (HDX/CKAN) | H | ✅ 25 tbl, 180 brgy — raw tables in `raw/hdx/`. Iloilo subset (barangay-filtered) written to `data/processed/cchain_iloilo/` by `data/fetch/subset_iloilo.py` (run script to populate). |
| NHFR | [DOH National Health Facility Registry](https://nhfr.doh.gov.ph/Home) | Soc/Societal | live | open gov | direct / data.gov.ph | H | ☐ |
| DEPED | [DepEd school masterlist](https://ebeis.deped.gov.ph/beis/reports_info/masterlist) (+ coords via OSM) | Soc/Societal | 2024 | open gov | direct / data.gov.ph | M | ☐ |
| GHSL | [GHSL built-up + population](https://human-settlement.emergency.copernicus.eu/download.php) + [WorldPop](https://www.worldpop.org/) | Soc | 2023 | open | direct | H | ⏳ |

### Economic (currently weakest dimension — biggest uplift)
| ID | Dataset | Dim | Vintage | License | Access | Conf | Status |
|---|---|---|---|---|---|---|---|
| BIR-ZV | [BIR zonal values RDO 74 Iloilo](https://www.bir.gov.ph/zonal-values) — current **DO 17-2021** (4th rev., eff. 2021-09-09→present) | Econ | 2021 | gov | XLS (manual) | M | ✅ `raw/economic/BIR_ZV_RDO74_IloiloCity.xls` (2.5 MB, 10 sheets). **Sheet 9 (DO17-2021)** = current Iloilo City schedule (9,709 rows incl. legal preamble + classification legend RR/CR/RC/I…); Sheets 1–8 = historical revisions 1990–2012. Grabbed the **.xls** via the site's "View RDO excel" link — richer than the assumed PDF. **✅ Parsed Sheet 9 → `processed/economic/bir_zonal_rdo74_2021.csv`** (5,680 priced entries: location→classification→PHP/m²). **ECON-1 L→M** (CR-003, applied). |
| ASPBI | [PSA ASPBI via OpenStat](https://openstat.psa.gov.ph) — establishments + employment by region & sector | Econ | 2022 | open gov | PSA OpenStat PX-Web API | M | ✅ **2022** (latest on OpenStat; 2023 not yet published) — `psa_openstat_aspbi2022_wholesale_retail_by_region.csv` (53 KB) + `psa_openstat_aspbi2022_accommodation_food_by_region.csv` (14 KB); Geolocation incl. **Western Visayas**. Fetched by `fetch_economic.py` (DB 2D/2022). Supersedes the 2015 subset; more sectors under DB 2D/2G if needed |
| PSA-PVRTY | [PSA OpenStat DB__3D](https://openstat.psa.gov.ph) — poverty threshold + incidence by region/province (incl. Region VI + Iloilo province) | Econ | 2006–2015 | open gov | PSA OpenStat PX-Web API | M | ✅ CSV 11 KB (`psa_openstat_poverty_threshold_by_region.csv`) |
| PSA-TRADE | [PSA OpenStat DB__2D](https://openstat.psa.gov.ph) — wholesale & retail trade establishments (partial ASPBI proxy) | Econ | 2015 | open gov | PSA OpenStat PX-Web API | M | ✅ CSV 49 KB (`psa_openstat_trade_establishments_2015.csv`) |
| FIES | [PSA FIES 2023 via OpenStat](https://openstat.psa.gov.ph) — income & expenditure by Region/Province/HUC | Econ | 2023 | open gov | PSA OpenStat PX-Web API | M | ✅ **2023** (full release IS on OpenStat — the prior "not in OpenStat" note was stale) — `psa_openstat_fies2023_income_expenditure_by_region.csv` incl. **City of Iloilo** (101k families, avg income ₱478.7k, expenditure ₱306.7k) + `psa_openstat_fies2023_gini_by_region.csv`. Fetched by `fetch_economic.py` (DB 1E/IE); 12 FIES tables available |
| DOT-TOUR | [DOT tourism arrivals](https://tourism.gov.ph/tourism-statistics) (visitor arrivals by region 2024) | Econ | 2024 | open gov | direct | M | ☐ **lowest priority — changes no confidence tier.** OpenStat 2I = tourism **expenditure** only (national), already in hand (`psa_openstat_tourism_expenditure_national.csv`). Regional **arrivals** exist only on tourism.gov.ph (JS SPA) → browser download if the fidelity is ever needed: tourism.gov.ph/tourism-statistics → "Visitor Arrivals by Region" 2024 → `raw/economic/DOT_VisitorArrivals_Region_2024.xlsx` |
| PSA-TOUR | [PSA OpenStat DB__2I](https://openstat.psa.gov.ph) — national inbound tourism expenditure 2000–2024 | Econ | 2000–2024 | open gov | PSA OpenStat PX-Web API | M | ✅ CSV 2.4 KB (`psa_openstat_tourism_expenditure_national.csv`) |
| PSA-GVA | [PSA OpenStat DB__2B__NA](https://openstat.psa.gov.ph) — GVA in accommodation & food service 2000–2025 | Econ | 2000–2025 | open gov | PSA OpenStat PX-Web API | M | ✅ CSV 2.6 KB (`psa_openstat_gva_accommodation_food_service.csv`) |
| WB-ECON | [World Bank Open Data API](https://api.worldbank.org/v2/country/PH/) — Philippines GDP/cap, GINI, poverty, unemployment, GNI, urban %, GDP growth (2017–2024) | Econ | 2017–2024 | CC BY 4.0 | REST API | M | ✅ 7 JSON files (1.6–2.1 KB each): `wb_ph_gdp_per_capita_usd.json`, `wb_ph_gini_index.json`, `wb_ph_poverty_headcount_215usd.json`, `wb_ph_unemployment_rate.json`, `wb_ph_gni_per_capita_atlas.json`, `wb_ph_urban_population_pct.json`, `wb_ph_gdp_growth_rate.json` |
| HDX-PVRTY | [HDX Philippines poverty statistics](https://data.humdata.org/dataset/philippines-poverty-statistics) — annual per-capita poverty threshold by region XLSX (cross-reference to PSA-PVRTY) | Econ | 2006–2020 | open gov | HDX direct | M | ✅ XLSX 2.7 MB (`hdx_ph_poverty_threshold_by_region.xlsx`) |

### Ecological / Societal
| ID | Dataset | Dim | Vintage | License | Access | Conf | Status |
|---|---|---|---|---|---|---|---|
| OPENAQ | [OpenAQ API](https://docs.openaq.org/) + [EMB live air](https://air.emb.gov.ph/ambient-air-quality-monitoring/) (PM2.5/PM10/NO2/SO2/CO/O3) | Eco | live | open | API (key) | H | ⏳ |
| S5P-NO2 | [Sentinel-5P NO₂](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S5P_OFFL_L3_NO2) | Eco | live | open | GEE | M | ⏳ |
| LST | [Landsat 8/9 LST](https://www.usgs.gov/landsat-missions) (urban heat island) | Eco/Societal | live | open | GEE/USGS | M | ⏳ |
| S1-GFM | [Copernicus Global Flood Monitoring](https://global-flood.emergency.copernicus.eu/) — 2024 Iloilo flood extent (validation) | Eco | 2015→ | open | direct | M | ⏳ |
| PAGASA-NOAH | [PAGASA flood maps](https://bagong.pagasa.dost.gov.ph/products-and-services/flood-hazard-maps) + [Project NOAH](https://noah.up.edu.ph/) | Eco | current | open | direct | H | ☐ |
| NHCP | [NHCP declared heritage sites](https://nhcp.gov.ph/) + OSM heritage tags | Societal | current | open | direct/API | M | ☐ |

### Knowledge base (GraphRAG corpus)
| ID | Dataset | Dim | Vintage | Access | Conf | Status |
|---|---|---|---|---|---|---|
| LIT-CALDERON | [Calderon 2014 Iloilo BRT model (TSSP)](https://ncts.upd.edu.ph/tssp/wp-content/uploads/2018/08/Calderon14.pdf) | KB/Behav | 2014 | PDF | H | ✅ |
| LIT-BIKE19 | [TSSP-2019 Iloilo bicycle-use study](https://ncts.upd.edu.ph/tssp/wp-content/uploads/2019/09/TSSP2019-04_Factors-Influencing-Bicycle-Use-in-a-Medium-Sized-City-the-Case-of-Iloilo-1-City-Philippines.pdf) | KB/Behav | 2019 | PDF | H | ✅ |
| LIT-BIKE-SERPP | [SERP-P "Infrastructure Attracts" (Macalalag)](https://serp-p.pids.gov.ph/publication/public/view?slug=infrastructure-attracts-the-case-of-iloilo-city-s-cycling-infrastructure) | KB/Behav | 2021 | landing | H | ☐ |
| LIT-POPGIS | [Copernicus pop-forecast GIS 2021](https://isprs-archives.copernicus.org/articles/XLVI-4-W6-2021/185/2021/isprs-archives-XLVI-4-W6-2021-185-2021.pdf) | KB/Soc | 2021 | PDF (CC BY) | H | ✅ |
| LIT-CDP | [Iloilo CDP 2023-2028](https://iloilocity.gov.ph/main/wp-content/uploads/2023/05/CDP2023-2028_4-13_Final-Document.pdf) | KB | 2023 | PDF | H | ☐ (URL 404; via CPDO page) |
| LIT-ZONING | [Iloilo Zoning Ordinance (CLUP 2021-2029)](https://www.scribd.com/document/398676319/Zoning-Ordinance-Iloilo-City) | KB/Econ | 2021-29 | Scribd (manual) | M | ☐ |
| LIT-UNESCAP | [UNESCAP Iloilo e-mobility 2025](https://www.unescap.org/sites/default/d8files/event-documents/Session4_IloiloCity_Mr.Ronald.pdf) | KB | 2025 | PDF | H | ☐ |
| LIT-ICLEI | [ICLEI Iloilo roadmap](https://talkofthecities.iclei.org/rising-for-a-sustainable-future-iloilo-citys-roadmap/) | KB | 2025 | web | H | ☐ |
| LIT-CAA | [Clean Air Asia SMMR Iloilo (article)](https://cleanairasia.org/our-news/iloilo-city-strengthens-sustainable-urban-mobility-planning-through-training-workshop-data) | KB | 2024 | web | H | ☐ |
| LPTRP | [Enhanced LPTRP routes (MC 2023-036)](https://ilonggoengineer.com/iloilocity-lptrp/) — 25 routes, scrape to `raw/transport/` | Behav/KB | 2023 | scrape | M | ✅ **URL index only** — `raw/transport/routes.json` has 24 route titles + source URLs; **no route geometries**. Actual route geometries must be extracted from the linked URLs or from the **49 OSM PT relations** already in `raw/osm/iloilo_osm.json`. `lptrp_index.txt` mirrors the title list. |

---

## Tier B — optional, contact-free (catalog + script; fetch on demand, some need a free key)
| ID | Dataset | Why | Access |
|---|---|---|---|
| SENTINEL2 | [Sentinel-2 imagery](https://browser.dataspace.copernicus.eu/) | green cover, new-construction detection | account |
| TOMTOM | [TomTom Traffic API](https://developer.tomtom.com/) | real-time congestion baseline | key |
| HERE | [HERE Traffic API](https://developer.here.com/) | TomTom backup | key |
| OPENWEATHER | [OpenWeather API](https://openweathermap.org/api) | weather-trigger scenarios | key |
| GEMINI | [Gemini 3.1 (AI Studio)](https://aistudio.google.com/) | persona gen + orchestration | key |
| NAMRIA | [NAMRIA topo/coastline](https://www.namria.gov.ph/) | storm-surge, official base | direct |
| MOBILITY-ARCHIVE | [Google](https://www.google.com/covid19/mobility/) / Apple mobility archives | baseline behavior calibration (2020-22) | direct |

---

## Tier C — fidelity upgrades that need a human (open substitute already in hand → never a blocker)
Send-ready drafts in [`outreach/`](outreach/). See each file for who / exact ask / full message.
| ID | Who | Ask | Open substitute we already have | Draft |
|---|---|---|---|---|
| C-LTFRB | LTFRB Region VI + Iloilo transport office | authoritative route geometries, headways, fleet, ridership | published LPTRP guides + OSM (~80%, Medium conf) | `outreach/ltfrb-vi-foi.md` |
| C-CBMS | PSA Iloilo (033) 327-9219 | detailed CBMS poverty/household-profile tables | public barangay population + CCHAIN | `outreach/psa-cbms-request.md` |
| C-LIPAD | PhilLiDAR/LiPAD (lipad@dream.upd.edu.ph) | 1m DTM / classified LAZ | open 10m flood maps + GLO-30 DEM | `outreach/lipad-dtm-request.md` |
| C-CAA | Clean Air Asia (SMMR) | Iloilo data-inventory report | public article (enrichment only, not a sim input) | `outreach/clean-air-asia-smmr.md` |
