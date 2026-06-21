"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Map } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import DeckGL from "@deck.gl/react";
import { TripsLayer } from "@deck.gl/geo-layers";
import InspectDrawer, { ProvenanceData } from "@/components/InspectDrawer";
import SynthesisNarrative, { SynthesisCitation } from "@/components/SynthesisNarrative";
import ValidationPanel from "@/components/ValidationPanel";
import BiasAuditLog from "@/components/BiasAuditLog";
import DimensionCardSkeleton from "@/components/DimensionCardSkeleton";
import RunProgress from "@/components/RunProgress";
import RunStatusBanner from "@/components/RunStatusBanner";
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
import { Route, Activity, Gauge, Waves, X, LayoutList } from "lucide-react";
import { useTheme } from "@/components/ThemeProvider";
import { MAP_STYLE_DARK, MAP_STYLE_LIGHT } from "@/lib/mapStyles";
import type { MapRef } from "react-map-gl/maplibre";

const ILOILO_BOUNDS = {
  minLng: 122.48,
  maxLng: 122.62,
  minLat: 10.64,
  maxLat: 10.79,
  minZoom: 11
};

const handleViewStateChange = ({ viewState }: any) => {
  viewState.longitude = Math.min(Math.max(viewState.longitude, ILOILO_BOUNDS.minLng), ILOILO_BOUNDS.maxLng);
  viewState.latitude = Math.min(Math.max(viewState.latitude, ILOILO_BOUNDS.minLat), ILOILO_BOUNDS.maxLat);
  viewState.zoom = Math.max(viewState.zoom, ILOILO_BOUNDS.minZoom);
  return viewState;
};

/** One DIMENSION_RESULT rendered as a glass-box metric card. */
interface ResultCard {
  key: string;
  dimension: string;
  metric: string;
  value: string;
  unit: string;
  conf: string;
  range: string;
  provData: ProvenanceData;
}



export default function ScenarioSimulation() {
  const params = useParams();
  const scenarioId = params.id as string;
  const mapRef = useRef<MapRef>(null);
  const { theme } = useTheme();

  useEffect(() => {
    if (mapRef.current) {
      mapRef.current.getMap().setStyle(theme === "dark" ? MAP_STYLE_DARK : MAP_STYLE_LIGHT);
    }
  }, [theme]);

  const [time, setTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);

  const [showResultsPanel, setShowResultsPanel] = useState(true);
  const [inspectingMetric, setInspectingMetric] = useState<string | null>(null);



  const [runState, setRunState] = useState<RunState>(initialRunState);
  const [runAttempt, setRunAttempt] = useState(0);

  const [results, setResults] = useState<ResultCard[]>([]);
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
      mapRef.current.getMap().flyTo({
        center: [122.56, 10.71],
        zoom: 14.5,
        duration: 800,
        essential: true,
      });
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
  
  const layers = [...dataLayers, ...(activeLayers.agents ? [tripsLayer] : [])].map((layer: any) => {
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
        // Build provenance data payload format expected by InspectDrawer
        const value = typeof msg.value === "number" ? msg.value : Number(msg.value);
        const range = Array.isArray(msg.range) && msg.range.length === 2
          ? `${msg.range[0]}..${msg.range[1]}`
          : "";
        const confidence = typeof msg.confidence === "string" ? msg.confidence : "L";
        const metric = typeof msg.metric === "string" ? msg.metric : String(msg.equation_id ?? "metric");
        const provData: ProvenanceData = {
          metric,
          value: String(msg.value),
          range,
          confidence,
          confidenceBasis: "Computed from input dataset confidences per methods §2",
          equationId: String(msg.equation_id ?? ""),
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
          value: Number.isFinite(value) && value > 0 ? `+${msg.value}` : String(msg.value),
          unit: typeof msg.unit === "string" ? msg.unit : "",
          conf: confidence,
          range,
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
    <div className="flex h-screen w-full flex-col md:flex-row overflow-hidden bg-background">

      {/* Floating Restore Button when panel is dismissed */}
      {!showResultsPanel && (
        <div className="absolute top-4 right-4 z-20 pointer-events-auto">
          <button
            onClick={() => setShowResultsPanel(true)}
            className="flex items-center gap-2 bg-surface/95 backdrop-blur-md border border-border shadow-lg rounded-full px-4 py-2 text-sm font-medium text-text hover:text-primary hover:border-primary/50 transition-all"
          >
            <LayoutList className="w-4 h-4" />
            Show Results
          </button>
        </div>
      )}

      {/* 5-Dimension Impact Panel (Right Side, normally overlay but docked here) */}
      {showResultsPanel && (
        <div className="w-full md:w-[360px] lg:w-[400px] h-full bg-surface/50 backdrop-blur-xl shadow-lg z-10 flex flex-col border-l border-white/10 order-2 md:order-1 overflow-y-auto relative">
          <div className="p-4 border-b border-white/10 bg-transparent flex justify-between items-center gap-2">
            <div className="min-w-0">
            <h2 className="text-lg font-bold text-foreground">Scenario Results</h2>
            <p className="text-xs text-text-muted font-mono truncate">{scenarioId}</p>
          </div>
            <div className="flex items-center gap-2 shrink-0">
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

        <div className="p-4 flex-1 flex flex-col gap-4">
          <RunProgress runState={runState} />
          <RunStatusBanner runState={runState} onRetry={retryRun} />

          {DIMENSIONS.map((dim) => {
            const dimResults = results.filter((r) => r.dimension === dim);
            if (dimResults.length === 0) {
              return (
                <DimensionCardSkeleton
                  key={dim}
                  name={dim}
                  colorClass={getDimensionColor(dim)}
                  expectedResults={EXPECTED_RESULTS[dim]}
                  active={isRunActive}
                />
              );
            }
            return (
              <div key={dim} className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${getDimensionColor(dim)}`} />
                    <span className="text-sm font-semibold capitalize">{dim}</span>
                  </div>
                  <span className="text-xs font-mono text-text-muted">
                    {dimResults.length}/{EXPECTED_RESULTS[dim]} results
                  </span>
                </div>

                {dimResults.map((card) => (
                  <div
                    key={card.key}
                    className="border border-border rounded-xl p-4 bg-surface-elevated hover:border-primary/50 transition-all cursor-pointer group"
                    onClick={() => { setInspectData(card.provData); setIsDrawerOpen(true); setInspectingMetric(dim); }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">{card.metric}</span>
                      {/* Confidence Chip */}
                      <div className={`text-xs px-2 py-0.5 border rounded-full font-mono ${
                        card.conf === 'H' ? 'bg-success/10 text-success border-success/20' :
                        card.conf === 'M' ? 'bg-warning/10 text-warning border-warning/20' :
                        'bg-destructive/10 text-destructive border-destructive/20 border-dashed'
                      }`}>
                        {card.conf}
                      </div>
                    </div>
                    <div className="flex items-end gap-2 mb-1">
                      <span className="text-2xl font-bold font-mono tracking-tight">{card.value}</span>
                      <span className="text-xs text-text-muted mb-1">{card.unit}</span>
                    </div>
                    <div className="text-xs text-text-muted font-mono flex justify-between">
                      <span>R: {card.range}</span>
                      <span className="opacity-0 group-hover:opacity-100 text-primary transition-opacity">Inspect →</span>
                    </div>
                  </div>
                ))}
              </div>
            );
          })}

          {synthesis && (
            <SynthesisNarrative
              narrative={synthesis.narrative}
              citations={synthesis.citations}
              resolvableEquationIds={results.map((r) => r.provData.equationId)}
              onCiteClick={handleCiteClick}
            />
          )}

          <ValidationPanel />
          <BiasAuditLog runId={scenarioId} />
        </div>
      </div>
      )}

      {/* Map Area */}
      <div className="flex-1 relative order-1 md:order-2">
        <DeckGL
          initialViewState={{
            longitude: 122.56,
            latitude: 10.72,
            zoom: 13,
            pitch: 45,
            bearing: 0
          }}
          controller={true}
          onViewStateChange={handleViewStateChange}
          layers={layers}
        >
          <Map
            ref={mapRef}
            mapStyle={theme === "dark" ? MAP_STYLE_DARK : MAP_STYLE_LIGHT}
            mapLib={maplibregl}
            reuseMaps
          />
        </DeckGL>

        {/* Map layer toggles — drives useMapLayers + the page-owned TripsLayer */}
        <div className="absolute left-4 top-4 z-10">
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
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-surface/95 backdrop-blur-md px-6 py-3 rounded-xl shadow-lg border border-border flex items-center gap-4 min-w-[300px]">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="w-8 h-8 flex items-center justify-center rounded-full bg-primary text-primary-foreground hover:bg-primary-hover transition-colors"
          >
            {isPlaying ? "⏸" : "▶"}
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

      <InspectDrawer
        isOpen={isDrawerOpen}
        onClose={() => { setIsDrawerOpen(false); setInspectingMetric(null); }}
        metricId={inspectData?.equationId || null}
        data={inspectData}
      />
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
