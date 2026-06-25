import { DIMENSIONS } from "@/lib/marketing-content";

/**
 * Architecture diagram: input to orchestrator to unified kernel to five
 * modules and synthesis to visualization.
 */
export function ArchitectureDiagram() {
  return (
    <div
      className="overflow-x-auto rounded-2xl border border-border bg-surface p-6 sm:p-8"
      role="img"
      aria-label="MATRIX architecture: user scenario input flows through Azure OpenAI orchestrator to a unified SUMO simulation kernel, then to five parallel impact modules and synthesis, ending at Next.js and Deck.gl visualization"
    >
      <div className="mx-auto flex min-w-[280px] max-w-2xl flex-col items-stretch gap-0">
        <Node label="Input" title="NL query or map drop" />

        <FlowArrow />

        <Node
          label="Orchestrator"
          title="Azure OpenAI gpt-5.4"
          detail="Parse to simulation plan"
          accent
        />

        <FlowArrow />

        <div className="rounded-xl border-2 border-primary/35 bg-primary/5 px-5 py-4 text-center shadow-md shadow-primary/10">
          <p className="text-xs font-medium text-primary">Unified kernel</p>
          <p className="mt-1 text-base font-bold">
            SUMO + Persona Pool + Bias Auditor
          </p>
          <p className="mt-1 text-xs text-text-muted">
            One trajectory dataset, per-agent and per-tick
          </p>
        </div>

        <FlowArrow />

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 sm:gap-2.5">
          {DIMENSIONS.map((d) => (
            <div
              key={d.name}
              className="flex items-center gap-2 rounded-lg border border-border bg-surface-elevated px-3 py-2"
            >
              <span
                className="h-2 w-2 shrink-0 rounded-full"
                style={{ backgroundColor: d.color }}
                aria-hidden="true"
              />
              <span className="text-xs font-semibold">{d.name}</span>
            </div>
          ))}
          <div className="col-span-2 flex items-center justify-center rounded-lg border border-dashed border-border bg-surface-elevated px-3 py-2 sm:col-span-1">
            <span className="text-xs font-semibold">Synthesis agent</span>
          </div>
        </div>

        <FlowArrow />

        <Node
          label="Visualization"
          title="Next.js + Deck.gl"
          detail="Streams trajectories, scores, and brief"
        />
      </div>
    </div>
  );
}

function Node({
  label,
  title,
  detail,
  accent,
}: {
  label: string;
  title: string;
  detail?: string;
  accent?: boolean;
}) {
  return (
    <div
      className={
        accent
          ? "rounded-xl border border-primary/30 bg-primary/10 px-4 py-3 text-center"
          : "rounded-xl border border-border bg-surface-elevated px-4 py-3 text-center"
      }
    >
      <p
        className={
          accent
            ? "text-xs font-medium text-primary"
            : "text-xs font-medium text-text-muted"
        }
      >
        {label}
      </p>
      <p className="mt-1 text-sm font-semibold">{title}</p>
      {detail ? (
        <p className="mt-0.5 text-xs text-text-muted">{detail}</p>
      ) : null}
    </div>
  );
}

function FlowArrow() {
  return (
    <div
      aria-hidden="true"
      className="flex flex-col items-center py-1 text-text-muted"
    >
      <div className="h-3 w-px bg-border" />
      <svg width="10" height="6" viewBox="0 0 10 6" fill="currentColor">
        <path d="M5 6L0 0h10L5 6z" />
      </svg>
    </div>
  );
}
