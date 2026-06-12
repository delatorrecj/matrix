"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Map } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import DeckGL from "@deck.gl/react";
import { TripsLayer } from "@deck.gl/geo-layers";
import InspectDrawer, { ProvenanceData } from "@/components/InspectDrawer";
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

const MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty";

export default function ScenarioSimulation() {
  const params = useParams();
  const scenarioId = params.id as string;

  const [time, setTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);

  const [runState, setRunState] = useState<RunState>(initialRunState);
  const [runAttempt, setRunAttempt] = useState(0);

  const [results, setResults] = useState<ResultCard[]>([]);
  const [tripsData, setTripsData] = useState<{ path: [number, number][], timestamps: number[] }[]>([]);
  const [synthesis, setSynthesis] = useState<{ narrative: string } | null>(null);
  const [inspectData, setInspectData] = useState<ProvenanceData | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);

  const dispatch = useCallback((event: RunEvent) => {
    setRunState((s) => reduceRunEvent(s, event));
  }, []);

  // DeckGL setup
  const layers = [
    new TripsLayer({
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
    })
  ];

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
        // Accumulate playback frames for Deck.gl
        // Note: For simplicity we expect the backend to stream agents with paths
        if (Array.isArray(msg.agents)) {
          const agents = msg.agents;
          setTripsData((prev) => [...prev, ...agents]);
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
          equationText: `Result for ${metric}`,
          inputs: (Array.isArray(msg.input_dataset_ids) ? msg.input_dataset_ids : []).map((id: string) => ({
            id, name: id, confidence, vintage: "current"
          })),
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
          setSynthesis({ narrative: msg.narrative });
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
    setSynthesis(null);
    setRunState(initialRunState());
    setRunAttempt((a) => a + 1);
  }, []);

  // Simple playback loop
  useEffect(() => {
    let animationFrame: number;
    const animate = () => {
      setTime(t => (t + 1) % 1000);
      animationFrame = requestAnimationFrame(animate);
    };
    if (isPlaying) {
      animationFrame = requestAnimationFrame(animate);
    }
    return () => cancelAnimationFrame(animationFrame);
  }, [isPlaying]);

  const isRunActive = !isTerminal(runState.phase) && runState.phase !== "disconnected";

  return (
    <div className="flex h-screen w-full flex-col md:flex-row overflow-hidden bg-background">

      {/* 5-Dimension Impact Panel (Right Side, normally overlay but docked here) */}
      <div className="w-full md:w-[360px] lg:w-[400px] h-full bg-surface shadow-md z-10 flex flex-col border-l border-border order-2 md:order-1 overflow-y-auto">
        <div className="p-4 border-b border-border flex justify-between items-center gap-2">
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
                    className="border border-border rounded-lg p-4 bg-surface hover:border-primary transition-colors cursor-pointer group"
                    onClick={() => { setInspectData(card.provData); setIsDrawerOpen(true); }}
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
            <div className="p-4 bg-primary/5 border border-primary/20 rounded-lg mt-2">
              <h4 className="text-xs font-bold text-primary mb-2 uppercase">Synthesis</h4>
              <p className="text-sm text-foreground">{synthesis.narrative}</p>
            </div>
          )}

          <ValidationPanel />
          <BiasAuditLog runId={scenarioId} />
        </div>
      </div>

      {/* Map Area */}
      <div className="flex-1 relative order-1 md:order-2">
        <DeckGL
          initialViewState={{
            longitude: 122.56,
            latitude: 10.71,
            zoom: 13,
            pitch: 45,
            bearing: 0
          }}
          controller={true}
          layers={layers}
        >
          <Map
            mapStyle={MAP_STYLE}
            mapLib={maplibregl}
            reuseMaps
          />
        </DeckGL>

        {/* Timeline Scrubber */}
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-surface px-6 py-3 rounded-full shadow-lg border border-border flex items-center gap-4 min-w-[300px]">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="w-8 h-8 flex items-center justify-center rounded-full bg-primary text-primary-foreground hover:bg-primary-hover transition-colors"
          >
            {isPlaying ? "⏸" : "▶"}
          </button>
          <input
            type="range"
            min="0"
            max="1000"
            value={time}
            onChange={(e) => setTime(Number(e.target.value))}
            className="flex-1 accent-primary"
          />
          <span className="text-xs font-mono w-12">{time}</span>
        </div>
      </div>

      <InspectDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
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
