"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { Map } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import DeckGL from "@deck.gl/react";
import { TripsLayer } from "@deck.gl/geo-layers";
import type { Layer } from "@deck.gl/core";
import InspectDrawer, { ProvenanceData } from "@/components/InspectDrawer";
import { type SynthesisCitation } from "@/components/SynthesisNarrative";
import { DimensionResultGroup } from "@/components/DimensionResultGroup";
import { SummaryView } from "@/components/SummaryView";
import { AnalyticsView } from "@/components/AnalyticsView";
import { ScenarioBrief } from "@/components/ScenarioBrief";
import type { ResultCardData } from "@/components/ResultCard";
import { MapAttribution } from "@/components/MapAttribution";
import RunProgress from "@/components/RunProgress";
import RunStatusBanner from "@/components/RunStatusBanner";
import { IconNavRail } from "@/components/IconNavRail";
import {
  DIMENSIONS,
  EXPECTED_RESULTS,
  RunEvent,
  RunState,
  buildSimulationWsUrl,
  initialRunState,
  isTerminal,
  reduceRunEvent,
  statusLabel,
} from "@/lib/simulationRun";
import { LayerLegend } from "@/components/LayerLegend";
import {
  useMapLayers,
  fetchStaticLayer,
  confidenceCellsFromGeoJSON,
} from "@/components/map";
import type {
  ConfidenceCell,
  EdgeCounts,
  EdgesFeatureCollection,
  FeatureCollection,
  MapLayerToggles,
} from "@/components/map";
import { Route, Activity, Gauge, Waves, X, LayoutList, Play, Pause, ChevronLeft } from "lucide-react";
import { useTheme } from "@/components/ThemeProvider";
import { MAP_STYLE_DARK, MAP_STYLE_LIGHT, syncBuilding3dLayer } from "@/lib/mapStyles";
import type { MapRef } from "react-map-gl/maplibre";

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

export default function ScenarioSimulation() {
  const router = useRouter();
  const params = useParams();
  const scenarioId = params.id as string;
  const mapRef = useRef<MapRef>(null);
  const { theme } = useTheme();

  useEffect(() => {
    if (mapRef.current) {
      mapRef.current.getMap().setStyle(theme === "dark" ? MAP_STYLE_DARK : MAP_STYLE_LIGHT);
    }
  }, [theme]);

  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (!map) return;

    const ensureBuilding3D = () => {
      syncBuilding3dLayer(map, theme, true);
    };

    if (map.isStyleLoaded()) {
      ensureBuilding3D();
    }

    map.on("style.load", ensureBuilding3D);

    return () => {
      map.off("style.load", ensureBuilding3D);
    };
  }, [theme]);

  const [time, setTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);

  const [showResultsPanel, setShowResultsPanel] = useState(true);
  // CR-010: the dock is summary-only by default; "analytics" opens the full,
  // interpreted detail view (driven by the nav rail + the "View full analytics" link).
  const [panelView, setPanelView] = useState<"summary" | "analytics">("summary");
  const [inspectingMetric, setInspectingMetric] = useState<string | null>(null);

  const [viewState, setViewState] = useState({
    longitude: 122.56,
    latitude: 10.72,
    zoom: 13,
    pitch: 45,
    bearing: 0
  });



  const [runState, setRunState] = useState<RunState>(initialRunState);
  const [runAttempt, setRunAttempt] = useState(0);

  const [results, setResults] = useState<ResultCardData[]>([]);
  const [tripsData, setTripsData] = useState<{ id: string, path: [number, number][], timestamps: number[] }[]>([]);
  const [maxTime, setMaxTime] = useState(1000);

  // Map data layers. `agents` toggles the page-owned TripsLayer; congestion/confidence/flood
  // are assembled by useMapLayers. Static files (edges/flood/confidence) load once; congestion
  // is driven by the live EDGE_COUNTS stream event (reset per run, like tripsData/results).
  const [edgeCounts, setEdgeCounts] = useState<EdgeCounts>({});
  const [activeLayers, setActiveLayers] = useState<MapLayerToggles>({
    agents: true, congestion: true, confidence: false, flood: false,
  });
  const [edgesGeoJSON, setEdgesGeoJSON] = useState<EdgesFeatureCollection | null>(null);
  const [floodGeoJSON, setFloodGeoJSON] = useState<FeatureCollection | null>(null);
  const [confidenceCells, setConfidenceCells] = useState<ConfidenceCell[]>([]);
  const [synthesis, setSynthesis] = useState<{
    narrative: string;
    citations: SynthesisCitation[];
  } | null>(null);
  const [inspectData, setInspectData] = useState<ProvenanceData | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  useEffect(() => {
    if (inspectingMetric && isDrawerOpen && mapRef.current) {
      setViewState(prev => ({
        ...prev,
        longitude: 122.56,
        latitude: 10.71,
        zoom: 14.5,
        transitionDuration: 800,
      }));
    }
  }, [inspectingMetric, isDrawerOpen]);

  const wsRef = useRef<WebSocket | null>(null);

  const dispatch = useCallback((event: RunEvent) => {
    setRunState((s) => reduceRunEvent(s, event));
  }, []);

  // DeckGL setup — data layers (flood/congestion/confidence, bottom→top) sit under the
  // animated agent trajectories. useMapLayers omits any layer whose data is absent.
  const dataLayers = useMapLayers(activeLayers, {
    edgesGeoJSON,
    edgeCounts,
    confidenceCells,
    floodGeoJSON,
  });
  const tripsLayer = new TripsLayer({
    id: "trips-layer",
    data: tripsData,
    getPath: (d: { path: [number, number][] }) => d.path,
    getTimestamps: (d: { timestamps: number[] }) => d.timestamps,
    getColor: [29, 78, 216],
    opacity: 0.8,
    widthMinPixels: 2,
    rounded: true,
    trailLength: 100,
    currentTime: time,
  });
  
  const layers = [...dataLayers, ...(activeLayers.agents ? [tripsLayer] : [])].map((layer: Layer) => {
    if (!inspectingMetric || !isDrawerOpen) return layer;
    
    let isHighlighted = false;
    const dim = inspectingMetric.toLowerCase();
    
    if (dim === "ecological" && layer.id === "flood-layer") isHighlighted = true;
    if (dim === "behavioral" && (layer.id === "trips-layer" || layer.id === "congestion-layer")) isHighlighted = true;
    if (["social", "economic", "societal"].includes(dim) && layer.id === "confidence-layer") isHighlighted = true;

    return layer.clone({ opacity: isHighlighted ? (layer.props.opacity ?? 1) : 0.05 });
  });

  const handleToggleLayer = useCallback((id: string) => {
    setActiveLayers((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  // Static map layers load once (graceful no-op on a miss — fetchStaticLayer resolves null).
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const [edges, flood, confidence] = await Promise.all([
        fetchStaticLayer("edges"),
        fetchStaticLayer("flood"),
        fetchStaticLayer("confidence"),
      ]);
      if (cancelled) return;
      setEdgesGeoJSON(edges as EdgesFeatureCollection | null);
      setFloodGeoJSON(flood);
      setConfidenceCells(confidence ? confidenceCellsFromGeoJSON(confidence) : []);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // WebSocket connection — one run per (scenarioId, runAttempt).
  useEffect(() => {
    const ws = new WebSocket(buildSimulationWsUrl(scenarioId));
    wsRef.current = ws;

    ws.onopen = () => dispatch({ type: "WS_OPEN" });

    ws.onmessage = (event) => {
      let msg: Record<string, unknown>;
      try {
        msg = JSON.parse(event.data);
      } catch {
        return; // malformed frame — never crash the page
      }
      if (msg === null || typeof msg !== "object") return;

      // All lifecycle/progress bookkeeping goes through the pure reducer
      // (unknown event types are a no-op there by design).
      dispatch(msg as RunEvent);

      if (msg.type === "PLAYBACK_FRAME") {
        // Accumulate playback frames for Deck.gl TripsLayer
        const tick = typeof msg.tick === "number" ? msg.tick : 0;
        setMaxTime((prev) => Math.max(prev, tick));
        if (Array.isArray(msg.agents)) {
          // Hoist the narrowed array into a typed local: Array.isArray narrowing on
          // `msg.agents` (an `unknown` field) does not survive into the setTripsData
          // closure, so `next build` type-checks it as `unknown` without this.
          const agents = msg.agents as Array<{ id: string; lon: number; lat: number }>;
          setTripsData((prev) => {
            const next = [...prev];
            for (const a of agents) {
              const idx = next.findIndex((t) => t.id === a.id);
              if (idx >= 0) {
                // Agent exists, append to path and timestamps
                next[idx] = {
                  ...next[idx],
                  path: [...next[idx].path, [a.lon, a.lat]],
                  timestamps: [...next[idx].timestamps, tick],
                };
              } else {
                // New agent
                next.push({
                  id: a.id,
                  path: [[a.lon, a.lat]],
                  timestamps: [tick],
                });
              }
            }
            return next;
          });
        }
      } else if (msg.type === "EDGE_COUNTS") {
        // Aggregate per-edge counts that drive the congestion choropleth.
        if (msg.edge_counts && typeof msg.edge_counts === "object") {
          setEdgeCounts(msg.edge_counts as EdgeCounts);
        }
      } else if (msg.type === "DIMENSION_RESULT") {
        // Build provenance data payload format expected by InspectDrawer.
        // The raw value/range stay untouched here (Inspect = glass box, full
        // precision); the Summary/Analytics views format them at render via
        // src/lib/format.ts (CR-010) — no pre-rounding, no false precision.
        const value = typeof msg.value === "number" ? msg.value : Number(msg.value);
        const rawRange: [number, number] | null =
          Array.isArray(msg.range) &&
          msg.range.length === 2 &&
          typeof msg.range[0] === "number" &&
          typeof msg.range[1] === "number"
            ? [msg.range[0], msg.range[1]]
            : null;
        const range = rawRange ? `${rawRange[0]}..${rawRange[1]}` : "";
        const confidence = typeof msg.confidence === "string" ? msg.confidence : "L";
        const equationId = String(msg.equation_id ?? "");
        const metric = typeof msg.metric === "string" ? msg.metric : (equationId || "metric");
        const provData: ProvenanceData = {
          metric,
          value: String(msg.value),
          range,
          confidence,
          confidenceBasis: "Computed from input dataset confidences per methods §2",
          equationId,
          // No equation text or per-dataset metadata arrives over the stream yet —
          // the drawer renders honest "not provided" fallbacks (never invented).
          inputs: (Array.isArray(msg.input_dataset_ids) ? msg.input_dataset_ids : []).map(
            (id: string) => ({ id })
          ),
          assumptions: Array.isArray(msg.assumptions) ? msg.assumptions : [],
          references: Array.isArray(msg.references) ? msg.references : []
        };

        setResults((prev) => [...prev, {
          key: `${msg.dimension}:${metric}:${prev.length}`,
          dimension: String(msg.dimension ?? "unknown"),
          metric,
          equationId,
          unit: typeof msg.unit === "string" ? msg.unit : "",
          conf: confidence,
          rawValue: value,
          rawRange,
          provData
        }]);
      } else if (msg.type === "SYNTHESIS") {
        if (typeof msg.narrative === "string") {
          const citations = (Array.isArray(msg.citations) ? msg.citations : []).filter(
            (c): c is SynthesisCitation =>
              !!c &&
              typeof c === "object" &&
              typeof (c as { equation_id?: unknown }).equation_id === "string"
          );
          setSynthesis({ narrative: msg.narrative, citations });
        }
      } else if (msg.type === "DONE") {
        ws.close();
      }
    };

    // onerror is always followed by onclose; the reducer turns a mid-run close
    // into the "disconnected" phase (sticky terminal phases are unaffected).
    ws.onclose = () => dispatch({ type: "WS_CLOSED" });

    return () => {
      // Tear down silently on unmount/retry — don't report it as a disconnect.
      ws.onopen = null;
      ws.onclose = null;
      ws.onmessage = null;
      ws.close();
    };
  }, [scenarioId, runAttempt, dispatch]);

  // Citation chip → Inspect drawer: resolve the equation id against the
  // accumulated results (glass box: an unmatched citation never opens a drawer —
  // SynthesisNarrative renders it disabled instead).
  const handleCiteClick = useCallback(
    (equationId: string) => {
      const match = results.find((r) => r.provData.equationId === equationId);
      if (!match) return;
      setInspectData(match.provData);
      setIsDrawerOpen(true);
    },
    [results]
  );

  // Cancel: user-initiated stop — distinct from error and from done.
  const cancelRun = useCallback(() => {
    dispatch({ type: "CANCEL" });
    wsRef.current?.close();
  }, [dispatch]);

  // Retry/reconnect: reset accumulated stream state and open a fresh WS
  // (the server re-streams the run from the start).
  const retryRun = useCallback(() => {
    setResults([]);
    setTripsData([]);
    setEdgeCounts({});
    setSynthesis(null);
    setRunState(initialRunState());
    setRunAttempt((a) => a + 1);
  }, []);

  // Simple playback loop
  useEffect(() => {
    let animationFrame: number;
    const animate = () => {
      setTime(t => {
        // Wrap around at maxTime if it's > 0, otherwise wrap at 1000
        const loopTime = maxTime > 0 ? maxTime : 1000;
        return (t + 1) % loopTime;
      });
      animationFrame = requestAnimationFrame(animate);
    };
    if (isPlaying) {
      animationFrame = requestAnimationFrame(animate);
    }
    return () => cancelAnimationFrame(animationFrame);
  }, [isPlaying, maxTime]);

  const isRunActive = !isTerminal(runState.phase) && runState.phase !== "disconnected";

  return (
    <div className="relative h-dvh w-full overflow-hidden bg-background text-foreground flex print:h-auto print:block print:overflow-visible print:bg-white">
      {/* ICON NAV RAIL */}
      <div className="print:hidden">
        <IconNavRail
          activeId={panelView === "analytics" ? "analytics" : "trajectories"}
          onNavigate={(id) => {
            if (id === "home") {
              router.push("/");
            } else if (id === "trajectories") {
              setPanelView("summary");
              setShowResultsPanel(true);
            } else if (id === "analytics") {
              setPanelView("analytics");
              setShowResultsPanel(true);
            }
          }}
        />
      </div>

      {/* Print-only executive brief (CR-010 WS-5 T5.4). The dedicated, one-page,
          BLUF-ordered brief with an evidence appendix. window.print() is scoped to
          this by hiding the live UI below at print time. */}
      <ScenarioBrief results={results} narrative={synthesis?.narrative} scenarioId={scenarioId} />

      {/* Main layout contents — hidden at print so only the brief above prints. */}
      <div className="flex-1 flex h-screen w-full flex-col md:flex-row overflow-hidden relative print:hidden">

      {/* Floating Restore Button when panel is dismissed */}
      {!showResultsPanel && (
        <div className="absolute top-24 right-4 z-20 pointer-events-auto print:hidden">
          <button
            onClick={() => setShowResultsPanel(true)}
            className="glass flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium text-text hover:text-primary hover:border-primary/50 transition-all active:scale-[0.98]"
          >
            <LayoutList className="w-4 h-4" />
            Show Results
          </button>
        </div>
      )}

      {/* Results panel — summary dock by default; widens into the full analytics view */}
      {showResultsPanel && (
        <div className={`w-full h-full bg-surface/85 backdrop-blur-xl shadow-lg z-10 flex flex-col border-l border-border order-2 md:order-1 overflow-hidden relative print:w-full print:border-none print:shadow-none print:bg-white print:overflow-visible print:h-auto ${panelView === "analytics" ? "md:w-[680px] lg:w-[860px]" : "md:w-[360px] lg:w-[400px]"}`}>
          <div className="p-4 border-b border-border bg-transparent flex justify-between items-center gap-2 print:border-black">
            <div className="min-w-0 flex items-center gap-2">
              {panelView === "analytics" && (
                <button
                  onClick={() => setPanelView("summary")}
                  className="p-1 rounded-lg text-text-muted hover:text-text hover:bg-surface-elevated transition-colors print:hidden shrink-0"
                  aria-label="Back to summary"
                  title="Back to summary"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
              )}
              <div className="min-w-0">
                <h2 className="text-lg font-bold text-foreground print:text-black">
                  {panelView === "analytics" ? "Full analytics" : "Scenario summary"}
                </h2>
                <p className="text-xs text-text-muted font-mono truncate print:text-black">{scenarioId}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0 print:hidden">
              <button
                onClick={() => window.print()}
                className="text-xs px-2 py-1 rounded border border-border text-text-muted hover:border-primary hover:text-primary transition-colors"
                title="Download Executive Brief (PDF)"
                aria-label="Download Executive Brief"
              >
                Download Brief
              </button>
              <span className="text-xs font-mono bg-secondary px-2 py-1 rounded" data-testid="ws-status">
                {statusLabel(runState)}
              </span>
              {isRunActive && (
                <button
                  onClick={cancelRun}
                  className="text-xs px-2 py-1 rounded border border-border text-text-muted hover:border-error hover:text-error transition-colors"
                  data-testid="cancel-run"
                >
                  Cancel
                </button>
              )}
              <button
                onClick={() => setShowResultsPanel(false)}
                className="p-1.5 rounded-lg text-text-muted hover:text-text hover:bg-surface-elevated transition-colors"
                aria-label="Close results panel"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

        <div className="p-4 flex-1 flex flex-col gap-4 overflow-y-auto overflow-x-hidden print:overflow-visible">
          <div className="print:hidden">
            <RunProgress runState={runState} />
            <RunStatusBanner runState={runState} onRetry={retryRun} />
          </div>

          {!isDrawerOpen &&
            (panelView === "analytics" ? (
              <AnalyticsView
                results={results}
                synthesis={synthesis}
                scenarioId={scenarioId}
                isRunActive={isRunActive}
                onInspect={(card) => { setInspectData(card.provData); setIsDrawerOpen(true); setInspectingMetric(card.dimension); }}
                onCiteClick={handleCiteClick}
              />
            ) : (
              <SummaryView
                results={results}
                narrative={synthesis?.narrative}
                isRunActive={isRunActive}
                onInspect={(card) => { setInspectData(card.provData); setIsDrawerOpen(true); setInspectingMetric(card.dimension); }}
                onOpenAnalytics={() => setPanelView("analytics")}
              />
            ))}
        </div>

        {/* Map attribution — replaces MapLibre's default white control (ODbL/OpenMapTiles). */}
        <div className="px-4 py-2.5 border-t border-border shrink-0 print:hidden">
          <MapAttribution />
        </div>

        <InspectDrawer
          isOpen={isDrawerOpen}
          onClose={() => { setIsDrawerOpen(false); setInspectingMetric(null); }}
          metricId={inspectData?.equationId || null}
          data={inspectData}
        >
          <div className="flex flex-col gap-4 mt-2">
            <h4 className="text-sm font-medium text-text-muted uppercase tracking-wider mb-1">
              Category Breakdown
            </h4>
            {DIMENSIONS.map((dim) => (
              <DimensionResultGroup
                key={dim}
                dim={dim}
                dimResults={results.filter((r) => r.dimension === dim)}
                expectedResults={EXPECTED_RESULTS[dim]}
                isRunActive={isRunActive}
                colorClass={getDimensionColor(dim)}
                variant="drawer"
                onInspect={(card) => { setInspectData(card.provData); setIsDrawerOpen(true); setInspectingMetric(dim); }}
              />
            ))}
          </div>
        </InspectDrawer>
      </div>
      )}

      {/* Map Area */}
      <div className="flex-1 relative order-1 md:order-2 print:h-[600px] print:w-full print:block">
        <DeckGL
          viewState={{
            ...viewState,
            padding: { right: (showResultsPanel || isDrawerOpen) ? 424 : 0, left: 64, top: 0, bottom: 0 }
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
            attributionControl={false}
            reuseMaps
          />
        </DeckGL>

        {/* Map layer toggles — drives useMapLayers + the page-owned TripsLayer */}
        <div className="absolute left-4 top-4 z-10 print:hidden">
          <LayerLegend
            layers={[
              { id: "agents", label: "Agent Trajectories", icon: Route, active: !!activeLayers.agents },
              { id: "congestion", label: "Congestion", icon: Activity, active: !!activeLayers.congestion },
              { id: "confidence", label: "Confidence", icon: Gauge, active: !!activeLayers.confidence },
              { id: "flood", label: "Flood Zones", icon: Waves, active: !!activeLayers.flood },
            ]}
            onToggleLayer={handleToggleLayer}
          />
        </div>

        {/* Timeline Scrubber */}
        <div className="glass absolute bottom-6 left-1/2 -translate-x-1/2 px-6 py-3 rounded-xl flex items-center gap-4 min-w-[300px] print:hidden">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            aria-label={isPlaying ? "Pause playback" : "Play playback"}
            className="w-8 h-8 flex items-center justify-center rounded-full bg-primary text-primary-foreground hover:bg-primary-hover transition-colors active:scale-95"
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
          </button>
          <input
            type="range"
            min="0"
            max={maxTime > 0 ? maxTime : 1000}
            value={time}
            onChange={(e) => setTime(Number(e.target.value))}
            className="flex-1 accent-primary"
          />
          <span className="text-xs font-mono w-12">{time}</span>
        </div>
      </div>
      </div>
    </div>
  );
}

function getDimensionColor(dim: string) {
  switch(dim.toLowerCase()) {
    case 'behavioral': return 'bg-[#2563EB]';
    case 'social': return 'bg-[#DB2777]';
    case 'economic': return 'bg-[#CA8A04]';
    case 'ecological': return 'bg-[#16A34A]';
    case 'societal': return 'bg-[#9333EA]';
    default: return 'bg-gray-500';
  }
}
