"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Map, NavigationControl } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

// Use OpenFreeMap style as the default basemap
const MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty";

export default function Home() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    try {
      // For now, we mock the scenario creation and route to a dummy scenario
      // In a real implementation, this would POST to /scenario and use the returned ID
      const fakeId = "ref-1-school-molo"; 
      router.push(`/scenario/${fakeId}`);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-full flex-col md:flex-row">
      {/* Sidebar / Input Area */}
      <div className="w-full md:w-1/3 lg:w-1/4 p-6 bg-surface shadow-md z-10 flex flex-col">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-foreground">MATRIX</h1>
          <p className="text-sm text-text-muted">Multi-Agent Twin for Routing & Infrastructure eXchange</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <label htmlFor="scenario-input" className="text-sm font-medium text-foreground">
            What project would you like to simulate?
          </label>
          <textarea
            id="scenario-input"
            className="w-full rounded-md border border-border p-3 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary min-h-[120px] resize-none"
            placeholder="e.g., What if we build a 3,000-seat school in Molo?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="rounded-md bg-primary py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary-hover disabled:opacity-50 transition-colors"
          >
            {loading ? "Parsing..." : "Simulate Scenario"}
          </button>
        </form>

        <div className="mt-8">
          <h2 className="text-sm font-medium text-foreground mb-3">Reference Scenarios</h2>
          <div className="flex flex-col gap-2">
            <button 
              onClick={() => { setQuery("What if we build a 3,000-seat school in Molo?"); }}
              className="text-left text-sm p-3 rounded border border-border hover:border-primary transition-colors bg-secondary/30"
            >
              School in Molo
            </button>
            <button 
              onClick={() => { setQuery("Add a BRT lane on Diversion Rd"); }}
              className="text-left text-sm p-3 rounded border border-border hover:border-primary transition-colors bg-secondary/30"
            >
              BRT on Diversion Rd
            </button>
            <button 
              onClick={() => { setQuery("Close a lane due to flooding"); }}
              className="text-left text-sm p-3 rounded border border-border hover:border-primary transition-colors bg-secondary/30"
            >
              Flooding Closure
            </button>
          </div>
        </div>
      </div>

      {/* Map Area */}
      <div className="flex-1 relative bg-muted">
        <Map
          initialViewState={{
            longitude: 122.56,
            latitude: 10.71,
            zoom: 12,
            pitch: 45,
            bearing: 0
          }}
          mapStyle={MAP_STYLE}
          mapLib={maplibregl}
          interactive={true}
        >
          <NavigationControl position="top-right" />
        </Map>
      </div>
    </div>
  );
}
