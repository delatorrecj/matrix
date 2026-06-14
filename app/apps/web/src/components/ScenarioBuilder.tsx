"use client";

/**
 * ScenarioBuilder — a structured, multi-step builder that lets a planner express
 * an infrastructure intervention without writing free-text, then serializes the
 * choices into a precise natural-language query and submits it through the
 * existing `POST /scenario` flow (`createScenario`). This is the UI half of
 * "simulate way beyond the 3 demo presets".
 *
 * GLASS BOX: the review step shows the *exact* string that will be sent. There is
 * no hidden rewriting between what the user sees and what `createScenario` posts.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * SERIALIZATION GRAMMAR  (see `buildScenarioQuery`)
 * ─────────────────────────────────────────────────────────────────────────────
 * The orchestrator (Scenario v2) parses an NL string into
 *   intervention_type ∈ {lane_closure, full_closure, speed_change,
 *                         capacity_change, new_facility}
 *   + location (street/corridor name)
 *   + geometry (GeoJSON, optional)
 *   + parameters ({lanes_closed, max_speed_kph, capacity_factor,
 *                  facility_kind, capacity, ...}).
 *
 * `buildScenarioQuery(state)` emits a regular sentence per type. `<LOC>` below is
 * the location clause — `on <street>` / `at <street>` when a name is given, or the
 * map-point form `at [<lon>, <lat>]` (5-dp, WGS84 lon/lat order) when only a point
 * was dropped. If both a name and geometry exist, the name drives the sentence and
 * the geometry rides along in the suffix.
 *
 *   lane_closure     "Close <n> lane[s] <LOC>"
 *   full_closure     "Fully close <LOC>"
 *   speed_change     "Reduce speed to <kph> km/h <LOC>"
 *   capacity_change  "Change capacity to <pct>% <LOC>"
 *   new_facility     "Build a <capacity>-<unit> <facility_kind> <LOC>"
 *                      unit = seat (school) | stall (market) | bay (terminal)
 *
 * GEOMETRY SUFFIX (only when a point or polygon was drawn). A single regular,
 * documented sentence is appended so the orchestrator can recover the exact
 * geometry deterministically:
 *
 *   " Geometry (GeoJSON): {<compact GeoJSON Feature>}"
 *
 * The Feature's `geometry` is a `Point` (`[lon, lat]`) for a dropped pin or a
 * `Polygon` (`[[[lon, lat], …, <first repeated>]]`) for a drawn area. Coordinates
 * are WGS84 lon/lat, 5 decimal places. The suffix is plain text the orchestrator
 * splits on the literal token `Geometry (GeoJSON):`.
 */

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Map } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import DeckGL from "@deck.gl/react";
import { ScatterplotLayer, PolygonLayer, PathLayer } from "@deck.gl/layers";
import type { Layer, PickingInfo } from "@deck.gl/core";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Loader2,
  MapPin,
  Pencil,
  RotateCcw,
  Building2,
  Gauge,
  SignpostBig,
  Ban,
  Waypoints,
} from "lucide-react";

import {
  AmbiguousScenarioError,
  ApiUnreachableError,
  createScenario,
} from "@/lib/api";

// ── Domain types ─────────────────────────────────────────────────────────────

export type InterventionType =
  | "lane_closure"
  | "full_closure"
  | "speed_change"
  | "capacity_change"
  | "new_facility";

export type FacilityKind = "school" | "market" | "terminal";

/** A drawn geometry: a single dropped point, or a polygon of ≥3 vertices. */
export type DrawnGeometry =
  | { kind: "point"; point: [number, number] }
  | { kind: "polygon"; vertices: [number, number][] };

export interface BuilderState {
  interventionType: InterventionType;
  /** Street / corridor name, e.g. "Diversion Road". Empty when placing on map only. */
  locationName: string;
  /** Optional geometry drawn on the map. */
  geometry: DrawnGeometry | null;
  // Per-type parameters (only the relevant ones are read per intervention type).
  lanesClosed: number; // lane_closure: 1–4
  maxSpeedKph: number; // speed_change
  capacityPct: number; // capacity_change (percent of baseline)
  facilityKind: FacilityKind; // new_facility
  facilityCapacity: number; // new_facility (seats / stalls / bays)
}

export const INITIAL_BUILDER_STATE: BuilderState = {
  interventionType: "lane_closure",
  locationName: "",
  geometry: null,
  lanesClosed: 1,
  maxSpeedKph: 30,
  capacityPct: 50,
  facilityKind: "school",
  facilityCapacity: 3000,
};

const INTERVENTIONS: {
  type: InterventionType;
  label: string;
  blurb: string;
  Icon: typeof Ban;
}[] = [
  { type: "lane_closure", label: "Lane closure", blurb: "Close one or more lanes on a road", Icon: SignpostBig },
  { type: "full_closure", label: "Full road closure", blurb: "Close a corridor entirely", Icon: Ban },
  { type: "speed_change", label: "Speed change", blurb: "Set a new speed limit", Icon: Gauge },
  { type: "capacity_change", label: "Capacity change", blurb: "Scale road throughput up or down", Icon: Waypoints },
  { type: "new_facility", label: "New facility", blurb: "Add a school, market, or terminal", Icon: Building2 },
];

/** seats / stalls / bays — the count unit per facility kind. */
const FACILITY_UNIT: Record<FacilityKind, string> = {
  school: "seat",
  market: "stall",
  terminal: "bay",
};

// ── Serialization (pure, testable in isolation) ──────────────────────────────

/** Round a coordinate to 5 decimal places (≈1 m), trimming trailing zeros. */
function fmtCoord(n: number): string {
  return Number(n.toFixed(5)).toString();
}

/** Build the compact GeoJSON Feature suffix for a drawn geometry, or "". */
export function buildGeometrySuffix(geometry: DrawnGeometry | null): string {
  if (!geometry) return "";

  let geo:
    | { type: "Point"; coordinates: number[] }
    | { type: "Polygon"; coordinates: number[][][] };
  if (geometry.kind === "point") {
    geo = {
      type: "Point",
      coordinates: [geometry.point[0], geometry.point[1]].map((c) => Number(fmtCoord(c))),
    };
  } else {
    if (geometry.vertices.length < 3) return ""; // not a valid polygon yet
    // Close the ring: GeoJSON polygons repeat the first vertex as the last.
    const ring = geometry.vertices.map((v) => [Number(fmtCoord(v[0])), Number(fmtCoord(v[1]))]);
    const closed = [...ring, ring[0]];
    geo = { type: "Polygon", coordinates: [closed] };
  }

  const feature = { type: "Feature", geometry: geo, properties: {} };
  return ` Geometry (GeoJSON): ${JSON.stringify(feature)}`;
}

/** The point/centroid coordinate clause used when no street name is given. */
function pointClause(geometry: DrawnGeometry | null): string | null {
  if (!geometry) return null;
  if (geometry.kind === "point") {
    return `[${fmtCoord(geometry.point[0])}, ${fmtCoord(geometry.point[1])}]`;
  }
  if (geometry.vertices.length === 0) return null;
  // Centroid of the drawn vertices — a stable, documented anchor for the area.
  const n = geometry.vertices.length;
  const cx = geometry.vertices.reduce((s, v) => s + v[0], 0) / n;
  const cy = geometry.vertices.reduce((s, v) => s + v[1], 0) / n;
  return `[${fmtCoord(cx)}, ${fmtCoord(cy)}]`;
}

/**
 * Build the location clause. `prep` is the leading preposition ("on" for roads,
 * "at" for facilities). Returns e.g. "on Diversion Road" or "at [122.561, 10.712]".
 * Returns "" when neither a name nor a usable geometry is present.
 */
function locationClause(state: BuilderState, prep: "on" | "at"): string {
  const name = state.locationName.trim();
  if (name) return `${prep} ${name}`;
  const pt = pointClause(state.geometry);
  if (pt) return `at ${pt}`; // coordinates always read naturally with "at"
  return "";
}

/** Format an integer with thousands separators, e.g. 3000 → "3,000". */
function withCommas(n: number): string {
  return Math.round(n).toLocaleString("en-US");
}

/**
 * Serialize builder state into the precise NL query string sent to the
 * orchestrator. Pure: no I/O, no React. See the module docstring for the grammar.
 */
export function buildScenarioQuery(state: BuilderState): string {
  const suffix = buildGeometrySuffix(state.geometry);
  let sentence: string;

  switch (state.interventionType) {
    case "lane_closure": {
      const n = Math.max(1, Math.round(state.lanesClosed));
      const loc = locationClause(state, "on");
      sentence = `Close ${n} ${n === 1 ? "lane" : "lanes"}${loc ? ` ${loc}` : ""}`;
      break;
    }
    case "full_closure": {
      const loc = locationClause(state, "on");
      // "Fully close the corridor on X" reads oddly; collapse to "Fully close X".
      const tail = loc ? loc.replace(/^on /, "") : "the corridor";
      sentence = `Fully close ${tail}`;
      break;
    }
    case "speed_change": {
      const kph = Math.max(1, Math.round(state.maxSpeedKph));
      const loc = locationClause(state, "on");
      sentence = `Reduce speed to ${kph} km/h${loc ? ` ${loc}` : ""}`;
      break;
    }
    case "capacity_change": {
      const pct = Math.max(0, Math.round(state.capacityPct));
      const loc = locationClause(state, "on");
      sentence = `Change capacity to ${pct}%${loc ? ` ${loc}` : ""}`;
      break;
    }
    case "new_facility": {
      const cap = Math.max(0, Math.round(state.facilityCapacity));
      const unit = FACILITY_UNIT[state.facilityKind];
      const loc = locationClause(state, "at");
      sentence = `Build a ${withCommas(cap)}-${unit} ${state.facilityKind}${loc ? ` ${loc}` : ""}`;
      break;
    }
  }

  return `${sentence.trim()}.${suffix}`;
}

// ── Map config (mirrors home page.tsx / scenario page) ───────────────────────

const MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty";
const INITIAL_VIEW_STATE = {
  longitude: 122.56,
  latitude: 10.71,
  zoom: 13,
  pitch: 0,
  bearing: 0,
};

type DrawMode = "point" | "polygon";

// ── Component ────────────────────────────────────────────────────────────────

const STEPS = ["Type", "Location", "Parameters", "Review"] as const;
type StepIndex = 0 | 1 | 2 | 3;

export default function ScenarioBuilder() {
  const router = useRouter();
  const [step, setStep] = useState<StepIndex>(0);
  const [state, setState] = useState<BuilderState>(INITIAL_BUILDER_STATE);

  const [drawMode, setDrawMode] = useState<DrawMode>("point");

  // Manual lon/lat entry — the always-available fallback to clicking the map
  // (and the only path exercised in jsdom tests, where WebGL can't render).
  const [manualLon, setManualLon] = useState("");
  const [manualLat, setManualLat] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [clarification, setClarification] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const update = useCallback(
    <K extends keyof BuilderState>(key: K, value: BuilderState[K]) => {
      setState((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  const query = useMemo(() => buildScenarioQuery(state), [state]);

  // ── Geometry capture ──────────────────────────────────────────────────────

  const commitPoint = useCallback(
    (lon: number, lat: number) => {
      update("geometry", { kind: "point", point: [lon, lat] });
    },
    [update]
  );

  const addPolygonVertex = useCallback((lon: number, lat: number) => {
    setState((s) => {
      const existing =
        s.geometry?.kind === "polygon" ? s.geometry.vertices : [];
      const vertices: [number, number][] = [...existing, [lon, lat]];
      return { ...s, geometry: { kind: "polygon", vertices } };
    });
  }, []);

  const handleMapClick = useCallback(
    (info: PickingInfo) => {
      const c = info.coordinate;
      if (!c || c.length < 2) return;
      const [lon, lat] = c;
      if (drawMode === "point") commitPoint(lon, lat);
      else addPolygonVertex(lon, lat);
    },
    [drawMode, commitPoint, addPolygonVertex]
  );

  const addManualCoord = useCallback(() => {
    const lon = Number(manualLon);
    const lat = Number(manualLat);
    if (manualLon.trim() === "" || manualLat.trim() === "") return;
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) return;
    if (drawMode === "point") commitPoint(lon, lat);
    else addPolygonVertex(lon, lat);
    setManualLon("");
    setManualLat("");
  }, [manualLon, manualLat, drawMode, commitPoint, addPolygonVertex]);

  const clearGeometry = useCallback(() => {
    update("geometry", null);
  }, [update]);

  const switchDrawMode = useCallback(
    (mode: DrawMode) => {
      setDrawMode(mode);
      // Switching capture modes starts fresh — point and polygon don't mix.
      update("geometry", null);
    },
    [update]
  );

  // Deck.gl visual layers for the drawn geometry (skipped automatically in tests
  // where DeckGL is mocked to a div).
  const layers = useMemo(() => {
    const out: Layer[] = [];
    const g = state.geometry;
    if (g?.kind === "point") {
      out.push(
        new ScatterplotLayer({
          id: "drawn-point",
          data: [g.point],
          getPosition: (d: [number, number]) => d,
          getRadius: 8,
          radiusMinPixels: 6,
          getFillColor: [29, 78, 216, 220],
        })
      );
    } else if (g?.kind === "polygon" && g.vertices.length > 0) {
      out.push(
        new ScatterplotLayer({
          id: "drawn-vertices",
          data: g.vertices,
          getPosition: (d: [number, number]) => d,
          getRadius: 6,
          radiusMinPixels: 4,
          getFillColor: [29, 78, 216, 220],
        })
      );
      if (g.vertices.length >= 2) {
        out.push(
          new PathLayer({
            id: "drawn-edges",
            data: [[...g.vertices, ...(g.vertices.length >= 3 ? [g.vertices[0]] : [])]],
            getPath: (d: [number, number][]) => d,
            getColor: [29, 78, 216, 200],
            getWidth: 2,
            widthMinPixels: 2,
          })
        );
      }
      if (g.vertices.length >= 3) {
        out.push(
          new PolygonLayer({
            id: "drawn-polygon",
            data: [g.vertices],
            getPolygon: (d: [number, number][]) => d,
            getFillColor: [29, 78, 216, 60],
            getLineColor: [29, 78, 216, 0],
            stroked: false,
          })
        );
      }
    }
    return out;
  }, [state.geometry]);

  // ── Submit ─────────────────────────────────────────────────────────────────

  const handleSubmit = useCallback(async () => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    setClarification(null);
    setSubmitError(null);
    try {
      const scenario = await createScenario(query);
      router.push(`/scenario/${scenario.scenario_id}`);
      // Keep the spinner up while Next.js navigates away.
    } catch (err) {
      if (err instanceof AmbiguousScenarioError) {
        setClarification(err.message);
      } else if (err instanceof ApiUnreachableError) {
        setSubmitError("Could not reach the MATRIX API. Start the API and try again.");
      } else {
        setSubmitError(err instanceof Error ? err.message : "Scenario request failed");
      }
      setIsSubmitting(false);
    }
  }, [isSubmitting, query, router]);

  // ── Step navigation ─────────────────────────────────────────────────────────

  const canAdvance = useMemo(() => {
    if (step === 1) {
      // Location: require either a typed name or a usable geometry.
      const hasName = state.locationName.trim().length > 0;
      const g = state.geometry;
      const hasGeo =
        g?.kind === "point" || (g?.kind === "polygon" && g.vertices.length >= 3);
      return hasName || hasGeo;
    }
    return true;
  }, [step, state.locationName, state.geometry]);

  const isRoadType = state.interventionType !== "new_facility";

  return (
    <div className="flex h-[100dvh] w-full flex-col bg-background text-foreground">
      {/* Header + stepper */}
      <header className="border-b border-border bg-surface px-6 py-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight">Scenario Builder</h1>
            <p className="text-xs text-text-muted mt-0.5">
              Compose an intervention, then submit it as a precise query.
            </p>
          </div>
          <ol className="hidden sm:flex items-center gap-2" aria-label="Builder progress">
            {STEPS.map((label, i) => (
              <li key={label} className="flex items-center gap-2">
                <span
                  aria-current={i === step ? "step" : undefined}
                  className={`flex items-center gap-1.5 text-xs font-medium ${
                    i === step ? "text-primary" : i < step ? "text-foreground" : "text-text-muted"
                  }`}
                >
                  <span
                    className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${
                      i === step
                        ? "bg-primary text-primary-foreground"
                        : i < step
                        ? "bg-primary/15 text-primary"
                        : "bg-secondary text-text-muted"
                    }`}
                  >
                    {i + 1}
                  </span>
                  {label}
                </span>
                {i < STEPS.length - 1 && <span className="text-text-muted">/</span>}
              </li>
            ))}
          </ol>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="mx-auto max-w-3xl">
          {/* STEP 0 — Intervention type */}
          {step === 0 && (
            <section aria-labelledby="step-type-heading">
              <h2 id="step-type-heading" className="text-sm font-semibold mb-3">
                What kind of intervention?
              </h2>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {INTERVENTIONS.map(({ type, label, blurb, Icon }) => {
                  const active = state.interventionType === type;
                  return (
                    <button
                      key={type}
                      type="button"
                      aria-pressed={active}
                      onClick={() => update("interventionType", type)}
                      className={`flex items-start gap-3 rounded-lg border p-4 text-left transition-colors ${
                        active
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-primary hover:bg-primary/5"
                      }`}
                    >
                      <Icon className="mt-0.5 h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
                      <span>
                        <span className="block text-sm font-semibold">{label}</span>
                        <span className="block text-xs text-text-muted mt-0.5">{blurb}</span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </section>
          )}

          {/* STEP 1 — Location */}
          {step === 1 && (
            <section aria-labelledby="step-loc-heading">
              <h2 id="step-loc-heading" className="text-sm font-semibold mb-3">
                {isRoadType ? "Which corridor or street?" : "Where should it go?"}
              </h2>

              <label htmlFor="location-name" className="text-xs font-medium text-text-muted block mb-1">
                Street / corridor name
              </label>
              <input
                id="location-name"
                type="text"
                value={state.locationName}
                onChange={(e) => update("locationName", e.target.value)}
                placeholder="e.g. Diversion Road"
                className="w-full bg-background border border-border rounded-md p-2.5 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none"
              />

              <div className="mt-5">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-text-muted">
                    …or place it on the map
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      aria-pressed={drawMode === "point"}
                      onClick={() => switchDrawMode("point")}
                      className={`flex items-center gap-1 text-xs px-2 py-1 rounded border transition-colors ${
                        drawMode === "point"
                          ? "border-primary bg-primary/5 text-primary"
                          : "border-border text-text-muted hover:border-primary"
                      }`}
                    >
                      <MapPin className="h-3.5 w-3.5" aria-hidden="true" /> Point
                    </button>
                    <button
                      type="button"
                      aria-pressed={drawMode === "polygon"}
                      onClick={() => switchDrawMode("polygon")}
                      className={`flex items-center gap-1 text-xs px-2 py-1 rounded border transition-colors ${
                        drawMode === "polygon"
                          ? "border-primary bg-primary/5 text-primary"
                          : "border-border text-text-muted hover:border-primary"
                      }`}
                    >
                      <Pencil className="h-3.5 w-3.5" aria-hidden="true" /> Area
                    </button>
                    <button
                      type="button"
                      onClick={clearGeometry}
                      className="flex items-center gap-1 text-xs px-2 py-1 rounded border border-border text-text-muted hover:border-error hover:text-error transition-colors"
                    >
                      <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" /> Clear
                    </button>
                  </div>
                </div>

                <p className="text-[11px] text-text-muted mb-2">
                  {drawMode === "point"
                    ? "Click the map to drop a point."
                    : "Click the map to add polygon vertices (3+ for an area)."}
                </p>

                <div
                  className="h-[320px] w-full overflow-hidden rounded-lg border border-border"
                  data-testid="builder-map"
                >
                  <DeckGL
                    initialViewState={INITIAL_VIEW_STATE}
                    controller={true}
                    onClick={handleMapClick}
                    layers={layers}
                    getCursor={() => "crosshair"}
                  >
                    <Map mapStyle={MAP_STYLE} mapLib={maplibregl} reuseMaps />
                  </DeckGL>
                </div>

                {/* Manual lon/lat fallback — always available. */}
                <div className="mt-3 flex flex-wrap items-end gap-2">
                  <div>
                    <label htmlFor="manual-lon" className="text-[11px] text-text-muted block mb-0.5">
                      Longitude
                    </label>
                    <input
                      id="manual-lon"
                      type="number"
                      step="any"
                      value={manualLon}
                      onChange={(e) => setManualLon(e.target.value)}
                      placeholder="122.561"
                      className="w-28 bg-background border border-border rounded-md p-1.5 text-sm outline-none focus:border-primary"
                    />
                  </div>
                  <div>
                    <label htmlFor="manual-lat" className="text-[11px] text-text-muted block mb-0.5">
                      Latitude
                    </label>
                    <input
                      id="manual-lat"
                      type="number"
                      step="any"
                      value={manualLat}
                      onChange={(e) => setManualLat(e.target.value)}
                      placeholder="10.712"
                      className="w-28 bg-background border border-border rounded-md p-1.5 text-sm outline-none focus:border-primary"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={addManualCoord}
                    className="h-[34px] rounded-md border border-border px-3 text-sm hover:border-primary hover:bg-primary/5 transition-colors"
                  >
                    {drawMode === "point" ? "Set point" : "Add vertex"}
                  </button>
                </div>

                {/* Live geometry summary */}
                <GeometrySummary geometry={state.geometry} />
              </div>
            </section>
          )}

          {/* STEP 2 — Parameters */}
          {step === 2 && (
            <section aria-labelledby="step-params-heading">
              <h2 id="step-params-heading" className="text-sm font-semibold mb-3">
                Parameters
              </h2>

              {state.interventionType === "lane_closure" && (
                <Field label="Lanes to close" htmlFor="param-lanes">
                  <select
                    id="param-lanes"
                    value={state.lanesClosed}
                    onChange={(e) => update("lanesClosed", Number(e.target.value))}
                    className="w-full bg-background border border-border rounded-md p-2.5 text-sm outline-none focus:border-primary"
                  >
                    {[1, 2, 3, 4].map((n) => (
                      <option key={n} value={n}>
                        {n} {n === 1 ? "lane" : "lanes"}
                      </option>
                    ))}
                  </select>
                </Field>
              )}

              {state.interventionType === "full_closure" && (
                <p className="text-sm text-text-muted">
                  A full closure has no extra parameters — the corridor at the chosen
                  location is closed entirely.
                </p>
              )}

              {state.interventionType === "speed_change" && (
                <Field label="Target speed (km/h)" htmlFor="param-speed">
                  <input
                    id="param-speed"
                    type="number"
                    min={1}
                    max={120}
                    value={state.maxSpeedKph}
                    onChange={(e) => update("maxSpeedKph", Number(e.target.value))}
                    className="w-40 bg-background border border-border rounded-md p-2.5 text-sm outline-none focus:border-primary"
                  />
                </Field>
              )}

              {state.interventionType === "capacity_change" && (
                <Field label="Capacity (% of baseline)" htmlFor="param-capacity">
                  <input
                    id="param-capacity"
                    type="number"
                    min={0}
                    max={200}
                    value={state.capacityPct}
                    onChange={(e) => update("capacityPct", Number(e.target.value))}
                    className="w-40 bg-background border border-border rounded-md p-2.5 text-sm outline-none focus:border-primary"
                  />
                </Field>
              )}

              {state.interventionType === "new_facility" && (
                <div className="space-y-4">
                  <Field label="Facility kind" htmlFor="param-facility-kind">
                    <select
                      id="param-facility-kind"
                      value={state.facilityKind}
                      onChange={(e) => update("facilityKind", e.target.value as FacilityKind)}
                      className="w-full bg-background border border-border rounded-md p-2.5 text-sm outline-none focus:border-primary"
                    >
                      <option value="school">School</option>
                      <option value="market">Market</option>
                      <option value="terminal">Transport terminal</option>
                    </select>
                  </Field>
                  <Field
                    label={`Capacity (${FACILITY_UNIT[state.facilityKind]}s)`}
                    htmlFor="param-facility-capacity"
                  >
                    <input
                      id="param-facility-capacity"
                      type="number"
                      min={0}
                      value={state.facilityCapacity}
                      onChange={(e) => update("facilityCapacity", Number(e.target.value))}
                      className="w-40 bg-background border border-border rounded-md p-2.5 text-sm outline-none focus:border-primary"
                    />
                  </Field>
                </div>
              )}
            </section>
          )}

          {/* STEP 3 — Review + submit */}
          {step === 3 && (
            <section aria-labelledby="step-review-heading">
              <h2 id="step-review-heading" className="text-sm font-semibold mb-3">
                Review &amp; submit
              </h2>

              <p className="text-xs text-text-muted mb-2">
                This exact query is sent to the orchestrator — nothing is rewritten.
              </p>
              <div
                data-testid="review-query"
                className="rounded-lg border border-border bg-secondary/40 p-4 text-sm font-mono whitespace-pre-wrap break-words"
              >
                {query}
              </div>

              {state.geometry && (
                <div className="mt-4">
                  <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-1">
                    Attached GeoJSON
                  </h3>
                  <pre
                    data-testid="review-geojson"
                    className="rounded-lg border border-border bg-secondary/40 p-3 text-[11px] font-mono overflow-x-auto"
                  >
                    {JSON.stringify(geometryFeature(state.geometry), null, 2)}
                  </pre>
                </div>
              )}

              {clarification && (
                <div role="alert" className="mt-4 p-3 rounded-md border border-warning/30 bg-warning/10 text-sm">
                  <div className="flex items-center gap-2 font-semibold text-warning mb-1">
                    <AlertTriangle className="h-4 w-4" aria-hidden="true" />
                    Clarification needed
                  </div>
                  <p className="text-text">{clarification}</p>
                  <p className="text-xs text-text-muted mt-1">
                    Go back and add detail (a street name, or a more specific location),
                    then submit again.
                  </p>
                </div>
              )}

              {submitError && (
                <div role="alert" className="mt-4 p-3 rounded-md border border-error/30 bg-error/10 text-sm">
                  <div className="flex items-center gap-2 font-semibold text-error mb-1">
                    <AlertTriangle className="h-4 w-4" aria-hidden="true" />
                    Scenario request failed
                  </div>
                  <p className="text-text">{submitError}</p>
                </div>
              )}

              <button
                type="button"
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="mt-5 w-full bg-primary text-primary-foreground font-medium py-2.5 rounded-md hover:bg-primary-hover transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    Submitting scenario…
                  </>
                ) : (
                  "Submit scenario"
                )}
              </button>
            </section>
          )}
        </div>
      </div>

      {/* Footer nav */}
      <footer className="border-t border-border bg-surface px-6 py-3 flex items-center justify-between">
        <button
          type="button"
          onClick={() => setStep((s) => (s > 0 ? ((s - 1) as StepIndex) : s))}
          disabled={step === 0 || isSubmitting}
          className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-md border border-border hover:bg-secondary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back
        </button>

        <span className="text-xs text-text-muted">
          Step {step + 1} of {STEPS.length}
        </span>

        {step < STEPS.length - 1 ? (
          <button
            type="button"
            onClick={() => setStep((s) => ((s + 1) as StepIndex))}
            disabled={!canAdvance}
            className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Next <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </button>
        ) : (
          <span className="w-[72px]" aria-hidden="true" />
        )}
      </footer>
    </div>
  );
}

// ── Small presentational helpers ─────────────────────────────────────────────

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-1">
      <label htmlFor={htmlFor} className="text-xs font-medium text-text-muted block mb-1">
        {label}
      </label>
      {children}
    </div>
  );
}

/** Build the same GeoJSON Feature object the suffix serializes (for display). */
function geometryFeature(geometry: DrawnGeometry) {
  if (geometry.kind === "point") {
    return {
      type: "Feature",
      geometry: { type: "Point", coordinates: geometry.point.map((c) => Number(c.toFixed(5))) },
      properties: {},
    };
  }
  const ring = geometry.vertices.map((v) => v.map((c) => Number(c.toFixed(5))));
  const closed = ring.length >= 3 ? [...ring, ring[0]] : ring;
  return {
    type: "Feature",
    geometry: { type: "Polygon", coordinates: [closed] },
    properties: {},
  };
}

function GeometrySummary({ geometry }: { geometry: DrawnGeometry | null }) {
  if (!geometry) {
    return (
      <p className="mt-2 text-[11px] text-text-muted" data-testid="geometry-summary">
        No geometry drawn.
      </p>
    );
  }
  if (geometry.kind === "point") {
    return (
      <p className="mt-2 text-[11px] text-text-muted" data-testid="geometry-summary">
        Point at [{geometry.point[0].toFixed(5)}, {geometry.point[1].toFixed(5)}].
      </p>
    );
  }
  return (
    <p className="mt-2 text-[11px] text-text-muted" data-testid="geometry-summary">
      Polygon with {geometry.vertices.length}{" "}
      {geometry.vertices.length === 1 ? "vertex" : "vertices"}
      {geometry.vertices.length < 3 ? " (need 3+ for an area)" : ""}.
    </p>
  );
}
