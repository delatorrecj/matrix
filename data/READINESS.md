# MATRIX — Data Readiness by Impact Dimension

How the acquired data maps to MATRIX's five impact dimensions + the simulation engine.
This is the bridge from [INVENTORY.md](INVENTORY.md) (what we have) to the spec work
(PRD/SDD): it shows where data is **High** confidence vs. where the model must declare a
**confidence floor** — the honesty principle that is MATRIX's differentiator.

**Legend:** confidence H/M/L · ✅ in hand · ⏳ scripted/keyed · ✋ needs outreach (`outreach/`)

| Dimension | Data in hand (INVENTORY IDs) | Conf | Real gaps → next |
|---|---|---|---|
| **Engine / Base** | OSM network 12,579 ways ✅ · Overture segments 18,844 + connectors 18,893 + **148,630 buildings** ✅ · Overture/OSM land-use ✅ | **H** | DEM for gradients/flood (GLO-30 ⏳, PhilLiDAR ✋ — 10 m open) |
| **Behavioral** *(trip gen, mode shift, ped flow)* | road + transit network ✅ · OSM routes 54 + **published LPTRP 24 routes** ✅ · trip generators: Overture POIs 11,189 + OSM amenities + CCHAIN `osm_poi_*` ✅ · Calderon 2014 BRT calibration ✅ | **H** network / **M** behavior | **mode-share ground truth** is the soft spot — derived from literature, not a live travel survey → LTFRB FOI (`ltfrb-vi-foi.md` ✋) |
| **Social** *(equity, displacement, access)* | CCHAIN WorldPop 180 brgy ✅ · Meta **Relative Wealth Index** ✅ · **health-facility isochrones** (access time) ✅ · DOH health POIs + OSM schools/hospitals ✅ · Ookla internet ✅ | **M–H** | informal-settler maps (Sentinel-2 detect ⏳) · detailed CBMS tables (`psa-cbms-request.md` ✋) · POPCEN24 (manual) |
| **Economic** *(land value, footfall, jobs, tax)* | CCHAIN RWI + **nighttime lights** (activity proxy) ✅ · building stock 148k ✅ · **PSA poverty threshold + incidence by region/province** (Region VI + Iloilo rows) ✅ · **PSA wholesale/retail trade establishments 2015** (partial ASPBI proxy) ✅ · **PSA national tourism expenditure 2000–2024** ✅ · **PSA GVA accommodation & food service 2000–2025** ✅ · **World Bank PH GDP/cap, GINI, poverty, unemployment 2017–2024** ✅ · **HDX poverty threshold XLSX** (cross-ref) ✅ | **M** *(was L–M; macro baseline now solid)* | **BIR zonal values RDO 74** (☐ manual — best remaining ROI: land-value spatial layer for construction-cost simulation) · **PSA FIES 2023** (☐ manual — household income/expenditure by region) · **PSA ASPBI 2023** (☐ manual — full establishments/jobs by region) · **DOT regional visitor arrivals 2024** (☐ manual — for tourism-footfall calibration) |
| **Ecological** *(emissions, air, green, flood, heat)* | CCHAIN **ESA WorldCover** (green) ✅ · **NOAH hazards** flood/landslide/surge 180 brgy ✅ · `climate_indices` ✅ · OSM land-use/parks 643 ✅ | **H** hazards/green / **M** air | live air (OpenAQ ⏳ key / EMB) · DEM ⏳ · Landsat LST heat ⏳ · Sentinel-1 flood validation ⏳ |
| **Societal** *(heritage, health, walkability, noise)* | OSM heritage 117 ✅ · CCHAIN disease + health access ✅ · OSM bike/walk + Macalalag bike studies ✅ · Overture infrastructure 3,275 ✅ | **M** | NHCP declared-heritage list ☐ · noise = proximity proxy only (L) |
| **Knowledge base** *(GraphRAG)* | Calderon 2014, TSSP-2019 bike, ISPRS pop-forecast ✅ · catalog + READINESS + INVENTORY ✅ | **H** | Iloilo CDP/CLUP text (CDP URL 404 → CPDO) · UNESCAP/ICLEI (web) |

## Read-out for the spec

- **All five dimensions have real Iloilo data at barangay granularity today** — MATRIX is data-ready to spec and build.
- **Strongest:** Engine, Behavioral (network), Ecological (hazards/green) — High.
- **Confidence-floor dimensions:** Economic is now Medium (macro baseline acquired: poverty, trade, tourism, GVA, World Bank series); the remaining gap is the *spatial* land-value layer (BIR zonal values, ☐ manual) and 2023-vintage household income (FIES/ASPBI, ☐ manual). The **mode-share calibration** for Behavioral remains a soft spot.
- **Economic uplift summary (2026-06-02):** 12 files fetched via PSA OpenStat PX-Web API and World Bank Open Data — 4 CSV tables + 7 JSON indicator series + 1 XLSX cross-reference. All are national or regional (not city-level); city-level proxies remain CCHAIN RWI (barangay) + nighttime lights + 148 k building stock.
- **Nothing here blocks FMD or the build.** Remaining items are additive (more open data) or fidelity upgrades (the four `outreach/` drafts) — all with substitutes already in hand.
