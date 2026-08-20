import { AlertCircle, CheckCircle2, HelpCircle, MinusCircle } from "lucide-react";

export type ConfidenceLevel = "High" | "Medium" | "Low" | "N/A";
export type Applicability = "computed" | "not_modeled" | "not_applicable";

/**
 * Map the kernel's confidence letter ("H"/"M"/"L", what the stream carries) or a
 * full word onto the chip vocabulary. Single source of truth so every surface
 * renders confidence identically (anything unknown is the honest Low default,
 * never a guessed High).
 */
export function toConfidenceLevel(confidence: string | undefined): ConfidenceLevel {
  if (confidence === "H" || confidence === "High") return "High";
  if (confidence === "M" || confidence === "Medium") return "Medium";
  if (confidence === "N/A" || confidence === "NA") return "N/A";
  return "Low";
}

/** Chip level: N/A when the equation did not run; otherwise H/M/L. */
export function chipLevel(
  confidence: string | undefined,
  applicability?: string | null,
): ConfidenceLevel {
  if (applicability === "not_modeled" || applicability === "not_applicable") return "N/A";
  return toConfidenceLevel(confidence);
}

export function applicabilityLabel(applicability?: string | null): string | null {
  if (applicability === "not_modeled") return "Not modeled";
  if (applicability === "not_applicable") return "Not applicable to this intervention";
  return null;
}

interface ConfidenceChipProps {
  level: ConfidenceLevel;
  reason?: string;
  /** Compact = single-letter glyph (H/M/L) for dense card headers. */
  compact?: boolean;
  className?: string;
}

export function ConfidenceChip({ level, reason, compact = false, className = "" }: ConfidenceChipProps) {
  const isHigh = level === "High";
  const isMedium = level === "Medium";
  const isNA = level === "N/A";

  // print:* keeps the chip legible in the "Download Brief" PDF (the scenario page
  // is the only print surface; the rules are inert on screen).
  const baseClasses =
    "inline-flex items-center gap-1 px-1.5 py-0.5 rounded-sm text-[10px] uppercase tracking-wider font-semibold border print:bg-white print:text-black print:border-black print:border-solid";

  let styles = "";
  let Icon = HelpCircle;

  if (isNA) {
    styles = "bg-surface text-text-muted border-border";
    Icon = MinusCircle;
  } else if (isHigh) {
    styles = "bg-success/10 text-success border-success/20";
    Icon = CheckCircle2;
  } else if (isMedium) {
    styles = "bg-warning/10 text-warning border-warning/30 border-dashed";
    Icon = AlertCircle;
  } else {
    styles = "bg-error/10 text-error border-error/30 border-dashed opacity-80";
    Icon = AlertCircle;
  }

  const compactLabel = isNA ? "N/A" : level[0];

  return (
    <div className={`${baseClasses} ${styles} ${className}`} title={reason}>
      <Icon className="w-3 h-3" aria-hidden="true" />
      {compact ? compactLabel : level}
    </div>
  );
}
