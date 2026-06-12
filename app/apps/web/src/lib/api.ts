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

/**
 * `POST /scenario` — parse a natural-language query into a structured scenario.
 *
 * Throws `AmbiguousScenarioError` when the orchestrator asks for clarification
 * (HTTP 400 + `is_ambiguous`), `ApiUnreachableError` when the API is down, and
 * a plain `Error` for any other non-2xx response.
 */
export async function createScenario(query: string): Promise<ScenarioResponse> {
  const res = await apiFetch("/scenario", {
    method: "POST",
    body: JSON.stringify({ query, input_type: "nl" }),
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
