"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

/**
 * Validation & back-testing panel (PRD-F18, QAD VAL-01/02).
 *
 * Fetches `GET /validation` and renders the kernel's computed gate results —
 * no hardcoded numbers (anti-validation-theater). A gate that has not run is
 * shown honestly as NOT RUN with its reason; a provisional fixture carries a
 * visible PROVISIONAL badge. Field shapes mirror
 * `matrix_kernel/validation.py::GateResult.to_dict()`.
 */
export interface ValidationGate {
  gate_id: string;
  name: string;
  metric: string;
  value: number | null;
  unit: string;
  threshold: number;
  comparator: "<=" | ">=";
  status: "PASS" | "FAIL" | "NOT_RUN";
  fixture_id?: string;
  fixture_provenance?: string;
  fixture_provisional?: boolean;
  /** Tolerated alternate key for the provisional flag. */
  provisional?: boolean;
  simulated_source?: string | null;
  n_points?: number;
  threshold_provenance?: string;
  details?: Record<string, unknown>;
  notes?: string;
}

interface ValidationResponse {
  gates?: ValidationGate[];
  source?: string;
  note?: string;
  generated_at?: string;
}

type PanelState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "loaded";
      gates: ValidationGate[];
      note?: string;
      source?: string;
      generatedAt?: string;
    };

const STATUS_STYLES: Record<ValidationGate["status"], string> = {
  PASS: "bg-success/15 text-success border border-success/30",
  FAIL: "bg-error/15 text-error border border-error/30",
  NOT_RUN: "bg-secondary text-text-muted border border-border",
};

function comparatorGlyph(comparator: ValidationGate["comparator"]): string {
  return comparator === "<=" ? "≤" : "≥";
}

function isProvisional(gate: ValidationGate): boolean {
  return Boolean(gate.fixture_provisional ?? gate.provisional);
}

function GateCard({ gate }: { gate: ValidationGate }) {
  return (
    <div
      className="p-3 bg-background border border-border rounded"
      data-testid={`gate-${gate.gate_id}`}
    >
      <div className="flex justify-between items-start gap-2 mb-1">
        <span className="text-sm font-bold text-foreground">
          {gate.name}
          <span className="ml-1 font-mono font-normal text-xs text-text-muted">
            {gate.gate_id}
          </span>
        </span>
        <span className="flex items-center gap-1 shrink-0">
          {isProvisional(gate) && (
            <span
              className="text-[10px] font-mono bg-warning/15 text-warning border border-warning/30 border-dashed px-1.5 py-0.5 rounded uppercase"
              title="Computed against a provisional fixture — not publishable as validation."
              data-testid={`provisional-${gate.gate_id}`}
            >
              Provisional
            </span>
          )}
          <span
            // Wire JSON is unvalidated — an unknown status falls back to the
            // neutral style rather than an "undefined" class.
            className={`text-xs font-mono px-2 py-0.5 rounded ${STATUS_STYLES[gate.status] ?? STATUS_STYLES.NOT_RUN}`}
            data-testid={`status-${gate.gate_id}`}
          >
            {gate.status === "NOT_RUN" ? "NOT RUN" : gate.status}
          </span>
        </span>
      </div>

      <div className="flex justify-between text-xs font-mono mb-1">
        <span>
          {gate.metric}:{" "}
          {gate.value === null || gate.value === undefined ? (
            <span className="italic text-text-muted font-sans">not computed</span>
          ) : (
            gate.value
          )}
        </span>
        <span title={gate.threshold_provenance || undefined}>
          threshold {comparatorGlyph(gate.comparator)} {gate.threshold}
        </span>
      </div>
      <p className="text-[10px] text-text-muted mb-2">{gate.unit}</p>

      {gate.notes && <p className="text-xs italic text-text-muted mb-2">{gate.notes}</p>}

      <p
        className="text-[11px] text-text-muted line-clamp-2"
        title={gate.fixture_provenance || undefined}
      >
        {gate.fixture_provenance || (
          <span className="italic">fixture provenance not provided</span>
        )}
      </p>

      <details className="mt-1 text-[11px]">
        <summary className="cursor-pointer text-text-muted hover:text-foreground">
          Full provenance
        </summary>
        <dl className="mt-1 space-y-1 text-text-muted">
          <div>
            <dt className="inline font-semibold">Fixture: </dt>
            <dd className="inline">
              {gate.fixture_id || "not provided"} — {gate.fixture_provenance || "not provided"}
            </dd>
          </div>
          <div>
            <dt className="inline font-semibold">Threshold: </dt>
            <dd className="inline">{gate.threshold_provenance || "not provided"}</dd>
          </div>
          <div>
            <dt className="inline font-semibold">Simulated source: </dt>
            <dd className="inline">{gate.simulated_source || "none (gate not run)"}</dd>
          </div>
          {typeof gate.n_points === "number" && (
            <div>
              <dt className="inline font-semibold">Observation points: </dt>
              <dd className="inline">{gate.n_points}</dd>
            </div>
          )}
        </dl>
      </details>
    </div>
  );
}

export default function ValidationPanel() {
  const [state, setState] = useState<PanelState>({ status: "loading" });

  const load = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const res = await apiFetch("/validation");
      if (!res.ok) {
        throw new Error(`Validation request failed (HTTP ${res.status})`);
      }
      const body: ValidationResponse = await res.json();
      setState({
        status: "loaded",
        gates: Array.isArray(body.gates) ? body.gates : [],
        note: body.note,
        source: body.source,
        generatedAt: body.generated_at,
      });
    } catch (err) {
      setState({
        status: "error",
        message: err instanceof Error ? err.message : String(err),
      });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="border border-border rounded-lg bg-surface p-4 mt-4 shadow-sm">
      <div className="border-b border-border pb-2 mb-3">
        <h4 className="font-bold text-foreground text-sm uppercase tracking-wider">
          Validation & Back-Testing
        </h4>
      </div>

      {state.status === "loading" && (
        <p className="text-sm text-text-muted animate-pulse" data-testid="validation-loading">
          Loading validation gates…
        </p>
      )}

      {state.status === "error" && (
        <div className="text-sm" data-testid="validation-error">
          <p className="text-error mb-1">Could not load validation gates.</p>
          <p className="text-xs font-mono text-text-muted mb-2">{state.message}</p>
          <button
            type="button"
            onClick={() => void load()}
            className="text-xs px-2 py-1 rounded border border-border text-text-muted hover:border-primary hover:text-primary transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {state.status === "loaded" && state.gates.length === 0 && (
        <div className="text-sm text-text-muted" data-testid="validation-empty">
          <p>No validation gates reported — validation has not yet been run.</p>
          {state.note && <p className="text-xs italic mt-1">{state.note}</p>}
        </div>
      )}

      {state.status === "loaded" && state.gates.length > 0 && (
        <div className="space-y-4">
          {state.gates.map((gate) => (
            <GateCard key={gate.gate_id} gate={gate} />
          ))}
          {(state.note || state.source || state.generatedAt) && (
            <p className="text-[11px] text-text-muted italic" data-testid="validation-note">
              {[
                state.note,
                state.source && `source: ${state.source}`,
                state.generatedAt && `generated: ${state.generatedAt}`,
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
