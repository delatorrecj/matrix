"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { Map, Marker } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
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
import { InitializingState } from "@/components/InitializingState";
import { IconNavRail } from "@/components/IconNavRail";
import { ScenarioPromptReview } from "@/components/ScenarioPromptReview";
import {
  DIMENSIONS,
  EXPECTED_RESULTS,
  RunEvent,
  RunState,
  buildSimulationWsUrl,
  initialRunState,
  isTerminal,
  reduceRunEvent,
} from "@/lib/simulationRun";
import { mapPlaybackFromLatestRun, mapPlaybackFromWs } from "@/lib/mapPlayback";
import { accumulateTripFrame } from "@/lib/playbackTrips";
import { LayerLegend } from "@/components/LayerLegend";
import {
  useMapLayers,
  fetchStaticLayer,
  affectedEdgesLayer,
  filterAffectedFeatures,
  honestAffectedEdgeIds,
  resultsCameraFly,
  corridorAnchorLonLat,
  resultsMapPin,
  shouldAutoFly,
  zoomForBbox,
  zoomWithoutPullingOut,
} from "@/components/map";
import type {
  EdgeCounts,
  EdgesFeatureCollection,
  FeatureCollection,
  MapLayerToggles,
} from "@/components/map";
import { Route, Activity, Waves, X, LayoutList, ChevronLeft } from "lucide-react";
import { useTheme } from "@/components/ThemeProvider";
import { MAP_STYLE_DARK, MAP_STYLE_LIGHT, registerMissingImageFallback, syncBuilding3dLayer } from "@/lib/mapStyles";
import { buildProvenanceData, mapPaddingRight, statusChipLabel } from "@/lib/provenance";
import { getLatestRun, getScenario, type StoredDimensionResult } from "@/lib/api";
import { overlayPromptHandoff, takePromptHandoff, type PromptHandoff } from "@/lib/promptHandoff";
import { useHasMounted } from "@/lib/useHasMounted";
import { MapContextMenu } from "@/components/map/MapContextMenu";
import { useMapContextMenu } from "@/components/map/useMapContextMenu";
import { DeckGLOverlay } from "@/components/map/DeckGLOverlay";
import {
  SCENARIO_DEFAULT_VIEW,
  clampScenarioViewState,
} from "@/components/map/scenarioMapConstants";
import { isCityDefaultView, loadMapView, saveMapView } from "@/components/map/mapViewMemory";
import type { MapRef } from "react-map-gl/maplibre";
import type { DimensionId, RunTimings } from "@/lib/simulationRun";

const DEFAULT_VIEW = SCENARIO_DEFAULT_VIEW;
const handleViewStateChange = clampScenarioViewState;

/** Map a stored GET /runs|/latest-run result into the same card shape as DIMENSION_RESULT. */
function storedResultToCard(r: StoredDimensionResult, index: number): ResultCardData {
  const confidence = typeof r.confidence === "string" ? r.confidence : "L";
  const equationId = String(r.equation_id ?? "");
  const metric = typeof r.metric === "string" ? r.metric : equationId || "metric";
  const value = typeof r.value === "number" ? r.value : Number(r.value);
  const rawRange: [number, number] | null =
    Array.isArray(r.range) &&
    r.range.length === 2 &&
    typeof r.range[0] === "number" &&
    typeof r.range[1] === "number"
      ? [r.range[0], r.range[1]]
      : null;
  const range = rawRange ? `${rawRange[0]}..${rawRange[1]}` : "";
  return {
    key: `${r.dimension}:${metric}:${index}`,
    dimension: String(r.dimension ?? "unknown"),
    metric,
    equationId,
    unit: typeof r.unit === "string" ? r.unit : "",
    conf: confidence,
    rawValue: value,
    rawRange,
    directional: r.directional === true || confidence === "L",
    provData: buildProvenanceData({
      metric,
      value: String(r.value),
      range,
      confidence,
      equationId,
      input_dataset_ids: Array.isArray(r.input_dataset_ids) ? r.input_dataset_ids : [],
      assumptions: Array.isArray(r.assumptions) ? r.assumptions : [],
      references: Array.isArray(r.references) ? r.references : [],
    }),
  };
}

function hydrateRunStateFromStored(
  results: StoredDimensionResult[],
  durationMs: number | null,
  timings: RunTimings | null,
): RunState {
  const resultsByDimension: Record<DimensionId, number> = {
    behavioral: 0,
    ecological: 0,
    social: 0,
    economic: 0,
    societal: 0,
  };
  for (const r of results) {
    const dim = r.dimension;
    if (dim === "behavioral" || dim === "ecological" || dim === "social" || dim === "economic" || dim === "societal") {
      resultsByDimension[dim] += 1;
    }
  }
  return {
    phase: "done",
    wsOpened: false,
    queuePosition: null,
    resultsByDimension,
    resultCount: results.length,
    synthesisReceived: false,
    durationMs,
    timings,
    error: null,
  };
}

export default function ScenarioSimulation() {
  const router = useRouter();
  const params = useParams();
  const scenarioId = params.id as string;
  const mapRef = useRef<MapRef>(null);
  const { theme } = useTheme();
  const {
    containerRef: mapContainerRef,
    menuPosition,
    menuLngLat,
    closeMenu: closeMapMenu,
    handleContextMenu,
  } = useMapContextMenu({ mapRef });

  const [mapLoaded, setMapLoaded] = useState(false);
  const mapMounted = useHasMounted();
  const [exitConfirmOpen, setExitConfirmOpen] = useState(false);
  const [promptReview, setPromptReview] = useState<PromptHandoff | null>(null);

  useEffect(() => {
    let cancelled = false;
    const handoff = takePromptHandoff(scenarioId);
    if (handoff) setPromptReview(handoff);

    getScenario(scenarioId)
      .then((record) => {
        if (cancelled) return;
        setPromptReview((prev) => overlayPromptHandoff(record, prev));
      })
      .catch(() => {
        // Keep the handoff card if GET 404s (in-memory/Postgres split).
      });
    return () => {
      cancelled = true;
    };
  }, [scenarioId]);

  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (!map) return;

    const syncBuildings = (e?: { type: string; sourceId?: string }) => {
      if (e && e.type === "sourcedata" && e.sourceId !== "openmaptiles") return;
      if (map.getSource("openmaptiles")) {
        try {
          syncBuilding3dLayer(map, theme, true);
        } catch {
          // Style not fully ready yet — the next sourcedata/style.load event retries.
        }
      }
    };

    if (map.isStyleLoaded()) {
      syncBuildings();
    }

    map.on("style.load", syncBuildings);
    map.on("sourcedata", syncBuildings);
    const disposeMissingImage = registerMissingImageFallback(map);

    return () => {
      map.off("style.load", syncBuildings);
      map.off("sourcedata", syncBuildings);
      disposeMissingImage();
    };
  }, [theme, mapLoaded]);

  const [time, setTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);

  const [showResultsPanel, setShowResultsPanel] = useState(true);
  // CR-010: the dock is summary-only by default; "analytics" opens the full,
  // interpreted detail view (driven by the nav rail + the "View full analytics" link).
  const [panelView, setPanelView] = useState<"summary" | "analytics">("summary");
  const [inspectingMetric, setInspectingMetric] = useState<string | null>(null);

  const [viewState, setViewState] = useState(DEFAULT_VIEW);
  const [viewReady, setViewReady] = useState(false);

  useEffect(() => {
    const saved = loadMapView(scenarioId);
    if (saved) setViewState((prev) => ({ ...prev, ...saved }));
    setViewReady(true);
  }, [scenarioId]);

  useEffect(() => {
    if (!viewReady) return;
    saveMapView(scenarioId, {
      longitude: viewState.longitude,
      latitude: viewState.latitude,
      zoom: viewState.zoom,
      pitch: viewState.pitch,
      bearing: viewState.bearing,
    });
  }, [
    viewReady,
    scenarioId,
    viewState.longitude,
    viewState.latitude,
    viewState.zoom,
    viewState.pitch,
    viewState.bearing,
  ]);

  const [runState, setRunState] = useState<RunState>(initialRunState);
  const [runAttempt, setRunAttempt] = useState(0);
  /** After bootstrap: open WS only when there is no completed run to hydrate (or Re-run). */
  const [shouldSimulate, setShouldSimulate] = useState(false);
  const [bootstrapped, setBootstrapped] = useState(false);
  const [mapPlaybackExpired, setMapPlaybackExpired] = useState(false);

  const [results, setResults] = useState<ResultCardData[]>([]);
  const [tripsData, setTripsData] = useState<{ id: string, path: [number, number][], timestamps: number[] }[]>([]);
  const [maxTime, setMaxTime] = useState(1000);

  // Map data layers. `agents` toggles the page-owned TripsLayer; congestion/flood
  // are assembled by useMapLayers. Static files (edges/flood) load once; congestion
  // is driven by the live EDGE_COUNTS stream event (reset per run, like tripsData/results).
  const [edgeCounts, setEdgeCounts] = useState<EdgeCounts>({});
  const [affectedEdges, setAffectedEdges] = useState<string[]>([]);
  const [edgeResolution, setEdgeResolution] = useState<string | null>(null);
  const [overlayHonest, setOverlayHonest] = useState(false);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [activeLayers, setActiveLayers] = useState<MapLayerToggles>({
    agents: true, congestion: true, flood: false,
  });
  const [edgesGeoJSON, setEdgesGeoJSON] = useState<EdgesFeatureCollection | null>(null);
  const [floodGeoJSON, setFloodGeoJSON] = useState<FeatureCollection | null>(null);
  const [synthesis, setSynthesis] = useState<{
    narrative: string;
    citations: SynthesisCitation[];
  } | null>(null);
  const [inspectData, setInspectData] = useState<ProvenanceData | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const closeInspect = useCallback(() => {
    setIsDrawerOpen(false);
    setInspectingMetric(null);
    setInspectData(null);
  }, []);

  const openInspect = useCallback((provData: ProvenanceData, dimension: string) => {
    setInspectData(provData);
    setIsDrawerOpen(true);
    setInspectingMetric(dimension);
  }, []);

  const affectedCollection = useMemo(
    () =>
      filterAffectedFeatures(
        edgesGeoJSON,
        honestAffectedEdgeIds(edgeResolution, affectedEdges, overlayHonest),
      ),
    [edgesGeoJSON, edgeResolution, affectedEdges, overlayHonest],
  );

  const haloLayer = useMemo(() => affectedEdgesLayer(affectedCollection), [affectedCollection]);
  const corridorAnchor = useMemo(
    () => corridorAnchorLonLat(affectedCollection),
    [affectedCollection],
  );
  const mapPin = useMemo(() => resultsMapPin(corridorAnchor), [corridorAnchor]);

  // Live run, or a hydrate still on the city default: corridor box only.
  useEffect(() => {
    if (!mapLoaded || !viewReady) return;
    if (!shouldAutoFly(shouldSimulate, isCityDefaultView(viewState))) return;
    const map = mapRef.current;
    if (!map) return;
    const fly = resultsCameraFly(affectedCollection);
    if (fly.kind === "stay") return;
    const [minLng, minLat, maxLng, maxLat] = fly.bbox;
    map.flyTo({
      center: [(minLng + maxLng) / 2, (minLat + maxLat) / 2],
      zoom: zoomWithoutPullingOut(map.getZoom(), zoomForBbox(fly.bbox)),
      duration: 1800,
    });
  }, [affectedCollection, mapLoaded, shouldSimulate, viewReady]);

  const wsRef = useRef<WebSocket | null>(null);
  const leavingRef = useRef(false);

  const dispatch = useCallback((event: RunEvent) => {
    setRunState((s) => reduceRunEvent(s, event));
  }, []);

  // DeckGL setup — data layers (flood then congestion) sit under the animated
  // agent trajectories. useMapLayers omits any layer whose data is absent.
  const dataLayers = useMapLayers(activeLayers, {
    edgesGeoJSON,
    edgeCounts,
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
    jointRounded: true,
    capRounded: true,
    trailLength: 100,
    currentTime: time,
  });
  
  const layers = [
    ...dataLayers,
    ...(haloLayer ? [haloLayer] : []),
    ...(activeLayers.agents ? [tripsLayer] : []),
  ].map((layer: Layer) => {
    if (!inspectingMetric || !isDrawerOpen) return layer;
    
    let isHighlighted = false;
    const dim = inspectingMetric.toLowerCase();
    
    if (dim === "ecological" && layer.id === "flood-layer") isHighlighted = true;
    if (dim === "behavioral" && (layer.id === "trips-layer" || layer.id === "congestion-layer")) isHighlighted = true;

    return layer.clone({ opacity: isHighlighted ? (layer.props.opacity ?? 1) : 0.05 });
  });

  const handleToggleLayer = useCallback((id: string) => {
    setActiveLayers((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  // Static map layers load once (graceful no-op on a miss — fetchStaticLayer resolves null).
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const [edges, flood] = await Promise.all([
        fetchStaticLayer("edges"),
        fetchStaticLayer("flood"),
      ]);
      if (cancelled) return;
      setEdgesGeoJSON(edges as EdgesFeatureCollection | null);
      setFloodGeoJSON(flood);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Bootstrap: hydrate a completed run (no re-SUMO) or open WS for a fresh/re-run.
  useEffect(() => {
    let cancelled = false;
    setBootstrapped(false);
    setShouldSimulate(false);
    setMapPlaybackExpired(false);

    void (async () => {
      // Re-run / retry always simulates.
      if (runAttempt > 0) {
        if (!cancelled) {
          setShouldSimulate(true);
          setBootstrapped(true);
        }
        return;
      }
      try {
        const run = await getLatestRun(scenarioId);
        if (cancelled) return;
        if (run && run.status === "done" && Array.isArray(run.results) && run.results.length > 0) {
          const cards = run.results.map(storedResultToCard);
          setResults(cards);
          const playbackState = mapPlaybackFromLatestRun(run.playback, {
            affected_edges: run.affected_edges,
            edge_resolution: run.edge_resolution,
          });
          setEdgeCounts(playbackState.edgeCounts);
          setTripsData(playbackState.trips);
          setMaxTime((prev) => Math.max(prev, playbackState.maxTime));
          setMapPlaybackExpired(playbackState.playbackExpired);
          setEdgeResolution(playbackState.edgeResolution);
          setAffectedEdges(playbackState.affectedEdges);
          setOverlayHonest(playbackState.overlayHonest);
          if (typeof run.run_id === "string") setCurrentRunId(run.run_id);
          setSynthesis(null);
          const timings =
            run.timings && typeof run.timings === "object"
              ? (run.timings as RunTimings)
              : null;
          setRunState(
            hydrateRunStateFromStored(
              run.results,
              typeof run.duration_ms === "number" ? run.duration_ms : null,
              timings,
            ),
          );
          setShouldSimulate(false);
        } else {
          setShouldSimulate(true);
        }
      } catch {
        if (!cancelled) setShouldSimulate(true);
      } finally {
        if (!cancelled) setBootstrapped(true);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [scenarioId, runAttempt]);

  // WebSocket connection — one run per (scenarioId, runAttempt) when shouldSimulate.
  useEffect(() => {
    if (!bootstrapped || !shouldSimulate) return;

    const ws = new WebSocket(buildSimulationWsUrl(scenarioId));
    wsRef.current = ws;

    ws.onopen = () => dispatch({ type: "WS_OPEN" });

    ws.onmessage = (event) => {
      if (leavingRef.current) return;
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
        const tick = typeof msg.tick === "number" ? msg.tick : 0;
        setMaxTime((prev) => Math.max(prev, tick));
        if (Array.isArray(msg.agents)) {
          const agents = msg.agents as Array<{ id: string; lon: number; lat: number }>;
          setTripsData((prev) => accumulateTripFrame(prev, tick, agents));
        }
      } else if (msg.type === "EDGE_COUNTS") {
        const pb = mapPlaybackFromWs(msg);
        setEdgeCounts(pb.edgeCounts);
        setEdgeResolution(pb.edgeResolution);
        setAffectedEdges(pb.affectedEdges);
        setOverlayHonest(pb.overlayHonest);
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
        const provData = buildProvenanceData({
          metric,
          value: String(msg.value),
          range,
          confidence,
          equationId,
          input_dataset_ids: Array.isArray(msg.input_dataset_ids) ? msg.input_dataset_ids : [],
          assumptions: Array.isArray(msg.assumptions) ? msg.assumptions : [],
          references: Array.isArray(msg.references) ? msg.references : [],
        });

        setResults((prev) => [...prev, {
          key: `${msg.dimension}:${metric}:${prev.length}`,
          dimension: String(msg.dimension ?? "unknown"),
          metric,
          equationId,
          unit: typeof msg.unit === "string" ? msg.unit : "",
          conf: confidence,
          rawValue: value,
          rawRange,
          directional: msg.directional === true || confidence === "L",
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
        void getLatestRun(scenarioId)
          .then((run) => {
            if (run?.run_id) setCurrentRunId(run.run_id);
          })
          .catch(() => {});
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
  }, [bootstrapped, shouldSimulate, scenarioId, runAttempt, dispatch]);

  // Citation chip → Inspect drawer: resolve the equation id against the
  // accumulated results (glass box: an unmatched citation never opens a drawer —
  // SynthesisNarrative renders it disabled instead).
  const handleCiteClick = useCallback(
    (equationId: string) => {
      const match = results.find((r) => r.provData.equationId === equationId);
      if (!match) return;
      openInspect(match.provData, match.dimension);
    },
    [results, openInspect]
  );

  // Cancel: user-initiated stop — distinct from error and from done.
  const cancelRun = useCallback(() => {
    dispatch({ type: "CANCEL" });
    wsRef.current?.close();
  }, [dispatch]);

  // Home / logo: cancel an in-flight run, then leave for the cockpit. Soft
  // `router.push` is aborted by stream-driven re-renders and the two WebGL
  // maps; replace + hard assign is the path that actually unmounts this page.
  const exitToCockpit = useCallback(() => {
    leavingRef.current = true;
    if (!isTerminal(runState.phase)) {
      cancelRun();
    }
    closeInspect();
    setIsPlaying(false);
    router.replace("/app");
    window.location.assign("/app");
  }, [runState.phase, cancelRun, closeInspect, router]);

  // Retry/reconnect: reset accumulated stream state and open a fresh WS
  // (the server re-streams the run from the start).
  const retryRun = useCallback(() => {
    setResults([]);
    setTripsData([]);
    setEdgeCounts({});
    setAffectedEdges([]);
    setEdgeResolution(null);
    setSynthesis(null);
    setRunState(initialRunState());
    setRunAttempt((a) => a + 1);
  }, []);

  // DSD §5/§9: respect prefers-reduced-motion — do not auto-loop agent trips.
  useEffect(() => {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      setIsPlaying(false);
    }
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
  // "Results loaded" gate (CR-013): the run streamed every result + synthesis and
  // reached DONE. Until then the summary tab and the playback control show an
  // "Initializing" state instead of empty skeletons / an inert play button.
  const resultsReady = runState.phase === "done";
  const mapRightPadding = showResultsPanel || isDrawerOpen
    ? mapPaddingRight(showResultsPanel, panelView)
    : 0;

  const handleCopyCoordinates = async (lngLat: { lng: number; lat: number }) => {
    const text = `${lngLat.lat.toFixed(5)}, ${lngLat.lng.toFixed(5)}`;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Clipboard may be unavailable outside secure context.
    }
  };

  const handleCenterHere = (lngLat: { lng: number; lat: number }) => {
    mapRef.current?.flyTo({
      center: [lngLat.lng, lngLat.lat],
      zoom: Math.max(viewState.zoom, 15),
      duration: 600,
    });
  };

  return (
    <div className="relative h-dvh w-full overflow-hidden bg-background text-foreground flex print:h-auto print:block print:overflow-visible print:bg-white">
      {/* ICON NAV RAIL */}
      <div className="print:hidden">
        <IconNavRail
          activeId={panelView === "analytics" ? "analytics" : "trajectories"}
          onNavigate={(id) => {
            if (id === "home") {
              setExitConfirmOpen(true);
            } else if (id === "trajectories") {
              closeInspect();
              setPanelView("summary");
              setShowResultsPanel(true);
            } else if (id === "analytics") {
              closeInspect();
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
          <div className="p-4 border-b border-border bg-transparent flex flex-col gap-3 sm:flex-row sm:justify-between sm:items-start print:border-black">
            <div className="min-w-0 flex items-center gap-2 flex-1">
              {panelView === "analytics" && (
                <button
                  onClick={() => {
                    closeInspect();
                    setPanelView("summary");
                  }}
                  className="p-1 rounded-lg text-text-muted hover:text-text hover:bg-surface-elevated transition-colors print:hidden shrink-0"
                  aria-label="Back to summary"
                  title="Back to summary"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
              )}
              <div className="min-w-0">
                <h2 className="text-lg font-bold text-foreground print:text-black truncate">
                  {panelView === "analytics" ? "Full analytics" : "Scenario summary"}
                </h2>
                <p className="text-xs text-text-muted font-mono truncate print:text-black">{scenarioId}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end print:hidden">
              {resultsReady && (
                <button
                  onClick={() => window.print()}
                  className="text-xs px-2 py-1 rounded border border-border text-text-muted hover:border-primary hover:text-primary transition-colors whitespace-nowrap"
                  title="Download Executive Brief (PDF)"
                  aria-label="Download Executive Brief"
                >
                  Download Brief
                </button>
              )}
              {resultsReady && (
                <button
                  onClick={retryRun}
                  className="text-xs px-2 py-1 rounded border border-border text-text-muted hover:border-primary hover:text-primary transition-colors whitespace-nowrap"
                  title="Re-run simulation"
                  aria-label="Re-run simulation"
                  data-testid="rerun"
                >
                  Re-run
                </button>
              )}
              <span
                className="text-xs font-mono bg-secondary px-2 py-1 rounded max-w-[7rem] truncate"
                data-testid="ws-status"
                title={statusChipLabel(runState)}
              >
                {statusChipLabel(runState)}
              </span>
              {isRunActive && (
                <button
                  onClick={cancelRun}
                  className="text-xs px-2 py-1 rounded border border-border text-text-muted hover:border-error hover:text-error transition-colors whitespace-nowrap"
                  data-testid="cancel-run"
                >
                  Cancel
                </button>
              )}
              <button
                onClick={() => {
                  closeInspect();
                  setShowResultsPanel(false);
                }}
                className="p-1.5 rounded-lg text-text-muted hover:text-text hover:bg-surface-elevated transition-colors"
                aria-label="Close results panel"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

        <div className="relative flex-1 min-h-0">
          <div className="p-4 h-full flex flex-col gap-4 overflow-y-auto overflow-x-hidden print:overflow-visible">
            {promptReview && (
              <ScenarioPromptReview
                rawInput={promptReview.rawInput}
                description={promptReview.description}
                interventionType={promptReview.interventionType}
                location={promptReview.location}
                parameters={promptReview.parameters}
              />
            )}
            <div className="print:hidden">
              <RunProgress runState={runState} />
              {mapPlaybackExpired && (
                <p className="mt-1 text-xs text-text-muted">
                  Map playback expired. Re-run to restore trajectories.
                </p>
              )}
              <RunStatusBanner runState={runState} onRetry={retryRun} />
            </div>

            {panelView === "analytics" ? (
              <div className={`transition-all duration-300 ${isDrawerOpen ? "blur-[2px] opacity-40 pointer-events-none" : ""}`}>
                <AnalyticsView
                  results={results}
                  synthesis={synthesis}
                  scenarioId={scenarioId}
                  isRunActive={isRunActive}
                  onInspect={(card) => openInspect(card.provData, card.dimension)}
                  onCiteClick={handleCiteClick}
                />
              </div>
            ) : isRunActive && results.length === 0 ? (
              <div className={`transition-all duration-300 ${isDrawerOpen ? "blur-[2px] opacity-40 pointer-events-none" : ""}`}>
                <InitializingState />
              </div>
            ) : (
              <div className={`transition-all duration-300 ${isDrawerOpen ? "blur-[2px] opacity-40 pointer-events-none" : ""}`}>
                <SummaryView
                  results={results}
                  narrative={synthesis?.narrative}
                  isRunActive={isRunActive}
                  onInspect={(card) => openInspect(card.provData, card.dimension)}
                  onOpenAnalytics={() => setPanelView("analytics")}
                />
              </div>
            )}
          </div>
          <InspectDrawer
            isOpen={isDrawerOpen}
            onClose={closeInspect}
            metricId={inspectData?.equationId || null}
            data={inspectData}
            runId={currentRunId}
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
                  onInspect={(card) => openInspect(card.provData, dim)}
                />
              ))}
            </div>
          </InspectDrawer>
        </div>

        {/* Map attribution — replaces MapLibre's default white control (ODbL/OpenMapTiles). */}
        <div className="px-4 py-2.5 border-t border-border shrink-0 print:hidden">
          <MapAttribution />
        </div>
      </div>
      )}

      {/* Map Area */}
      <div className="flex-1 relative order-1 md:order-2 print:h-[600px] print:w-full print:block">
        <div
          ref={mapContainerRef}
          className="absolute inset-0"
          onContextMenu={handleContextMenu}
        >
        {mapMounted ? (
        <Map
          id="basemap-stage"
          ref={mapRef}
          longitude={viewState.longitude}
          latitude={viewState.latitude}
          zoom={viewState.zoom}
          pitch={viewState.pitch}
          bearing={viewState.bearing}
          padding={{ right: mapRightPadding, left: 64, top: 0, bottom: 0 }}
          onMove={(e) => setViewState(handleViewStateChange({ viewState: e.viewState }))}
          mapStyle={theme === "dark" ? MAP_STYLE_DARK : MAP_STYLE_LIGHT}
          mapLib={maplibregl}
          attributionControl={false}
          onLoad={() => setMapLoaded(true)}
          style={{ width: "100%", height: "100%" }}
        >
          <DeckGLOverlay layers={layers} />
          {mapPin && (
              <Marker
                longitude={mapPin[0]}
                latitude={mapPin[1]}
                anchor="center"
              >
                <div
                  className="relative h-5 w-5"
                  title={corridorAnchor ? "Affected corridor" : "Location of interest"}
                >
                  <span
                    className="absolute inset-0 rounded-full bg-dim-social/40 ring-1 ring-white/95 shadow-[0_0_6px_rgba(219,39,119,0.55)]"
                    aria-hidden="true"
                  />
                  <span
                    className="absolute inset-[4px] rounded-full bg-dim-social ring-1 ring-white"
                    aria-hidden="true"
                  />
                </div>
              </Marker>
            )}
        </Map>
        ) : (
          <div className="absolute inset-0 bg-background" aria-hidden="true" />
        )}
        {menuPosition && menuLngLat && (
          <MapContextMenu
            position={menuPosition}
            lngLat={menuLngLat}
            onClose={closeMapMenu}
            onCopyCoordinates={handleCopyCoordinates}
            onCenterHere={handleCenterHere}
          />
        )}
        </div>

        {/* Map layer toggles — drives useMapLayers + the page-owned TripsLayer */}
        <div className="absolute left-4 top-4 z-10 print:hidden" data-testid="scenario-map-layers">
          <LayerLegend
            layers={[
              { id: "agents", label: "Agent Trajectories", icon: Route, active: !!activeLayers.agents },
              { id: "congestion", label: "Congestion", icon: Activity, active: !!activeLayers.congestion },
              { id: "flood", label: "Flood Zones", icon: Waves, active: !!activeLayers.flood },
            ]}
            onToggleLayer={handleToggleLayer}
          />
        </div>

        </div>
      </div>

      {exitConfirmOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 print:hidden"
          role="dialog"
          aria-modal="true"
          aria-labelledby="exit-confirm-title"
        >
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setExitConfirmOpen(false)}
            aria-hidden="true"
          />
          <div className="glass relative w-full max-w-sm rounded-xl p-5">
            <h2 id="exit-confirm-title" className="text-base font-bold text-foreground">
              Leave this scenario?
            </h2>
            <p className="mt-2 text-sm text-text-muted">
              An in-progress run will be cancelled. Finished results stay saved.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setExitConfirmOpen(false)}
                className="px-3 py-1.5 rounded-lg border border-border text-sm font-medium text-text hover:bg-surface-elevated transition-colors"
              >
                Stay
              </button>
              <button
                type="button"
                onClick={() => {
                  setExitConfirmOpen(false);
                  exitToCockpit();
                }}
                className="px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary-hover transition-colors"
              >
                Leave
              </button>
            </div>
          </div>
        </div>
      )}
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
