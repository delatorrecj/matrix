"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Map } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import DeckGL from "@deck.gl/react";
import { TripsLayer } from "@deck.gl/geo-layers";

const MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty";

// Mock dimensions data according to DSD
const DIMENSIONS = [
  { id: "behavioral", name: "Behavioral", color: "bg-[#2563EB]", value: "+450", unit: "trips/day", conf: "M", range: "400..500" },
  { id: "social", name: "Social", color: "bg-[#DB2777]", value: "+12", unit: "min saved", conf: "H", range: "10..15" },
  { id: "economic", name: "Economic", color: "bg-[#CA8A04]", value: "+₱1.2M", unit: "GVA", conf: "L", range: "0.8..1.5M" },
  { id: "ecological", name: "Ecological", color: "bg-[#16A34A]", value: "-12%", unit: "CO₂e", conf: "M", range: "-10..-15%" },
  { id: "societal", name: "Societal", color: "bg-[#9333EA]", value: "85", unit: "index", conf: "H", range: "80..90" },
];

export default function ScenarioSimulation() {
  const params = useParams();
  const scenarioId = params.id as string;
  
  const [time, setTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);

  // DeckGL setup (mocked for now until WS provides real frame data)
  const layers = [
    new TripsLayer({
      id: "trips-layer",
      data: [], // Would stream from WS
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
        <div className="p-4 border-b border-border">
          <h2 className="text-lg font-bold text-foreground">Scenario Results</h2>
          <p className="text-xs text-text-muted font-mono">{scenarioId}</p>
        </div>
        
        <div className="p-4 flex-1 flex flex-col gap-4">
          {DIMENSIONS.map((dim) => (
            <div key={dim.id} className="border border-border rounded-lg p-4 bg-surface hover:border-primary transition-colors cursor-pointer group">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${dim.color}`} />
                  <span className="text-sm font-medium">{dim.name}</span>
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

    </div>
  );
}
