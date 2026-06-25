"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Map } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import DeckGL from "@deck.gl/react";
import {
  Users, Briefcase, Leaf, HeartHandshake, Route, Map as MapIcon,
  Layers, Play, Loader2, WifiOff, AlertTriangle, SlidersHorizontal,
  GraduationCap, TrainFront, CloudRain, X, LayoutList
} from "lucide-react";
import Link from "next/link";

import { DimensionCard } from "@/components/DimensionCard";
import { LogoMark } from "@/components/Logo";
import InspectDrawer, { ProvenanceData } from "@/components/InspectDrawer";
import { LayerLegend } from "@/components/LayerLegend";
import { IconNavRail } from "@/components/IconNavRail";
import { HeaderControls } from "@/components/HeaderControls";
import { MapAttribution } from "@/components/MapAttribution";
import { MapContextMenu } from "@/components/map/MapContextMenu";
import { useMapContextMenu } from "@/components/map/useMapContextMenu";
import { PlaybackBar } from "@/components/PlaybackBar";
import { useTheme } from "@/components/ThemeProvider";
import { AmbiguousScenarioError, ApiUnreachableError, createScenario } from "@/lib/api";
import { MAP_STYLE_DARK, MAP_STYLE_LIGHT, registerMissingImageFallback, syncBuilding3dLayer } from "@/lib/mapStyles";
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

// Preset reference scenarios — each submits a real NL query to POST /scenario.
const PRESETS: { label: string; query: string; icon: React.ElementType }[] = [
  { label: "School in Molo", query: "What if we build a 3,000-seat school in Molo?", icon: GraduationCap },
  { label: "RDT on Diversion Rd", query: "What if we run a RDT line along Diversion Road?", icon: TrainFront },
  { label: "Flooding Closure", query: "What if flooding closes the Diversion Road corridor for a day?", icon: CloudRain },
];

// Shown ONLY in the explicitly-labeled "Sample mode — API offline" state.
// These are illustrative sample values, never presented as simulation output.
const SAMPLE_PROVENANCE: ProvenanceData = {
  metric: "Economic Impact (SAMPLE, not a simulation result)",
  value: "₱12.5M",
  range: "₱8M to ₱15M",
  confidence: "Medium",
  confidenceBasis: "SAMPLE DATA. The MATRIX API is offline; this value is illustrative only and was not computed by the kernel.",
  equationId: "ECO-1",
  equationText: "ΔCost = Σ(Area_k * UnitCost_k) + Contingency",
  inputs: [
    { id: "DS-01", name: "BIR Zonal Values RDO 74", confidence: "High", vintage: "2023" },
    { id: "DS-02", name: "PSA ASPBI Construction Costs", confidence: "Medium", vintage: "2022" }
  ],
  assumptions: [
    "SAMPLE MODE: API offline. Every value shown is an illustrative placeholder, not kernel output.",
    "Contingency buffer set at 15%",
    "Inflation adjustment of 4.5% applied to 2022 data"
  ],
  references: ["DPWH Standard Cost Guidelines (2023)"]
};

export default function MatrixCockpit() {
  const router = useRouter();
  const mapRef = useRef<MapRef>(null);
  const { theme } = useTheme();
  const {
    containerRef: mapContainerRef,
    menuPosition,
    menuLngLat,
    closeMenu: closeMapMenu,
    handleContextMenu,
  } = useMapContextMenu({ mapRef });

  useEffect(() => {
    if (mapRef.current) {
      mapRef.current.getMap().setStyle(theme === "dark" ? MAP_STYLE_DARK : MAP_STYLE_LIGHT);
    }
  }, [theme]);

  const [showResultsPanel, setShowResultsPanel] = useState(true);
  // Mobile only: the scenario panel is a bottom sheet that peeks (query visible)
  // and expands on a tap of the grab handle. Ignored at md+ (it docks left).
  const [sheetExpanded, setSheetExpanded] = useState(false);
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

  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (!map) return;

    const updateBuildingVisibility = () => {
      syncBuilding3dLayer(map, theme, activeLayers.buildings);
    };

    if (map.isStyleLoaded()) {
      updateBuildingVisibility();
    }

    map.on("style.load", updateBuildingVisibility);
    const disposeMissingImage = registerMissingImageFallback(map);

    return () => {
      map.off("style.load", updateBuildingVisibility);
      disposeMissingImage();
    };
  }, [activeLayers.buildings, theme]);

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

  const handleCopyCoordinates = async (lngLat: { lng: number; lat: number }) => {
    const text = `${lngLat.lat.toFixed(5)}, ${lngLat.lng.toFixed(5)}`;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Clipboard may be unavailable outside secure context.
    }
  };

  const handleCenterHere = (lngLat: { lng: number; lat: number }) => {
    setViewState((prev) => ({
      ...prev,
      longitude: lngLat.lng,
      latitude: lngLat.lat,
      zoom: Math.max(prev.zoom, 15),
      transitionDuration: 600,
    }));
  };

  const handleUseLocation = (lngLat: { lng: number; lat: number }) => {
    setQuery(
      `What if we build a project at ${lngLat.lat.toFixed(4)}°N, ${lngLat.lng.toFixed(4)}°E in Iloilo?`
    );
    setSheetExpanded(true);
  };

  return (
    <div className="relative h-dvh w-full overflow-hidden bg-background text-foreground flex">

      {/* ICON NAV RAIL */}
      <IconNavRail
        activeId={activeNavId}
        onNavigate={handleNavigation}
        disabledIds={["trajectories", "analytics"]}
        disabledReason="Run a scenario first"
      />

      {/* MAP STAGE (Background) */}
      <div className="flex-1 relative">
        <div
          ref={mapContainerRef}
          className="absolute inset-0 z-0"
          onContextMenu={handleContextMenu}
        >
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
            layers={[]}
          >
            <Map
              ref={mapRef}
              mapStyle={theme === "dark" ? MAP_STYLE_DARK : MAP_STYLE_LIGHT}
              mapLib={maplibregl}
              attributionControl={false}
              reuseMaps
            />
          </DeckGL>
          {menuPosition && menuLngLat && (
            <MapContextMenu
              position={menuPosition}
              lngLat={menuLngLat}
              onClose={closeMapMenu}
              onCopyCoordinates={handleCopyCoordinates}
              onCenterHere={handleCenterHere}
              onUseLocation={handleUseLocation}
            />
          )}
        </div>

        {/* TOP RIGHT HEADER CONTROLS */}
        <div className="absolute top-4 right-4 z-10">
          <HeaderControls />
        </div>

        {/* SCENARIO PANEL — docked left rail at md+, a peek/expand bottom sheet on mobile. */}
        <div
          className={`glass absolute z-20 flex flex-col pointer-events-auto overflow-hidden
            inset-x-0 bottom-0 rounded-t-2xl transition-[height] duration-300 ${sheetExpanded ? "h-[85dvh]" : "h-[46dvh]"}
            md:inset-x-auto md:left-4 md:top-4 md:bottom-20 md:h-auto md:w-[320px] md:rounded-xl md:z-10 md:transition-none`}
        >
          {/* Mobile grab handle — tap to expand/collapse the sheet. */}
          <button
            type="button"
            onClick={() => setSheetExpanded((v) => !v)}
            aria-label={sheetExpanded ? "Collapse scenario panel" : "Expand scenario panel"}
            aria-expanded={sheetExpanded}
            className="md:hidden w-full pt-2.5 pb-1.5 flex items-center justify-center shrink-0"
          >
            <span className="h-1 w-10 rounded-full bg-text-muted/40" aria-hidden="true" />
          </button>

          {/* Sidebar Header with Logo */}
          <div className="px-5 pt-3 pb-4 md:pt-5 border-b border-border/60">
            <div className="flex items-center gap-2.5">
              <LogoMark className="h-7 w-7 text-primary shrink-0" />
              <h1 className="text-2xl font-bold uppercase tracking-[0.22em] text-text">MATRIX</h1>
            </div>
            <p className="text-[11px] text-text-muted leading-snug mt-1.5">
              Multi-Agent Twin for Routing <br className="hidden sm:block" />
              &amp; Infrastructure eXchange
            </p>
          </div>

          <div className="p-5 flex-1 overflow-y-auto">
            <label htmlFor="scenario-query" className="text-sm font-semibold mb-2 block text-text">Scenario Query</label>
            <textarea
              id="scenario-query"
              className="w-full bg-surface-elevated/50 border border-border rounded-lg p-3 text-sm text-text placeholder:text-text-muted/60 focus:border-primary focus:ring-1 focus:ring-primary outline-none resize-none min-h-[100px] transition-colors"
              placeholder="e.g., What if we build a 3,000-seat school in Molo?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={isSubmitting}
            />
            <button
              className="w-full mt-3 bg-primary text-white font-semibold py-2.5 rounded-lg hover:bg-primary-hover transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-md shadow-primary/20"
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

          {/* Map attribution — replaces MapLibre's default white control (ODbL/OpenMapTiles). */}
          <div className="px-5 py-2.5 border-t border-border/60 shrink-0">
            <MapAttribution />
          </div>
        </div>

        {/* LAYER LEGEND — closed by default, toggle via Layers nav icon */}
        {showLayers && (
          <div className="absolute left-2 top-20 md:left-[340px] md:top-4 z-30">
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
              className="glass flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium text-text hover:text-primary hover:border-primary/50 transition-all active:scale-[0.98]"
            >
              <LayoutList className="w-4 h-4" />
              Show Results
            </button>
          </div>
        )}
        {sampleMode && showResultsPanel && !inspectMetric && (
          <div className="absolute inset-x-2 top-20 bottom-[48dvh] w-auto md:inset-x-auto md:right-6 md:top-24 md:bottom-20 md:w-[360px] flex flex-col gap-4 z-10 pointer-events-auto overflow-y-auto overflow-x-hidden pb-6">
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
                Sample mode: API offline
              </div>
              <p className="text-xs text-text mt-2">
                The MATRIX API could not be reached. The cards below show <strong>illustrative sample
                values only</strong>. They are <strong>not</strong> simulation results. Start the API
                and re-run the scenario for live, glass-box numbers.
              </p>
            </div>
            <DimensionCard
              className="card-reveal" style={{ animationDelay: "0ms" }}
              id="dim-behavioral" name="Behavioral (sample)" icon={Route} colorVar="--color-dim-behavioral"
              score={-12.4} rangeMin={-14} rangeMax={-10} unit="%" confidence="Low"
              confidenceReason="Sample mode: illustrative value, not computed by the kernel"
              onInspect={setInspectMetric}
            />
            <DimensionCard
              className="card-reveal" style={{ animationDelay: "60ms" }}
              id="dim-social" name="Social (sample)" icon={Users} colorVar="--color-dim-social"
              score={4.2} rangeMin={2} rangeMax={6} unit="%" confidence="Low"
              confidenceReason="Sample mode: illustrative value, not computed by the kernel"
              onInspect={setInspectMetric}
            />
            <DimensionCard
              className="card-reveal" style={{ animationDelay: "120ms" }}
              id="dim-economic" name="Economic (sample)" icon={Briefcase} colorVar="--color-dim-economic"
              score={12500000} rangeMin={8000000} rangeMax={15000000} unit="₱" confidence="Low"
              confidenceReason="Sample mode: illustrative value, not computed by the kernel"
              onInspect={setInspectMetric}
            />
            <DimensionCard
              className="card-reveal" style={{ animationDelay: "180ms" }}
              id="dim-ecological" name="Ecological (sample)" icon={Leaf} colorVar="--color-dim-ecological"
              score={-840} rangeMin={-900} rangeMax={-750} unit=" tCO₂e" confidence="Low"
              confidenceReason="Sample mode: illustrative value, not computed by the kernel"
              onInspect={setInspectMetric}
            />
            <DimensionCard
              className="card-reveal" style={{ animationDelay: "240ms" }}
              id="dim-societal" name="Societal (sample)" icon={HeartHandshake} colorVar="--color-dim-societal"
              score={8.1} rangeMin={6.5} rangeMax={9.2} unit=" index" confidence="Low"
              confidenceReason="Sample mode: illustrative value, not computed by the kernel"
              onInspect={setInspectMetric}
            />
          </div>
        )}

        {/* BOTTOM BAR: Playback Bar — hidden on mobile (no trajectories on the home
            map yet, and it would collide with the scenario bottom sheet). */}
        <div className="hidden md:block absolute bottom-4 left-4 right-4 z-10 pointer-events-auto">
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
