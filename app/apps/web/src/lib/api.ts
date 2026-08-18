/**
 * Centralized client for the MATRIX FastAPI backend (REST side).
 *
 * Every REST call goes through `apiFetch` so cross-cutting concerns —
 * notably the env-gated API-key header arriving with the auth PR — can be
 * added in exactly one place. The WebSocket stream (`/simulate/{id}`) is
 * owned by the scenario page and uses NEXT_PUBLIC_API_WS_URL instead.
 */

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
).replace(/\/+$/, "");

/** Successful response of `POST /scenario`. */
export interface ScenarioResponse {
  scenario_id: string;
  description: string;
  corridor: string;
  lanes_closed: number;
  raw_input?: string;
  intervention_type?: string | null;
  location?: string | null;
  parameters?: Record<string, unknown>;
}

/** The orchestrator could not parse the query (HTTP 400, `is_ambiguous: true`). */
export class AmbiguousScenarioError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AmbiguousScenarioError";
  }
}

/** The API could not be reached at all (network failure / server down). */
export class ApiUnreachableError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiUnreachableError";
  }
}

/**
 * Thin wrapper around `fetch` for the MATRIX API.
 * Future auth (API-key header) gets wired here — nowhere else.
 */
export async function apiFetch(
  path: string,
  init?: RequestInit
): Promise<Response> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  // NOTE: when env-gated auth lands, add the API-key header here.
  try {
    return await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiUnreachableError(
      `Could not reach the MATRIX API at ${API_BASE_URL}`
    );
  }
}

/** A GeoJSON geometry (Point/Polygon) drawn on the map — the structured map-drop channel. */
export interface ScenarioGeometry {
  type: "Point" | "Polygon";
  coordinates: number[] | number[][][];
}

/**
 * `POST /scenario` — parse a natural-language query into a structured scenario.
 *
 * When a map-drop `geometry` is supplied it is sent as a structured field (NOT folded
 * into the NL string), so the kernel resolves edges from exactly what was drawn — the
 * LLM never originates geometry (PRD-F14). Omitted entirely when absent, so the plain
 * NL path posts `{query, input_type}` unchanged.
 *
 * Throws `AmbiguousScenarioError` when the orchestrator asks for clarification
 * (HTTP 400 + `is_ambiguous`), `ApiUnreachableError` when the API is down, and
 * a plain `Error` for any other non-2xx response.
 */
export async function createScenario(
  query: string,
  geometry?: ScenarioGeometry | null
): Promise<ScenarioResponse> {
  const body: Record<string, unknown> = { query, input_type: "nl" };
  if (geometry) body.geometry = geometry;
  const res = await apiFetch("/scenario", {
    method: "POST",
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    if (res.status === 400 && body?.is_ambiguous) {
      throw new AmbiguousScenarioError(
        body.error ??
          "The scenario query is ambiguous — please add more detail."
      );
    }
    throw new Error(
      body?.error ?? `Scenario request failed (HTTP ${res.status})`
    );
  }

  return res.json();
}

/** A saved scenario's parsed fields, as returned by `GET /scenario/{id}`. */
export interface ScenarioRecord {
  scenario_id: string;
  description: string;
  /** Planner's original NL query from POST /scenario. */
  raw_input?: string;
  intervention_type: string | null;
  location: string | null;
  /** Scenario.parameters (facility kind/capacity, lanes_closed, …). */
  parameters?: Record<string, unknown>;
  geometry: ScenarioGeometry | null;
  /** Gazetteer/map-drop [lon, lat]; the results map does not pan from this field. */
  location_of_interest?: [number, number] | null;
}

/**
 * `GET /scenario/{id}` — fetch a previously parsed scenario's fields
 * (`location`/`geometry`). Throws `ApiUnreachableError` when the API is down, and a plain
 * `Error` for any other non-2xx response (including a 404).
 */
export async function getScenario(scenarioId: string): Promise<ScenarioRecord> {
  const res = await apiFetch(`/scenario/${scenarioId}`);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error ?? `Scenario lookup failed (HTTP ${res.status})`);
  }
  return res.json();
}

/** One dimension result as returned by `GET /runs/{id}` / `latest-run`. */
export interface StoredDimensionResult {
  dimension: string;
  metric: string;
  equation_id: string;
  value: number;
  range: [number, number] | number[];
  unit: string;
  confidence: string;
  directional?: boolean;
  input_dataset_ids?: string[];
  references?: string[];
  assumptions?: string[];
}

/** Completed run payload for hydrate-on-reload (no re-SUMO). */
export interface LatestRunRecord {
  run_id: string;
  scenario_id: string;
  status: string;
  duration_ms?: number | null;
  timings?: Record<string, number> | null;
  affected_edges?: string[] | null;
  edge_resolution?: string | null;
  results: StoredDimensionResult[];
  playback?: {
    edge_counts: Record<string, number>;
    frames: Array<{ tick: number; agents: Array<{ id: string; lon: number; lat: number }> }>;
    affected_edges?: string[] | null;
    edge_resolution?: string | null;
  } | null;
}

/**
 * `GET /scenarios/{id}/latest-run` — most recent *done* run for this scenario.
 * Returns `null` on 404 (no completed run yet). Throws on other failures / unreachable.
 */
export async function getLatestRun(
  scenarioId: string
): Promise<LatestRunRecord | null> {
  const res = await apiFetch(
    `/scenarios/${encodeURIComponent(scenarioId)}/latest-run`
  );
  if (res.status === 404) return null;
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error ?? `Latest run lookup failed (HTTP ${res.status})`);
  }
  return res.json();
}
