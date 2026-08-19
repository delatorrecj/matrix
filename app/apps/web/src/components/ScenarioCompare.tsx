"use client";

import { useState } from "react";
import { compareScenarios, type LatestRunRecord } from "@/lib/api";
import { DIMENSION_LABELS } from "@/lib/metrics";

type Props = {
  scenarioId: string;
};

function firstBehavioralValue(run: LatestRunRecord | null): number | null {
  if (!run?.results?.length) return null;
  const beh = run.results.find((r) => r.dimension === "behavioral");
  if (!beh || typeof beh.value !== "number") return null;
  return beh.value;
}

/** Side-by-side latest runs for decision-intelligence compare (Phase 5). */
export function ScenarioCompare({ scenarioId }: Props) {
  const [otherId, setOtherId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [a, setA] = useState<LatestRunRecord | null>(null);
  const [b, setB] = useState<LatestRunRecord | null>(null);

  async function handleCompare() {
    const trimmed = otherId.trim();
    if (!trimmed || trimmed === scenarioId) {
      setError("Enter a different scenario id to compare.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const pair = await compareScenarios(scenarioId, trimmed);
      setA(pair.a);
      setB(pair.b);
      if (!pair.a && !pair.b) {
        setError("Neither scenario has a completed run yet.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Compare failed");
      setA(null);
      setB(null);
    } finally {
      setLoading(false);
    }
  }

  const valA = firstBehavioralValue(a);
  const valB = firstBehavioralValue(b);
  const delta =
    valA !== null && valB !== null ? valB - valA : null;

  return (
    <section
      className="rounded-lg border border-border p-4 space-y-3"
      data-testid="scenario-compare"
    >
      <h3 className="text-sm font-semibold">Compare scenarios</h3>
      <p className="text-xs text-text-muted">
        Side-by-side latest completed runs (same glass-box results as Inspect).
      </p>
      <div className="flex flex-col sm:flex-row gap-2">
        <input
          type="text"
          value={otherId}
          onChange={(e) => setOtherId(e.target.value)}
          placeholder="Other scenario id"
          className="flex-1 text-xs rounded-md border border-border bg-surface px-2 py-1.5 font-mono"
        />
        <button
          type="button"
          disabled={loading}
          onClick={() => void handleCompare()}
          className="text-xs px-3 py-1.5 rounded-md bg-primary text-primary-foreground font-medium disabled:opacity-50"
        >
          {loading ? "Loading…" : "Compare"}
        </button>
      </div>
      {error && <p className="text-xs text-error">{error}</p>}
      {(a || b) && (
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="rounded border border-border p-2">
            <p className="font-mono truncate" title={scenarioId}>
              A: {scenarioId}
            </p>
            <p className="text-text-muted mt-1">
              {a ? `${a.results?.length ?? 0} results` : "No completed run"}
            </p>
            {valA !== null && (
              <p className="mt-1">
                {DIMENSION_LABELS.behavioral}: {valA}
              </p>
            )}
          </div>
          <div className="rounded border border-border p-2">
            <p className="font-mono truncate" title={otherId.trim()}>
              B: {otherId.trim()}
            </p>
            <p className="text-text-muted mt-1">
              {b ? `${b.results?.length ?? 0} results` : "No completed run"}
            </p>
            {valB !== null && (
              <p className="mt-1">
                {DIMENSION_LABELS.behavioral}: {valB}
              </p>
            )}
          </div>
        </div>
      )}
      {delta !== null && (
        <p className="text-xs font-medium">
          Behavioral delta (B − A): {delta > 0 ? "+" : ""}
          {delta}
        </p>
      )}
    </section>
  );
}
