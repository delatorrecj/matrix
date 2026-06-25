/**
 * Dataset metadata registry (glass-box presentation).
 *
 * Transcribed from data/INVENTORY.md. Only enriches IDs already sent by the
 * kernel — never invents dataset lineage client-side (PRD-F14).
 */

import type { InputDataset } from "@/components/InspectDrawer";

export interface DatasetMeta {
  id: string;
  name: string;
  sourceLabel: string;
  url?: string;
  license?: string;
  vintage?: string;
  tier?: string;
  confidence?: string;
  sourceNote?: string;
}

/** Keyed by INVENTORY id (and common kernel aliases). */
export const DATASET_REGISTRY: Record<string, DatasetMeta> = {
  "OSM-ILO": {
    id: "OSM-ILO",
    name: "OpenStreetMap Iloilo extract",
    sourceLabel: "Overpass API",
    url: "https://overpass-api.de/api/interpreter",
    license: "ODbL",
    vintage: "live",
    tier: "A",
    confidence: "High",
    sourceNote: "Roads, transit, POIs, heritage tags for the Iloilo pilot bbox.",
  },
  OVERTURE: {
    id: "OVERTURE",
    name: "Overture Maps",
    sourceLabel: "Overture Maps Foundation",
    url: "https://docs.overturemaps.org/download/",
    license: "ODbL/CDLA",
    vintage: "2026-05",
    tier: "A",
    confidence: "High",
    sourceNote: "Buildings, places (POIs), and transportation features.",
  },
  "PERSONA-POOL": {
    id: "PERSONA-POOL",
    name: "Commuter persona pool",
    sourceLabel: "MATRIX kernel (literature-anchored static pool)",
    vintage: "2026",
    tier: "B",
    confidence: "Medium",
    sourceNote: "Mode-share anchored to Calderon 2014 Iloilo travel survey.",
  },
  "SUMO-NET": {
    id: "SUMO-NET",
    name: "SUMO road network",
    sourceLabel: "Eclipse SUMO / OSM import",
    vintage: "live",
    tier: "A",
    confidence: "High",
    sourceNote: "Physical network used for TraCI simulation.",
  },
  "WHO-EMEP": {
    id: "WHO-EMEP",
    name: "WHO/EMEP emission factors",
    sourceLabel: "WHO Air Quality Guidelines",
    url: "https://www.who.int/teams/environment-climate-change-and-health/air-quality-and-health/health-impacts/air-quality-guidelines",
    vintage: "2023",
    tier: "A",
    confidence: "High",
    sourceNote: "Transport emission factors per vehicle-km by mode.",
  },
  EMB: {
    id: "EMB",
    name: "EMB ambient air quality monitoring",
    sourceLabel: "DENR-EMB Philippines",
    url: "https://air.emb.gov.ph/ambient-air-quality-monitoring/",
    license: "open gov",
    vintage: "live",
    tier: "A",
    confidence: "High",
    sourceNote: "Ground PM₂.₅/PM₁₀/NO₂ readings for calibration.",
  },
  OPENAQ: {
    id: "OPENAQ",
    name: "OpenAQ global air quality API",
    sourceLabel: "OpenAQ",
    url: "https://docs.openaq.org/",
    license: "CC0",
    vintage: "live",
    tier: "A",
    confidence: "High",
  },
  "S5P-NO2": {
    id: "S5P-NO2",
    name: "Sentinel-5P NO₂ column",
    sourceLabel: "Copernicus / Google Earth Engine",
    url: "https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S5P_OFFL_L3_NO2",
    license: "open",
    vintage: "live",
    tier: "B",
    confidence: "Medium",
    sourceNote: "Satellite proxy — regional column, not ground PM₂.₅.",
  },
  CCHAIN: {
    id: "CCHAIN",
    name: "Project CCHAIN",
    sourceLabel: "Humanitarian Data Exchange",
    url: "https://data.humdata.org/dataset/project-cchain",
    license: "open",
    vintage: "2003–2022",
    tier: "A",
    confidence: "High",
    sourceNote: "Barangay-level Iloilo climate, socio-economic, and health tables.",
  },
  WORLDCOVER: {
    id: "WORLDCOVER",
    name: "ESA WorldCover 10m",
    sourceLabel: "ESA WorldCover",
    url: "https://esa-worldcover.org/en/data-access",
    license: "CC BY 4.0",
    vintage: "2021",
    tier: "A",
    confidence: "High",
  },
  LIPAD: {
    id: "LIPAD",
    name: "PhilLiDAR/LiPAD Iloilo flood hazard",
    sourceLabel: "LiPAD / UP DREAM",
    url: "https://lipad-fmc.dream.upd.edu.ph/",
    license: "open",
    vintage: "2015–2017",
    tier: "A",
    confidence: "High",
    sourceNote: "5-year and 25-year flood hazard rasters for Iloilo.",
  },
  DEM: {
    id: "DEM",
    name: "Copernicus GLO-30 DEM",
    sourceLabel: "Copernicus DEM",
    url: "https://copernicus-dem-30m.s3.amazonaws.com/",
    license: "open",
    vintage: "2021",
    tier: "A",
    confidence: "High",
  },
  "DEM-GLO30": {
    id: "DEM-GLO30",
    name: "Copernicus GLO-30 DEM",
    sourceLabel: "Copernicus DEM",
    url: "https://copernicus-dem-30m.s3.amazonaws.com/",
    license: "open",
    vintage: "2021",
    tier: "A",
    confidence: "High",
  },
  NHFR: {
    id: "NHFR",
    name: "DOH National Health Facility Registry",
    sourceLabel: "Department of Health Philippines",
    url: "https://nhfr.doh.gov.ph/Home",
    license: "open gov",
    vintage: "live",
    tier: "A",
    confidence: "High",
  },
  WorldPop: {
    id: "WorldPop",
    name: "WorldPop gridded population",
    sourceLabel: "WorldPop",
    url: "https://www.worldpop.org/",
    license: "open",
    vintage: "2023",
    tier: "A",
    confidence: "High",
  },
  "BIR-ZV": {
    id: "BIR-ZV",
    name: "BIR zonal values RDO 74 Iloilo",
    sourceLabel: "Bureau of Internal Revenue",
    url: "https://www.bir.gov.ph/zonal-values",
    license: "gov",
    vintage: "2021 (DO 17-2021)",
    tier: "B",
    confidence: "Medium",
    sourceNote: "Land-value schedule for Iloilo City (Sheet 9, 5,680 entries).",
  },
  "PSA-ASPBI": {
    id: "PSA-ASPBI",
    name: "PSA ASPBI (establishments & employment)",
    sourceLabel: "PSA OpenStat",
    url: "https://openstat.psa.gov.ph",
    license: "open gov",
    vintage: "2022",
    tier: "B",
    confidence: "Medium",
  },
  "PSA-OpenStat": {
    id: "PSA-OpenStat",
    name: "PSA OpenStat economic tables",
    sourceLabel: "PSA OpenStat",
    url: "https://openstat.psa.gov.ph",
    license: "open gov",
    vintage: "2022–2024",
    tier: "B",
    confidence: "Medium",
  },
  NHCP: {
    id: "NHCP",
    name: "NHCP declared heritage sites",
    sourceLabel: "National Historical Commission",
    url: "https://nhcp.gov.ph/",
    license: "open",
    vintage: "current",
    tier: "B",
    confidence: "Medium",
  },
  "TSSP-2019": {
    id: "TSSP-2019",
    name: "TSSP 2019 bike infrastructure survey",
    sourceLabel: "NCTS-UP / TSSP",
    vintage: "2019",
    tier: "B",
    confidence: "Medium",
    sourceNote: "Walkability and bike-lane coverage factors for Iloilo.",
  },
  "LIT-CALDERON": {
    id: "LIT-CALDERON",
    name: "Calderon 2014 Iloilo BRT model (TSSP)",
    sourceLabel: "NCTS-UP TSSP",
    url: "https://ncts.upd.edu.ph/tssp/wp-content/uploads/2018/08/Calderon14.pdf",
    vintage: "2014",
    tier: "A",
    confidence: "High",
    sourceNote: "Mode-share ground-truth anchor for Iloilo.",
  },
  Calderon2014: {
    id: "Calderon2014",
    name: "Calderon 2014 Iloilo travel survey",
    sourceLabel: "NCTS-UP TSSP",
    url: "https://ncts.upd.edu.ph/tssp/wp-content/uploads/2018/08/Calderon14.pdf",
    vintage: "2014",
    tier: "A",
    confidence: "High",
    sourceNote: "Literature citation key used in kernel references.",
  },
};

export function getDatasetMeta(id: string): DatasetMeta | undefined {
  return DATASET_REGISTRY[id];
}

/** Resolve kernel input_dataset_ids to InputDataset rows (id always present). */
export function resolveDatasetInputs(ids: string[]): InputDataset[] {
  return ids.map((id) => {
    const meta = getDatasetMeta(id);
    if (!meta) return { id };
    return {
      id: meta.id,
      name: meta.name,
      confidence: meta.confidence,
      vintage: meta.vintage,
      license: meta.license,
      tier: meta.tier,
      sourceNote: meta.sourceNote ?? meta.sourceLabel,
      url: meta.url,
    };
  });
}

export function resolveReferenceMeta(ref: string): DatasetMeta | undefined {
  return getDatasetMeta(ref);
}
