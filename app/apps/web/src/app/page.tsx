"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Map } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import DeckGL from "@deck.gl/react";
import { PolygonLayer } from "@deck.gl/layers";
import {
  Users, Briefcase, Leaf, HeartHandshake, Route, Map as MapIcon,
  Layers, Play, Loader2, WifiOff, AlertTriangle, SlidersHorizontal,
  GraduationCap, TrainFront, CloudRain, X, LayoutList
} from "lucide-react";
import Link from "next/link";

import { DimensionCard } from "@/components/DimensionCard";
import InspectDrawer, { ProvenanceData } from "@/components/InspectDrawer";
import { LayerLegend } from "@/components/LayerLegend";
import { IconNavRail } from "@/components/IconNavRail";
import { HeaderControls } from "@/components/HeaderControls";
import { PlaybackBar } from "@/components/PlaybackBar";
import { useTheme } from "@/components/ThemeProvider";
import { AmbiguousScenarioError, ApiUnreachableError, createScenario } from "@/lib/api";
import { MAP_STYLE_DARK, MAP_STYLE_LIGHT } from "@/lib/mapStyles";
import type { MapRef } from "react-map-gl/maplibre";

const INITIAL_VIEW_STATE = {
  longitude: 122.56,
  latitude: 10.72,
  zoom: 13,
  pitch: 45,
  bearing: 0
};

const ILOILO_BOUNDS = {
  minLng: 122.48,
  maxLng: 122.62,
  minLat: 10.64,
  maxLat: 10.79,
  minZoom: 11
};

// deck.gl onViewStateChange is generic over ViewStateT (TransitionProps | MapViewState),
// so no concrete view-state shape is assignable; we mutate the live viewState to clamp it.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const handleViewStateChange = ({ viewState }: any) => {
  viewState.longitude = Math.min(Math.max(viewState.longitude, ILOILO_BOUNDS.minLng), ILOILO_BOUNDS.maxLng);
  viewState.latitude = Math.min(Math.max(viewState.latitude, ILOILO_BOUNDS.minLat), ILOILO_BOUNDS.maxLat);
  viewState.zoom = Math.max(viewState.zoom, ILOILO_BOUNDS.minZoom);
  return viewState;
};

// Illustrative building footprints for the empty base map (visual placeholder
// only — real building extrusions stream with the simulation on /scenario/[id]).
type Building = { polygon: [number, number][]; height: number };
const BUILDINGS: Building[] = [
  { polygon: [[122.56, 10.71], [122.561, 10.71], [122.561, 10.711], [122.56, 10.711]], height: 20 },
  { polygon: [[122.562, 10.712], [122.563, 10.712], [122.563, 10.713], [122.562, 10.713]], height: 45 },
];

// Preset reference scenarios — each submits a real NL query to POST /scenario.
const PRESETS: { label: string; query: string; icon: React.ElementType }[] = [
  { label: "School in Molo", query: "What if we build a 3,000-seat school in Molo?", icon: GraduationCap },
  { label: "RDT on Diversion Rd", query: "What if we run a RDT line along Diversion Road?", icon: TrainFront },
  { label: "Flooding Closure", query: "What if flooding closes the Diversion Road corridor for a day?", icon: CloudRain },
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
  const mapRef = useRef<MapRef>(null);
  const { theme } = useTheme();

  useEffect(() => {
    if (mapRef.current) {
      mapRef.current.getMap().setStyle(theme === "dark" ? MAP_STYLE_DARK : MAP_STYLE_LIGHT);
    }
  }, [theme]);

  const [showResultsPanel, setShowResultsPanel] = useState(true);
  const [viewState, setViewState] = useState(INITIAL_VIEW_STATE);


  const [query, setQuery] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [clarification, setClarification] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [sampleMode, setSampleMode] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [inspectMetric, setInspectMetric] = useState<string | null>(null);
  const [showLayers, setShowLayers] = useState(false);
  const [activeNavId, setActiveNavId] = useState("home");

  useEffect(() => {
    if (inspectMetric && mapRef.current) {
      setViewState(prev => ({
        ...prev,
        longitude: 122.56,
        latitude: 10.71,
        zoom: 14.5,
        transitionDuration: 800,
      }));
    }
  }, [inspectMetric]);

  // Layer Toggles
  const [activeLayers, setActiveLayers] = useState<Record<string, boolean>>({
    buildings: true,
    agents: false,
    confidence: false,
  });

  const handleToggleLayer = (id: string) => {
    setActiveLayers(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleNavigation = (id: string) => {
    setActiveNavId(id);
    if (id === "layers") {
      setShowLayers(prev => !prev);
    }
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
      getFillColor: [30, 42, 71, 180],
      getLineColor: [59, 111, 224, 100],
      opacity: inspectMetric ? 0.05 : 1,
    })
  ].filter(Boolean);

  return (
    <div className="relative h-dvh w-full overflow-hidden bg-background text-foreground flex">

      {/* ICON NAV RAIL */}
      <IconNavRail activeId={activeNavId} onNavigate={handleNavigation} />

      {/* MAP STAGE (Background) */}
      <div className="flex-1 relative">
        <div className="absolute inset-0 z-0">
          <DeckGL
            viewState={{
              ...viewState,
              padding: {
                right: ((sampleMode && showResultsPanel) || !!inspectMetric) ? 424 : 0,
                left: 64, top: 0, bottom: 0
              }
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
            } as any}
            controller={true}
            onViewStateChange={(e) => setViewState(handleViewStateChange(e))}
            layers={layers}
          >
            <Map 
              ref={mapRef}
              mapStyle={theme === "dark" ? MAP_STYLE_DARK : MAP_STYLE_LIGHT} 
              mapLib={maplibregl} 
              reuseMaps 
            />
          </DeckGL>
        </div>

        {/* TOP RIGHT HEADER CONTROLS */}
        <div className="absolute top-4 right-4 z-10">
          <HeaderControls />
        </div>

        {/* LEFT RAIL: Scenario Bar */}
        <div className="absolute left-4 top-4 bottom-20 w-[320px] bg-surface/50 backdrop-blur-xl shadow-lg rounded-xl border border-white/10 flex flex-col z-10 pointer-events-auto overflow-hidden">
          {/* Sidebar Header with Logo */}
          <div className="p-4 border-b border-white/10 bg-transparent">
            <h1 className="text-4xl font-black uppercase tracking-widest text-text">MATRIX</h1>
            <p className="text-[10px] text-text-muted leading-tight mt-1">
              Multi-Agent Twin for Routing <br className="hidden sm:block" />
              & Infrastructure eXchange
            </p>
          </div>

          <div className="p-4 flex-1 overflow-y-auto">
            <label htmlFor="scenario-query" className="text-sm font-semibold mb-2 block text-text">Scenario Query</label>
            <textarea
              id="scenario-query"
              className="w-full bg-surface-elevated/50 backdrop-blur-md border border-border rounded-lg p-3 text-sm text-text placeholder:text-text-muted/60 focus:border-primary focus:ring-1 focus:ring-primary outline-none resize-none min-h-[100px] transition-colors"
              placeholder="e.g., What if we build a 3,000-seat school in Molo?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={isSubmitting}
            />
            <button
              className="w-full mt-3 bg-primary/80 backdrop-blur-xl text-white font-semibold py-2.5 rounded-lg hover:bg-primary-hover transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-md shadow-primary/20"
              onClick={() => handleSimulate()}
              disabled={isSubmitting || !query.trim()}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                  Parsing scenario…
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" aria-hidden="true" />
                  Simulate Scenario
                </>
              )}
            </button>

            {/* Secondary path: the structured builder (multi-step intervention composer). */}
            <Link
              href="/builder"
              className="mt-2 flex items-center justify-center gap-1.5 text-sm text-text-muted hover:text-primary transition-colors"
            >
              <SlidersHorizontal className="w-4 h-4" aria-hidden="true" />
              Build a structured scenario
            </Link>

            {clarification && (
              <div role="alert" className="mt-3 p-3 rounded-lg border border-warning/30 bg-warning/10 text-sm">
                <div className="flex items-center gap-2 font-semibold text-warning mb-1">
                  <AlertTriangle className="w-4 h-4" aria-hidden="true" />
                  Clarification needed
                </div>
                <p className="text-text">{clarification}</p>
              </div>
            )}

            {submitError && (
              <div role="alert" className="mt-3 p-3 rounded-lg border border-error/30 bg-error/10 text-sm">
                <div className="flex items-center gap-2 font-semibold text-error mb-1">
                  <AlertTriangle className="w-4 h-4" aria-hidden="true" />
                  Scenario request failed
                </div>
                <p className="text-text">{submitError}</p>
              </div>
            )}

            {/* Reference Scenarios */}
            <div className="mt-8">
              <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Reference Scenarios</h3>
              <div className="space-y-2">
                {PRESETS.map((preset) => {
                  const Icon = preset.icon;
                  return (
                    <button
                      key={preset.label}
                      className="w-full text-left text-sm p-3 rounded-xl bg-surface-elevated/50 backdrop-blur-md border border-border hover:border-primary/50 hover:bg-primary/5 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-3 group"
                      onClick={() => handlePreset(preset.query)}
                      disabled={isSubmitting}
                    >
                      <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 group-hover:bg-primary/20 transition-colors">
                        <Icon className="w-4 h-4 text-primary" />
                      </div>
                      <span className="text-text font-medium">{preset.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* LAYER LEGEND — closed by default, toggle via Layers nav icon */}
        {showLayers && (
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
        )}

        {/* RIGHT PANEL: shown ONLY in explicitly-labeled sample mode.
            Live results render on /scenario/[id] from the WebSocket stream. */}
        {sampleMode && !showResultsPanel && (
          <div className="absolute right-4 top-24 z-20 pointer-events-auto">
            <button
              onClick={() => setShowResultsPanel(true)}
              className="flex items-center gap-2 bg-surface/60 backdrop-blur-xl border border-border shadow-lg rounded-full px-4 py-2 text-sm font-medium text-text hover:text-primary hover:border-primary/50 transition-all"
            >
              <LayoutList className="w-4 h-4" />
              Show Results
            </button>
          </div>
        )}
        {sampleMode && showResultsPanel && !inspectMetric && (
          <div className="absolute right-6 top-24 bottom-20 w-[360px] flex flex-col gap-4 z-10 pointer-events-auto overflow-y-auto pb-6">
            <div className="flex justify-end sticky top-0 bg-background/40 backdrop-blur-xl z-20 -mx-4 -mt-4 px-4 py-2 rounded-t-xl">
              <button
                onClick={() => setShowResultsPanel(false)}
                className="p-1.5 rounded-lg text-text-muted hover:text-text hover:bg-surface-elevated transition-colors bg-surface/60 backdrop-blur-xl border border-border"
                aria-label="Close results panel"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div role="alert" className="bg-warning/10 border border-warning/40 border-dashed rounded-xl p-4 shadow-sm mt-2">
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

        {/* BOTTOM BAR: Enhanced Playback Bar */}
        <div className="absolute bottom-4 left-4 right-4 z-10 pointer-events-auto">
          <PlaybackBar
            isPlaying={isPlaying}
            onTogglePlay={() => setIsPlaying(!isPlaying)}
          />
        </div>
      </div>

      {/* INSPECT DRAWER — only reachable from sample-mode cards; carries sample-labeled provenance */}
      <InspectDrawer
        isOpen={!!inspectMetric}
        onClose={() => setInspectMetric(null)}
        metricId={inspectMetric}
        data={SAMPLE_PROVENANCE}
      >
        <div className="flex flex-col gap-4 mt-2">
          <h4 className="text-sm font-medium text-text-muted uppercase tracking-wider mb-1">
            Category Breakdown
          </h4>
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
      </InspectDrawer>

    </div>
  );
}
