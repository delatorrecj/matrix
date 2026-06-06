"use client";

import { useEffect, useState } from "react";

interface InspectDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  metricId: string | null;
}

interface InputDataset {
  id: string;
  name: string;
  confidence: string;
  vintage: string;
}

interface ProvenanceData {
  metric: string;
  value: string;
  range: string;
  confidence: string;
  confidenceBasis: string;
  equationId: string;
  equationText: string;
  inputs: InputDataset[];
  assumptions: string[];
  references: string[];
}

export default function InspectDrawer({ isOpen, onClose, metricId }: InspectDrawerProps) {
  const [data, setData] = useState<ProvenanceData | null>(null);

  useEffect(() => {
    if (isOpen && metricId) {
      // Mock fetch provenance data
      // In reality: GET /runs/[id]?inspect=metricId
      setData({
        metric: "Δ trips/day",
        value: "+450",
        range: "400..500",
        confidence: "M",
        confidenceBasis: "Calderon 2014 survey data is robust but over 10 years old.",
        equationId: "BEH-1",
        equationText: "Δ trips = Σ (population_i * mode_share_m * elasticity_c)",
        inputs: [
          { id: "OSM-ILO", name: "OpenStreetMap Iloilo Extract", confidence: "H", vintage: "2026" },
          { id: "PSA-FIES", name: "Family Income and Expenditure Survey", confidence: "H", vintage: "2023" }
        ],
        assumptions: [
          "Mode share anchor remains consistent with pre-pandemic distributions.",
          "Walking speed assumed to be 1.2 m/s."
        ],
        references: [
          "Calderon, J. (2014). Travel behavior in Iloilo City."
        ]
      });
    }
  }, [isOpen, metricId]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-background/20 backdrop-blur-sm z-40 transition-opacity"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-full max-w-[420px] bg-surface shadow-lg z-50 flex flex-col border-l border-border transform transition-transform duration-200 ease-out">
        
        {/* Header */}
        <div className="p-6 border-b border-border flex items-start justify-between bg-secondary/30">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="text-xs px-2 py-0.5 bg-background border border-border rounded font-mono">
                {data?.equationId || "..."}
              </span>
              <h3 className="text-lg font-bold text-foreground">{data?.metric || "Loading..."}</h3>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-mono font-bold tracking-tight">{data?.value}</span>
              <span className="text-sm font-mono text-text-muted">range: {data?.range}</span>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-background rounded-md text-text-muted transition-colors"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-8">
          
          {/* Confidence */}
          <section>
            <h4 className="text-sm font-medium text-text-muted mb-3 uppercase tracking-wider">Confidence</h4>
            <div className="p-4 border border-warning/20 bg-warning/5 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-warning font-bold font-mono border border-warning/30 px-2 rounded-sm bg-background">
                  {data?.confidence}
                </span>
                <span className="text-sm font-medium text-foreground">Medium Confidence</span>
              </div>
              <p className="text-sm text-text-muted">{data?.confidenceBasis}</p>
            </div>
          </section>

          {/* Equation */}
          <section>
            <h4 className="text-sm font-medium text-text-muted mb-3 uppercase tracking-wider">Equation</h4>
            <div className="p-4 bg-background border border-border rounded-lg font-mono text-sm overflow-x-auto">
              {data?.equationText}
            </div>
          </section>

          {/* Inputs */}
          <section>
            <h4 className="text-sm font-medium text-text-muted mb-3 uppercase tracking-wider">Input Datasets</h4>
            <div className="flex flex-col gap-2">
              {data?.inputs?.map((input: InputDataset) => (
                <div key={input.id} className="p-3 border border-border rounded-lg bg-background flex justify-between items-center group cursor-pointer hover:border-primary">
                  <div>
                    <div className="text-sm font-medium text-primary group-hover:underline">{input.id}</div>
                    <div className="text-xs text-text-muted">{input.name}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-mono">Conf: {input.confidence}</div>
                    <div className="text-xs font-mono text-text-muted">{input.vintage}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Assumptions */}
          <section>
            <h4 className="text-sm font-medium text-text-muted mb-3 uppercase tracking-wider">Assumptions</h4>
            <ul className="list-disc pl-5 space-y-2">
              {data?.assumptions?.map((ass: string, i: number) => (
                <li key={i} className="text-sm text-text-muted">{ass}</li>
              ))}
            </ul>
          </section>

        </div>
      </div>
    </>
  );
}
