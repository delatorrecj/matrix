"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { Map, Marker } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import DeckGL from "@deck.gl/react";
import { TripsLayer } from "@deck.gl/geo-layers";
import { FlyToInterpolator } from "@deck.gl/core";
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
import { LayerLegend } from "@/components/LayerLegend";
import {
  useMapLayers,
  fetchStaticLayer,
  confidenceCellsFromGeoJSON,
  affectedEdgesLayer,
  filterAffectedFeatures,
  honestAffectedEdgeIds,
  affectedBounds,
  zoomForBbox,
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
import { MAP_STYLE_DARK, MAP_STYLE_LIGHT, registerMissingImageFallback, syncBuilding3dLayer } from "@/lib/mapStyles";
import { buildProvenanceData, mapPaddingRight, statusChipLabel } from "@/lib/provenance";
import { getScenario, getLatestRun, type ScenarioGeometry, type StoredDimensionResult } from "@/lib/api";
import { useHasMounted } from "@/lib/useHasMounted";
import { MapContextMenu } from "@/components/map/MapContextMenu";
import { useMapContextMenu } from "@/components/map/useMapContextMenu";
import type { MapRef } from "react-map-gl/maplibre";
import type { DimensionId, RunTimings } from "@/lib/simulationRun";

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
const handleViewStateChange = ({ viewState }: any) => ({
  ...viewState,
  longitude: Math.min(Math.max(viewState.longitude, ILOILO_BOUNDS.minLng), ILOILO_BOUNDS.maxLng),
  latitude: Math.min(Math.max(viewState.latitude, ILOILO_BOUNDS.minLat), ILOILO_BOUNDS.maxLat),
  zoom: Math.max(viewState.zoom, ILOILO_BOUNDS.minZoom),
});

/** Reduce a scenario's GeoJSON geometry to a single [lng, lat] to fly the map to —
 * a Point's own coordinates, or the centroid (mean of the outer ring, excluding the
 * closing duplicate vertex) for a Polygon. Mirrors ScenarioBuilder's centroid logic. */
function geometryToLngLat(geometry: ScenarioGeometry | null): [number, number] | null {
  if (!geometry) return null;
  if (geometry.type === "Point") {
    const coords = geometry.coordinates as number[];
    return [coords[0], coords[1]];
  }
  const ring = (geometry.coordinates as number[][][])[0];
  if (!ring || ring.length === 0) return null;
  const vertices = ring.slice(0, -1).length > 0 ? ring.slice(0, -1) : ring;
  const n = vertices.length;
  const cx = vertices.reduce((s, v) => s + v[0], 0) / n;
  const cy = vertices.reduce((s, v) => s + v[1], 0) / n;
  return [cx, cy];
}

function recordLocationOfInterest(record: {
  location_of_interest?: [number, number] | null;
  geometry: ScenarioGeometry | null;
}): [number, number] | null {
  const loi = record.location_of_interest;
  if (Array.isArray(loi) && loi.length === 2 && typeof loi[0] === "number" && typeof loi[1] === "number") {
    return [loi[0], loi[1]];
  }
  return geometryToLngLat(record.geometry);
}

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
  const [locationOfInterest, setLocationOfInterest] = useState<[number, number] | null>(null);

  // CR-013: fetch the scenario's own parsed location once, so the results view can pan/
  // zoom to it instead of sitting at the generic Iloilo-wide default.
  useEffect(() => {
    let cancelled = false;
    getScenario(scenarioId)
      .then((record) => {
        if (cancelled) return;
        setLocationOfInterest(recordLocationOfInterest(record));
      })
      .catch(() => {
        // No scenario metadata (404 / API down) — keep the default view, no error surfaced.
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

  const [viewState, setViewState] = useState({
    longitude: 122.56,
    latitude: 10.72,
    zoom: 13,
    pitch: 45,
    bearing: 0
  });

  const [runState, setRunState] = useState<RunState>(initialRunState);
  const [runAttempt, setRunAttempt] = useState(0);
  /** After bootstrap: open WS only when there is no completed run to hydrate (or Re-run). */
  const [shouldSimulate, setShouldSimulate] = useState(false);
  const [bootstrapped, setBootstrapped] = useState(false);

  const [results, setResults] = useState<ResultCardData[]>([]);
  const [tripsData, setTripsData] = useState<{ id: string, path: [number, number][], timestamps: number[] }[]>([]);
  const [maxTime, setMaxTime] = useState(1000);

  // Map data layers. `agents` toggles the page-owned TripsLayer; congestion/confidence/flood
  // are assembled by useMapLayers. Static files (edges/flood/confidence) load once; congestion
  // is driven by the live EDGE_COUNTS stream event (reset per run, like tripsData/results).
  const [edgeCounts, setEdgeCounts] = useState<EdgeCounts>({});
  const [affectedEdges, setAffectedEdges] = useState<string[]>([]);
  const [edgeResolution, setEdgeResolution] = useState<string | null>(null);
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

  // Fly to the scenario's location of interest once, as soon as both the map and the
  // scenario metadata are ready. Cap zoom so trajectories/layers stay readable.
  useEffect(() => {
    if (locationOfInterest && mapLoaded) {
      const [lng, lat] = locationOfInterest;
      setViewState((prev) => ({
        ...prev,
        longitude: lng,
        latitude: lat,
        zoom: 15,
        transitionDuration: 2200,
        transitionInterpolator: new FlyToInterpolator({ speed: 1.2 }),
      }));
    }
  }, [locationOfInterest, mapLoaded]);

  const affectedCollection = useMemo(
    () =>
      filterAffectedFeatures(
        edgesGeoJSON,
        honestAffectedEdgeIds(edgeResolution, affectedEdges),
      ),
    [edgesGeoJSON, edgeResolution, affectedEdges],
  );

  const haloLayer = useMemo(() => affectedEdgesLayer(affectedCollection), [affectedCollection]);

  // Second fly: fit honest affected edges + 300 m buffer. Skip fallback (empty collection).
  useEffect(() => {
    if (!mapLoaded || !affectedCollection) return;
    const bbox = affectedBounds(affectedCollection);
    if (!bbox) return;
    const [minLng, minLat, maxLng, maxLat] = bbox;
    setViewState((prev) => ({
      ...prev,
      longitude: (minLng + maxLng) / 2,
      latitude: (minLat + maxLat) / 2,
      zoom: zoomForBbox(bbox),
      transitionDuration: 1800,
      transitionInterpolator: new FlyToInterpolator({ speed: 1.2 }),
    }));
  }, [affectedCollection, mapLoaded]);

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

  // Bootstrap: hydrate a completed run (no re-SUMO) or open WS for a fresh/re-run.
  useEffect(() => {
    let cancelled = false;
    setBootstrapped(false);
    setShouldSimulate(false);

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
          setTripsData([]);
          setEdgeCounts({});
          setAffectedEdges(
            Array.isArray(run.affected_edges)
              ? run.affected_edges.filter((id): id is string => typeof id === "string")
              : [],
          );
          setEdgeResolution(typeof run.edge_resolution === "string" ? run.edge_resolution : null);
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
        if (typeof msg.edge_resolution === "string") {
          setEdgeResolution(msg.edge_resolution);
        }
        if (Array.isArray(msg.affected_edges)) {
          setAffectedEdges(msg.affected_edges.filter((id): id is string => typeof id === "string"));
        }
        // Only fill location when scenario fetch left it unset (avoid re-fly mid-run).
        if (Array.isArray(msg.location_of_interest) && msg.location_of_interest.length === 2) {
          const [lon, lat] = msg.location_of_interest as [number, number];
          setLocationOfInterest((prev) => prev ?? [lon, lat]);
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

  // DSD §5/§9 (Impeccable register — motion row): respect prefers-reduced-motion.
  // The agent playback is the one substantive motion, but it must not auto-loop
  // for users who asked for reduced motion — start paused; they can still press play.
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
    setViewState((prev) => ({
      ...prev,
      longitude: lngLat.lng,
      latitude: lngLat.lat,
      zoom: Math.max(prev.zoom, 15),
      transitionDuration: 600,
    }));
  };

  return (
    <div className="relative h-dvh w-full overflow-hidden bg-background text-foreground flex print:h-auto print:block print:overflow-visible print:bg-white">
      {/* ICON NAV RAIL */}
      <div className="print:hidden">
        <IconNavRail
          activeId={panelView === "analytics" ? "analytics" : "trajectories"}
          onNavigate={(id) => {
            if (id === "home") {
              closeInspect();
              router.push("/app");
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

        <div className="p-4 flex-1 flex flex-col gap-4 overflow-y-auto overflow-x-hidden print:overflow-visible">
          <div className="print:hidden">
            <RunProgress runState={runState} />
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
              <InitializingState variant="panel" />
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

        {/* Map attribution — replaces MapLibre's default white control (ODbL/OpenMapTiles). */}
        <div className="px-4 py-2.5 border-t border-border shrink-0 print:hidden">
          <MapAttribution />
        </div>

        <InspectDrawer
          isOpen={isDrawerOpen}
          onClose={closeInspect}
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
                onInspect={(card) => openInspect(card.provData, dim)}
              />
            ))}
          </div>
        </InspectDrawer>
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
        <DeckGL
          viewState={{
            ...viewState,
            padding: { right: mapRightPadding, left: 64, top: 0, bottom: 0 }
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
            onLoad={() => setMapLoaded(true)}
          >
            {locationOfInterest && (
              <Marker longitude={locationOfInterest[0]} latitude={locationOfInterest[1]} anchor="bottom">
                <div
                  className="h-4 w-4 -translate-y-1 rounded-full border-2 border-white bg-primary shadow-lg"
                  title="Scenario location of interest"
                />
              </Marker>
            )}
          </Map>
        </DeckGL>
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

        {/* Timeline Scrubber — only once results have loaded (run reached DONE).
            While the first run is still computing, the control slot shows an
            "Initializing" pill instead of an inert play button. */}
        {resultsReady ? (
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
        ) : isRunActive ? (
          <div className="glass absolute bottom-6 left-1/2 -translate-x-1/2 px-6 py-3 rounded-xl flex items-center justify-center min-w-[300px] print:hidden">
            <InitializingState variant="pill" />
          </div>
        ) : null}
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
