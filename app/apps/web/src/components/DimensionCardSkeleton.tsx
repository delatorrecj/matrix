/**
 * Skeleton placeholder for a dimension whose DIMENSION_RESULT events have not
 * arrived yet. Glass-box rule (PRD-F14): never render placeholder numbers as if
 * they were real values — only neutral pulse blocks and an explicit "awaiting"
 * label (the expected-result count is pipeline metadata, not a metric value).
 *
 * `active=false` (run ended: done / error / cancelled / disconnected) stops the
 * pulse and relabels honestly — nothing is "awaited" once the stream is over.
 */
interface DimensionCardSkeletonProps {
  name: string;
  /** Tailwind bg-* class for the dimension hue dot (matches the result cards). */
  colorClass: string;
  expectedResults: number;
  /** Whether the run is still streaming (default true). */
  active?: boolean;
}

export default function DimensionCardSkeleton({
  name,
  colorClass,
  expectedResults,
  active = true,
}: DimensionCardSkeletonProps) {
  return (
    <div
      className="border border-dashed border-border rounded-lg p-4 bg-surface"
      data-testid={`skeleton-${name}`}
      aria-label={
        active
          ? `${name} dimension awaiting results`
          : `${name} dimension received no results`
      }
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full opacity-40 ${colorClass}`} />
          <span className="text-sm font-medium capitalize text-text-muted">
            {name}
          </span>
        </div>
        <span className="text-[10px] uppercase tracking-wider text-text-muted font-mono">
          {active
            ? `Awaiting ${expectedResults} result${expectedResults === 1 ? "" : "s"}`
            : "No results received"}
        </span>
      </div>
      <div className={`space-y-2${active ? " animate-pulse" : ""}`} aria-hidden="true">
        <div className="h-6 w-24 rounded bg-secondary" />
        <div className="h-3 w-36 rounded bg-secondary" />
      </div>
    </div>
  );
}
