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
// Aligned with the CR-010 metric registry (src/lib/metrics.ts): equation ids carry
// their real metric names/units/magnitudes so the Summary formatter produces sensible
// humanized output (e.g. BEH-1 = trips, not %).
const DIMENSION_RESULTS = [
  { type: "DIMENSION_RESULT", dimension: "behavioral", metric: "Δ trips on affected corridor (AM-peak)", value: -14, unit: "trips/window", range: [-17, -10], confidence: "L", directional: true, equation_id: "BEH-1", input_dataset_ids: ["PERSONA-POOL", "OSM-ILO"], assumptions: ["confidence capped at L: VAL-01 published FAIL — corridor volumes are directional, not city-calibrated"], references: [] },
  { type: "DIMENSION_RESULT", dimension: "ecological", metric: "Transport CO₂e Δ", value: -0.05, unit: "ktCO₂e/yr", range: [-0.08, -0.03], confidence: "M", equation_id: "ECO-1", input_dataset_ids: ["CCHAIN"], assumptions: [], references: [] },
  { type: "DIMENSION_RESULT", dimension: "social", metric: "Displacement risk count", value: 12, unit: "count", range: [10, 14], confidence: "H", equation_id: "SOC-2", input_dataset_ids: ["CCHAIN", "OSM-ILO"], assumptions: [], references: [] },
  { type: "DIMENSION_RESULT", dimension: "economic", metric: "Footfall Δ per zone", value: -16.8, unit: "visits/day", range: [-20, -13], confidence: "H", equation_id: "ECON-2", input_dataset_ids: ["PERSONA-POOL", "OVERTURE"], assumptions: [], references: [] },
  { type: "DIMENSION_RESULT", dimension: "societal", metric: "Societal composite", value: -0.5, unit: "0-100", range: [-0.8, -0.2], confidence: "M", equation_id: "SOCI-1", input_dataset_ids: ["NHCP"], assumptions: [], references: [] },
] as const;

// CR-010: a plain-language BLUF brief, bilingual by the `=== HILIGAYNON ===` delimiter
// (English first, then the marker, then Hiligaynon). Numbers carry inline [EQN-ID]
// citations exactly as the kernel's citation guard requires.
const SYNTHESIS = {
  type: "SYNTHESIS",
  narrative: [
    "HEADLINE",
    "Closing the lane eases the morning rush but trims local footfall; proceed with support for affected businesses.",
    "",
    "WHAT WE SIMULATED",
    "A lane closure on the affected corridor near the Molo school.",
    "",
    "KEY FINDINGS",
    "Morning traffic on the affected road eases, with trips falling by 14 [BEH-1].",
    "",
    "RECOMMENDATION",
    "Proceed with the closure, paired with footfall support for nearby businesses.",
    "",
    "KEY RISK",
    "A small number of nearby businesses may see fewer visitors.",
    "",
    "=== HILIGAYNON ===",
    "HEADLINE",
    "Ang pagsira sang dalan nagapahapos sang trapiko sa aga; padayuna upod ang bulig sa mga negosyo.",
    "",
    "KEY FINDINGS",
    "Nagnubo ang biyahe sa dalan sang 14 [BEH-1].",
  ].join("\n"),
  citations: [{ equation_id: "BEH-1" }, { equation_id: "ECO-1" }],
} as const;

const DONE = {
  type: "DONE",
  duration_ms: 8200,
  timings: { sumo_ms: 3000, modules_ms: 2000, llm_ms: 3200, total_ms: 8200 },
} as const;

/** Full canned stream, in server-event order. */
const STREAM: readonly unknown[] = [{ type: "ACCEPTED" }, ...DIMENSION_RESULTS, SYNTHESIS, DONE];

/** GET /validation — VAL-01 published FAIL matches the live ledger shape. */
const VALIDATION = {
  source: "e2e-fixture",
  note: "Illustrative gates for the mocked e2e run.",
  generated_at: "2026-08-16T06:22:55Z",
  gates: [
    {
      gate_id: "VAL-01",
      name: "Behavioral corridor back-test (Calderon 2014, Ungka–Iloilo corridors)",
      metric: "normalized_rmse",
      value: 4.738583,
      unit: "fraction of mean observed volume",
      threshold: 0.3,
      comparator: "<=",
      status: "FAIL",
      fixture_id: "LIT-CALDERON",
      fixture_provenance: "Calderon et al. (2014, TSSP) JICA STRADA 3 transit-model values.",
      fixture_provisional: false,
      simulated_source: "live-baseline:redis",
      n_points: 2,
      threshold_provenance: "FHWA Travel Model Validation Manual (2nd ed., 2010).",
      notes: "published FAIL — uncalibrated demand; corridor volumes are directional",
    },
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
