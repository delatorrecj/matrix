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

import { useCallback, useMemo, useState, useRef, useEffect, type CSSProperties } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Loader2,
  Building2,
  Gauge,
  SignpostBig,
  Ban,
  Waypoints,
  ChevronDown,
} from "lucide-react";

import {
  AmbiguousScenarioError,
  ApiUnreachableError,
  createScenario,
  type ScenarioGeometry,
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

// ── Component ────────────────────────────────────────────────────────────────


const STEPS = ["Type", "Location", "Parameters", "Review"] as const;
type StepIndex = 0 | 1 | 2 | 3;

export default function ScenarioBuilder() {
  const router = useRouter();
  const [step, setStep] = useState<StepIndex>(0);
  const [state, setState] = useState<BuilderState>(INITIAL_BUILDER_STATE);

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

  // ── Submit ─────────────────────────────────────────────────────────────────

  const handleSubmit = useCallback(async () => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    setClarification(null);
    setSubmitError(null);
    try {
      // Geometry travels as a STRUCTURED field (not just the NL suffix) so the kernel
      // resolves edges from exactly what was drawn (PRD-F14). The review query still
      // shows the suffix verbatim — what you see is still what is sent.
      const scenario = await createScenario(query, drawnGeometryToGeoJSON(state.geometry));
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
  }, [isSubmitting, query, router, state.geometry]);

  // ── Step navigation ─────────────────────────────────────────────────────────

  const canAdvance = useMemo(() => {
    if (step === 1) {
      // Location: require a non-empty location description text
      return state.locationName.trim().length > 0;
    }
    return true;
  }, [step, state.locationName]);

  const isRoadType = state.interventionType !== "new_facility";

  return (
    <div className="flex h-dvh w-full flex-col bg-background text-foreground">
      {/* Header + stepper */}
      <header className="border-b border-border bg-surface px-6 py-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <button
              onClick={() => router.push("/")}
              className="mt-1 flex items-center justify-center p-1.5 rounded-md text-text-muted hover:text-foreground hover:bg-secondary transition-colors"
              aria-label="Back to main interface"
              title="Back to main interface"
            >
              <ArrowLeft className="h-5 w-5" aria-hidden="true" />
            </button>
            <div>
              <h1 className="text-xl font-bold tracking-tight">Scenario Builder</h1>
              <p className="text-xs text-text-muted mt-0.5">
                Compose an intervention, then submit it as a precise query.
              </p>
            </div>
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

      <div className="flex-1 overflow-y-auto overflow-x-hidden px-6 py-6">
        <div className="mx-auto max-w-3xl">
          {/* STEP 0 — Intervention type */}
          <section
            key="step-0"
            aria-labelledby="step-type-heading"
            className={step === 0 ? "wizard-step" : "hidden"}
          >
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
                      className={`flex items-start gap-3 rounded-lg border p-4 text-left transition-all active:scale-[0.99] ${
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

          {/* STEP 1 — Location */}
          <section
            key="step-1"
            aria-labelledby="step-loc-heading"
            className={step === 1 ? "wizard-step" : "hidden"}
          >
            <h2 id="step-loc-heading" className="text-sm font-semibold mb-3">
              {isRoadType ? "Which corridor or street?" : "Where should it go?"}
            </h2>

            <div className="mb-4 rounded-lg border border-primary/20 bg-primary/5 p-3.5 text-xs text-text-muted">
              <p className="font-semibold text-primary mb-1">Pro-tip: Write a comprehensive location prompt</p>
              The simulation parser uses a local gazetteer and GraphRAG. You can specify exact corridors, intersecting landmarks, or colloquial Hiligaynon terms (e.g. <em>tulay sa forbes</em>, <em>super</em>, or <em>plasa</em>).
            </div>

            <label htmlFor="location-name" className="text-sm font-semibold mb-2 block text-text">
              Where is this happening?
            </label>
            <textarea
              id="location-name"
              className="w-full bg-surface-elevated/50 border border-border rounded-lg p-3 text-sm text-text placeholder:text-text-muted/60 focus:border-primary focus:ring-1 focus:ring-primary outline-none resize-none min-h-[100px] transition-colors"
              placeholder="e.g., Diversion Road (from the Iloilo Esplanade bridge up to the Jaro flyover, service lanes only)"
              value={state.locationName}
              onChange={(e) => update("locationName", e.target.value)}
            />

            <div className="mt-3">
              <span className="block text-xs font-semibold text-text-muted mb-2">Quick suggestions for Iloilo City:</span>
              <div className="flex flex-wrap gap-2">
                {[
                  "Diversion Road (Jaro to Mandurriao segment)",
                  "JM Basa Street (Calle Real historic district)",
                  "Molo Plaza area near the church",
                  "tulay sa forbes (Forbes Bridge)",
                  "Iloilo Terminal Market (Super)",
                ].map((sug) => (
                  <button
                    key={sug}
                    type="button"
                    onClick={() => update("locationName", sug)}
                    className="text-xs bg-secondary border border-border px-2.5 py-1.5 rounded-full hover:border-primary/50 hover:bg-primary/5 transition-all active:scale-95 text-text"
                  >
                    {sug}
                  </button>
                ))}
              </div>
            </div>
          </section>

          {/* STEP 2 — Parameters */}
          <section
            key="step-2"
            aria-labelledby="step-params-heading"
            className={step === 2 ? "wizard-step" : "hidden"}
          >
              <h2 id="step-params-heading" className="text-sm font-semibold mb-3">
                Parameters
              </h2>

              {state.interventionType === "lane_closure" && (
                <Field label="Lanes to close" htmlFor="param-lanes">
                  <CustomSelect
                    id="param-lanes"
                    value={state.lanesClosed}
                    onChange={(val) => update("lanesClosed", val as number)}
                    options={[
                      { value: 1, label: "1 lane" },
                      { value: 2, label: "2 lanes" },
                      { value: 3, label: "3 lanes" },
                      { value: 4, label: "4 lanes" },
                    ]}
                  />
                </Field>
              )}

              {state.interventionType === "full_closure" && (
                <p className="text-sm text-text-muted">
                  A full closure has no extra parameters. The corridor at the chosen
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
                    <CustomSelect
                      id="param-facility-kind"
                      value={state.facilityKind}
                      onChange={(val) => update("facilityKind", val as FacilityKind)}
                      options={[
                        { value: "school", label: "School" },
                        { value: "market", label: "Market" },
                        { value: "terminal", label: "Transport terminal" },
                      ]}
                    />
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

          {/* STEP 3 — Review + submit */}
          <section
            key="step-3"
            aria-labelledby="step-review-heading"
            className={step === 3 ? "wizard-step" : "hidden"}
          >
              <h2 id="step-review-heading" className="text-sm font-semibold mb-3">
                Review &amp; submit
              </h2>

              <p className="text-xs text-text-muted mb-2">
                This exact query is sent to the orchestrator. Nothing is rewritten.
              </p>
              <div
                data-testid="review-query"
                className="rounded-lg border border-border bg-secondary/40 p-4 text-sm font-mono whitespace-pre-wrap wrap-break-word"
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
                className="mt-5 w-full bg-primary text-primary-foreground font-medium py-2.5 rounded-md hover:bg-primary-hover transition-all active:scale-[0.99] disabled:opacity-60 disabled:cursor-not-allowed disabled:active:scale-100 flex items-center justify-center gap-2"
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
        </div>
      </div>

      {/* Footer nav */}
      <footer className="border-t border-border bg-surface px-6 py-3 flex items-center justify-between">
        <button
          type="button"
          onClick={() => setStep((s) => (s > 0 ? ((s - 1) as StepIndex) : s))}
          disabled={step === 0 || isSubmitting}
          className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-md border border-border hover:bg-secondary disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95 disabled:active:scale-100"
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
            className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary-hover disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95 disabled:active:scale-100"
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

/**
 * Drawn geometry → a bare GeoJSON *geometry* (Point/Polygon), 5-dp WGS84 lon/lat.
 * Returns `null` for an incomplete polygon (<3 vertices) — the same honesty rule as
 * `buildGeometrySuffix`. This is the structured channel sent to `POST /scenario`
 * (a bare geometry, not a Feature, so PostGIS `ST_GeomFromGeoJSON` accepts it directly).
 */
export function drawnGeometryToGeoJSON(
  geometry: DrawnGeometry | null
): ScenarioGeometry | null {
  if (!geometry) return null;
  if (geometry.kind === "point") {
    return { type: "Point", coordinates: geometry.point.map((c) => Number(c.toFixed(5))) };
  }
  if (geometry.vertices.length < 3) return null;
  const ring = geometry.vertices.map((v) => v.map((c) => Number(c.toFixed(5))));
  return { type: "Polygon", coordinates: [[...ring, ring[0]]] };
}

/** Build the GeoJSON Feature object the suffix serializes (for display). */
function geometryFeature(geometry: DrawnGeometry) {
  // For an incomplete polygon drawnGeometryToGeoJSON returns null; display the raw
  // (open) ring in that case so the review panel still shows what was drawn.
  const geo =
    drawnGeometryToGeoJSON(geometry) ??
    (geometry.kind === "polygon"
      ? { type: "Polygon", coordinates: [geometry.vertices.map((v) => v.map((c) => Number(c.toFixed(5))))] }
      : { type: "Point", coordinates: [] });
  return { type: "Feature", geometry: geo, properties: {} };
}

// ── Custom Select Component for theme-friendly styling ──────────────────────

interface CustomSelectOption<T> {
  value: T;
  label: string;
}

interface CustomSelectProps<T> {
  id?: string;
  value: T;
  onChange: (val: T) => void;
  options: CustomSelectOption<T>[];
  ariaLabel?: string;
}

function CustomSelect<T extends string | number>({
  id,
  value,
  onChange,
  options,
  ariaLabel,
}: CustomSelectProps<T>) {
  const [isOpen, setIsOpen] = useState(false);
  const [menuStyle, setMenuStyle] = useState<CSSProperties>({});
  const containerRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (!isOpen || !buttonRef.current) return;

    const updateMenuPosition = () => {
      const rect = buttonRef.current!.getBoundingClientRect();
      setMenuStyle({
        position: "fixed",
        top: rect.bottom + 4,
        left: rect.left,
        width: rect.width,
        zIndex: 200,
      });
    };

    updateMenuPosition();
    window.addEventListener("resize", updateMenuPosition);
    // Repositioning the fixed menu on every scroll frame is jank-prone (and a
    // per-frame scroll handler is banned). The fixed menu would drift from its
    // button on scroll, so close it once instead — native <select> behaves the
    // same. `once` auto-removes the listener after the first scroll.
    const closeOnScroll = () => setIsOpen(false);
    window.addEventListener("scroll", closeOnScroll, { capture: true, once: true });

    return () => {
      window.removeEventListener("resize", updateMenuPosition);
      window.removeEventListener("scroll", closeOnScroll, { capture: true });
    };
  }, [isOpen]);

  const selectedOption = options.find((opt) => opt.value === value);

  return (
    <div ref={containerRef} className={`relative w-full ${isOpen ? "z-20" : ""}`}>
      <button
        ref={buttonRef}
        id={id}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={ariaLabel || "Select option"}
        onClick={() => setIsOpen((prev) => !prev)}
        className="w-full flex items-center justify-between bg-surface border border-border rounded-md px-3 py-2.5 text-sm text-text outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors text-left"
      >
        <span>{selectedOption ? selectedOption.label : String(value)}</span>
        <ChevronDown
          className={`ml-2 h-4 w-4 text-text-muted shrink-0 pointer-events-none transition-transform ${isOpen ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>

      {isOpen && (
        <ul
          role="listbox"
          style={menuStyle}
          className="rounded-md border border-border bg-surface-elevated shadow-lg max-h-60 overflow-y-auto py-1 outline-none animate-in fade-in slide-in-from-top-1 duration-100"
        >
          {options.map((opt) => (
            <li
              key={opt.value}
              role="option"
              aria-selected={opt.value === value}
              onClick={() => {
                onChange(opt.value);
                setIsOpen(false);
              }}
              className={`cursor-pointer select-none px-3 py-2 text-sm transition-colors ${
                opt.value === value
                  ? "bg-primary/10 text-primary font-semibold"
                  : "text-text hover:bg-surface hover:text-primary"
              }`}
            >
              {opt.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}


