# MATRIX — Data Readiness by Impact Dimension

How the acquired data maps to MATRIX's five impact dimensions + the simulation engine.
This is the bridge from [INVENTORY.md](INVENTORY.md) (what we have) to the spec work
(PRD/SDD): it shows where data is **High** confidence vs. where the model must declare a
**confidence floor** — the honesty principle that is MATRIX's differentiator.

**Legend:** confidence H/M/L · ✅ in hand · ⏳ scripted/keyed · ✋ outreach archived (WONT-FILE — CR-016 open-data-only)

| Dimension | Data in hand (INVENTORY IDs) | Conf | Real gaps → next |
|---|---|---|---|
| **Engine / Base** | OSM network ✅ · Overture buildings/POIs ✅ · land-use ✅ | **H** | DEM gradients: GLO-30 ⏳ / LiPAD 10 m flood open ✅ path · refresh: [OPEN_REFRESH.md](OPEN_REFRESH.md) |
| **Behavioral** *(trip gen, mode shift, ped flow)* | OSM + LPTRP index + PT relations ✅ · Calderon 2014 ✅ · Tier-B WorldPop demand ✅ (`demand_calibration.py`, `MATRIX_DEMAND_SCALE`) | **H** network / **M** behavior | Mode-share stays **literature** (no FOI). VAL-01 live NRMSE at API startup (PASS or honest FAIL). Refresh OSM + recalibrate demand monthly / pre-demo. |
| **Social** *(equity, displacement, access)* | CCHAIN WorldPop + RWI + health isochrones ✅ · DOH/OSM POIs ✅ | **M–H** | Open only: GHSL/WorldPop freshness; CBMS FOI **wont-file** (use CCHAIN) |
| **Economic** *(land value, footfall, jobs, tax)* | BIR CSV ✅ · FIES/ASPBI OpenStat ✅ · WB + CCHAIN lights/buildings ✅ | **M** | Skip DOT regional tourism (no conf unlock). Re-pull OpenStat on refresh. |
| **Ecological** *(emissions, air, green, flood, heat)* | ESA WorldCover ✅ · NOAH hazards ✅ · WHO-EMEP ✅ · OpenAQ fixture ✅ | **H** hazards/green / **M→L** air | LiPAD 10 m hazard ∩ roads · OpenAQ free key · GFM event VAL-02 stays NOT_RUN |
| **Societal** *(heritage, health, walkability, noise)* | OSM heritage ✅ · CCHAIN health ✅ · bike/walk lit ✅ | **M** | NHCP FOI **wont-file** — keep OSM historic tags |
| **Knowledge base** *(GraphRAG)* | Calderon, TSSP-2019, ISPRS ✅ | **H** | Open web corpus only (no CPDO chase) |

## Read-out for the spec

- **All five dimensions have real Iloilo data at barangay granularity today** — MATRIX is data-ready to spec and build.
- **Strongest:** Engine, Behavioral (network), Ecological (hazards/green) — High.
- **Implementation Status:** All five impact modules (Behavioral, Ecological, Social, Economic, Societal) are implemented in the kernel (`app/packages/kernel/matrix_kernel/modules/`) as of Milestone A completion. They successfully consume the baseline/scenario trajectories and return glass-box provenanced results.
- **Confidence-floor dimensions:** Economic is Medium (FIES/ASPBI/BIR in hand). Behavioral **mode-share stays M** on literature — **CR-016 open-data-only** (FOI wont-file); do not invent shares. VAL-01 absolute corridor volumes are directional.
- **Economic uplift summary (2026-06-02):** OpenStat + World Bank fetches; city proxies remain CCHAIN RWI + lights + buildings.
- **Nothing blocks the build.** Freshness = [OPEN_REFRESH.md](OPEN_REFRESH.md). Outreach drafts under `outreach/` are **archive only** (CR-016).
- **Post-gazetteer backlog:** [CR-019](../docs/cr-019-credibility-next-steps.md) — ship live-net gazetteer (CR-018); do not raise chips by wiring unused files; later work is independent VAL-01 + named provisional methods.
