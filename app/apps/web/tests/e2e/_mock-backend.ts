/**
 * Deterministic backend mock for the scenario-page e2e (tier-1, no live stack).
 *
 * The scenario page talks to three backend surfaces (all default to :8000):
 *   - WebSocket  ws://localhost:8000/simulate/{id}  — the progressive run stream
 *   - REST       GET /validation                    — validation gates (via apiFetch)
 *   - REST       GET /audit/{runId}                 — public bias-audit log (BiasAuditLog)
 *
 * We intercept all three with Playwright so the e2e is hermetic: no API, no Redis,
 * no SUMO. The frames mirror matrix_api/main.py's EVENT_TYPES order
 * (ACCEPTED → DIMENSION_RESULT* → SYNTHESIS → DONE) and the kernel's result/gate
 * shapes, so the test exercises the REAL reducer + render path against canned data.
 *
 * These values are illustrative fixtures, not sourced numbers — they only prove the
 * UI wiring, never ship.
 */
import type { Page } from "@playwright/test";

/** One canned DIMENSION_RESULT per dimension (shape: matrix_kernel.results.DimensionResult). */
const DIMENSION_RESULTS = [
  { type: "DIMENSION_RESULT", dimension: "behavioral", metric: "Mode shift to transit", value: 12.5, unit: "%", range: [9.0, 16.0], confidence: "M", equation_id: "BEH-1", input_dataset_ids: ["PERSONA-POOL", "OSM-ILO"], assumptions: ["illustrative e2e fixture"], references: [] },
  { type: "DIMENSION_RESULT", dimension: "ecological", metric: "CO2e change", value: -3.2, unit: "t/day", range: [-4.1, -2.3], confidence: "M", equation_id: "ECO-1", input_dataset_ids: ["CCHAIN"], assumptions: [], references: [] },
  { type: "DIMENSION_RESULT", dimension: "social", metric: "Displacement risk count", value: 24, unit: "count", range: [18, 30], confidence: "M", equation_id: "SOC-2", input_dataset_ids: ["CCHAIN", "OSM-ILO"], assumptions: [], references: [] },
  { type: "DIMENSION_RESULT", dimension: "economic", metric: "Footfall Δ per zone", value: 140, unit: "visits/day", range: [110, 170], confidence: "M", equation_id: "ECON-2", input_dataset_ids: ["PERSONA-POOL", "OVERTURE"], assumptions: [], references: [] },
  { type: "DIMENSION_RESULT", dimension: "societal", metric: "Societal composite", value: 68, unit: "0-100", range: [60, 75], confidence: "M", equation_id: "SOCI-1", input_dataset_ids: ["NHCP"], assumptions: [], references: [] },
] as const;

const SYNTHESIS = {
  type: "SYNTHESIS",
  narrative: "Illustrative synthesis for e2e: closing the lane shifts mode share toward transit (BEH-1) and lowers CO2e (ECO-1).",
  citations: [{ equation_id: "BEH-1" }, { equation_id: "ECO-1" }],
} as const;

const DONE = {
  type: "DONE",
  duration_ms: 8200,
  timings: { sumo_ms: 3000, modules_ms: 2000, gemini_ms: 3200, total_ms: 8200 },
} as const;

/** Full canned stream, in server-event order. */
const STREAM: readonly unknown[] = [{ type: "ACCEPTED" }, ...DIMENSION_RESULTS, SYNTHESIS, DONE];

/** GET /validation — two NOT_RUN gates (matrix_kernel.validation.GateResult.to_dict shape). */
const VALIDATION = {
  source: "e2e-fixture",
  note: "Illustrative gates for the mocked e2e run.",
  generated_at: "2026-06-20T00:00:00Z",
  gates: [
    { gate_id: "VAL-01", name: "Behavioral corridor RMSE", metric: "RMSE", value: null, unit: "veh/h", threshold: 0.15, comparator: "<=", status: "NOT_RUN", fixture_id: "calderon2014", fixture_provenance: "Calderon 2014 BRT model", simulated_source: null, threshold_provenance: "QAD VAL-01" },
    { gate_id: "VAL-02", name: "Flood redistribution IoU", metric: "IoU", value: null, unit: "ratio", threshold: 0.5, comparator: ">=", status: "NOT_RUN", fixture_provisional: true, fixture_provenance: "placeholder extent" },
  ],
};

/** GET /audit/{runId} — a within-tolerance log (BiasAuditLog AuditLog shape). */
const AUDIT = {
  run_id: "ref-1-school-molo",
  batch_id: "e2e-fixture",
  target_mode_share: { jeepney: 0.5, tricycle: 0.05, private_car: 0.15, motorcycle: 0.15, walk: 0.1, bicycle: 0.05 },
  observed_mode_share: { jeepney: 0.48, tricycle: 0.05, private_car: 0.17, motorcycle: 0.15, walk: 0.1, bicycle: 0.05 },
  reweighted: false,
  timestamp: "2026-06-20T00:00:00Z",
};

/**
 * Intercept the scenario page's WS + REST surfaces with canned data.
 * Call BEFORE page.goto so the routes/init-script are in place when the page mounts.
 */
export async function mockMatrixBackend(page: Page): Promise<void> {
  // Make the basemap hermetic: abort external OpenFreeMap style/tiles/glyphs so the e2e
  // never waits on (or flakes from) an external host. maplibre handles the fetch error
  // gracefully — the panel under test renders regardless of the map canvas.
  await page.route(/openfreemap\.org/, (route) => route.abort());

  await page.route("**/validation", (route) => route.fulfill({ json: VALIDATION }));
  await page.route("**/audit/**", (route) => route.fulfill({ json: AUDIT }));

  // WebSocket: stub `window.WebSocket` in-page rather than using page.routeWebSocket.
  // routeWebSocket's mock socket wedges context teardown (hangs to the test timeout);
  // a plain in-page fake the page fully owns has no such lifecycle. On a /simulate/ URL
  // it replays the canned frames (open → frames → close) on the next tick — after the
  // page's effect has assigned its on* handlers — and falls back to the real socket for
  // any other URL.
  await page.addInitScript((frames: unknown[]) => {
    const RealWebSocket = window.WebSocket;
    class FakeWebSocket {
      static readonly CONNECTING = 0;
      static readonly OPEN = 1;
      static readonly CLOSING = 2;
      static readonly CLOSED = 3;
      url: string;
      readyState = 0;
      onopen: ((ev: unknown) => void) | null = null;
      onmessage: ((ev: { data: string }) => void) | null = null;
      onclose: ((ev: unknown) => void) | null = null;
      onerror: ((ev: unknown) => void) | null = null;
      constructor(url: string) {
        this.url = url;
        if (!/\/simulate\//.test(url)) {
          return new RealWebSocket(url) as unknown as FakeWebSocket;
        }
        setTimeout(() => {
          this.readyState = 1;
          this.onopen?.({});
          for (const frame of frames) this.onmessage?.({ data: JSON.stringify(frame) });
          this.readyState = 3;
          this.onclose?.({});
        }, 0);
      }
      send(): void {}
      close(): void {
        this.readyState = 3;
        this.onclose?.({});
      }
    }
    window.WebSocket = FakeWebSocket as unknown as typeof WebSocket;
  }, STREAM as unknown[]);
}
