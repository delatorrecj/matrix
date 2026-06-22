"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

interface AuditLog {
  run_id: string;
  batch_id: string;
  target_mode_share: Record<string, number>;
  observed_mode_share: Record<string, number>;
  reweighted: boolean;
  adjustment_factors?: Record<string, number> | null;
  timestamp: string;
}

export default function BiasAuditLog({ runId }: { runId: string }) {
  const [log, setLog] = useState<AuditLog | null>(null);

  useEffect(() => {
    // Same env-driven origin as every other REST call (NEXT_PUBLIC_API_URL) — never a
    // hardcoded localhost, so the panel works in a deployed build, not just local dev.
    apiFetch(`/audit/${runId}`)
      .then(res => res.json())
      .then(data => setLog(data))
      .catch(console.error);
  }, [runId]);

  if (!log) return <div className="text-sm p-4 text-text-muted animate-pulse">Loading Bias Audit Log...</div>;

  return (
    <div className="border border-border rounded-lg bg-surface p-4 mt-4 text-sm font-mono shadow-sm">
      <div className="flex justify-between items-center mb-4 border-b border-border pb-2">
        <h4 className="font-bold text-foreground">Bias Audit Log (Public)</h4>
        <span className="bg-primary/10 text-primary px-2 py-0.5 rounded text-xs">Run: {log.run_id.substring(0, 8)}</span>
      </div>
      
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <span className="text-text-muted block text-xs uppercase mb-1">Target Mode Share</span>
          {Object.entries(log.target_mode_share).map(([mode, share]) => (
            <div key={mode} className="flex justify-between border-b border-border border-dashed last:border-0 py-1">
              <span>{mode}</span>
              <span>{(share * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>
        <div>
          <span className="text-text-muted block text-xs uppercase mb-1">Observed (Generated)</span>
          {Object.entries(log.observed_mode_share).map(([mode, share]) => (
            <div key={mode} className="flex justify-between border-b border-border border-dashed last:border-0 py-1">
              <span>{mode}</span>
              <span className={Math.abs(share - log.target_mode_share[mode]) > 0.03 ? "text-destructive font-bold" : "text-success"}>
                {(share * 100).toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </div>
      
      <div className="flex justify-between items-center bg-background p-2 rounded border border-border">
        <span className="text-text-muted">Reweight Triggered (±3% tol):</span>
        <span className={log.reweighted ? "text-destructive font-bold" : "text-success font-bold"}>
          {log.reweighted ? "YES" : "NO"}
        </span>
      </div>

      {log.adjustment_factors && Object.keys(log.adjustment_factors).length > 0 && (
        <div className="mt-3 bg-background p-2 rounded border border-border">
          <span className="text-text-muted block text-xs uppercase mb-1">
            Adjustment Factors (f<sub>k</sub> = target / observed)
          </span>
          {Object.entries(log.adjustment_factors).map(([mode, factor]) => (
            <div key={mode} className="flex justify-between border-b border-border border-dashed last:border-0 py-1">
              <span>{mode}</span>
              <span className={factor > 1 ? "text-success" : factor < 1 ? "text-destructive" : ""}>
                ×{factor.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
