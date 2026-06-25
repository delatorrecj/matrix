import type { LucideIcon } from "lucide-react";
import {
  Building2,
  GraduationCap,
  ScanSearch,
  Scale,
  SlidersHorizontal,
  Wrench,
} from "lucide-react";

/** Five impact dimensions. Hues match globals.css `--color-dim-*` tokens. */
export const DIMENSIONS: { name: string; color: string; blurb: string }[] = [
  {
    name: "Behavioral",
    color: "#2563EB",
    blurb: "How people re-route and shift travel when the network changes.",
  },
  {
    name: "Social",
    color: "#DB2777",
    blurb: "Who is affected or displaced, and how the burden is shared.",
  },
  {
    name: "Economic",
    color: "#CA8A04",
    blurb: "Construction cost, land value, and livelihoods along the corridor.",
  },
  {
    name: "Ecological",
    color: "#16A34A",
    blurb: "Emissions and flood exposure under the simulated change.",
  },
  {
    name: "Societal",
    color: "#9333EA",
    blurb: "Access to services and long-run wellbeing across barangays.",
  },
];

export const GLASS_BOX: { icon: LucideIcon; title: string; body: string }[] = [
  {
    icon: ScanSearch,
    title: "Every number is traceable",
    body: "Each result carries the equation that produced it, the datasets it drew from, and a computed confidence level. Open the Inspect drawer on any figure to see its full provenance.",
  },
  {
    icon: Scale,
    title: "Honest by construction",
    body: "Outputs are confidence-anchored ranges, not false-precision point estimates. The AI narrates and cites the results. It never originates a number. A bias auditor keeps a public audit log.",
  },
  {
    icon: SlidersHorizontal,
    title: "One reality, five lenses",
    body: "A single agent-based simulation feeds all five impact modules, so the dimensions can never contradict each other. You score one simulated reality, not five disconnected guesses.",
  },
];

export const PROBLEM_CARDS: { title: string; body: string }[] = [
  {
    title: "Static studies can't predict emergent behavior",
    body: "A traffic count from 2022 won't predict how a new mall reshapes every household within three kilometers, or which jeepney route gains demand and which barangay loses footfall.",
  },
  {
    title: "Cross-domain impacts live in silos",
    body: "Environmental, transport, economic, and social reviews sit in different offices. By the time they reach the same desk, the project is often already approved.",
  },
  {
    title: "Existing tools need specialists",
    body: "Vissim, Aimsun, CityEngine, and AnyLogic require transport engineers or modelers, not the city planner asking a plain-language what-if.",
  },
];

export const TARGET_USERS: {
  icon: LucideIcon;
  title: string;
  who: string;
  useCase: string;
}[] = [
  {
    icon: Building2,
    title: "LGU planners and city government",
    who: "Iloilo CPDO, NEDA Region VI, DOTr Regional Office VI",
    useCase:
      "Pre-evaluate infrastructure proposals, prioritize capital projects, and validate impact assessments with simulation-backed evidence.",
  },
  {
    icon: Wrench,
    title: "Developers and master planners",
    who: "Megaworld Iloilo Business Park, Ayala Land, local developers",
    useCase:
      "Site selection, building placement, entrance design, and anticipating community pushback before public consultation.",
  },
  {
    icon: GraduationCap,
    title: "Civic and academic stakeholders",
    who: "UP Visayas SURP, Clean Air Asia, ICLEI, transport cooperatives",
    useCase:
      "Independent verification of impact claims, academic research, and policy advocacy with simulation-backed evidence.",
  },
];

export const PROOF_POINTS: string[] = [
  "Five dimensions from one simulation kernel: internally consistent, not five contradicting tools.",
  "Glass-box provenance: every output traces to an equation, named open data, and computed confidence.",
  "No hardware. Pure cloud and open data, deployable where IoT simulators can't afford to.",
  "Anchored to Iloilo, 2026 ASEAN Clean Tourist City Award (2nd time, Jan 30, 2026, Cebu).",
];

export const COMPETITORS: {
  name: string;
  strength: string;
  nlInput: boolean | "partial";
  fiveDimsOneRun: boolean | "partial";
  perDimConfidence: boolean;
  needsSpecialist: boolean;
}[] = [
  {
    name: "PTV Vissim / Aimsun",
    strength: "Microscopic traffic simulation",
    nlInput: false,
    fiveDimsOneRun: false,
    perDimConfidence: false,
    needsSpecialist: true,
  },
  {
    name: "ESRI CityEngine",
    strength: "3D urban / GIS modeling",
    nlInput: false,
    fiveDimsOneRun: false,
    perDimConfidence: false,
    needsSpecialist: true,
  },
  {
    name: "Replica",
    strength: "Data-driven mobility / activity models",
    nlInput: "partial",
    fiveDimsOneRun: false,
    perDimConfidence: false,
    needsSpecialist: true,
  },
  {
    name: "UrbanFootprint",
    strength: "Land-use + environmental scenario planning",
    nlInput: false,
    fiveDimsOneRun: "partial",
    perDimConfidence: false,
    needsSpecialist: true,
  },
  {
    name: "AnyLogic",
    strength: "General multi-method simulation",
    nlInput: false,
    fiveDimsOneRun: "partial",
    perDimConfidence: false,
    needsSpecialist: true,
  },
  {
    name: "MATRIX",
    strength: "Pre-construction 5-dim impact, glass-box",
    nlInput: true,
    fiveDimsOneRun: true,
    perDimConfidence: true,
    needsSpecialist: true,
  },
];

export const ASEAN_CITIES: {
  city: string;
  pattern: string;
  openData: string;
}[] = [
  {
    city: "Jakarta",
    pattern: "Ojek, angkot, bajaj, BRT TransJakarta",
    openData: "TransJakarta GTFS, OSM strong",
  },
  {
    city: "Bangkok",
    pattern: "Songthaew, tuk-tuk, motorcycle taxi, BTS/MRT",
    openData: "Strong GTFS, OSM strong",
  },
  {
    city: "Ho Chi Minh City",
    pattern: "Xe om, xe buyt, metro under construction",
    openData: "Limited GTFS, OSM strong",
  },
  {
    city: "Kuala Lumpur",
    pattern: "Rapid KL, bas mini, e-hailing",
    openData: "Rapid KL GTFS, OSM strong",
  },
];

export const TEAM: { name: string; roles: string; linkedin: string }[] = [
  {
    name: "Carlos Jerico Dela Torre",
    roles: "AI and Software Development, Product and Business Architecture, Team Lead",
    linkedin: "https://www.linkedin.com/in/delatorrecj",
  },
  {
    name: "Yushin Bjorn Matsuda",
    roles: "AI and Software Development, UI/UX Design",
    linkedin: "https://www.linkedin.com/in/matsuda-yushin",
  },
  {
    name: "Maria Espina",
    roles: "QA, UI/UX Design",
    linkedin: "https://www.linkedin.com/in/maria-espina-b89243309",
  },
  {
    name: "Rica Mae Mago",
    roles: "QA, Research and Marketing",
    linkedin: "https://www.linkedin.com/in/rica-mae-mago",
  },
  {
    name: "Russell Jay Fajardo",
    roles: "QA, Research and Marketing",
    linkedin: "https://www.linkedin.com/in/russell-jay-fajardo-775b19307",
  },
];

export const TECH_STACK: { category: string; items: string[] }[] = [
  {
    category: "Simulation",
    items: ["Eclipse SUMO via TraCI Python API", "OSMnx network ingestion"],
  },
  {
    category: "AI and ML",
    items: [
      "Azure OpenAI gpt-5.4 (orchestration, synthesis, personas)",
      "openai SDK to Azure AI Foundry v1 endpoint",
      "Microsoft GraphRAG + ChromaDB",
      "XGBoost corridor volume forecaster",
    ],
  },
  {
    category: "Backend",
    items: [
      "FastAPI + WebSocket progressive stream",
      "Postgres + PostGIS (in-memory fallback)",
      "Redis (persona pool, baseline, trajectory cache)",
    ],
  },
  {
    category: "Frontend",
    items: [
      "Next.js 14 App Router",
      "Tailwind CSS v4 + shadcn/ui",
      "Mapbox GL JS + Deck.gl TripsLayer",
    ],
  },
];

export const DATA_TIERS: { tier: string; label: string; examples: string }[] = [
  {
    tier: "Tier 1",
    label: "Day 1 downloadable",
    examples: "OSM Geofabrik PH, PSA census, Sentinel-2, PAGASA, NOAH, OpenWeather",
  },
  {
    tier: "Tier 2",
    label: "FOI-pending",
    examples: "LTFRB Region VI routes, PSA APIS barangay-level, Iloilo City CLUP",
  },
  {
    tier: "Tier 3",
    label: "Institutional outreach",
    examples: "Clean Air Asia SMMR data inventory, ICLEI roadmap data",
  },
  {
    tier: "Tier 4",
    label: "Academic baseline",
    examples: "Calderon 2014 BRT model, Macalalag 2021 bike study, Philippine Geomatics 2021",
  },
];

export const PIPELINE_STAGES: {
  startSec: number;
  endSec: number;
  label: string;
  detail: string;
}[] = [
  {
    startSec: 0,
    endSec: 5,
    label: "Parse",
    detail: "Natural-language query to structured simulation plan (Azure OpenAI)",
  },
  {
    startSec: 5,
    endSec: 15,
    label: "Retrieve",
    detail: "GraphRAG knowledge retrieval from ChromaDB corpus",
  },
  {
    startSec: 15,
    endSec: 60,
    label: "Simulate",
    detail: "SUMO agent run with pre-warmed persona pool and delta against nightly baseline",
  },
  {
    startSec: 60,
    endSec: 80,
    label: "Score",
    detail: "Five impact modules compute in parallel on one trajectory dataset",
  },
  {
    startSec: 80,
    endSec: 90,
    label: "Synthesize",
    detail: "Synthesis agent generates plain-language brief with citations",
  },
];

export const WHY_WINS: { title: string; claim: string }[] = [
  {
    title: "A combination that doesn't exist elsewhere",
    claim:
      "Plain-language input, five impact dimensions from one simulated reality, and per-dimension confidence: a combination not found in the tools planners typically evaluate.",
  },
  {
    title: "Built for real-time, built honestly",
    claim:
      "Interactive visualization with animated agent playback, unified-kernel architecture, and confidence-anchored outputs that respect data limits honestly.",
  },
  {
    title: "Grounded in Iloilo, scalable across ASEAN",
    claim:
      "Iloilo is actively building the data infrastructure MATRIX consumes. The ASEAN scaling path is concrete with no hardware dependency.",
  },
  {
    title: "Designed to be understood at a glance",
    claim:
      "Animated simulation playback shows how a project ripples through a city. Five dimensions tell one coherent story, anchored to Iloilo's 2026 ASEAN Clean Tourist City Award.",
  },
];

export const BIAS_MITIGATIONS: { title: string; body: string }[] = [
  {
    title: "Mode-share anchor",
    body: "Persona generation constrained to match Iloilo ground-truth mode share. Deviations beyond ±3% trigger reweighting.",
  },
  {
    title: "Public bias audit log",
    body: "A bias auditor runs after every persona batch and logs adjustments keyed to scenario_id.",
  },
  {
    title: "Confidence floor",
    body: "Dimensions below the confidence threshold are flagged directional only, not reported as precise.",
  },
  {
    title: "Open methodology",
    body: "Every simulation logs assumptions, data sources, and confidence anchors for reproducibility.",
  },
];
