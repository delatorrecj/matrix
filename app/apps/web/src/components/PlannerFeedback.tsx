"use client";

import { useState } from "react";
import { submitPlannerFeedback } from "@/lib/api";

type Props = {
  runId: string | null;
  equationId: string | null;
};

/** PRD-F20 — planner plausible/implausible feedback on a glass-box result. */
export function PlannerFeedback({ runId, equationId }: Props) {
  const [verdict, setVerdict] = useState<"plausible" | "implausible" | "">("");
  const [note, setNote] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  if (!runId || !equationId) return null;

  async function handleSubmit(next: "plausible" | "implausible") {
    setVerdict(next);
    setStatus("sending");
    try {
      await submitPlannerFeedback({
        run_id: runId!,
        equation_id: equationId!,
        verdict: next,
        note: note.trim(),
      });
      setStatus("sent");
    } catch {
      setStatus("error");
    }
  }

  return (
    <section className="space-y-3 pt-4 border-t border-border/50">
      <h4 className="text-sm font-medium text-text-muted uppercase tracking-wider">
        Planner feedback
      </h4>
      <p className="text-xs text-text-muted">
        Flag this result for CPDO triage (PRD-F20). Feedback is persisted on the run record.
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={status === "sending"}
          onClick={() => void handleSubmit("plausible")}
          className={`flex-1 py-2 text-xs font-semibold rounded-md border transition-colors ${
            verdict === "plausible"
              ? "border-success bg-success/10 text-success"
              : "border-border hover:bg-surface-elevated"
          }`}
        >
          Plausible
        </button>
        <button
          type="button"
          disabled={status === "sending"}
          onClick={() => void handleSubmit("implausible")}
          className={`flex-1 py-2 text-xs font-semibold rounded-md border transition-colors ${
            verdict === "implausible"
              ? "border-error bg-error/10 text-error"
              : "border-border hover:bg-surface-elevated"
          }`}
        >
          Implausible
        </button>
      </div>
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Optional note or observed value context"
        rows={2}
        className="w-full text-xs rounded-md border border-border bg-surface px-2 py-1.5 resize-none"
      />
      {status === "sent" && (
        <p className="text-xs text-success">Feedback saved. Thank you.</p>
      )}
      {status === "error" && (
        <p className="text-xs text-error">Could not save feedback. Try again.</p>
      )}
    </section>
  );
}
