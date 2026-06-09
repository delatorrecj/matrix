"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Map } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import DeckGL from "@deck.gl/react";
import { TripsLayer } from "@deck.gl/geo-layers";
import InspectDrawer, { ProvenanceData } from "@/components/InspectDrawer";

interface Dimension {
  id: string;
  name: string;
  color: string;
  value: string;
  unit: string;
  conf: string;
  range: string;
  provData: ProvenanceData;
}
import ValidationPanel from "@/components/ValidationPanel";
import BiasAuditLog from "@/components/BiasAuditLog";

const MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty";

export default function ScenarioSimulation() {
  const params = useParams();
  const scenarioId = params.id as string;
  
  const [time, setTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [wsStatus, setWsStatus] = useState("Connecting...");

  const [dimensions, setDimensions] = useState<Dimension[]>([]);
  const [tripsData, setTripsData] = useState<{ path: [number, number][], timestamps: number[] }[]>([]);
  const [synthesis, setSynthesis] = useState<{ narrative: string } | null>(null);
  const [inspectData, setInspectData] = useState<ProvenanceData | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

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

  // WebSocket Connection
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/simulate/${scenarioId}`);

    ws.onopen = () => setWsStatus("Connected");
    
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "ACCEPTED") {
        setWsStatus("Running simulation...");
      } else if (msg.type === "PLAYBACK_FRAME") {
        // Accumulate playback frames for Deck.gl
        // Note: For simplicity we expect the backend to stream agents with paths
        setTripsData(prev => [...prev, ...msg.agents]);
      } else if (msg.type === "DIMENSION_RESULT") {
        // Build provenance data payload format expected by InspectDrawer
        const provData = {
          metric: msg.metric,
          value: String(msg.value),
          range: msg.range ? `${msg.range[0]}..${msg.range[1]}` : "",
          confidence: msg.confidence,
          confidenceBasis: "Computed from input dataset confidences per methods §2",
          equationId: msg.equation_id,
          equationText: `Result for ${msg.metric}`,
          inputs: (msg.input_dataset_ids || []).map((id: string) => ({
            id, name: id, confidence: msg.confidence, vintage: "current"
          })),
          assumptions: msg.assumptions || [],
          references: msg.references || []
        };
        
        setDimensions(prev => [...prev, {
          id: msg.dimension,
          name: msg.dimension,
          color: getDimensionColor(msg.dimension),
          value: msg.value > 0 ? `+${msg.value}` : String(msg.value),
          unit: msg.unit,
          conf: msg.confidence,
          range: provData.range,
          provData
        }]);
      } else if (msg.type === "SYNTHESIS") {
        setSynthesis(msg);
      } else if (msg.type === "DONE") {
        setWsStatus(`Done (${msg.duration_ms}ms)`);
        ws.close();
      }
    };

    ws.onerror = () => setWsStatus("Error connecting to simulation");
    ws.onclose = () => setWsStatus("Disconnected");

    return () => ws.close();
  }, [scenarioId]);

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

  return (
    <div className="flex h-screen w-full flex-col md:flex-row overflow-hidden bg-background">
      
      {/* 5-Dimension Impact Panel (Right Side, normally overlay but docked here) */}
      <div className="w-full md:w-[360px] lg:w-[400px] h-full bg-surface shadow-md z-10 flex flex-col border-l border-border order-2 md:order-1 overflow-y-auto">
        <div className="p-4 border-b border-border flex justify-between items-center">
          <div>
            <h2 className="text-lg font-bold text-foreground">Scenario Results</h2>
            <p className="text-xs text-text-muted font-mono">{scenarioId}</p>
          </div>
          <span className="text-xs font-mono bg-secondary px-2 py-1 rounded">{wsStatus}</span>
        </div>
        
        <div className="p-4 flex-1 flex flex-col gap-4">
          {dimensions.map((dim) => (
            <div 
              key={dim.id} 
              className="border border-border rounded-lg p-4 bg-surface hover:border-primary transition-colors cursor-pointer group"
              onClick={() => { setInspectData(dim.provData); setIsDrawerOpen(true); }}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${dim.color}`} />
                  <span className="text-sm font-medium capitalize">{dim.name}</span>
                </div>
                {/* Confidence Chip */}
                <div className={`text-xs px-2 py-0.5 border rounded-full font-mono ${
                  dim.conf === 'H' ? 'bg-success/10 text-success border-success/20' : 
                  dim.conf === 'M' ? 'bg-warning/10 text-warning border-warning/20' : 
                  'bg-destructive/10 text-destructive border-destructive/20 border-dashed'
                }`}>
                  {dim.conf}
                </div>
              </div>
              <div className="flex items-end gap-2 mb-1">
                <span className="text-2xl font-bold font-mono tracking-tight">{dim.value}</span>
                <span className="text-xs text-text-muted mb-1">{dim.unit}</span>
              </div>
              <div className="text-xs text-text-muted font-mono flex justify-between">
                <span>R: {dim.range}</span>
                <span className="opacity-0 group-hover:opacity-100 text-primary transition-opacity">Inspect →</span>
              </div>
            </div>
          ))}

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
