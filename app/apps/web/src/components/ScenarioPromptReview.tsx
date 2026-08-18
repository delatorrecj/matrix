"use client";

const TYPE_LABELS: Record<string, string> = {
  lane_closure: "Lane closure",
  full_closure: "Full closure",
  speed_change: "Speed change",
  capacity_change: "Capacity change",
  new_facility: "New facility",
};

const KIND_UNITS: Record<string, string> = {
  school: "seats",
  market: "stalls",
  terminal: "bays",
};

export function formatScenarioPlan(opts: {
  interventionType?: string | null;
  location?: string | null;
  parameters?: Record<string, unknown> | null;
}): string | null {
  const bits: string[] = [];
  const type = opts.interventionType?.trim();
  if (type) bits.push(TYPE_LABELS[type] ?? type.replace(/_/g, " "));
  const location = opts.location?.trim();
  if (location) bits.push(location);
  const params = opts.parameters ?? {};
  const kind = typeof params.facility_kind === "string" ? params.facility_kind : "";
  if (kind) bits.push(kind);
  const capacity = typeof params.capacity === "number" ? params.capacity : Number(params.capacity);
  if (Number.isFinite(capacity) && capacity > 0) {
    const unit = KIND_UNITS[kind] ?? "";
    bits.push(unit ? `${capacity.toLocaleString("en-US")} ${unit}` : capacity.toLocaleString("en-US"));
  }
  return bits.length > 0 ? bits.join(" · ") : null;
}

/**
 * Original NL query + parsed intervention, so the results dock still shows
 * what the planner asked after the run narrative takes over.
 */
export function ScenarioPromptReview({
  rawInput,
  description,
  interventionType,
  location,
  parameters,
}: {
  rawInput?: string | null;
  description?: string | null;
  interventionType?: string | null;
  location?: string | null;
  parameters?: Record<string, unknown> | null;
}) {
  const question = (rawInput?.trim() || description?.trim() || "");
  const plan = formatScenarioPlan({ interventionType, location, parameters });
  if (!question && !plan) return null;

  return (
    <div
      className="rounded-xl border border-border bg-surface-elevated/50 px-3 py-2.5"
      data-testid="scenario-prompt-review"
    >
      {question ? (
        <div>
          <p className="text-[10px] uppercase tracking-wider text-text-muted font-medium">
            Your question
          </p>
          <p className="mt-0.5 text-sm leading-relaxed text-foreground">{question}</p>
        </div>
      ) : null}
      {plan ? (
        <div className={question ? "mt-2" : undefined}>
          <p className="text-[10px] uppercase tracking-wider text-text-muted font-medium">
            Plan
          </p>
          <p className="mt-0.5 text-sm text-foreground">{plan}</p>
        </div>
      ) : null}
    </div>
  );
}
