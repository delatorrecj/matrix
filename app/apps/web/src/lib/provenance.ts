/**
 * Build fully enriched ProvenanceData for the Inspect drawer.
 *
 * Merges live WebSocket fields with static equation/dataset registries
 * (methods-matrix §3 + INVENTORY). Never invents computed values.
 */

import type { ProvenanceData } from "@/components/InspectDrawer";
import { getEquationText } from "@/lib/equations";
import { resolveDatasetInputs } from "@/lib/datasets";

export interface ProvenanceWireFields {
  metric: string;
  value: string;
  range: string;
  confidence: string;
  equationId: string;
  input_dataset_ids: string[];
  assumptions: string[];
  references: string[];
  confidenceBasis?: string;
  applicability?: string;
}

export function buildProvenanceData(fields: ProvenanceWireFields): ProvenanceData {
  return {
    metric: fields.metric,
    value: fields.value,
    range: fields.range,
    confidence: fields.confidence,
    confidenceBasis:
      fields.confidenceBasis ?? "Computed from input dataset confidences per methods §2",
    equationId: fields.equationId,
    equationText: getEquationText(fields.equationId),
    inputs: resolveDatasetInputs(fields.input_dataset_ids),
    assumptions: fields.assumptions,
    references: fields.references,
    applicability: fields.applicability,
  };
}

/** Panel width constants — keep map padding in sync with results panel. */
export const PANEL_WIDTH = {
  summary: { md: 360, lg: 400 },
  analytics: { md: 680, lg: 860 },
  navRail: 64,
} as const;

export function mapPaddingRight(
  showResultsPanel: boolean,
  panelView: "summary" | "analytics"
): number {
  if (!showResultsPanel) return 0;
  // Tailwind md/lg breakpoints — use lg width when panel is open (conservative centering).
  return panelView === "analytics" ? PANEL_WIDTH.analytics.lg : PANEL_WIDTH.summary.lg;
}

/** Short header chip label — avoids crushing the panel title on narrow widths. */
export function statusChipLabel(state: import("@/lib/simulationRun").RunState): string {
  switch (state.phase) {
    case "connecting":
      return "Connecting…";
    case "queued":
      return state.queuePosition !== null ? `Queued #${state.queuePosition}` : "Queued";
    case "running":
      return "Running…";
    case "done":
      return "Done";
    case "error":
      return "Error";
    case "cancelled":
      return "Cancelled";
    case "disconnected":
      return state.wsOpened ? "Disconnected" : "Unreachable";
  }
}
