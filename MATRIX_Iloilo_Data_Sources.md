# MATRIX — Iloilo City Data Sources

**Pilot City:** Iloilo City, Western Visayas, Philippines
**Metropolitan Area:** Metro Iloilo–Guimaras (~1.04M population)
**Land Area:** 78.34 sq km (Iloilo City proper), ~362 sq km (Metro Iloilo)
**Barangays:** 180 (across 7 districts)
**Population:** ~473,728 (2024 census)

---

## Why Iloilo City for MATRIX

1. **ASEAN Clean Tourist City Award 2026** — direct narrative alignment with AAIH 2026 jury expectations.
2. **Tractable scale** — 78 sq km builds in 6 weeks; Davao at 244 sq km does not.
3. **Active smart city infrastructure** — free public Wi-Fi, electric PUJs, air quality monitors meeting international standards, barangay CCTV, navigation systems in taxis.
4. **Modal diversity perfect for behavioral simulation** — traditional jeepneys, modern PUJs (mini-bus jeepneys), Ceres provincial buses, P2P premium buses, tricycles, taxis, and the largest bike-lane network in the Philippines (~100 km).
5. **Suburban Metro Iloilo character** — Pavia, Oton, Leganes, San Miguel, Sta. Barbara, Cabatuan, Zarraga form a genuinely suburban developing network around the urban core.
6. **Institutional readiness** — Clean Air Asia SMMR data governance workshop (Nov 2024), Dutch government cycling partnership, ICLEI sustainability roadmap, UNESCAP electric mobility partnership.
7. **Peer-reviewed academic baseline** — JICA STRADA-3 BRT model published (Calderon, TSSP 2014); cycling infrastructure study (Macalalag, 2021); population forecasting GIS study (Philippine Geomatics Symposium, 2021).

---

## 2026-06 Update — Currency & Additions (live manifest: `data/INVENTORY.md`)

This catalog's narrative still holds, but **acquisition has moved to a live, tracked manifest at [`data/INVENTORY.md`](data/INVENTORY.md)** with re-runnable scripts in `data/fetch/`. Key changes from a June 2026 open-data review:

**Currency upgrades (prefer the newer vintage):**
- **PSA 2020 Census → 2024 POPCEN-CBMS** (enumerated Dec 2024, official 2025; all 180 Iloilo barangays). Adds household-profile indicators (water, electricity, internet, sanitation, food insecurity, disaster-prep) + geotagging. Keep 2020 only for time-trend. *(PSA blocks scripted downloads — fetch via browser.)*
- **Microsoft Building Footprints → Overture Maps (2026-05)** — buildings + places (POIs) + transportation; monthly.
- **ESA WorldCover 2021 → + Google Dynamic World** (near-real-time) for current land cover.
- **CLUP is 2021–2029** (not 2023–2032); pair with the **CDP 2023–2028**.
- **Transit:** the current **Enhanced LPTRP (LTFRB MC 2023-036)** — 25 routes, ~600 modern jeepneys — is published street-by-street; reconstruct from public guides + OSM (no FOI needed for the build).

**Major addition — Project CCHAIN (HDX, open):** 20 years (2003–2022) of **barangay-level** data for Iloilo across 30 tables — climate, **air quality**, ESA WorldCover, NOAH hazards, WorldPop population, Google/Microsoft buildings, **Meta Relative Wealth Index**, nighttime lights, **health-facility accessibility isochrones**, OSM POIs. One download covering large parts of the Social, Economic, and Ecological dimensions.

**Other additions by dimension (all open / contact-free):**
- *Engine:* Copernicus GLO-30 DEM; **PhilLiDAR/LiPAD** Iloilo 10 m flood maps + DTM; HazardHunterPH.
- *Economic (was weakest):* **BIR zonal values** (RDO 74); PSA ASPBI establishments; FIES income; DOT tourism arrivals.
- *Social / Societal:* **DOH National Health Facility Registry**; DepEd school masterlist; GHSL/WorldPop; **NHCP** heritage sites.
- *Ecological:* **OpenAQ + EMB** live air sensors; Sentinel-5P NO₂; Landsat 8/9 LST (urban heat); **Copernicus Sentinel-1 Global Flood Monitoring** (2024 Iloilo flood extent, for validation).

**Outreach is last-resort only.** Four send-ready drafts in [`data/outreach/`](data/outreach/) (LTFRB VI, PSA CBMS, PhilLiDAR 1 m DTM, Clean Air Asia) — each a *fidelity upgrade* with an open substitute already in hand; **none blocks the build.**

---

## Tier 1 — Core Geospatial and Network Data (Day 1 download)

### 1.1 OpenStreetMap Iloilo City Extract

**Why:** Foundation layer. Road network, jeepney routes, bike lanes, points of interest, building footprints. Sufficient detail for SUMO network generation via `osmnx` + `netconvert`.

**Sources:**
- **Geofabrik PH extract:** https://download.geofabrik.de/asia/philippines.html (entire country .osm.pbf, ~700MB)
- **MapTiler Davao/Iloilo tiles:** https://data.maptiler.com/downloads/dataset/osm/asia/philippines/ (city-specific extracts)
- **Overpass API:** https://overpass-turbo.eu/ (for custom bounded queries — fastest for the 78 sq km Iloilo footprint)
- **HOTOSM Export Tool:** https://export.hotosm.org/ (filtered .shp / .geojson exports)

**Bounding box for Iloilo City Proper:** approx. `10.65,122.50,10.78,122.61` (south, west, north, east)
**Bounding box for Metro Iloilo–Guimaras:** approx. `10.55,122.40,10.85,122.80`

**License:** ODbL — free to use, must attribute OpenStreetMap contributors.

---

### 1.2 Iloilo Public Transport Routes (OSM-tagged)

**Why:** Jeepney and UV Express routes in Iloilo are already mapped in OSM with the Philippines-specific tagging scheme. Less rich than Metro Manila but enough for a working baseline.

**Sources:**
- **OSM Wiki PH Public Transport guide:** https://wiki.openstreetmap.org/wiki/Philippines/Public_transportation
- **Query Overpass for `route=bus` and `route=jeepney` within Iloilo bbox**
- **GTFS conversion tool:** https://github.com/grote/osm2gtfs — convert OSM transit data into a GTFS feed for OpenTripPlanner ingestion

**Note:** Iloilo does *not* have a published municipal GTFS feed like sakayph for Manila. You will likely need to build a partial GTFS from OSM + LTFRB route descriptions (next item).

---

### 1.3 LTFRB Western Visayas Route Plans

**Why:** Authoritative route definitions for modern PUJs operating in Iloilo. Iloilo was one of the first cities to roll out modern (mini-bus) jeepneys under the PUVMP — these routes are documented.

**Sources:**
- **LTFRB official routes (FOI):** https://www.foi.gov.ph/agencies/ltfrb/
- **LTFRB Regional Office VI (Western Visayas):** file FOI request for "Iloilo City modern PUJ route plan"
- **DOTr FOI portal:** https://www.foi.gov.ph/agencies/dotr/
- **Successful precedent:** DOTr has previously granted route maps via FOI within ~30 days (see Davao HPBS FOI #DOTr-786801430487, approved 2020)

**Filing tip:** File on Day 1. Even if data arrives late, the FOI receipt strengthens your "real-world deployment" narrative.

---

## Tier 2 — Demographic, Climate, and Land Use Data (Open Download)

### 2.1 Philippine Statistics Authority (PSA) — 2020 Census + 2024 PopCen

**Why:** Barangay-level population, household, and demographic data. Critical for calibrating commuter agent populations and mode-share archetypes.

**Sources:**
- **2020 Census of Population and Housing:** https://psa.gov.ph/content/2020-census-population-and-housing-2020-cph-population-counts-declared-official-president
- **2024 PopCen Update:** https://psa.gov.ph/content/2024-census-population-popcen-population-counts-declared-official-president
- **Western Visayas Region VI tables:** https://psa.gov.ph/system/files/phcd/2022-12/%281%29%20Region%206_final.xlsx (XLSX direct download)
- **Regional Social and Economic Trends (RSET) 2021:** https://rsso06.psa.gov.ph/sites/default/files/RSET%202021_Western%20Visayas.pdf

**Format:** XLSX, PDF tables.
**License:** Open government data, attribution required.

---

### 2.2 Iloilo City Comprehensive Land Use Plan (CLUP) 2021–2029

**Why:** Zoning, infrastructure, transport vision documented by the city itself. Use for land-use overlay and TOD scoring inputs.

**Sources:**
- **CLUP PDF (Volume 1):** Iloilo City Government — request directly via city.iloilo.gov.ph or through the City Planning and Development Office (CPDO)
- **City Government Portal:** https://www.iloilocity.gov.ph/

---

### 2.3 OpenWeather API — Climate Triggers

**Why:** Weather-conditional scenarios (typhoon, monsoon flooding) are concrete "what-if" inputs the simulation engine handles well.

**Sources:**
- **OpenWeather Free Tier:** https://openweathermap.org/api — 1000 calls/day, current weather + 5-day forecast
- **Iloilo City coordinates:** lat 10.7202, lon 122.5621

---

### 2.4 PAGASA Flood and Climate Data

**Why:** Iloilo experienced severe flooding most recently in 2024; flood corridors directly affect transit behavior. Adds resilience angle for the SDG 13 / Climate Action narrative.

**Sources:**
- **PAGASA Climate Information:** https://www.pagasa.dost.gov.ph/climate
- **Project NOAH (Nationwide Operational Assessment of Hazards):** https://noah.up.edu.ph/
- **NOAH hazard maps for Iloilo:** flood, landslide, storm surge layers

---

## Tier 3 — Traffic, Mobility, and Real-Time APIs

### 3.1 TomTom Traffic API (Developer Tier)

**Why:** Real-time and historical congestion data for Iloilo. The free developer tier covers prototype-scale usage.

**Sources:**
- **TomTom Traffic API:** https://developer.tomtom.com/traffic-api/documentation/product-information/introduction
- **TomTom Traffic Index (Iloilo):** https://www.tomtom.com/traffic-index/ (search Iloilo)
- **Pricing:** Free tier covers 2,500 requests/day, enough for prototype + live demo

**Documentation needed in submission:** Cite TomTom as a baseline traffic-conditions source.

---

### 3.2 HERE Traffic API (Backup)

**Why:** Backup if TomTom rate-limits during demos.

**Sources:**
- **HERE Developer Portal:** https://developer.here.com/
- **Free tier:** 250K requests/month

---

### 3.3 Google Mobility Index (Aggregated)

**Why:** Already discontinued for new data but historical 2020–2022 data is still downloadable. Useful for calibrating baseline commuter behavior patterns.

**Sources:**
- **Google COVID-19 Community Mobility Reports archive:** https://www.google.com/covid19/mobility/
- **Apple Mobility Trends archive:** various academic mirrors (archived)

---

## Tier 4 — Specialized Studies and Institutional Reports

### 4.1 Calderon et al. (2014) — Iloilo BRT Modeling (TSSP)

**Why:** JICA STRADA-3 transit model for Iloilo. Peer-reviewed baseline. **Cite for validation methodology.**

**Sources:**
- **PDF:** https://ncts.upd.edu.ph/tssp/wp-content/uploads/2018/08/Calderon14.pdf
- **Citation:** Calderon, et al. (2014). *Introduction of Bus and BRT Systems along a Major Road Corridor in Iloilo City.* TSSP Annual Conference.

---

### 4.2 Macalalag (2021) — Iloilo Bicycle Infrastructure Study

**Why:** Empirical evidence on Iloilo cycling adoption. Critical for the bike-lane behavioral layer.

**Sources:**
- Search Google Scholar: `Macalalag Iloilo bicycle infrastructure 2021`
- Likely deposited in UP Diliman or UP Visayas repositories

---

### 4.3 Forecasting Urban Population Distribution of Iloilo City (Philippine Geomatics 2021)

**Why:** GIS-based barangay-level population forecasting using OLS + spatial lag models. Direct methodological reference for our barangay-level commuter agent generation.

**Sources:**
- **PDF:** https://isprs-archives.copernicus.org/articles/XLVI-4-W6-2021/185/2021/isprs-archives-XLVI-4-W6-2021-185-2021.pdf
- **License:** CC BY 4.0 (citable, reusable)

---

### 4.4 Iloilo City Sustainable Urban Mobility — Clean Air Asia SMMR (2024)

**Why:** Documents Iloilo's *current* data inventory and data gaps as identified by the city itself. **Perfect for the AI-Use & Ethics Report's stakeholder engagement section.**

**Sources:**
- **Clean Air Asia article:** https://cleanairasia.org/our-news/iloilo-city-strengthens-sustainable-urban-mobility-planning-through-training-workshop-data
- **Sustainable Mobility, Manila Region (SMMR) Project:** contact Clean Air Asia for full report

---

### 4.5 UNESCAP Iloilo Electric Mobility Document (2025)

**Why:** Recent (July 2025) UNESCAP session document on Iloilo urban mobility. Directly aligns with ASEAN clean city framing.

**Sources:**
- **PDF:** https://www.unescap.org/sites/default/d8files/event-documents/Session4_IloiloCity_Mr.Ronald.pdf
- **Title:** *Urban Mobility in Iloilo City: Challenges, Perspectives, and How Electric [Vehicles fit in]*

---

### 4.6 ICLEI Iloilo Sustainability Roadmap

**Why:** International institutional partnership credibility for the pitch.

**Sources:**
- **ICLEI CityTalk Iloilo article:** https://talkofthecities.iclei.org/rising-for-a-sustainable-future-iloilo-citys-roadmap/

---

## Tier 5 — Imagery and Spatial Layers

### 5.1 Sentinel-2 Satellite Imagery (ESA Copernicus)

**Why:** 10m resolution multispectral imagery for land-use classification, identifying informal settlements, and detecting new construction not yet in OSM.

**Sources:**
- **Copernicus Open Access Hub:** https://scihub.copernicus.eu/
- **AWS Sentinel-2 Public Dataset:** https://registry.opendata.aws/sentinel-2/
- **Sentinel Hub EO Browser:** https://apps.sentinel-hub.com/eo-browser/ (free, browser-based)

---

### 5.2 PhilGIS — Philippine GIS Data Portal

**Why:** Free Philippine-specific shapefiles including provincial and municipal boundaries.

**Sources:**
- **PhilGIS:** http://philgis.org/
- **Available layers:** admin boundaries, roads, rivers, land cover

---

### 5.3 Microsoft Building Footprints (Bing Maps)

**Why:** AI-generated building footprints across the Philippines. Useful for population disaggregation and pedestrian flow modeling.

**Sources:**
- **GitHub:** https://github.com/microsoft/GlobalMLBuildingFootprints
- **License:** ODbL

---

## Tier 6 — Tools and Libraries (Open Source)

| Tool | Purpose | URL | License |
|---|---|---|---|
| Eclipse SUMO | Urban mobility simulation | https://eclipse.dev/sumo/ | EPL 2.0 |
| OSMnx | OSM → graph network in Python | https://osmnx.readthedocs.io/ | MIT |
| ChromaDB | Vector store for GraphRAG | https://www.trychroma.com/ | Apache 2.0 |
| Microsoft GraphRAG | Knowledge graph + retrieval | https://github.com/microsoft/graphrag | MIT |
| LightRAG | Lightweight GraphRAG alternative | https://github.com/HKUDS/LightRAG | MIT |
| Mesa (Python ABM) | Lightweight backup simulator | https://mesa.readthedocs.io/ | Apache 2.0 |
| OpenTripPlanner | Multimodal routing | https://www.opentripplanner.org/ | LGPL |
| Polars | Fast tabular ETL | https://pola.rs/ | MIT |
| DuckDB | Embedded analytical DB | https://duckdb.org/ | MIT |
| Deck.gl | WebGL map visualization | https://deck.gl/ | MIT |
| Mapbox GL JS / MapLibre GL | Map rendering | https://maplibre.org/ | BSD-3 |
| FastAPI | Backend API | https://fastapi.tiangolo.com/ | MIT |
| Next.js 14 | Frontend framework | https://nextjs.org/ | MIT |
| Supabase | Postgres + Auth + Storage | https://supabase.com/ | Apache 2.0 |

---

## Day 1 Action Checklist

Once your team commits to Iloilo, execute these in parallel on Day 1 (May 15–16):

**Track A — Data acquisition (any team member):**
- [ ] Download Geofabrik PH .osm.pbf
- [ ] Run Overpass query for Iloilo City + Metro Iloilo bounding box
- [ ] Download PSA Region VI 2020 census tables
- [ ] Download UNESCAP Iloilo electric mobility PDF
- [ ] Download Calderon 2014 BRT modeling paper (PDF)
- [ ] Download Iloilo population forecasting paper (PDF)

**Track B — FOI filings (team lead, in parallel):**
- [ ] File LTFRB Region VI FOI request for "Iloilo City modern PUJ route plan and operational data"
- [ ] File DOTr FOI request for "Iloilo City public transport route inventory"
- [ ] File PSA FOI request for "Iloilo City barangay-level commuter household data" (if needed beyond 2020 census)
- [ ] Email Clean Air Asia for SMMR Iloilo data inventory report

**Track C — Account creation:**
- [ ] Register TomTom Developer account (free tier)
- [ ] Register HERE Developer account (backup)
- [ ] Register OpenWeather API key
- [ ] Register Sentinel Hub account
- [ ] Verify Google AI Studio access for Gemini 3.1 Flash-Lite

**Track D — Infrastructure setup:**
- [ ] Create GitHub org repo (public, MIT license)
- [ ] Provision Supabase project
- [ ] Set up Vercel deployment
- [ ] Pull Eclipse SUMO Docker image
- [ ] Test OSM → SUMO conversion on a small Iloilo neighborhood (e.g., Mandurriao District)

If all tracks complete by end of Day 2, you are on schedule for the Tier 2 feature ceiling.

---

## What Changes in MATRIX.md if We Confirm Iloilo

If you confirm Iloilo as the pilot city, here is the diff against the current MATRIX.md:

1. **Pilot city pivot:** Metro Manila corridors → Iloilo City + Metro Iloilo–Guimaras
2. **Mode-share anchor recalibration:** Manila modes (50% jeepney / 10% bus / 8% rail / 15% informal / 17% private) → Iloilo modes (estimated: heavy jeepney + modern PUJ, no rail, significant bike share, moderate tricycle in suburban barangays, Ceres provincial bus)
3. **Government client narrative:** DOTr / MMDA / LRTA → DOTr Regional Office VI / LTFRB Region VI / Iloilo City Planning and Development Office
4. **Real-estate client narrative:** Ayala Land / Megaworld (Metro Manila projects) → Megaworld (Iloilo Business Park), Ayala Land (Sicogon, Atria Park District), local developers
5. **Validation corridor:** EDSA / LRT-1 → Diversion Road / Iloilo–Cabatuan airport corridor / Sta. Barbara–Iloilo City spine
6. **Scaling story:** ASEAN informal transit → ASEAN clean & multimodal cities (Iloilo's bike-capital story plays globally)
7. **New angle:** ASEAN Clean Tourist City Award 2026 → tie directly to AAIH 2026 theme
8. **DROP:** MMDA traffic flow data, LRTA / MRT-3 ridership, DILG MC 2020-036 (already removed), Caloocan TRID 2013 study
9. **ADD:** Calderon BRT model, UNESCAP Iloilo electric mobility, Clean Air Asia SMMR data governance, ICLEI sustainability roadmap, Dutch government cycling partnership
10. **PWA companion app:** Repositioned from "tricycle visibility" → "Iloilo cyclist + jeepney rider behavioral mapping" (positive framing, smaller user base to recruit)

Confirm Iloilo and I'll regenerate MATRIX.md with these changes baked in.
