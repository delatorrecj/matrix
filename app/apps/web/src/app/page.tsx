"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Map } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import DeckGL from "@deck.gl/react";
import { PolygonLayer } from "@deck.gl/layers";
import { Users, Briefcase, Leaf, HeartHandshake, Route, Map as MapIcon, Layers, Play, Pause, SkipBack, SkipForward, Loader2, WifiOff, AlertTriangle } from "lucide-react";

import { DimensionCard } from "@/components/DimensionCard";
import InspectDrawer, { ProvenanceData } from "@/components/InspectDrawer";
import { LayerLegend } from "@/components/LayerLegend";
import { AmbiguousScenarioError, ApiUnreachableError, createScenario } from "@/lib/api";

const MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty";

const INITIAL_VIEW_STATE = {
  longitude: 122.56,
  latitude: 10.71,
  zoom: 13,
  pitch: 45,
  bearing: 0
};

// Illustrative building footprints for the empty base map (visual placeholder
// only — real building extrusions stream with the simulation on /scenario/[id]).
type Building = { polygon: [number, number][]; height: number };
const BUILDINGS: Building[] = [
  { polygon: [[122.56, 10.71], [122.561, 10.71], [122.561, 10.711], [122.56, 10.711]], height: 20 },
  { polygon: [[122.562, 10.712], [122.563, 10.712], [122.563, 10.713], [122.562, 10.713]], height: 45 },
];

// Preset reference scenarios — each submits a real NL query to POST /scenario.
const PRESETS: { label: string; query: string }[] = [
  { label: "School in Molo", query: "What if we build a 3,000-seat school in Molo?" },
  { label: "BRT on Diversion Rd", query: "What if we run a BRT line along Diversion Road?" },
  { label: "Flooding Closure", query: "What if flooding closes the Diversion Road corridor for a day?" },
];

// Shown ONLY in the explicitly-labeled "Sample mode — API offline" state.
// These are illustrative sample values, never presented as simulation output.
const SAMPLE_PROVENANCE: ProvenanceData = {
  metric: "Economic Impact (SAMPLE — not a simulation result)",
  value: "₱12.5M",
  range: "₱8M – ₱15M",
  confidence: "Medium",
  confidenceBasis: "SAMPLE DATA — the MATRIX API is offline; this value is illustrative only and was not computed by the kernel.",
  equationId: "ECO-1",
  equationText: "ΔCost = Σ(Area_k * UnitCost_k) + Contingency",
  inputs: [
    { id: "DS-01", name: "BIR Zonal Values RDO 74", confidence: "High", vintage: "2023" },
    { id: "DS-02", name: "PSA ASPBI Construction Costs", confidence: "Medium", vintage: "2022" }
  ],
  assumptions: [
    "SAMPLE MODE: API offline — every value shown is an illustrative placeholder, not kernel output.",
    "Contingency buffer set at 15%",
    "Inflation adjustment of 4.5% applied to 2022 data"
  ],
  references: ["DPWH Standard Cost Guidelines (2023)"]
};

export default function MatrixCockpit() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [clarification, setClarification] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [sampleMode, setSampleMode] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [inspectMetric, setInspectMetric] = useState<string | null>(null);

  // Layer Toggles
  const [activeLayers, setActiveLayers] = useState<Record<string, boolean>>({
    buildings: true,
    agents: false,
    confidence: false,
  });

  const handleToggleLayer = (id: string) => {
    setActiveLayers(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleSimulate = async (overrideQuery?: string) => {
    const text = (overrideQuery ?? query).trim();
    if (!text || isSubmitting) return;

    setIsSubmitting(true);
    setClarification(null);
    setSubmitError(null);
    setSampleMode(false);

    try {
      const scenario = await createScenario(text);
      router.push(`/scenario/${scenario.scenario_id}`);
      // Keep the spinner visible while Next.js navigates away.
    } catch (err) {
      if (err instanceof AmbiguousScenarioError) {
        setClarification(err.message);
      } else if (err instanceof ApiUnreachableError) {
        setSampleMode(true);
      } else {
        setSubmitError(err instanceof Error ? err.message : "Scenario request failed");
      }
      setIsSubmitting(false);
    }
  };

  const handlePreset = (presetQuery: string) => {
    setQuery(presetQuery);
    void handleSimulate(presetQuery);
  };

  const layers = [
    activeLayers.buildings && new PolygonLayer({
      id: "buildings-layer",
      data: BUILDINGS,
      extruded: true,
      wireframe: true,
      getPolygon: (d: Building) => d.polygon,
      getElevation: (d: Building) => d.height,
      getFillColor: [200, 200, 200, 150],
      getLineColor: [100, 100, 100, 200],
    })
  ].filter(Boolean);

  return (
    <div className="relative h-[100dvh] w-full overflow-hidden bg-background text-foreground flex">

      {/* MAP STAGE (Background) */}
      <div className="absolute inset-0 z-0">
        <DeckGL
          initialViewState={INITIAL_VIEW_STATE}
          controller={true}
          layers={layers}
        >
          <Map mapStyle={MAP_STYLE} mapLib={maplibregl} />
        </DeckGL>
      </div>

      {/* LEFT RAIL: Scenario Bar */}
      <div className="absolute left-4 top-4 bottom-24 w-[320px] bg-surface/95 backdrop-blur-md shadow-md rounded-lg border border-border flex flex-col z-10 pointer-events-auto overflow-hidden">
        <div className="p-4 border-b border-border bg-primary/5">
          <h1 className="text-xl font-bold tracking-tight">MATRIX</h1>
          <p className="text-xs text-text-muted mt-1">Multi-Agent Twin for Routing & Infrastructure eXchange</p>
        </div>

        <div className="p-4 flex-1 overflow-y-auto">
          <label htmlFor="scenario-query" className="text-sm font-semibold mb-2 block">Scenario Query</label>
          <textarea
            id="scenario-query"
            className="w-full bg-background border border-border rounded-md p-3 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none resize-none min-h-[100px]"
            placeholder="e.g., What if we build a 3,000-seat school in Molo?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={isSubmitting}
          />
          <button
            className="w-full mt-3 bg-primary text-primary-foreground font-medium py-2 rounded-md hover:bg-primary-hover transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            onClick={() => handleSimulate()}
            disabled={isSubmitting || !query.trim()}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                Parsing scenario…
              </>
            ) : (
              "Simulate Scenario"
            )}
          </button>

          {clarification && (
            <div role="alert" className="mt-3 p-3 rounded-md border border-warning/30 bg-warning/10 text-sm">
              <div className="flex items-center gap-2 font-semibold text-warning mb-1">
                <AlertTriangle className="w-4 h-4" aria-hidden="true" />
                Clarification needed
              </div>
              <p className="text-text">{clarification}</p>
            </div>
          )}

          {submitError && (
            <div role="alert" className="mt-3 p-3 rounded-md border border-error/30 bg-error/10 text-sm">
              <div className="flex items-center gap-2 font-semibold text-error mb-1">
                <AlertTriangle className="w-4 h-4" aria-hidden="true" />
                Scenario request failed
              </div>
              <p className="text-text">{submitError}</p>
            </div>
          )}

          <div className="mt-8">
            <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Reference Scenarios</h3>
            <div className="space-y-2">
              {PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  className="w-full text-left text-sm p-2.5 rounded border border-border hover:border-primary hover:bg-primary/5 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                  onClick={() => handlePreset(preset.query)}
                  disabled={isSubmitting}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* LAYER LEGEND */}
      <div className="absolute left-[340px] top-4 z-10">
        <LayerLegend
          layers={[
            { id: "buildings", label: "3D Buildings", icon: Layers, active: activeLayers.buildings },
            { id: "agents", label: "Agent Trajectories", icon: Route, active: activeLayers.agents },
            { id: "confidence", label: "Confidence Heatmap", icon: MapIcon, active: activeLayers.confidence },
          ]}
          onToggleLayer={handleToggleLayer}
        />
      </div>

      {/* RIGHT PANEL: shown ONLY in explicitly-labeled sample mode.
          Live results render on /scenario/[id] from the WebSocket stream. */}
      {sampleMode && (
        <div className="absolute right-4 top-4 bottom-24 w-[360px] flex flex-col gap-3 z-10 pointer-events-auto overflow-y-auto">
          <div role="alert" className="bg-warning/10 border border-warning/40 border-dashed rounded-lg p-4 shadow-sm">
            <div className="flex items-center gap-2 font-bold text-warning text-sm">
              <WifiOff className="w-4 h-4" aria-hidden="true" />
              Sample mode — API offline
            </div>
            <p className="text-xs text-text mt-2">
              The MATRIX API could not be reached. The cards below show <strong>illustrative sample
              values only</strong> — they are <strong>not</strong> simulation results. Start the API
              and re-run the scenario for live, glass-box numbers.
            </p>
          </div>
          <DimensionCard
            id="dim-behavioral" name="Behavioral (sample)" icon={Route} colorVar="--color-dim-behavioral"
            score={-12.4} rangeMin={-14} rangeMax={-10} unit="%" confidence="Low"
            confidenceReason="Sample mode: illustrative value, not computed by the kernel"
            onInspect={setInspectMetric}
          />
          <DimensionCard
            id="dim-social" name="Social (sample)" icon={Users} colorVar="--color-dim-social"
            score={4.2} rangeMin={2} rangeMax={6} unit="%" confidence="Low"
            confidenceReason="Sample mode: illustrative value, not computed by the kernel"
            onInspect={setInspectMetric}
          />
          <DimensionCard
            id="dim-economic" name="Economic (sample)" icon={Briefcase} colorVar="--color-dim-economic"
            score={12500000} rangeMin={8000000} rangeMax={15000000} unit="₱" confidence="Low"
            confidenceReason="Sample mode: illustrative value, not computed by the kernel"
            onInspect={setInspectMetric}
          />
          <DimensionCard
            id="dim-ecological" name="Ecological (sample)" icon={Leaf} colorVar="--color-dim-ecological"
            score={-840} rangeMin={-900} rangeMax={-750} unit=" tCO₂e" confidence="Low"
            confidenceReason="Sample mode: illustrative value, not computed by the kernel"
            onInspect={setInspectMetric}
          />
          <DimensionCard
            id="dim-societal" name="Societal (sample)" icon={HeartHandshake} colorVar="--color-dim-societal"
            score={8.1} rangeMin={6.5} rangeMax={9.2} unit=" index" confidence="Low"
            confidenceReason="Sample mode: illustrative value, not computed by the kernel"
            onInspect={setInspectMetric}
          />
        </div>
      )}

      {/* BOTTOM BAR: Timeline Scrubber */}
      <div className="absolute bottom-4 left-4 right-4 h-16 bg-surface/90 backdrop-blur shadow-md border border-border rounded-lg z-10 pointer-events-auto flex items-center px-6 gap-6">
        <div className="flex items-center gap-3">
          <button className="p-2 hover:bg-secondary rounded-full text-text transition-colors"><SkipBack className="w-4 h-4" /></button>
          <button
            className="p-3 bg-primary text-primary-foreground hover:bg-primary-hover rounded-full transition-colors"
            onClick={() => setIsPlaying(!isPlaying)}
          >
            {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
          </button>
          <button className="p-2 hover:bg-secondary rounded-full text-text transition-colors"><SkipForward className="w-4 h-4" /></button>
        </div>

        <div className="flex-1 flex items-center gap-4">
          <span className="text-xs font-mono font-medium text-text-muted">06:00</span>
          <div className="flex-1 h-2 bg-secondary rounded-full relative overflow-hidden">
            <div className="absolute left-0 top-0 bottom-0 w-1/3 bg-primary rounded-full"></div>
          </div>
          <span className="text-xs font-mono font-medium text-text-muted">22:00</span>
        </div>
      </div>

      {/* INSPECT DRAWER — only reachable from sample-mode cards; carries sample-labeled provenance */}
      <InspectDrawer
        isOpen={!!inspectMetric}
        onClose={() => setInspectMetric(null)}
        metricId={inspectMetric}
        data={SAMPLE_PROVENANCE}
      />

    </div>
  );
}
